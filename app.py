"""
Markdown邮件发送系统 Flask API
"""
import logging
import os
import sys
import time
import uuid
from flask import Flask, request, jsonify, g, has_request_context
from werkzeug.middleware.proxy_fix import ProxyFix

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import load_env
from src.ai import AIConfigurationError, AIProviderError, AIResponseError
from src.core.template_registry import TemplateRegistry
from src.core.renderer import Renderer
from src.config import get_smtp_profiles_public
from src.email_sender import AttachmentData, EmailSender
from src.logging_setup import configure_logging, request_id_var
from src.utils.email_validator import validate_email

load_env()
configure_logging(force=True)
logger = logging.getLogger("app")

app = Flask(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return int(raw_value)
    except ValueError:
        logger.warning("invalid_int_env | name=%s value=%s fallback=%s", name, raw_value, default)
        return default


if _env_bool("ENABLE_PROXY_FIX", True):
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=_env_int("PROXY_FIX_X_FOR", 1),
        x_proto=_env_int("PROXY_FIX_X_PROTO", 1),
        x_host=_env_int("PROXY_FIX_X_HOST", 1),
        x_port=_env_int("PROXY_FIX_X_PORT", 1),
        x_prefix=_env_int("PROXY_FIX_X_PREFIX", 0),
    )

# 初始化核心组件
renderer = Renderer()
template_registry = TemplateRegistry()


def external_path(path: str) -> str:
    normalized_path = path if path.startswith("/") else f"/{path}"
    prefix = (request.script_root or "").rstrip("/")
    return f"{prefix}{normalized_path}" if prefix else normalized_path


def error_response(message: str, status: int = 400, **extra):
    payload = {"success": False, "error": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), status


def log_request_step(stage: str, **details):
    payload = dict(details)
    if has_request_context():
        payload.setdefault("endpoint", request.path)
    logger.info("stage=%s | %s", stage, payload)


@app.before_request
def assign_request_id():
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
    g.request_id = request_id
    g.request_start = time.time()
    g.request_id_token = request_id_var.set(request_id)


@app.after_request
def log_request_complete(response):
    duration_ms = None
    if hasattr(g, "request_start"):
        duration_ms = int((time.time() - g.request_start) * 1000)
    logger.info(
        "request_complete | method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.path,
        response.status_code,
        duration_ms,
    )
    if hasattr(g, "request_id_token"):
        request_id_var.reset(g.request_id_token)
    return response


@app.route('/', methods=['GET'])
def home():
    """首页 - 显示API使用说明"""
    return jsonify({
        "message": "📧 Markdown邮件发送系统",
        "description": "支持多模板的邮件发送系统（主题由模板定义）",
        "base_path": request.script_root or "/",
        "endpoints": {
            f"GET {external_path('/')}": "显示此帮助信息",
            f"GET {external_path('/health')}": "健康检查",
            f"GET {external_path('/templates')}": "获取可用模板列表",
            f"GET {external_path('/smtp-configs')}": "获取可用SMTP主体列表",
            f"POST {external_path('/api/send')}": "发送邮件（统一请求字段）"
        },
        "request_schema": {
            "template": "模板ID (字符串)",
            "to": "收件人邮箱 (字符串)",
            "cc": "可选，抄送列表 (数组)",
            "data": "可选，模板渲染数据对象",
            "smtp_name": "可选，发件SMTP主体标识；省略时使用默认主体"
        },
        "example": {
            "template": "notification",
            "smtp_name": "junyan_qq",
            "to": "user@example.com",
            "cc": ["cc@example.com"],
            "data": {"MESSAGE": "上线提醒", "CURRENT_TIME": "2024-06-01"}
        }
    })


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({"status": "healthy", "message": "邮件发送系统运行正常"})


@app.route('/templates', methods=['GET'])
def get_templates():
    """获取所有可用的模板"""
    return jsonify({
        "success": True,
        "templates": template_registry.list_templates(),
        "count": len(template_registry.templates)
    })


@app.route('/smtp-configs', methods=['GET'])
def get_smtp_configs():
    """获取全部SMTP主体（密码默认脱敏）"""
    smtp_configs = get_smtp_profiles_public()
    return jsonify({
        "success": True,
        "smtp_configs": smtp_configs,
        "count": len(smtp_configs)
    })


@app.route('/api/send', methods=['POST'])
def send_email():
    """发送邮件：模板ID + 请求体数据"""
    log_request_step(
        "request_received",
        remote_addr=request.remote_addr,
        content_type=request.headers.get("Content-Type"),
        content_length=request.content_length,
    )

    data = request.get_json(silent=True)
    if not data:
        log_request_step("json_parse_failed", raw_body_present=bool(request.data))
        return error_response("请求体不能为空，需要JSON格式的数据")

    template_id = data.get('template')
    recipient_email = data.get('to')
    cc_recipients = data.get('cc', []) or []
    template_data = data.get('data') or {}
    smtp_name = data.get('smtp_name')
    errors = {}
    if not template_id:
        errors['template'] = "缺少必需字段 template"
    if not recipient_email:
        errors['to'] = "缺少必需字段 to"
    elif not validate_email(recipient_email):
        errors['to'] = f"收件人邮箱格式不正确: {recipient_email}"

    if cc_recipients:
        if not isinstance(cc_recipients, list):
            errors['cc'] = "cc 必须是数组"
        else:
            invalid_cc = [addr for addr in cc_recipients if not validate_email(addr)]
            if invalid_cc:
                errors['cc'] = f"抄送邮箱格式不正确: {', '.join(invalid_cc)}"

    if not isinstance(template_data, dict):
        errors['data'] = "data 必须是对象"
    if smtp_name is not None and not isinstance(smtp_name, str):
        errors['smtp_name'] = "smtp_name 必须是字符串"

    if errors:
        log_request_step("validation_failed", errors=errors)
        return error_response("请求验证失败", 400, details=errors)

    # 获取模板定义
    template_def = template_registry.get(template_id)
    if not template_def:
        log_request_step("template_not_found", template=template_id)
        return error_response(
            f"模板不存在: {template_id}",
            404,
            available_templates=list(template_registry.templates.keys())
        )

    # 校验模板所需字段
    missing_fields = [
        field for field in template_def.required_fields
        if field not in template_data or template_data.get(field) in (None, '')
    ]
    if missing_fields:
        log_request_step("missing_template_fields", template=template_id, missing_fields=missing_fields)
        return error_response(
            "缺少必需的模板变量",
            400,
            missing_fields=missing_fields
        )

    enriched_template_data = dict(template_data)

    try:
        attachment_specs = template_def.attachments_for()
    except ValueError as exc:
        return error_response(f"模板附件配置错误: {exc}", 400, template=template_id)
    except OSError as exc:
        return error_response(f"读取模板附件失败: {exc}", 500, template=template_id)

    # 渲染 Markdown 内容
    try:
        md_content = template_def.render(enriched_template_data, renderer)
    except ValueError as exc:
        log_request_step("render_failed_value_error", template=template_id, error=str(exc))
        return error_response(str(exc), 400)
    except AIConfigurationError as exc:
        log_request_step("render_failed_ai_config", template=template_id, error=str(exc))
        return error_response(str(exc), 500, template=template_id)
    except (AIProviderError, AIResponseError) as exc:
        log_request_step("render_failed_ai_provider", template=template_id, error=str(exc))
        return error_response(str(exc), 502, template=template_id)
    except FileNotFoundError as exc:
        log_request_step("render_failed_missing_file", template=template_id, error=str(exc))
        return error_response(f"模板文件缺失: {exc}", 500)
    except Exception as exc:  # noqa: BLE001
        log_request_step("render_failed_exception", template=template_id, error=str(exc))
        return error_response(f"渲染模板失败: {exc}", 500)
    log_request_step("render_success", template=template_id)

    # 处理主题
    email_subject = template_def.default_subject

    try:
        attachments = [
            AttachmentData(
                filename=spec.path.name,
                content=spec.path.read_bytes(),
                content_id=f"{template_id}-{spec.slot}",
            )
            for spec in attachment_specs
        ]
    except OSError as exc:
        return error_response(f"读取模板附件失败: {exc}", 500, template=template_id)

    try:
        email_sender = EmailSender(smtp_name=smtp_name)
    except (KeyError, ValueError) as exc:
        error_message = exc.args[0] if exc.args else str(exc)
        return error_response(
            error_message,
            400,
            available_smtp_configs=get_smtp_profiles_public()
        )

    # 发送邮件
    success, message = email_sender.send_markdown_email(
        md_content=md_content,
        recipient=recipient_email,
        subject=email_subject,
        cc_recipients=cc_recipients,
        attachments=attachments,
    )

    if success:
        return jsonify({
            "success": True,
            "message": message,
            "template": template_id,
            "subject": email_subject,
            "recipient": recipient_email,
            "cc": cc_recipients,
            "smtp_name": email_sender.smtp_name,
            "smtp_user": email_sender.smtp_user,
            "attachment_count": len(attachments),
            "attachment_names": [attachment.filename for attachment in attachments],
        })

    log_request_step("send_failed", template=template_id, recipient=recipient_email, error=message)
    return error_response(message, 400, template=template_id)


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        "success": False,
        "error": "API端点不存在",
        "available_endpoints": [
            f"GET {external_path('/')}",
            f"GET {external_path('/health')}",
            f"GET {external_path('/templates')}",
            f"GET {external_path('/smtp-configs')}",
            f"POST {external_path('/api/send')}",
        ]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({"success": False, "error": "服务器内部错误"}), 500


if __name__ == '__main__':
    logger.info("server_starting")
    app.run(host='0.0.0.0', port=5000, debug=True)
