from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.config.setting import settings
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
import logging

template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
jinja_env = Environment(
    loader=FileSystemLoader(template_dir),
    autoescape=select_autoescape(['html', 'xml'])
)


def render_template(template_name_with_folder: str, **context) -> str:
    try:
        template = jinja_env.get_template(template_name_with_folder)
        return template.render(**context)
    except Exception as e:
        logging.error(f"Failed to render Jinja2 template {template_name_with_folder}: {e}")
        raise


class MailService:
    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        if not self.api_key or self.api_key == "YOUR_SENDGRID_API_KEY_HERE":
            print("WARNING: SendGrid API key is not set. Emails will not be sent.")
            self.client = None
        else:
            self.client = SendGridAPIClient(self.api_key)
        self.sender_email = settings.MAIL_FROM_EMAIL

    def send_verification_email(
        self, to_email: str, username: str, verification_link: str
    ):
        if not self.client:
            print(
                f"Skipping email to {to_email} due to missing API key."
            )
            return

        subject = "[Husky Hold'em] - Please Verify Your Email"
        try:
            html_content = render_template(
                "email/verify_email.html",
                username=username,
                verification_link=verification_link,
            )
        except Exception:
            raise Exception(
                "Failed to prepare verification email due to a template error."
            )

        message = Mail(
            from_email=self.sender_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
        )

        try:
            response = self.client.send(message)
            print(
                f"Verification email sent to {to_email}, status code: {response.status_code}"
            )
            return response
        except Exception as e:
            print(f"Error sending verification email to {to_email}: {e}")
            print("WARNING: Email service is not properly configured. Continuing without sending email.")
            return None
