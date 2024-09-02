import smtplib
import os
from email.message import EmailMessage
import config

class EmailClient:
    def __init__(self):
        self.sender_email = os.getenv('EMAIL_ADDRESS')
        self.sender_password = os.getenv('EMAIL_PASSWORD')
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.receiver_email = os.getenv('TO_EMAIL')
        self.cc_emails = os.getenv('CC_EMAILS')

    def send_email(self, subject, body, is_html=False):
        """
        Sends an email with the given subject and body.

        :param subject: The subject of the email.
        :param body: The body content of the email.
        :param is_html: If True, sends the email as HTML.
        """
        msg = EmailMessage()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        msg['Subject'] = subject

        if self.cc_emails:
            cc_list = self.cc_emails.split(",")
            msg['Cc'] = ", ".join(cc_list)
        else:
            cc_list = []

        if is_html:
            msg.add_alternative(body, subtype='html')
        else:
            msg.set_content(body)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                config.app_logger.info("Email sent successfully to %s", self.receiver_email)
                if cc_list:
                    config.app_logger.info("CC'd to %s", ", ".join(cc_list))
        except Exception as e:
            config.app_logger.error("Failed to send email: %s", str(e))
