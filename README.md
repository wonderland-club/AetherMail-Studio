# 📧 Markdown邮件发送系统

一个通用的 Markdown → HTML → 邮件 发送系统，统一的 `/api/send` 接口，模板与对应的处理代码放在同一目录，支持 `{{&VAR}}` 占位符渲染。

## ✨ 功能特点
- 📧 **SMTP 支持**：使用环境变量配置 SMTP 账号即可发送
- 🧩 **模板模块化**：`templates/<id>/` 内同时存放 `template.md` 和 `template.py`
- 🏗️ **统一接口**：单一 `POST /api/send`，固定字段名：`template`、`to`、`cc`、`data`
- 🔄 **占位符渲染**：`{{&VAR}}` 形式的变量由请求体 `data` 提供，缺失即报错
- 🎨 **Markdown 转 HTML**：通用渲染链路，收件人/抄送/主题在公共模块中处理
- 🔒 **安全配置**：使用 `.env` 提供的 SMTP 配置

## 🚀 快速开始

### 方法一：一键启动（推荐）
```bash
python start.py
```
启动脚本会自动检查环境配置、运行测试并启动服务器。

### 方法二：手动启动

1) 安装依赖
```bash
pip install -r requirements.txt
```

2) 配置邮箱
```bash
cp .env.example .env
```
编辑 `.env`：
```env
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_smtp_authorization_code
```

3) 运行基础测试（可选）
```bash
python test_smtp.py
python test_email.py
python test_api.py
```

4) 启动服务
```bash
python app.py
```

## 📧 API 使用

### 统一接口：POST /api/send
请求体字段（固定命名，所有模板共用）：
```json
{
  "template": "模板ID，字符串",
  "to": "收件人邮箱，字符串",
  "cc": ["可选，抄送数组"],
  "data": {"可选，模板渲染数据对象"}
}
```

示例：发送通知模板（包含占位符）
```bash
curl -X POST http://127.0.0.1:5000/api/send   -H "Content-Type: application/json"   -d '{
    "template": "notification",
    "to": "user@example.com",
    "cc": [],
    "data": {"MESSAGE": "上线提醒", "CURRENT_TIME": "2024-06-01 12:00"}
  }'
```

示例：发送优点清单（无占位符）
```bash
curl -X POST http://127.0.0.1:5000/api/send   -H "Content-Type: application/json"   -d '{
    "template": "advantages",
    "to": "user@example.com",
    "data": {}
  }'
```

响应示例
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

### 模板列表：GET /templates
返回已注册模板的基本信息（ID、默认主题、必需字段）。

### 健康检查：GET /health
返回运行状态。

## 📁 项目结构
```
markdowm_tomail_server/
├── app.py                   # Flask API，统一 /api/send
├── start.py                 # 启动/检查脚本
├── requirements.txt         # 依赖
├── templates/               # 模板目录（每个模板一个子目录）
│   ├── advantages/
│   │   ├── template.md
│   │   └── template.py
│   └── notification/
│       ├── template.md
│       └── template.py
├── src/
│   ├── core/
│   │   ├── renderer.py      # 处理 {{&VAR}} 占位符
│   │   └── template_registry.py
│   ├── config.py            # SMTP 配置
│   ├── email_sender.py      # Markdown → HTML → 邮件发送
│   └── utils/
│       └── email_validator.py
├── test_api.py              # API 示例测试
├── test_smtp.py             # SMTP 连通性测试
└── DESIGN_NOTES.md / GMAIL_COMPATIBILITY_FIX.md
```

## 🧠 模板开发约定
- 每个模板目录包含：`template.md`（正文）、`template.py`（定义 ID/默认主题/必需字段/render 函数）。
- 占位符格式 `{{&VAR}}`，变量名需与请求体 `data` 中的键一致，缺失会返回 400。
- 主题由模板定义 `DEFAULT_SUBJECT` 或可选 `get_subject(data)` 决定。

## 🔒 配置
- SMTP 信息来自 `.env`；缺少 `SMTP_USER` 或 `SMTP_PASSWORD` 会在启动时报错。

## 🧪 测试
- `python test_api.py` 使用新的字段名 `template`/`to`/`cc`/`data`。
- 运行测试前需在 `.env` 中配置好 SMTP。
