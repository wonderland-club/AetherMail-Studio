"""
邮件发送核心功能
"""
import mimetypes
import smtplib
import ssl
from email.utils import formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Tuple
import pypandoc
try:
    from premailer import transform
    PREMAILER_AVAILABLE = True
except ImportError:
    PREMAILER_AVAILABLE = False
    print("⚠️ Premailer不可用，将使用基础HTML")

from .config import get_smtp_profile

class AttachmentData:
    """附件数据类"""
    def __init__(
        self,
        filename: str,
        content: bytes,
        content_type: Optional[str] = None,
        content_id: Optional[str] = None,
    ):
        self.filename = filename
        self.content = content
        self.content_type = content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.content_id = content_id

class EmailSender:
    """邮件发送器"""
    
    def __init__(self, smtp_name: Optional[str] = None):
        self.profile = get_smtp_profile(smtp_name)
        self.smtp_server = self.profile.host
        self.smtp_port = self.profile.port
        self.smtp_user = self.profile.user
        self.smtp_password = self.profile.password
        self.smtp_secure = self.profile.secure
        self.sender_name = self.profile.sender_name
        self.smtp_name = self.profile.smtp_name

    def _connect_server(self, context: ssl.SSLContext):
        """根据安全模式建立SMTP连接"""
        if self.smtp_secure == 'ssl':
            return smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)

        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        return server
    
    def _convert_md_to_html(self, md_text: str) -> Tuple[Optional[str], Optional[str]]:
        """将Markdown转换为HTML"""
        try:
            # 使用pypandoc将MD转为HTML
            html_content = pypandoc.convert_text(
                md_text,
                'html',
                format='md',
                extra_args=['--wrap=none']
            )
            
            # 添加邮件友好的CSS样式
            basic_css = """
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                font-size: 14px; 
                line-height: 1.6; 
                color: #333 !important; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px;
                background-color: #ffffff;
            }
            h1, h2, h3, h4, h5, h6 { 
                color: #2c3e50; 
                margin-top: 25px; 
                margin-bottom: 15px;
            }
            h1 { font-size: 2.2em; border-bottom: 3px solid #e74c3c; padding-bottom: 10px; }
            h2 { font-size: 1.8em; border-bottom: 2px solid #3498db; padding-bottom: 8px; }
            h3 { font-size: 1.5em; color: #8e44ad; }
            p { 
                margin: 15px 0; 
                text-align: justify;
            }
            ul, ol { 
                margin: 15px 0; 
                padding-left: 30px; 
            }
            li { margin: 8px 0; }
            code { 
                background-color: #f8f9fa; 
                padding: 2px 6px; 
                border-radius: 4px; 
                font-family: 'Courier New', monospace;
                color: #e74c3c;
            }
            pre {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #3498db;
                overflow-x: auto;
            }
            blockquote {
                border-left: 4px solid #bdc3c7;
                margin: 20px 0;
                padding: 10px 20px;
                background-color: #f9f9f9;
                font-style: italic;
            }
            a:link, a:visited { 
                color: #3498db; 
                text-decoration: none; 
            }
            a:hover { 
                color: #2980b9; 
                text-decoration: underline;
            }
            .im { 
                color: #333 !important; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                font-size: 14px; 
                line-height: 1.6; 
            }
            div[style*="color"] {
                color: inherit !important;
            }
            span[style*="color"] {
                color: inherit !important;
            }
            """
            
            html_with_css = f"<style>{basic_css}</style><div class='email-content'>{html_content}</div>"
            
            # 使用premailer内联CSS（如果可用）
            if PREMAILER_AVAILABLE:
                try:
                    inlined_html = transform(html_with_css)
                except Exception:
                    inlined_html = html_with_css
            else:
                inlined_html = html_with_css
            
            return inlined_html, None
            
        except Exception as e:
            return None, f"Markdown转HTML失败: {str(e)}"
    
    def _build_message(
        self,
        html_content: str,
        plain_text: str,
        recipient: str,
        subject: str,
        cc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[AttachmentData]] = None,
    ) -> Tuple[MIMEMultipart, List[str]]:
        """构建带附件的MIME邮件"""
        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = formataddr((self.sender_name, self.smtp_user)) if self.sender_name else self.smtp_user
        msg['To'] = recipient

        if cc_recipients:
            msg['Cc'] = ', '.join(cc_recipients)

        body_part = MIMEMultipart('alternative')
        body_part.attach(MIMEText(plain_text, 'plain', 'utf-8'))
        body_part.attach(MIMEText(html_content, 'html', 'utf-8'))
        msg.attach(body_part)

        if attachments:
            for attachment in attachments:
                maintype, subtype = attachment.content_type.split('/', 1)
                part = MIMEBase(maintype, subtype)
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.set_param('name', attachment.filename, header='Content-Type', charset='utf-8')
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=('utf-8', '', attachment.filename),
                )
                if attachment.content_id:
                    part['Content-ID'] = f"<{attachment.content_id}>"
                    part['X-Attachment-Id'] = attachment.content_id
                msg.attach(part)

        recipients = [recipient]
        if cc_recipients:
            recipients.extend(cc_recipients)

        return msg, recipients

    def _send_email(self, html_content: str, plain_text: str, recipient: str,
                   subject: str, cc_recipients: Optional[List[str]] = None,
                   attachments: Optional[List[AttachmentData]] = None) -> Tuple[bool, str]:
        """发送邮件"""
        try:
            # 创建SSL上下文
            context = ssl.create_default_context()

            # 连接到SMTP服务器
            server = self._connect_server(context)
            server.login(self.smtp_user, self.smtp_password)

            msg, recipients = self._build_message(
                html_content=html_content,
                plain_text=plain_text,
                recipient=recipient,
                subject=subject,
                cc_recipients=cc_recipients,
                attachments=attachments,
            )

            # 发送邮件
            server.sendmail(self.smtp_user, recipients, msg.as_string())
            server.quit()

            return True, f"邮件发送成功 (SMTP: {self.smtp_name})"

        except smtplib.SMTPAuthenticationError as e:
            return False, f"SMTP认证失败，请检查邮箱和授权码: {str(e)}"
        except smtplib.SMTPConnectError as e:
            return False, f"SMTP连接失败，请检查网络连接: {str(e)}"
        except smtplib.SMTPException as e:
            return False, f"SMTP错误: {str(e)}"
        except Exception as e:
            return False, f"邮件发送失败: {str(e)}"
    
    def send_markdown_email(self, md_content: str, recipient: str, subject: str,
                          cc_recipients: Optional[List[str]] = None,
                          attachments: Optional[List[AttachmentData]] = None) -> Tuple[bool, str]:
        """发送Markdown邮件"""
        
        # 转换Markdown为HTML
        html_content, error = self._convert_md_to_html(md_content)
        if error:
            return False, error
        
        # 发送邮件
        success, message = self._send_email(
            html_content=html_content,
            plain_text=md_content,  # 原始MD作为纯文本版本
            recipient=recipient,
            subject=subject,
            cc_recipients=cc_recipients,
            attachments=attachments
        )
        
        return success, message
