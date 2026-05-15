from celery import shared_task
import logging
import requests
from django.conf import settings
from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)

# ======================================================================
# 📧 EMAIL TASK (FORCED ADMIN EMAIL ONLY)
# ======================================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def send_async_email(self, subject, message, recipient_list=None):
    try:
        print("📧 EMAIL TASK STARTED (ADMIN ONLY)")

        url = "https://api.resend.com/emails"

        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

        # 🔥 FORCE SINGLE ADMIN EMAIL ONLY
        payload = {
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": ["neureatreat@gmail.com"],
            "subject": subject,
            "text": message,
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code not in [200, 201]:
            raise Exception(f"Resend Error: {response.text}")

        print("✅ EMAIL SENT TO ADMIN ONLY")
        return "success"

    except Exception as e:
        print("❌ EMAIL TASK FAILED:", repr(e))
        logger.exception("Email task failed")
        raise self.retry(exc=e, countdown=10)


# ======================================================================
# 🚨 EMERGENCY WHATSAPP TASK (UNCHANGED)
# ======================================================================

@shared_task(bind=True, max_retries=5)
def send_emergency_whatsapp_task(self, user_id, crisis_note):
    from django.contrib.auth import get_user_model
    from .models import Alert, EmergencyContact

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)

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
                phone = "+2" + phone

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