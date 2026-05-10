from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)


# =========================
# 📧 EMAIL TASK (FIXED)
# =========================
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def send_async_email(self, subject, message, recipient_list):
    import requests
    try:
        print("📧 EMAIL TASK STARTED (via Resend):", recipient_list)

        # Use DEFAULT_FROM_EMAIL or EMAIL_HOST_USER as fallback
        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', ''))
        api_key = getattr(settings, 'RESEND_API_KEY', '')

        if not api_key:
            raise ValueError("RESEND_API_KEY is not set in environment or settings")
            
        if not sender:
            raise ValueError("Sender email is not set in settings")

        if not recipient_list:
            raise ValueError("No recipients provided")

        payload = {
            "from": sender,
            "to": recipient_list,
            "subject": subject,
            "text": message
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        print("🚀 Sending via Resend API...")
        response = requests.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=10)
        
        # ⚠️ اطبع الخطأ التفصيلي من Resend قبل عمل raise لتتمكن من رؤيته في سجلات Railway
        if not response.ok:
            print("❌ RESEND API ERROR DETAILS:", response.text)
            
        # Raise an exception if HTTP status code is 4xx or 5xx
        response.raise_for_status()

        print("✅ EMAIL SENT RESULT:", response.json())
        return response.json()

    except Exception as e:
        print("❌ EMAIL TASK FAILED:", repr(e))
        logger.exception("Email task failed")
        raise self.retry(exc=e, countdown=10)


# =========================
# 🚨 EMERGENCY WHATSAPP TASK (FIXED)
# =========================
@shared_task(bind=True, max_retries=5)
def send_emergency_whatsapp_task(self, user_id, crisis_note):
    from django.contrib.auth import get_user_model
    from .models import Alert, EmergencyContact

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)

        # create alert
        Alert.objects.create(
            user=user,
            message=f"🚨 WhatsApp Alert Triggered: {crisis_note}",
            type='emergency'
        )

        contacts = EmergencyContact.objects.filter(user=user)

        if not contacts.exists():
            print("⚠️ No emergency contacts found")
            return

        client = TwilioClient(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )

        for contact in contacts:
            clean_phone = str(contact.phone).replace(" ", "").strip()

            if not clean_phone.startswith('+'):
                clean_phone = '+' + clean_phone

            print("📱 Sending WhatsApp to:", clean_phone)

            client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{clean_phone}",
                body=(
                    f"🚨 *NEUREA EMERGENCY ALERT* 🚨\n\n"
                    f"Patient: *{user.get_full_name() or user.username}*\n"
                    f"Status: High Risk Detected\n"
                    f"AI Insight: {crisis_note}\n\n"
                    f"Please contact them immediately."
                )
            )

        print("📱 WhatsApp alerts sent successfully")

    except Exception as e:
        print("❌ WHATSAPP TASK FAILED:", repr(e))
        logger.exception("WhatsApp task failed")
        raise self.retry(exc=e, countdown=20)