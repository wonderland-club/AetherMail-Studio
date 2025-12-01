"""蛋白质摄入估算模板（按8个模块计算）"""
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


TEMPLATE_ID = "protein_calculation"
DESCRIPTION = "蛋白质摄入估算与建议（基于身高、体重、活动、目标、肾功能、孕/哺乳状态）"
DEFAULT_SUBJECT = "蛋白质摄入建议"
REQUIRED_FIELDS = ["height_cm", "weight_kg", "activity_level", "goal", "kidney_status"]


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _calc_weight_eff(height_cm: float, weight_kg: float) -> Tuple[float, float, float, float, str]:
    """模块0：有效体重，返回 (height_m, BMI, weight_eff, weight_ideal, note)"""
    height_m = height_cm / 100.0
    if height_m <= 0:
        raise ValueError("请提供有效的身高")
    bmi = weight_kg / (height_m ** 2)
    weight_ideal = 22 * height_m * height_m
    if bmi >= 27:
        weight_eff = weight_ideal + 0.4 * (weight_kg - weight_ideal)
        note = f"BMI≥27，按理想体重 {weight_ideal:.1f} kg + 超出部分40% 折算"
    else:
        weight_eff = weight_kg
        note = "BMI<27，直接使用真实体重"
    return height_m, bmi, weight_eff, weight_ideal, note


def _coef_base(age: Optional[int]) -> float:
    """模块1：基础蛋白系数（按年龄）"""
    if age is not None and age >= 60:
        return 1.0
    return 0.8


_ACTIVITY_COEF = {
    "sedentary": 1.0,
    "light": 1.1,
    "moderate": 1.4,
    "high": 1.8,
}

_ACTIVITY_LABEL = {
    "sedentary": "几乎不运动（久坐为主，很少进行锻炼）",
    "light": "每周 1–2 次轻度运动（散步/轻瑜伽等）",
    "moderate": "每周 3–5 次中等强度运动（常规力量/有氧）",
    "high": "每周 5 次以上高强度运动 / 运动员级训练",
}


def _apply_activity(coef_base: float, level: str) -> Tuple[float, float, str]:
    """模块2：活动水平调整，返回 (k_activity, coef_after_act, label)"""
    key = (level or "").lower()
    if key not in _ACTIVITY_COEF:
        key = "moderate"
    k_activity = _ACTIVITY_COEF[key]
    return k_activity, coef_base * k_activity, _ACTIVITY_LABEL.get(key, key)


def _adjust_by_goal(coef_after_act: float, goal: str) -> float:
    """模块3：目标导向调整"""
    g = (goal or "").lower()
    coef = coef_after_act

    if g == "maintain":
        return coef
    if g == "fat_loss":
        coef *= 1.15
        coef = max(coef, 1.2)
        coef = min(coef, 2.0)
        return coef
    if g == "muscle_gain":
        coef *= 1.20
        coef = max(coef, 1.6)
        coef = min(coef, 2.0)
        return coef

    # 其他目标：中等偏高
    coef *= 1.15
    coef = max(coef, 1.4)
    coef = min(coef, 2.0)
    return coef


def _kidney_mode(status: str, on_dialysis: Optional[bool]) -> str:
    """将表单字段归一化到 none/ckd/dialysis"""
    st = (status or "").lower()
    if st == "none" or not st:
        return "none"
    if st == "ckd":
        if on_dialysis is True:
            return "dialysis"
        return "ckd"
    return "none"


def _adjust_by_kidney(coef_goal: float, mode: str) -> float:
    """模块4：肾功能修正"""
    if mode == "none":
        return coef_goal
    if mode == "ckd":
        return min(max(coef_goal, 0.6), 0.8)
    if mode == "dialysis":
        return min(max(coef_goal, 1.0), 1.2)
    return coef_goal


def _extra_preg_lact(
    sex: str,
    female_stage: str,
    preg_trimester: Optional[str],
    lact_stage: Optional[str],
    kidney_mode: str,
) -> float:
    """模块5：孕期/哺乳额外克数"""
    if sex != "female":
        return 0.0
    if kidney_mode in ("ckd", "dialysis"):
        return 0.0

    if female_stage == "pregnant":
        if preg_trimester == "T1":
            return 1.0
        if preg_trimester == "T2":
            return 9.0
        if preg_trimester == "T3":
            return 28.0
        return 0.0

    if female_stage == "lactating":
        if lact_stage == "L1":
            return 19.0
        if lact_stage == "L2":
            return 13.0
        return 0.0

    return 0.0


def _coef_limits(kidney_mode: str, age: Optional[int]) -> Tuple[float, float]:
    """模块6：系数上下限"""
    age_val = age if age is not None else 30
    if kidney_mode == "none":
        coef_min = 1.0 if age_val >= 60 else 0.8
        coef_max = 2.0
    elif kidney_mode == "ckd":
        coef_min, coef_max = 0.6, 0.8
    else:  # dialysis
        coef_min, coef_max = 1.0, 1.5
    return coef_min, coef_max


def _diet_label(diet_type: str) -> str:
    key = (diet_type or "").lower()
    mapping = {
        "omnivore": "不忌口（荤素均衡）",
        "lacto_ovo": "蛋奶素",
        "vegan": "纯素",
    }
    return mapping.get(key, diet_type or "未提供")


def _goal_label(goal: str) -> str:
    mapping = {
        "fat_loss": "减脂（减重）",
        "muscle_gain": "增肌（力量/体重提升）",
        "maintain": "维持当前体重与健康",
    }
    return mapping.get(goal, goal or "未提供")


def _sex_text(sex: str) -> str:
    if sex == "male":
        return "男性"
    if sex == "female":
        return "女性"
    return "未提供"


def _preg_lact_note(sex: str, female_stage: str, preg_trimester: Optional[str], lact_stage: Optional[str]) -> str:
    if sex != "female":
        return "非女性，无孕/哺乳状态"
    if female_stage == "pregnant":
        if preg_trimester == "T1":
            return "孕期：早孕（T1）"
        if preg_trimester == "T2":
            return "孕期：中孕（T2）"
        if preg_trimester == "T3":
            return "孕期：晚孕（T3）"
        return "孕期：未说明孕周"
    if female_stage == "lactating":
        if lact_stage == "L1":
            return "哺乳期：产后 0–6 个月（L1）"
        if lact_stage == "L2":
            return "哺乳期：产后 6 个月后（L2）"
        return "哺乳期：未说明阶段"
    return "女性，未处于孕/哺乳期"


def _kidney_note(mode: str) -> str:
    if mode == "ckd":
        return "有肾病（未透析）"
    if mode == "dialysis":
        return "有肾病且正在透析"
    return "无肾脏问题"


def render(data: Dict[str, Any], renderer):
    """渲染蛋白质摄入估算模板"""
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")

    incoming = dict(data or {})
    weight_kg = _to_float(incoming.get("weight_kg"))
    height_cm = _to_float(incoming.get("height_cm"))
    if weight_kg is None or height_cm is None:
        raise ValueError("缺少模板变量: weight_kg 或 height_cm")
    if weight_kg <= 0 or height_cm <= 0:
        raise ValueError("请提供有效的身高和体重")

    age = _to_int(incoming.get("age"))
    sex = (incoming.get("sex") or "").lower()
    activity_level = (incoming.get("activity_level") or "").lower()
    goal = (incoming.get("goal") or "").lower() or "maintain"
    kidney_status = (incoming.get("kidney_status") or "").lower()
    on_dialysis = incoming.get("on_dialysis")
    female_stage = (incoming.get("female_stage") or "none").lower()
    preg_trimester = incoming.get("preg_trimester")
    lact_stage = incoming.get("lact_stage")
    diet_type = incoming.get("diet_type") or ""

    height_m, bmi, weight_eff, weight_ideal, weight_note = _calc_weight_eff(height_cm, weight_kg)
    coef_base = _coef_base(age)
    k_activity, coef_after_act, activity_label = _apply_activity(coef_base, activity_level)
    coef_goal = _adjust_by_goal(coef_after_act, goal)
    kidney_mode = _kidney_mode(kidney_status, on_dialysis)
    coef_kidney = _adjust_by_kidney(coef_goal, kidney_mode)
    extra_preg_lact_g = _extra_preg_lact(sex, female_stage, preg_trimester, lact_stage, kidney_mode)
    coef_min, coef_max = _coef_limits(kidney_mode, age)

    # 模块7：克数换算
    prot_base_target_g = coef_kidney * weight_eff
    prot_target_raw_g = prot_base_target_g + extra_preg_lact_g
    prot_min_g = coef_min * weight_eff + extra_preg_lact_g
    prot_max_g = coef_max * weight_eff + extra_preg_lact_g
    prot_target_g = min(prot_target_raw_g, prot_max_g)

    X = round(prot_target_g)
    Y = round(prot_min_g)
    Z = round(prot_max_g)

    kidney_text = _kidney_note(kidney_mode)
    range_line = (
        f"参考范围：{Y}–{Z} g/天（系数 {coef_min:.2f}–{coef_max:.2f} g/kg，"
        f"有效体重 {weight_eff:.1f} kg）"
    )
    result_line = (
        f"建议每日蛋白质约 {X} g（范围 {Y}–{Z} g/天，"
        f"折算系数 {coef_kidney:.2f} g/kg，已按肾功能/目标/活动综合考虑）。"
    )

    payload: Dict[str, Any] = {
        "NAME": incoming.get("name") or "朋友",
        "AGE_TEXT": f"{age} 岁" if age is not None else "未提供",
        "SEX_TEXT": _sex_text(sex),
        "HEIGHT_CM": f"{height_cm:.1f}",
        "WEIGHT_KG": f"{weight_kg:.1f}",
        "BMI": f"{bmi:.1f}",
        "WEIGHT_EFF": f"{weight_eff:.1f}",
        "WEIGHT_EFF_NOTE": weight_note,
        "ACTIVITY_LABEL": activity_label,
        "GOAL_LABEL": _goal_label(goal),
        "DIET_LABEL": _diet_label(diet_type),
        "KIDNEY_NOTE": kidney_text,
        "NOTE_PREG_LACT": _preg_lact_note(sex, female_stage, preg_trimester, lact_stage),
        "COEF_BASE": f"{coef_base:.2f}",
        "K_ACTIVITY": f"{k_activity:.2f}",
        "COEF_AFTER_ACT": f"{coef_after_act:.2f}",
        "COEF_GOAL": f"{coef_goal:.2f}",
        "COEF_KIDNEY": f"{coef_kidney:.2f}",
        "EXTRA_PREG_LACT_G": f"{extra_preg_lact_g:.1f}",
        "COEF_MIN": f"{coef_min:.2f}",
        "COEF_MAX": f"{coef_max:.2f}",
        "PROT_BASE_TARGET_G": f"{prot_base_target_g:.1f}",
        "PROT_TARGET_RAW_G": f"{prot_target_raw_g:.1f}",
        "PROT_MIN_G": f"{Y}",
        "PROT_MAX_G": f"{Z}",
        "PROT_TARGET_G": f"{X}",
        "RESULT_LINE": result_line,
        "RANGE_LINE": range_line,
    }

    return renderer.render(md_text, payload)
