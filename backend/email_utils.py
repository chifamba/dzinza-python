# backend/email_utils.py
import smtplib
from email.mime.text import MIMEText
import structlog

# Assuming your application config instance is available via this import path
# Adjust if your config is located elsewhere or named differently
from backend.config import config as app_config

logger = structlog.get_logger(__name__)

def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Sends an email using SMTP settings from the application configuration.

    Args:
        to_email: The recipient's email address.
        subject: The subject of the email.
        html_body: The HTML content of the email.

    Returns:
        True if the email was sent successfully (or appeared to be in a sandbox), False otherwise.
    """
    # Ensure all necessary configurations are present
    if not all([app_config.EMAIL_SERVER, 
                app_config.EMAIL_PORT, 
                app_config.MAIL_SENDER_EMAIL, # Check for sender email
                app_config.EMAIL_USERNAME, # Username for login
                app_config.EMAIL_PASSWORD]): # Password for login
        logger.error("Email configuration is incomplete. Cannot send email.",
                     server_set=bool(app_config.EMAIL_SERVER),
                     port_set=bool(app_config.EMAIL_PORT),
                     sender_email_set=bool(app_config.MAIL_SENDER_EMAIL),
                     username_set=bool(app_config.EMAIL_USERNAME))
        return False

    try:
        msg = MIMEText(html_body, 'html')
        # Use MAIL_SENDER_NAME and MAIL_SENDER_EMAIL for the 'From' header
        msg['From'] = f"{app_config.MAIL_SENDER_NAME} <{app_config.MAIL_SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        logger.info("Attempting to send email", 
                    to=to_email, 
                    subject=subject, 
                    from_addr=msg['From'],
                    server=app_config.EMAIL_SERVER,
                    port=app_config.EMAIL_PORT,
                    use_tls=app_config.EMAIL_USE_TLS)

        with smtplib.SMTP(app_config.EMAIL_SERVER, app_config.EMAIL_PORT) as server:
            if app_config.EMAIL_USE_TLS:
                server.starttls()
            # Only attempt login if username and password are provided
            if app_config.EMAIL_USERNAME and app_config.EMAIL_PASSWORD:
                server.login(app_config.EMAIL_USERNAME, app_config.EMAIL_PASSWORD)
            else:
                logger.info("Proceeding with email sending without SMTP authentication (no username/password configured).")

            server.sendmail(app_config.MAIL_SENDER_EMAIL, [to_email], msg.as_string())
        
        logger.info(f"Email successfully sent (or simulated) to {to_email} with subject: {subject}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error sending email to {to_email}: {e}", exc_info=False) # exc_info=False for auth errors
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"SMTP Server Disconnected error sending email to {to_email}: {e}", exc_info=True)
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP Connection Error sending email to {to_email}: {e}", exc_info=True)
    except smtplib.SMTPException as e: # Catch other SMTPlib specific exceptions
        logger.error(f"SMTP Error sending email to {to_email}: {e}", exc_info=True)
    except ConnectionRefusedError as e: # Specific catch for connection refused
        logger.error(f"Connection Refused Error sending email to {to_email} (server: {app_config.EMAIL_SERVER}:{app_config.EMAIL_PORT}): {e}", exc_info=True)
    except OSError as e: # Catch other OS-level errors like "Temporary failure in name resolution"
         logger.error(f"OS Error (e.g., name resolution) sending email to {to_email}: {e}", exc_info=True)
    except Exception as e:
        # Generic catch for any other unexpected errors
        logger.error(f"Unexpected error sending email to {to_email}: {e}", exc_info=True)
    
    # If any exception occurred, return False
    return False
