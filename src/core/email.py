import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from .settings import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_name = settings.SMTP_FROM_NAME
    
    def send_email(
        self, 
        to_emails: List[str], 
        subject: str, 
        html_content: str, 
        text_content: str = None
    ) -> bool:
        """Send email using Google SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.smtp_user}>"
            msg['To'] = ', '.join(to_emails)
            
            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Connect to Gmail SMTP
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_verification_email(self, email: str, first_name: str, verification_token: str) -> bool:
        """Send email verification email."""
        verification_link = f"{settings.FRONTEND_URL}/auth/verify?token={verification_token}"
        
        subject = "Verify your Budget Tracker account"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
                .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; }}
                .button {{ 
                    display: inline-block; 
                    background-color: #2563eb; 
                    color: white; 
                    padding: 12px 30px; 
                    text-decoration: none; 
                    border-radius: 6px;
                    margin: 20px 0;
                }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Budget Tracker!</h1>
                </div>
                <div class="content">
                    <h2>Hi {first_name},</h2>
                    <p>Thank you for registering with Budget Tracker. Please verify your email address to complete your account setup.</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email Address</a>
                    </div>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #fffff;">{verification_link}</p>
                    
                    <p>This verification link will expire in 24 hours.</p>
                    
                    <p>If you didn't create this account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Budget Tracker. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {first_name},
        
        Thank you for registering with Budget Tracker. Please verify your email address by clicking the link below:
        
        {verification_link}
        
        This verification link will expire in 24 hours.
        
        If you didn't create this account, please ignore this email.
        
        Best regards,
        Budget Tracker Team
        """
        
        return self.send_email([email], subject, html_content, text_content)
    
    def send_password_reset_email(self, email: str, first_name: str, reset_token: str) -> bool:
        """Send password reset email."""
        reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
        
        subject = "Reset your Budget Tracker password"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
                .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; }}
                .button {{ 
                    display: inline-block; 
                    background-color: #dc2626; 
                    color: white; 
                    padding: 12px 30px; 
                    text-decoration: none; 
                    border-radius: 6px;
                    margin: 20px 0;
                }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; }}
                .warning {{ 
                    background-color: #fef3c7; 
                    border: 1px solid #f59e0b; 
                    border-radius: 6px; 
                    padding: 15px; 
                    margin: 20px 0;
                    color: #92400e;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <h2>Hi {first_name},</h2>
                    <p>We received a request to reset your Budget Tracker account password.</p>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong> If you didn't request this password reset, please ignore this email. Your account is secure.
                    </div>
                    
                    <p>To reset your password, click the button below:</p>
                    
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </div>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{reset_link}</p>
                    
                    <p><strong>This reset link will expire in 24 hours.</strong></p>
                    
                    <p>For security reasons, you'll need to create a new password that:</p>
                    <ul>
                        <li>Is at least 8 characters long</li>
                        <li>Contains at least one uppercase letter</li>
                        <li>Contains at least one lowercase letter</li>
                        <li>Contains at least one number</li>
                    </ul>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Budget Tracker. All rights reserved.</p>
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {first_name},
        
        We received a request to reset your Budget Tracker account password.
        
        SECURITY NOTICE: If you didn't request this password reset, please ignore this email. Your account is secure.
        
        To reset your password, click the link below:
        {reset_link}
        
        This reset link will expire in 24 hours.
        
        Best regards,
        Budget Tracker Team
        
        This is an automated message, please do not reply to this email.
        """
        
        return self.send_email([email], subject, html_content, text_content)

# Create email service instance
email_service = EmailService()