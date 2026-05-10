from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)

# ==============================================================================
# 📧 EMAIL TASK (GMAIL SMTP + CELERY)
# ==============================================================================

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def send_async_email(self, subject, message, recipient_list):
    try:
        print("📧 EMAIL TASK STARTED (Gmail SMTP):", recipient_list)

        # Validation
        if not recipient_list:
            raise ValueError("❌ recipient_list is empty")

        # Send email using Django SMTP
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )

        print("✅ EMAIL SENT SUCCESSFULLY (SMTP)")
        return "success"

    except Exception as e:
        print("❌ EMAIL TASK FAILED:", repr(e))
        logger.exception("Email task failed")
        raise self.retry(exc=e, countdown=10)


# ==============================================================================
# 🚨 EMERGENCY WHATSAPP TASK (UNCHANGED - TWILIO)
# ==============================================================================

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