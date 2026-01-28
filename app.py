"""
Markdown邮件发送系统 Flask API
"""
import logging
import os
import sys
import time
import uuid
from flask import Flask, request, jsonify, g

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import load_env
from src.core.template_registry import TemplateRegistry
from src.core.renderer import Renderer
from src.email_sender import EmailSender
from src.logging_setup import configure_logging, request_id_var
from src.utils.email_validator import validate_email

load_env()
configure_logging(force=True)
logger = logging.getLogger("app")

app = Flask(__name__)

# 初始化核心组件
renderer = Renderer()
template_registry = TemplateRegistry()
email_sender = EmailSender()
logger.info("templates_loaded | count=%s", len(template_registry.templates))
logger.info("smtp_config_loaded")


def log_request_step(stage: str, **kwargs):
    """统一的请求日志，避免输出敏感正文，仅记录关键信息"""
    safe_kwargs = {"endpoint": "/api/send"}
    for key, val in kwargs.items():
        try:
            if key in {"request_data", "template_data"} and isinstance(val, dict):
                safe_kwargs[f"{key}_keys"] = sorted(list(val.keys()))
            elif key == "cc_recipients" and isinstance(val, list):
                safe_kwargs[key] = len(val)
            else:
                safe_kwargs[key] = val
        except Exception:
            safe_kwargs[key] = str(val)
    logger.info("stage=%s | %s", stage, safe_kwargs)


def error_response(message: str, status: int = 400, **extra):
    payload = {"success": False, "error": message}
    if extra:
        payload.update(extra)
    return jsonify(payload), status


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
        "endpoints": {
            "GET /": "显示此帮助信息",
            "GET /health": "健康检查",
            "GET /templates": "获取可用模板列表",
            "POST /api/send": "发送邮件（统一请求字段）"
        },
        "request_schema": {
            "template": "模板ID (字符串)",
            "to": "收件人邮箱 (字符串)",
            "cc": "可选，抄送列表 (数组)",
            "data": "可选，模板渲染数据对象",
            "attachments": "预留，可选"
        },
        "example": {
            "template": "notification",
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
    log_request_step(
        "parsed_request",
        template=template_id,
        recipient=recipient_email,
        cc_recipients=cc_recipients,
        request_data=template_data,
    )
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

    # 渲染 Markdown 内容
    try:
        log_request_step("render_begin", template=template_id, template_data=template_data)
        md_content = template_def.render(template_data, renderer)
    except ValueError as exc:
        log_request_step("render_failed_value_error", template=template_id, error=str(exc))
        return error_response(str(exc), 400)
    except FileNotFoundError as exc:
        log_request_step("render_failed_missing_file", template=template_id, error=str(exc))
        return error_response(f"模板文件缺失: {exc}", 500)
    except Exception as exc:  # noqa: BLE001
        log_request_step("render_failed_exception", template=template_id, error=str(exc))
        return error_response(f"渲染模板失败: {exc}", 500)
    log_request_step("render_success", template=template_id)

    # 处理主题
    email_subject = template_def.subject_for(template_data)
    if not email_subject:
        email_subject = f"来自邮件系统的{template_id}"
    log_request_step(
        "send_begin",
        template=template_id,
        recipient=recipient_email,
        cc_count=len(cc_recipients),
        subject=email_subject,
    )

    # 发送邮件
    success, message = email_sender.send_markdown_email(
        md_content=md_content,
        recipient=recipient_email,
        subject=email_subject,
        cc_recipients=cc_recipients,
    )

    if success:
        return jsonify({
            "success": True,
            "message": message,
            "template": template_id,
            "subject": email_subject,
            "recipient": recipient_email,
            "cc": cc_recipients,
        })

    log_request_step("send_failed", template=template_id, recipient=recipient_email, error=message)
    return error_response(message, 400, template=template_id)


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({
        "success": False,
        "error": "API端点不存在",
        "available_endpoints": ["GET /", "GET /health", "GET /templates", "POST /api/send"]
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({"success": False, "error": "服务器内部错误"}), 500


if __name__ == '__main__':
    logger.info("server_starting")
    app.run(host='0.0.0.0', port=5000, debug=True)
