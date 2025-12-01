# 蛋白质摄入估算报告

Hi {{&NAME}}，以下是基于你填写的数据生成的蛋白质摄入建议。

## 输入概要
- 年龄/性别：{{&AGE_TEXT}} / {{&SEX_TEXT}}
- 身高/体重：{{&HEIGHT_CM}} cm / {{&WEIGHT_KG}} kg，BMI {{&BMI}}
- 有效体重：{{&WEIGHT_EFF}} kg（{{&WEIGHT_EFF_NOTE}}）
- 活动水平：{{&ACTIVITY_LABEL}}
- 目标：{{&GOAL_LABEL}}
- 饮食偏好：{{&DIET_LABEL}}
- 肾脏状况：{{&KIDNEY_NOTE}}
- 生理备注：{{&NOTE_PREG_LACT}}

## 模块拆解（对应 0-8 步）
- 模块0 有效体重：按 BMI 计算后用于所有 g/kg 换算
- 模块1 年龄基线：{{&COEF_BASE}} g/kg
- 模块2 活动系数：×{{&K_ACTIVITY}} → {{&COEF_AFTER_ACT}} g/kg
- 模块3 目标调整：{{&COEF_GOAL}} g/kg（依据当前目标）
- 模块4 肾功能修正：模式 {{&KIDNEY_NOTE}} → {{&COEF_KIDNEY}} g/kg
- 模块5 孕/哺乳额外：{{&EXTRA_PREG_LACT_G}} g/天（仅女性且无肾病时启用）
- 模块6 安全范围：{{&COEF_MIN}}–{{&COEF_MAX}} g/kg
- 模块7 换算克数：基础 {{&PROT_BASE_TARGET_G}} g → 叠加 {{&PROT_TARGET_RAW_G}} g；范围 {{&PROT_MIN_G}}–{{&PROT_MAX_G}} g
- 模块8 推荐值：{{&RESULT_LINE}}

## 建议
- {{&RANGE_LINE}}
- 如有基础疾病或处于孕/哺乳期，请与医生/营养师确认个性化方案。
