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
复制 `.env.example` 为 `.env`，并按需替换示例值。配置采用多 SMTP 主体格式：
```env
DEFAULT_SMTP_NAME=junyan_qq
SMTP_PROFILES=junyan_qq,huaqing_exmail

SMTP_PROFILE_JUNYAN_QQ_NAME=俊彦 QQ 邮箱
SMTP_PROFILE_JUNYAN_QQ_HOST=smtp.qq.com
SMTP_PROFILE_JUNYAN_QQ_PORT=465
SMTP_PROFILE_JUNYAN_QQ_SECURE=ssl
SMTP_PROFILE_JUNYAN_QQ_USER=your_qq@example.com
SMTP_PROFILE_JUNYAN_QQ_PASSWORD=your_qq_smtp_password
SMTP_PROFILE_JUNYAN_QQ_SENDER_NAME=俊彦

SMTP_PROFILE_HUAQING_EXMAIL_NAME=华清美伦 企业邮
SMTP_PROFILE_HUAQING_EXMAIL_HOST=smtp.exmail.qq.com
SMTP_PROFILE_HUAQING_EXMAIL_PORT=465
SMTP_PROFILE_HUAQING_EXMAIL_SECURE=ssl
SMTP_PROFILE_HUAQING_EXMAIL_USER=your_exmail@example.com
SMTP_PROFILE_HUAQING_EXMAIL_PASSWORD=your_exmail_password
SMTP_PROFILE_HUAQING_EXMAIL_SENDER_NAME=华清美伦
```
外部调用统一使用 `smtp_name`。`SMTP_PROFILES`、`DEFAULT_SMTP_NAME` 以及每个主体的 `HOST / USER / PASSWORD` 缺失时程序会直接报错；默认使用 SSL 465 端口。

3) 可选：验证依赖  
```bash
python - <<'PY'
import pypandoc
print("pandoc_version =", pypandoc.get_pandoc_version())
print("pandoc_path    =", pypandoc.get_pandoc_path())
PY
```

4) 启动  
开发环境：
```bash
python start.py      # 推荐：带检查提示
# 或
python app.py        # 直接启动 Flask
```
生产环境（Gunicorn）：
```bash
python -m gunicorn -c gunicorn.conf.py wsgi:app
```

5) 创建一个空白模板  
```bash
python create_template.py --template-id demo_notice --subject "测试主题"
```
可选追加：
```bash
python create_template.py --template-id demo_notice --subject "测试主题" --description "测试通知模板"
```
命令会默认创建 `template.py`、`template.md` 以及 `attachments/slot1~3/`。  
完整模板规范、可选 AI hook 写法和维护矩阵见 [templates/新增模板说明.md](/Users/schen/Documents/MyProjects/AetherMail-Studio/templates/%E6%96%B0%E5%A2%9E%E6%A8%A1%E6%9D%BF%E8%AF%B4%E6%98%8E.md)。

6) 试发一封（示例模板 `notification`）  
```bash
curl -X POST http://127.0.0.1:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "template": "notification",
    "smtp_name": "junyan_qq",
    "to": "user@example.com",
    "cc": [],
    "data": {"MESSAGE": "上线提醒", "CURRENT_TIME": "2024-06-01 12:00"}
  }'
```

7) 验证真实豆包链路（推荐先发给当前 SMTP 主体自己的邮箱）  
以 `junyan_qq` 为例，`to` 直接填该主体自己的邮箱：
```bash
curl -X POST http://127.0.0.1:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "template": "doubao_smoke_test",
    "smtp_name": "junyan_qq",
    "to": "junyan101@qq.com",
    "cc": [],
    "data": {
      "NAME": "俊彦",
      "TOPIC": "验证豆包调用、Markdown 渲染与 SMTP 发送链路"
    }
  }'
```

## 📦 Conda 环境
- `environment.yml` 固定 Python 3.10，并预装 `flask`、`pypandoc`、`pandoc`、`python-dotenv`、`email-validator`，其余（如 `gunicorn`、`premailer`、`volcengine-python-sdk[ark]`）通过 pip 安装。  
- 清理环境：`conda env remove -n aethermail`。  
- 如需自定义环境名，修改 `environment.yml` 的 `name` 后重新创建。

## 🚀 生产部署（Gunicorn）
- WSGI 入口为 `wsgi:app`，Gunicorn 配置文件为 `gunicorn.conf.py`。
- 默认监听 `127.0.0.1:5000`，适合放在 `nginx` 反向代理后面。
- 默认使用 `gthread` worker，适合当前这种会等待 SMTP、AI 接口和 Markdown 转换的 I/O 阻塞型请求。
- 默认超时为 180 秒；如果某些模板会调用外部 AI，建议不要把超时设得太低。
- 仓库附带了可直接改的样板文件：
  - `deploy/systemd/aethermail-studio.service`
  - `deploy/nginx/aethermail-studio.conf`

启动命令：
```bash
python -m gunicorn -c gunicorn.conf.py wsgi:app
```

常用环境变量（可写进 `.env` 或 systemd `Environment=`）：
```env
GUNICORN_BIND=127.0.0.1:5000
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=180
GUNICORN_GRACEFUL_TIMEOUT=30
GUNICORN_KEEPALIVE=5
GUNICORN_LOG_LEVEL=info
GUNICORN_FORWARDED_ALLOW_IPS=127.0.0.1
```

如果部署在 `nginx` 后面，应用默认启用了 `ProxyFix`，会信任 1 层代理转发头；对应变量如下：
```env
ENABLE_PROXY_FIX=true
PROXY_FIX_X_FOR=1
PROXY_FIX_X_PROTO=1
PROXY_FIX_X_HOST=1
PROXY_FIX_X_PORT=1
PROXY_FIX_X_PREFIX=1
```

最小 `nginx` 反代示例：
```nginx
location = / {
    return 302 /aether_mail_studio/;
}

location = /aether_mail_studio {
    return 302 /aether_mail_studio/;
}

location /aether_mail_studio/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /aether_mail_studio;
    proxy_read_timeout 180s;
}
```

如果你按当前仓库里的部署样板走，公网入口会是：
```text
http://115.190.255.162/aether_mail_studio/
http://115.190.255.162/aether_mail_studio/health
http://115.190.255.162/aether_mail_studio/templates
http://115.190.255.162/aether_mail_studio/smtp-configs
http://115.190.255.162/aether_mail_studio/api/send
```

推荐的服务器目录约定：
```text
/srv/aethermail-studio
├── .env
├── .venv/
├── gunicorn.conf.py
└── ...
```

一套最小上线步骤：
1. 安装系统依赖：`python3.10+`、`python3-venv`、`pandoc`、`nginx`。
2. 将项目放到 `/srv/aethermail-studio`，并创建专用用户 `aethermail`。
3. 在项目目录创建虚拟环境并安装依赖：
```bash
cd /srv/aethermail-studio
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
4. 配置 `.env`，确认 SMTP 和豆包相关变量可用。
5. 复制 `deploy/systemd/aethermail-studio.service` 到 `/etc/systemd/system/`，按实际路径调整。
6. 复制 `deploy/nginx/aethermail-studio.conf` 到 `/etc/nginx/sites-available/`。当前样板默认使用 `115.190.255.162` 并将应用挂在 `/aether_mail_studio/`。
7. 启用并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aethermail-studio
sudo ln -sf /etc/nginx/sites-available/aethermail-studio.conf /etc/nginx/sites-enabled/aethermail-studio.conf
sudo nginx -t
sudo systemctl reload nginx
```

如果你坚持用 Conda 而不是 `.venv`，只需要把 systemd 里的 `PATH` 和 `ExecStart` 改成 Conda 环境对应的 `bin` 路径。

## 🧠 运行逻辑（请求如何走）
- 应用入口 `app.py`：初始化 `Renderer`（占位符渲染）、`TemplateRegistry`（扫描 `templates/*/template.py`）、`EmailSender`（Markdown→HTML→SMTP），并注册 Flask 路由。  
- `POST /api/send`：校验 `template`/`to`/`cc`/`data` 格式 → 读取模板定义和必填字段 → 调用模板的 `render(data, renderer)` 生成 Markdown → 使用模板的 `DEFAULT_SUBJECT` 作为主题。  
- `EmailSender`：用 pypandoc 将 Markdown 转 HTML，若有 `premailer` 则内联 CSS，随后通过 `.env` 中选定的 SMTP 主体发送邮件（纯文本+HTML双版本，支持抄送/模板附件）。  
- 其他路由：`GET /templates` 返回已注册模板的元信息；`GET /health` 用于健康检查；`GET /` 给出入门提示。

## 📧 API 使用
`POST /api/send` 请求体（固定字段）：
```json
{
  "template": "模板ID，字符串",
  "smtp_name": "可选，SMTP主体标识；省略时使用默认主体",
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
  "smtp_name": "junyan_qq",
  "subject": "服务上线通知",
  "recipient": "user@example.com",
  "cc": []
}
```
可通过 `GET /smtp-configs` 查看当前所有可用 SMTP 主体（密码默认脱敏）。

## 📁 项目结构
```
markdowm_tomail_server/
├── create_template.py       # 新建空白模板脚手架
├── deploy/                  # systemd / nginx 部署样板
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
│   ├── doubao_smoke_test/   # 最小 AI 验证模板
│   └── protein_calculation/…
├── src/
│   ├── ai/                  # 豆包服务层、AI异常、Markdown标准化
│   ├── core/
│   │   ├── renderer.py      # 处理 {{&VAR}} 占位符
│   │   └── template_registry.py
│   ├── config.py            # SMTP 配置加载（支持多主体）
│   ├── email_sender.py      # Markdown → HTML → 邮件发送
│   └── utils/
│       └── email_validator.py
├── tests/
│   ├── test_ai_service.py   # AI 服务层单测
│   └── test_ai_api.py       # AI 模板接口与错误映射单测
├── test_smtp.py             # SMTP 连通性测试
└── examples/send_email.py   # API 调用示例
```

## 🧩 模板开发约定
- 模板开发规范已收敛到 [templates/新增模板说明.md](/Users/schen/Documents/MyProjects/AetherMail-Studio/templates/%E6%96%B0%E5%A2%9E%E6%A8%A1%E6%9D%BF%E8%AF%B4%E6%98%8E.md)。
- 当前只有一种模板脚手架，AI 能力是模板内部的可选扩展点，不区分 `basic/ai` 两套生成模式。

## 🧪 测试
- `python test_smtp.py --list`：查看当前 SMTP 主体。  
- `python test_smtp.py --smtp-name huaqing_exmail`：验证指定 SMTP 主体连通性。  
- `python examples/send_email.py`：按示例模板调用 API。
- `python -m unittest tests.test_create_template`：验证统一脚手架生成结果和可选 AI hook 升级路径。
- `python -m unittest tests.test_ai_service tests.test_ai_api`：验证 AI 服务层、AI 模板错误映射和蛋白模板的 stub 渲染链路。
