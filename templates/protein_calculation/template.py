"""蛋白质摄入估算模板（8 模块算法 + 豆包 AI 文案生成）"""
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

# 确保 .env 被加载到环境变量中（用于 ARK_API_KEY 等）
load_dotenv()


TEMPLATE_ID = "protein_calculation"
DESCRIPTION = "蛋白质摄入估算与建议（基于身高、体重、活动、目标、肾功能、孕/哺乳状态）"
DEFAULT_SUBJECT = "「一场」SpaceOne｜你的蛋白质计划已准备好"
# 关键计算字段，其余字段有默认值或可选
REQUIRED_FIELDS = ["height_cm", "weight_kg", "activity_level", "goal", "kidney_status"]

_ARK_MODEL = os.getenv("ARK_MODEL_ID", "ep-20251201140344-9wc9s")
_ARK_BASE_URL = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")


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
    """模块0：有效体重"""
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
    """模块2：活动水平调整"""
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

    coef *= 1.15
    coef = max(coef, 1.4)
    coef = min(coef, 2.0)
    return coef


def _kidney_mode(status: str, on_dialysis: Optional[bool]) -> str:
    """模块4：肾功能归一化到 none/ckd/dialysis"""
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


def _get_ark_client():
    # 创建豆包客户端（需 ARK_API_KEY）
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        return None
    try:
        from volcenginesdkarkruntime import Ark
    except Exception:
        return None
    return Ark(base_url=_ARK_BASE_URL, api_key=api_key)


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text") or "")
        return "\n".join(texts)
    return str(content)


def _normalize_markdown(md: str) -> str:
    """给 AI 文案补齐基础的换行与列表空行"""
    if not md:
        return ""
    lines = [line.rstrip() for line in md.splitlines()]
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if out and out[-1] == "":
                continue
            out.append("")
            continue

        is_heading = stripped.startswith("#")
        is_unordered = stripped.startswith(("- ", "* ", "+ "))
        # 有序列表匹配：数字. 空格
        is_ordered = bool(re.match(r"^\d+\.\s", stripped))

        if out and out[-1] != "" and (is_heading or is_unordered or is_ordered):
            out.append("")

        out.append(stripped)

    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()

    return "\n".join(out)


def _maybe_ai_sections(ai_payload: Dict[str, Any]) -> Dict[str, str]:
    client = _get_ark_client()
    if not client:
        print("[protein_calculation] AI 未启用：缺少 ARK_API_KEY 或 SDK 不可用")
        return {}

    # Prompt 保持原样（含示例），仅注入结构化 JSON
    prompt = f"""

# 蛋白质摄入建议报告生成指南

## 你的角色
你是一名温暖、专业的中文注册营养师,正在为一位认真对待自己健康的用户生成个性化的蛋白质摄入建议报告。

## 核心原则
- **温暖鼓励**:用户花时间填写问卷本身就值得肯定
- **清晰易懂**:所有专业术语都要用"人话"解释
- **个性化**:根据用户的具体情况定制内容
- **安全第一**:该提醒的地方一定要温和但明确地说清楚

---

## 输出格式要求

### ⚠️ 关键规则
1. **直接生成用户看到的正文**,不要出现任何写作步骤的标题或提示语
2. **禁止出现的词组**:
   - "开场 & 正反馈"
   - "核心结论一句话"  
   - "告诉 TA:为什么是这个数字"
   - "步骤一""第一部分"等结构说明
   - 任何其他提示性标题

3. **可以使用的组织方式**:
   - 自然的段落
   - 有序/无序列表(但不加说明性小标题)
   - 适当的空行分隔

4. **输出格式**: 
   - 返回纯 Markdown 文本,放在 `report_md` 字段中
   - 不要包裹代码块标记
   - 段落之间空一行

---

## 内容框架(内部参考,不要照抄到正文)

### 1. 温暖的开场(必须包含的正反馈)

用用户昵称自然地打招呼,然后流畅地表达这两层意思:

**第一层 - 肯定行动本身**:
> "愿意认真填完这份问卷,本身就是你为自己健康做出的一个很棒的决定。"

**第二层 - 展望未来**:
> "你已经迈出了把身体交还给自己的一步,后面就是按计划吃好、动好。"

💡 **写作提示**: 把这两句话自然地融入开场段落,不要生硬堆砌。

---

### 2. 核心数字结论

用**一段话**把这三个数字说清楚:
- **目标值** X = `protein_target_g`
- **合理范围** Y ~ Z = `protein_min_g` ~ `protein_max_g`

**示例语句**(可同义改写):
> "综合你的情况,建议你每天摄入约 X 克蛋白质,合理范围大概在 Y–Z 克之间。"

---

### 3. 用"人话"解释计算逻辑

**引入语**(自然过渡):
> "我们大致是按下面几个步骤帮你算出这个数字的:"

然后按逻辑顺序解释,用**无序或有序列表**组织,但不给每一步加小标题:

#### 第一步:从身高体重开始(有效体重)

**如果 BMI ≥ 27**:
> "你现在有点偏重,所以我们没有直接用'当前体重'去放大蛋白需求,而是按更接近理想体重的'有效体重'来估算,这样更安全、也更贴近真实需要。"

**如果 BMI < 27**:
> "你的蛋白需求是按当前体重来估算的。"

#### 第二步:按年龄定基础底线

**年龄 < 60 岁**:
> "按成年人的标准,每公斤体重要至少配 0.8 克蛋白,这是不亏待身体的底线。"

**年龄 ≥ 60 岁**:
> "随着年龄增长,肌肉和免疫力更吃蛋白,所以我们把你的基础标准提高到每公斤 1.0 克左右,让身体更有底气。"

#### 第三步:运动量的影响

根据 `activity_level` 转成自然表述:

**示例句式**:
> "你平时的运动量是【几乎不动/轻度/中等/较高】,这会影响肌肉蛋白的消耗,所以我们在基础标准上按照运动量做了相应的【保持/轻微上调/明显上调/大幅提升】。"

- **几乎不动**: 保留基础系数
- **轻度运动**: 略微上调
- **中等运动**: 明显上调  
- **高强度/运动员**: 提升到运动营养学推荐区间

#### 第四步:目标的微调(减脂/增肌/维持)

**减脂目标**:
> "在减脂阶段,蛋白稍微吃高一点,可以减缓肌肉流失、增加饱腹感,所以我们把系数再往上轻轻推了一档,但仍控制在安全范围内。"

**增肌目标**:
> "既然想长肌肉,那就得给身体足够的'砖头',我们把你的蛋白标准拉到偏高区间,让训练更有回报。"

**维持目标**:
> "你目前目标是稳住体重和状态,所以我们就用前面按【年龄 + 运动量】得到的标准作为主要参考。"

#### 第五步:肾功能 & 安全护栏

**无肾病** (`kidney_mode == "none"`):
> "在没有肾病的前提下,我们给你留了一个大致 0.8–2.0 g/kg 的安全区间,确保既有用又不过度。"

**慢性肾病** (`kidney_mode == "ckd"`):
> "因为你有肾功能问题,我们把蛋白严格锁在 0.6–0.8 g/kg 的区间内,优先保证肾脏安全,所以即便你有减脂/增肌想法,蛋白也不能随意往上加。"

**透析** (`kidney_mode == "dialysis"`):
> "你正在透析,透析本身会带走一部分氨基酸,所以反而需要适中偏高的蛋白摄入(大致 1.0–1.5 g/kg),我们就是在这个区间内给你定的。"

#### 第六步:孕期/哺乳的额外加成(如适用)

**如果处于孕期或哺乳期**:
> "你现在处在【第 X 孕期/哺乳阶段】,身体有一部分蛋白是在'为宝宝打工',所以我们在前面的基础上,又给你额外加了【N 克/天】的蛋白额度。"

**⚠️ 必须加上安全提醒**:
> "孕期/哺乳期是高敏感阶段,这份建议可以作为日常饮食参考,但具体方案仍建议和产科/儿科医生确认。"

#### 第七步:全局安全检查

**收束语**:
> "在后台我们还做了一轮'安全检查',把结果限制在适合你这个阶段的上下限之间,所以你现在看到的 X、Y、Z 是在兼顾目标和安全边界之后得出的数字。"

---

### 4. 食物换算:怎么把克数吃出来

#### 统一换算规则(用无序列表)

- 1 个中等鸡蛋 ≈ 6 g 蛋白
- 100 g 熟鸡胸肉 ≈ 30 g 蛋白  
- 250 ml 牛奶 ≈ 8 g 蛋白
- 100 g 北豆腐 ≈ 8 g 蛋白
- 1 勺分离乳清蛋白粉 ≈ 20–25 g 蛋白

#### 一日饮食示例(根据目标值 X)

**X < 60 g**:
> 示例组合:1 份肉 + 1 杯奶 + 1–2 个鸡蛋

**60–100 g**:  
> 示例组合:两顿有肉/豆腐的正餐 + 2 个鸡蛋 + 1 杯奶

**X > 100 g**:
> 在上述基础上,可以在训练后加 1 勺分离乳清蛋白粉

#### 根据饮食类型调整(diet_type)

**杂食/蛋奶素** (`omnivore` / `lacto_ovo`):
- 以肉/蛋/奶为主,豆制品辅助

**纯素** (`vegan`):  
- 改用豆类、豆腐、豆浆、坚果、全谷物 + 植物蛋白粉
- **不要提乳清蛋白**

---

### 5. 蛋白粉补充说明

#### 无肾病时的正常推荐

**当 `kidney_mode == "none"` 时**:
> "如果你忙到没时间好好吃饭,或者训练后一餐跟不上,可以考虑用一勺分离乳清蛋白粉当补充,它乳糖少、蛋白纯,冲水就能喝。但它是锦上添花,不是替代三餐。"

#### 特殊人群的中性表述

**肾病 (`ckd` / `dialysis`) 或 孕期/哺乳期**:
> "如果以后考虑额外加蛋白粉,建议先和肾内科/产科/儿科医生确认。"

---

### 6. 个性化提醒(按需选择 1-2 条)

**年龄 ≥ 60 岁**:
> "请尽量保证每天都吃够蛋白,这对维持肌肉和行动力特别关键,可以搭配一点简单阻力训练更好。"

**慢性肾病**:
> "你这边最大优先级是保护肾脏,所以蛋白越精准越好,不建议自行再加高蛋白食物或补剂。"

**透析**:
> "注意在医生建议范围内吃够蛋白,同时配合足够的能量,防止越透越瘦。"

**高强度训练 + 增肌**:
> "重点是把蛋白分配到每一餐、在训练后及时补充,避免无意义地吃到特别夸张的超高蛋白。"

---

### 7. 温暖收尾 + 免责声明

#### 鼓励性收尾

**基调**: 鼓励 + 放松

**示例**:
> "饮食习惯是慢慢调整的,不用一下子做到完美,能比现在好一点就是进步,坚持比特别精准更重要。"

#### 固定免责声明(所有用户都带)

> **免责声明:** 本邮件内容基于你在问卷中填写的信息和一般营养学共识,仅供日常饮食规划参考,不构成医疗诊断或处方。如你患有慢性疾病、正在妊娠或哺乳,或医生已给出特殊饮食要求,请以专业医生和营养师的意见为准。

---

写作注意事项:

- ✅ 自然引用数字(目标克数、范围、BMI 等)
- ❌ 不要重复列出"基础信息"模块的内容  
- ✅ 段落之间空一行
- ✅ 有序列表用 `1.` `2.`,无序列表用 `- `
- ❌ 不要把多条内容挤在同一行
- ❌ 绝对不要在正文中出现本提示词的结构标题或"步骤"描述

记住:你生成的是给用户看的温暖、专业的营养建议,不是给自己看的写作大纲。
以下是结构化数据（含数字）：
{json.dumps(ai_payload, ensure_ascii=False, indent=2)}

请直接返回 JSON 字符串，不要添加代码块标记。
"""

    try:
        completion = client.chat.completions.create(
            model=_ARK_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
            reasoning_effort="high",
            extra_headers={"x-is-encrypted": "true"},
        )
    except Exception as exc:
        print(f"[protein_calculation] AI 调用失败：{exc}")
        return {}

    content = getattr(completion.choices[0].message, "content", None) if completion.choices else None
    text = _content_to_text(content)
    if not text:
        print("[protein_calculation] AI 返回为空")
        return {}
    try:
        data = json.loads(text)
    except Exception as exc:
        print(f"[protein_calculation] AI 返回非 JSON：{exc}")
        return {}

    result = {}
    # 仅接受字符串字段，避免意外结构
    for key in ["intro", "rationale", "food_plan", "powder", "reminders", "disclaimer", "report_md"]:
        if key in data and isinstance(data[key], str):
            result[key] = data[key].strip()
    if result:
        print("[protein_calculation] 已使用 AI 生成的文案片段/Markdown")
    return result


def _build_report(ai_ctx: Dict[str, Any], ai_sections: Dict[str, str]) -> str:
    """将 AI 生成的片段或完整 Markdown 组装为最终报告"""
    if ai_sections.get("report_md"):
        return _normalize_markdown(ai_sections["report_md"])

    # 未提供完整 report_md 时，按分段字段拼装
    intro = ai_sections.get("intro", "").strip()
    rationale = ai_sections.get("rationale", "").strip()
    food_plan = ai_sections.get("food_plan", "").strip()
    powder = ai_sections.get("powder", "").strip()
    reminders = ai_sections.get("reminders", "").strip()
    disclaimer = ai_sections.get("disclaimer", "").strip()

    parts = []
    if intro:
        parts.append("## 开场 & 正反馈\n" + intro)
    parts.append("## 核心结论一句话\n" + ai_ctx.get("core_line", ""))
    if rationale:
        parts.append("## 为什么是这个数字\n" + rationale)
    if food_plan:
        parts.append("## 怎么吃出来（食物换算与示例）\n" + food_plan)
    if powder:
        parts.append("## 蛋白粉要不要\n" + powder)
    if reminders:
        parts.append("## 个性化提醒\n" + reminders)
    if disclaimer:
        parts.append("## 收尾 & 免责声明\n" + disclaimer)

    return _normalize_markdown("\n\n".join([p for p in parts if p]).strip())


def render(data: Dict[str, Any], renderer):
    """渲染蛋白质摄入估算模板"""
    md_path = Path(__file__).with_name("template.md")
    md_text = md_path.read_text(encoding="utf-8")

    incoming = dict(data or {})
    # 基础校验与数值转换
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
    preg_trimester = incoming.get("preg_trimester") or ""
    lact_stage = incoming.get("lact_stage") or ""
    diet_type = (incoming.get("diet_type") or "").lower()

    height_m, bmi, weight_eff, weight_ideal, weight_note = _calc_weight_eff(height_cm, weight_kg)
    coef_base = _coef_base(age)
    k_activity, coef_after_act, activity_label = _apply_activity(coef_base, activity_level)
    coef_goal = _adjust_by_goal(coef_after_act, goal)
    kidney_mode = _kidney_mode(kidney_status, on_dialysis)
    coef_kidney = _adjust_by_kidney(coef_goal, kidney_mode)
    extra_preg_lact_g = _extra_preg_lact(sex, female_stage, preg_trimester, lact_stage, kidney_mode)
    coef_min, coef_max = _coef_limits(kidney_mode, age)

    prot_base_target_g = coef_kidney * weight_eff
    prot_target_raw_g = prot_base_target_g + extra_preg_lact_g
    prot_min_g = coef_min * weight_eff + extra_preg_lact_g
    prot_max_g = coef_max * weight_eff + extra_preg_lact_g
    prot_target_g = min(prot_target_raw_g, prot_max_g)

    X = round(prot_target_g)
    Y = round(prot_min_g)
    Z = round(prot_max_g)

    kidney_text = _kidney_note(kidney_mode)
    core_line = f"综合你的信息，建议每天摄入约 {X} 克蛋白质，合理范围在 {Y}–{Z} 克之间。"
    range_line = (
        f"参考范围：{Y}–{Z} g/天（系数 {coef_min:.2f}–{coef_max:.2f} g/kg，"
        f"有效体重 {weight_eff:.1f} kg）。"
    )
    result_line = (
        f"建议每日蛋白质约 {X} g（范围 {Y}–{Z} g/天，"
        f"折算系数 {coef_kidney:.2f} g/kg，已按肾功能/目标/活动综合考虑）。"
    )

    ai_context = {
        "name": incoming.get("name") or "朋友",
        "age": age,
        "sex": sex or "未提供",
        "female_stage": female_stage or "none",
        "preg_trimester": preg_trimester or "未提供",
        "lact_stage": lact_stage or "未提供",
        "height_cm": round(height_cm, 1),
        "weight_kg": round(weight_kg, 1),
        "bmi": round(bmi, 1),
        "weight_eff": round(weight_eff, 1),
        "weight_note": weight_note,
        "activity_level": activity_level or "moderate",
        "activity_label": activity_label,
        "goal": goal,
        "goal_label": _goal_label(goal),
        "diet_type": diet_type or "omnivore",
        "kidney_mode": kidney_mode,
        "kidney_note": kidney_text,
        "coef_used_g_per_kg": round(coef_kidney, 2),
        "coef_min": round(coef_min, 2),
        "coef_max": round(coef_max, 2),
        "extra_preg_lact_g": round(extra_preg_lact_g, 1),
        "protein_target_g": X,
        "protein_min_g": Y,
        "protein_max_g": Z,
        "prot_base_target_g": round(prot_base_target_g, 1),
        "prot_target_raw_g": round(prot_target_raw_g, 1),
        "range_line": range_line,
        "result_line": result_line,
        "core_line": core_line,
    }

    # 发送给豆包的结构化 JSON，便于提示词引用
    ai_payload = {
        "user": {
            "name": ai_context["name"],
            "age": age,
            "sex": sex,
            "female_stage": female_stage,
            "preg_trimester": preg_trimester or "",
            "lact_stage": lact_stage or "",
            "diet_type": diet_type or "omnivore",
            "goal": goal,
            "goal_label": _goal_label(goal),
            "activity_level": activity_level or "moderate",
            "activity_label": activity_label,
            "kidney_mode": kidney_mode,
        },
        "metrics": {
            "height_cm": float(height_cm),
            "weight_kg": float(weight_kg),
            "bmi": round(bmi, 1),
            "weight_eff": round(weight_eff, 1),
            "weight_note": weight_note,
        },
        "coefficients": {
            "coef_base": round(coef_base, 2),
            "k_activity": round(k_activity, 2),
            "coef_after_act": round(coef_after_act, 2),
            "coef_goal": round(coef_goal, 2),
            "coef_used_g_per_kg": round(coef_kidney, 2),
            "coef_min": round(coef_min, 2),
            "coef_max": round(coef_max, 2),
        },
        "protein_plan": {
            "protein_target_g": X,
            "protein_min_g": Y,
            "protein_max_g": Z,
            "prot_base_target_g": round(prot_base_target_g, 1),
            "prot_target_raw_g": round(prot_target_raw_g, 1),
            "extra_preg_lact_g": round(extra_preg_lact_g, 1),
        },
        "phrases": {
            "core_line": core_line,
            "range_line": range_line,
            "result_line": result_line,
        },
    }

    # AI 生成文案，未返回则直接报错
    ai_sections = _maybe_ai_sections(ai_payload)
    if not ai_sections:
        raise RuntimeError("AI 未返回内容，请检查 ARK 配置或模型输出")
    ai_report = _build_report(ai_context, ai_sections)
    if not ai_report:
        raise RuntimeError("AI 文案为空，无法渲染报告")

    payload: Dict[str, Any] = {
        "NAME": ai_context["name"],
        "AGE_TEXT": f"{age} 岁" if age is not None else "未提供",
        "AGE": str(age) if age is not None else "未提供",
        "SEX": sex or "未提供",
        "SEX_TEXT": _sex_text(sex),
        "FEMALE_STAGE": female_stage or "none",
        "PREG_TRIMESTER": preg_trimester or "未提供",
        "LACT_STAGE": lact_stage or "未提供",
        "HEIGHT_CM": f"{height_cm:.1f}",
        "WEIGHT_KG": f"{weight_kg:.1f}",
        "BMI": f"{bmi:.1f}",
        "WEIGHT_EFF": f"{weight_eff:.1f}",
        "WEIGHT_EFF_NOTE": weight_note,
        "ACTIVITY_LEVEL": activity_level or "moderate",
        "ACTIVITY_LABEL": activity_label,
        "GOAL": goal or "maintain",
        "GOAL_LABEL": _goal_label(goal),
        "DIET_TYPE": diet_type or "omnivore",
        "DIET_LABEL": _diet_label(diet_type),
        "KIDNEY_MODE": kidney_mode,
        "KIDNEY_NOTE": kidney_text,
        "NOTE_PREG_LACT": _preg_lact_note(sex, female_stage, preg_trimester, lact_stage),
        "COEF_BASE": f"{coef_base:.2f}",
        "K_ACTIVITY": f"{k_activity:.2f}",
        "COEF_AFTER_ACT": f"{coef_after_act:.2f}",
        "COEF_GOAL": f"{coef_goal:.2f}",
        "COEF_USED_G_PER_KG": f"{coef_kidney:.2f}",
        "EXTRA_PREG_LACT_G": f"{extra_preg_lact_g:.1f}",
        "COEF_MIN": f"{coef_min:.2f}",
        "COEF_MAX": f"{coef_max:.2f}",
        "PROT_BASE_TARGET_G": f"{prot_base_target_g:.1f}",
        "PROT_TARGET_RAW_G": f"{prot_target_raw_g:.1f}",
        "PROTEIN_MIN_G": f"{Y}",
        "PROTEIN_MAX_G": f"{Z}",
        "PROTEIN_TARGET_G": f"{X}",
        "RESULT_LINE": result_line,
        "RANGE_LINE": range_line,
        "CORE_LINE": core_line,
        "AI_REPORT": ai_report,
    }

    return renderer.render(md_text, payload)
