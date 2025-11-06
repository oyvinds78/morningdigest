import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import base64

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class EmailSender:
    def __init__(self, auth_manager, config_loader):
        self.auth_manager = auth_manager
        self.config = config_loader
        self.gmail_service = None
        
    def send_digest(self, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Send the morning digest email"""
        try:
            # Get email configuration
            gmail_address = self.config.get('email.gmail_address') or self.config.get('GMAIL_ADDRESS')
            recipient_email = self.config.get('email.recipient_email') or self.config.get('RECIPIENT_EMAIL')
            
            if not gmail_address or not recipient_email:
                logging.error("Email addresses not configured")
                return False
            
            # Try Gmail API first, fallback to SMTP
            if self._send_via_gmail_api(gmail_address, recipient_email, subject, html_content, text_content):
                return True
            
            # Fallback to SMTP
            return self._send_via_smtp(gmail_address, recipient_email, subject, html_content, text_content)
            
        except Exception as e:
            logging.error(f"Failed to send digest email: {e}")
            return False
    
    def _send_via_gmail_api(self, sender: str, recipient: str, subject: str, 
                           html_content: str, text_content: Optional[str] = None) -> bool:
        """Send email using Gmail API"""
        try:
            # Authenticate Gmail service
            if not self.gmail_service:
                self.gmail_service = self.auth_manager.authenticate_gmail()
            
            if not self.gmail_service:
                logging.warning("Gmail API authentication failed, will try SMTP")
                return False
            
            # Create message
            message = self._create_mime_message(sender, recipient, subject, html_content, text_content)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            result = self.gmail_service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            if result:
                logging.info(f"Email sent successfully via Gmail API to {recipient}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Gmail API send failed: {e}")
            return False
    
    def _send_via_smtp(self, sender: str, recipient: str, subject: str, 
                      html_content: str, text_content: Optional[str] = None) -> bool:
        """Send email using SMTP (requires app password)"""
        try:
            # Get app password from environment or config
            import os
            app_password = os.getenv('GMAIL_APP_PASSWORD') or self.config.get('email.app_password')
            
            if not app_password:
                logging.error("Gmail app password not configured for SMTP")
                return False
            
            # Create message
            message = self._create_mime_message(sender, recipient, subject, html_content, text_content)
            
            # SMTP configuration
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            
            # Create secure connection and send
            context = ssl.create_default_context()
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(sender, app_password)
                server.send_message(message)
            
            logging.info(f"Email sent successfully via SMTP to {recipient}")
            return True
            
        except Exception as e:
            logging.error(f"SMTP send failed: {e}")
            return False
    
    def _create_mime_message(self, sender: str, recipient: str, subject: str, 
                           html_content: str, text_content: Optional[str] = None) -> MIMEMultipart:
        """Create MIME message for email"""
        
        # Create message container
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = recipient
        message["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        
        # Add custom headers
        message["X-Mailer"] = "Morning Digest AI Assistant"
        message["X-Priority"] = "3"  # Normal priority
        
        # Create text part (fallback)
        if text_content:
            text_part = MIMEText(text_content, "plain", "utf-8")
        else:
            # Create simple text version from HTML
            text_content = self._html_to_text_simple(html_content)
            text_part = MIMEText(text_content, "plain", "utf-8")
        
        # Create HTML part
        html_part = MIMEText(html_content, "html", "utf-8")
        
        # Add parts to message
        message.attach(text_part)
        message.attach(html_part)
        
        return message
    
    def _html_to_text_simple(self, html_content: str) -> str:
        """Convert HTML to simple text for fallback"""
        import re
        
        # Remove HTML tags
        text = re.sub('<.*?>', '', html_content)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Add some basic formatting
        text = text.replace('📅 KALENDER', '\n=== KALENDER ===\n')
        text = text.replace('📰 NYHETER', '\n=== NYHETER ===\n')
        text = text.replace('💻 TECH', '\n=== TECH & KARRIERE ===\n')
        text = text.replace('📧 NEWSLETTER', '\n=== NEWSLETTER-HØYDEPUNKTER ===\n')
        text = text.replace('🌤️ VÆRET', '\n=== VÆRET ===\n')
        
        return text.strip()
    
    def send_test_email(self) -> bool:
        """Send a test email to verify configuration"""
        try:
            test_subject = f"Test - Morning Digest - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            test_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Test Email</title>
            </head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">🧪 Test Email</h1>
                <p>This is a test email from your Morning Digest system.</p>
                <p><strong>Time:</strong> {time}</p>
                <p><strong>Status:</strong> ✅ Email system working correctly</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>Configuration Check:</h3>
                    <ul>
                        <li>✅ Email sending functional</li>
                        <li>✅ HTML formatting working</li>
                        <li>✅ Authentication successful</li>
                    </ul>
                </div>
                
                <p style="color: #7f8c8d; font-size: 12px;">
                    Generated by Morning Digest AI Assistant
                </p>
            </body>
            </html>
            """.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            test_text = f"""
            TEST EMAIL - Morning Digest
            
            This is a test email from your Morning Digest system.
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            Status: Email system working correctly
            
            Configuration Check:
            - Email sending functional
            - Authentication successful
            
            Generated by Morning Digest AI Assistant
            """
            
            success = self.send_digest(test_subject, test_html, test_text)
            
            if success:
                logging.info("Test email sent successfully")
                print("✅ Test email sent successfully!")
                print("Check your inbox to confirm delivery.")
            else:
                logging.error("Test email failed")
                print("❌ Test email failed to send.")
            
            return success
            
        except Exception as e:
            logging.error(f"Test email error: {e}")
            print(f"❌ Test email error: {e}")
            return False
    
    def send_error_notification(self, error_details: Dict[str, Any]) -> bool:
        """Send error notification email"""
        try:
            subject = f"❌ Morning Digest Error - {datetime.now().strftime('%Y-%m-%d')}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Morning Digest Error</title>
            </head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #e74c3c;">❌ Morning Digest Error</h1>
                <p>The morning digest encountered an error during execution.</p>
                
                <div style="background: #fff5f5; border: 1px solid #fed7d7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #e74c3c; margin-top: 0;">Error Details:</h3>
                    <p><strong>Time:</strong> {error_details.get('timestamp', 'Unknown')}</p>
                    <p><strong>Component:</strong> {error_details.get('component', 'Unknown')}</p>
                    <p><strong>Error:</strong> {error_details.get('error', 'Unknown error')}</p>
                    
                    {f"<p><strong>Stack Trace:</strong></p><pre style='background: #f7f7f7; padding: 10px; overflow-x: auto; font-size: 12px;'>{error_details.get('stack_trace', '')}</pre>" if error_details.get('stack_trace') else ''}
                </div>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">
                    <h4>Troubleshooting Steps:</h4>
                    <ol>
                        <li>Check the application logs for more details</li>
                        <li>Verify API keys and authentication</li>
                        <li>Check network connectivity</li>
                        <li>Restart the system if necessary</li>
                    </ol>
                </div>
                
                <p style="color: #7f8c8d; font-size: 12px;">
                    This is an automated error notification from Morning Digest AI Assistant
                </p>
            </body>
            </html>
            """
            
            return self.send_digest(subject, html_content)
            
        except Exception as e:
            logging.error(f"Failed to send error notification: {e}")
            return False
    
    def validate_email_config(self) -> Dict[str, bool]:
        """Validate email configuration"""
        results = {
            'gmail_address_configured': False,
            'recipient_configured': False,
            'gmail_api_available': False,
            'smtp_credentials_available': False
        }
        
        # Check email addresses
        gmail_address = self.config.get('email.gmail_address') or self.config.get('GMAIL_ADDRESS')
        recipient_email = self.config.get('email.recipient_email') or self.config.get('RECIPIENT_EMAIL')
        
        results['gmail_address_configured'] = bool(gmail_address)
        results['recipient_configured'] = bool(recipient_email)
        
        # Check Gmail API
        try:
            gmail_service = self.auth_manager.authenticate_gmail()
            results['gmail_api_available'] = bool(gmail_service)
        except Exception:
            results['gmail_api_available'] = False
        
        # Check SMTP credentials
        import os
        app_password = os.getenv('GMAIL_APP_PASSWORD') or self.config.get('email.app_password')
        results['smtp_credentials_available'] = bool(app_password)
        
        return results

# Example usage
def main():
    """Test email functionality"""
    from auth_manager import AuthManager
    from config_loader import ConfigLoader
    
    # Initialize components
    auth_manager = AuthManager()
    config_loader = ConfigLoader()
    email_sender = EmailSender(auth_manager, config_loader)
    
    print("=== Email Configuration Test ===\n")
    
    # Validate configuration
    validation = email_sender.validate_email_config()
    
    print("Email Configuration Status:")
    for item, is_valid in validation.items():
        status = "✓" if is_valid else "✗"
        readable_name = item.replace('_', ' ').title()
        print(f"{status} {readable_name}")
    
    print()
    
    # Send test email if configuration is valid
    if validation['gmail_address_configured'] and validation['recipient_configured']:
        if validation['gmail_api_available'] or validation['smtp_credentials_available']:
            test_choice = input("Send test email? (y/n): ").strip().lower()
            if test_choice == 'y':
                email_sender.send_test_email()
        else:
            print("❌ No valid authentication method available")
            print("Configure either Gmail API or SMTP app password")
    else:
        print("❌ Email addresses not configured")
        print("Set GMAIL_ADDRESS and RECIPIENT_EMAIL environment variables")

if __name__ == "__main__":
    main()