"""
邮件发送核心功能
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Tuple, Dict, Any
import pypandoc
try:
    from premailer import transform
    PREMAILER_AVAILABLE = True
except ImportError:
    PREMAILER_AVAILABLE = False
    print("⚠️ Premailer不可用，将使用基础HTML")
import os

from .config import SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, DEFAULT_SENDER_NAME

class AttachmentData:
    """附件数据类"""
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.content = content

class EmailSender:
    """邮件发送器"""
    
    def __init__(self):
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_password = SMTP_PASSWORD
        self.sender_name = DEFAULT_SENDER_NAME
    
    def _convert_md_to_html(self, md_text: str) -> Tuple[Optional[str], Optional[str]]:
        """将Markdown转换为HTML"""
        try:
            # 使用pypandoc将MD转为HTML
            html_content = pypandoc.convert_text(
                md_text, 
                'html', 
                format='md',
                extra_args=['--standalone']
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
                except Exception as premailer_error:
                    print(f"⚠️ Premailer处理失败，使用原始HTML: {premailer_error}")
                    inlined_html = html_with_css
            else:
                inlined_html = html_with_css
            
            return inlined_html, None
            
        except Exception as e:
            return None, f"Markdown转HTML失败: {str(e)}"
    
    def _send_email(self, html_content: str, plain_text: str, mail_recipient: str,
                   subject: str, cc_recipients: Optional[List[str]] = None,
                   attachments: Optional[List[AttachmentData]] = None) -> Tuple[bool, str]:
        """发送邮件"""
        try:
            # 创建SSL上下文
            context = ssl.create_default_context()
            
            # 连接到SMTP服务器
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
            server.login(self.smtp_user, self.smtp_password)
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = mail_recipient
            
            if cc_recipients:
                msg['Cc'] = ', '.join(cc_recipients)
            
            # 添加邮件内容（纯文本 + HTML）
            msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 添加附件
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.content)
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment.filename}'
                    )
                    msg.attach(part)
            
            # 准备收件人列表
            recipients = [mail_recipient]
            if cc_recipients:
                recipients.extend(cc_recipients)
            
            # 发送邮件
            server.sendmail(self.smtp_user, recipients, msg.as_string())
            server.quit()
            
            return True, "邮件发送成功"
            
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
            mail_recipient=recipient,
            subject=subject,
            cc_recipients=cc_recipients,
            attachments=attachments
        )
        
        return success, message