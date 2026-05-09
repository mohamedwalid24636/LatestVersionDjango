from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)


# =========================
# 📧 EMAIL TASK
# =========================
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3
)
def send_async_email(self, subject, message, recipient_list):
    try:
        print("📧 EMAIL TASK STARTED:", recipient_list)

        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )

        print("📧 EMAIL RESULT:", result)
        return result

    except Exception as e:
        print("❌ EMAIL TASK FAILED:", str(e))
        logger.exception("Email task failed")
        raise self.retry(exc=e, countdown=10)


# =========================
# 🚨 EMERGENCY WHATSAPP TASK
# =========================
@shared_task(bind=True, max_retries=5)
def send_emergency_whatsapp_task(self, user_id, crisis_note):
    from django.contrib.auth import get_user_model
    from .models import Alert, EmergencyContact

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)

        # Create alert in system
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
                body=(
                    f"🚨 *NEUREA EMERGENCY ALERT* 🚨\n\n"
                    f"Patient: *{user.get_full_name() or user.username}*\n"
                    f"Status: High Risk Detected\n"
                    f"AI Insight: {crisis_note}\n\n"
                    f"Please contact them immediately."
                ),
                to=f"whatsapp:{clean_phone}"
            )

    except Exception as e:
        print("❌ WHATSAPP TASK FAILED:", str(e))
        raise self.retry(exc=e, countdown=20)