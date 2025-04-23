# backend/src/email_sender.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.mail_server = os.environ.get("MAIL_SERVER")
        self.mail_port = int(os.environ.get("MAIL_PORT", 587))  # Default to 587 if not set
        self.mail_username = os.environ.get("MAIL_USERNAME")
        self.mail_password = os.environ.get("MAIL_PASSWORD")
        self.mail_sender = os.environ.get("MAIL_SENDER")

        if not all([self.mail_server, self.mail_username, self.mail_password, self.mail_sender]):
            logger.error("Missing email configuration environment variables.")
            raise ValueError("Missing email configuration environment variables.")

    def send_email(self, to, subject, body):
        try:
            message = MIMEMultipart()
            message["From"] = self.mail_sender
            message["To"] = to
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.mail_server, self.mail_port) as server:
                server.starttls()
                server.login(self.mail_username, self.mail_password)
                server.sendmail(self.mail_sender, to, message.as_string())
            logger.info(f"Email sent successfully to {to}")
        except Exception as e:
            logger.error(f"Error sending email to {to}: {e}")
            raise