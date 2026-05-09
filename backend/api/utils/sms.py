from django.conf import settings
from twilio.rest import Client as TwilioClient

def trigger_emergency_protocol(user, crisis_note):
    from ..models import Alert, EmergencyContact
    
    # Create database record of the alert
    Alert.objects.create(
        user=user,
        message=f"🚨 WhatsApp Alert Triggered: {crisis_note}",
        type='emergency'
    )
    
    contacts = EmergencyContact.objects.filter(user=user)
    
    if contacts.exists():
        try:
            client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            for contact in contacts:
                # Clean the phone number (remove spaces)
                clean_phone = str(contact.phone).replace(" ", "").strip()
                if not clean_phone.startswith('+'):
                    clean_phone = '+' + clean_phone

                # Send via WhatsApp
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
                print(f"WhatsApp message sent to {clean_phone}")
        except Exception as e:
            print(f"WhatsApp Delivery Error: {e}")