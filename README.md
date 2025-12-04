# 📧 Markdown邮件发送系统

一个通用的 Markdown → HTML → 邮件 发送系统，统一 `/api/send` 接口，模板与处理代码同目录，支持 `{{&VAR}}` 占位符渲染。

## 🚀 快速开始（Conda）
1) 创建并激活环境  
```bash
conda env create -f environment.yml
conda activate aethermail
# 之后更新依赖
conda env update -f environment.yml --prune
```

2) 配置邮箱（`.env`）  
在项目根目录新建 `.env`（示例值按需替换）：
```env
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_smtp_authorization_code
DEFAULT_SENDER_NAME=Markdown Mailer
DEFAULT_SUBJECT_PREFIX=[AetherMail]
```
`SMTP_USER` / `SMTP_PASSWORD` 缺失时程序会直接报错；默认使用 SSL 465 端口。

3) 可选：验证依赖  
```bash
python - <<'PY'
import pypandoc
print("pandoc_version =", pypandoc.get_pandoc_version())
print("pandoc_path    =", pypandoc.get_pandoc_path())
PY
```

4) 启动  
```bash
python start.py      # 推荐：带检查提示
# 或
python app.py        # 直接启动 Flask
```

5) 试发一封（示例模板 `notification`）  
```bash
curl -X POST http://127.0.0.1:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "template": "notification",
    "to": "user@example.com",
    "cc": [],
    "data": {"MESSAGE": "上线提醒", "CURRENT_TIME": "2024-06-01 12:00"}
  }'
```

## 📦 Conda 环境
- `environment.yml` 固定 Python 3.10，并预装 `flask`、`pypandoc`、`pandoc`、`python-dotenv`、`email-validator`，其余（如 `premailer`、`volcengine-python-sdk[ark]`）通过 pip 安装。  
- 清理环境：`conda env remove -n aethermail`。  
- 如需自定义环境名，修改 `environment.yml` 的 `name` 后重新创建。

## 🧠 运行逻辑（请求如何走）
- 应用入口 `app.py`：初始化 `Renderer`（占位符渲染）、`TemplateRegistry`（扫描 `templates/*/template.py`）、`EmailSender`（Markdown→HTML→SMTP），并注册 Flask 路由。  
- `POST /api/send`：校验 `template`/`to`/`cc`/`data` 格式 → 读取模板定义和必填字段 → 调用模板的 `render(data, renderer)` 生成 Markdown → 用模板的 `subject_for` 生成主题。  
- `EmailSender`：用 pypandoc 将 Markdown 转 HTML，若有 `premailer` 则内联 CSS，随后通过 `.env` 中的 SMTP 配置发送邮件（纯文本+HTML双版本，支持抄送/附件预留）。  
- 其他路由：`GET /templates` 返回已注册模板的元信息；`GET /health` 用于健康检查；`GET /` 给出入门提示。

## 📧 API 使用
`POST /api/send` 请求体（固定字段）：
```json
{
  "template": "模板ID，字符串",
  "to": "收件人邮箱，字符串",
  "cc": ["可选，抄送数组"],
  "data": {"可选，模板渲染数据对象"}
}
```
返回示例：
```json
{
  "success": true,
  "message": "邮件发送成功",
  "template": "notification",
  "subject": "服务上线通知",
  "recipient": "user@example.com",
  "cc": []
}
```

## 📁 项目结构
```
markdowm_tomail_server/
├── app.py                   # Flask API，统一 /api/send
├── start.py                 # 启动/检查脚本
├── environment.yml          # Conda 环境定义（含 pandoc）
├── requirements.txt         # pip 依赖（如需与 Conda 同步参考）
├── templates/               # 模板目录（每个模板一个子目录）
│   ├── advantages/
│   │   ├── template.md
│   │   └── template.py
│   ├── notification/
│   │   ├── template.md
│   │   └── template.py
│   └── protein_calculation/…
├── src/
│   ├── core/
│   │   ├── renderer.py      # 处理 {{&VAR}} 占位符
│   │   └── template_registry.py
│   ├── config.py            # SMTP 配置加载
│   ├── email_sender.py      # Markdown → HTML → 邮件发送
│   └── utils/
│       └── email_validator.py
├── test_api.py              # API 示例测试
└── test_smtp.py             # SMTP 连通性测试
```

## 🧩 模板开发约定
- 每个模板目录包含：`template.md`（正文）、`template.py`（定义 ID/默认主题/必需字段/render 函数）。  
- 占位符格式 `{{&VAR}}`，变量名需与请求体 `data` 中的键一致，缺失会返回 400。  
- 主题由模板的 `DEFAULT_SUBJECT` 或可选的 `get_subject(data)` 决定。

## 🧪 测试
- `python test_smtp.py`：验证 SMTP 连通性（需已配置 `.env`）。  
- `python test_api.py`：基于示例数据的 API 请求测试。
