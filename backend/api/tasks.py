from celery import shared_task
from django.conf import settings
import logging
import requests

from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)

# =========================
# 📧 EMAIL TASK (RESEND FIXED + PRODUCTION SAFE)
# =========================
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def send_async_email(self, subject, message, recipient_list):
    try:
        print("📧 EMAIL TASK STARTED (Resend):", recipient_list)

        api_key = getattr(settings, 'RESEND_API_KEY', None)
        sender = getattr(settings, 'DEFAULT_FROM_EMAIL', None)

        if not api_key:
            raise ValueError("❌ RESEND_API_KEY is missing")

        if not sender:
            raise ValueError("❌ DEFAULT_FROM_EMAIL is missing")

        if not recipient_list:
            raise ValueError("❌ recipient_list is empty")

        # Resend requires SINGLE email string (not list)
        to_email = recipient_list[0]

        payload = {
            "from": sender,
            "to": to_email,
            "subject": subject,
            "text": message
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        print("🚀 Sending request to Resend...")

        response = requests.post(
            "https://api.resend.com/emails",
            json=payload,
            headers=headers,
            timeout=10
        )

        # مهم جدًا: اطبع التفاصيل قبل أي exception
        print("📡 STATUS CODE:", response.status_code)
        print("📡 RESPONSE:", response.text)

        if not response.ok:
            raise Exception(f"Resend Error: {response.text}")

        print("✅ EMAIL SENT SUCCESSFULLY")
        return response.json()

    except Exception as e:
        print("❌ EMAIL TASK FAILED:", repr(e))
        logger.exception("Email task failed")
        raise self.retry(exc=e, countdown=10)


# =========================
# 🚨 EMERGENCY WHATSAPP TASK (CLEAN + SAFE)
# =========================
@shared_task(bind=True, max_retries=5)
def send_emergency_whatsapp_task(self, user_id, crisis_note):
    from django.contrib.auth import get_user_model
    from .models import Alert, EmergencyContact

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)

        # Create alert
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
            phone = str(contact.phone).strip().replace(" ", "")

            if not phone.startswith("+"):
                phone = "+" + phone

            print("📱 Sending WhatsApp to:", phone)

            client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}",
                to=f"whatsapp:{phone}",
                body=(
                    "🚨 *NEUREA EMERGENCY ALERT* 🚨\n\n"
                    f"Patient: *{user.get_full_name() or user.username}*\n"
                    "Status: High Risk Detected\n"
                    f"AI Insight: {crisis_note}\n\n"
                    "Please contact them immediately."
                )
            )

        print("📱 WhatsApp alerts sent successfully")

    except Exception as e:
        print("❌ WHATSAPP TASK FAILED:", repr(e))
        logger.exception("WhatsApp task failed")
        raise self.retry(exc=e, countdown=20)