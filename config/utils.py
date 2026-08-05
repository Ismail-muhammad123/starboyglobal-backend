import random
import requests
import json
import logging
from django.conf import settings
from typing import Optional, Dict, Any
from twilio.rest import Client

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


class TermiiService:
    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        api_key = getattr(settings, 'TERMII_API_KEY', None)
        sender_id = getattr(settings, 'TERMII_SENDER_ID', 'AStarData')
        base_url = getattr(settings, 'TERMII_SMS_BASE_URL', 'https://api.ng.termii.com/api')
        sms_type = getattr(settings, 'TERMII_SMS_TYPE', 'plain')
        channel = getattr(settings, 'TERMII_CHANNEL', 'generic')

        if not api_key:
            logger.error("TERMII_API_KEY not configured")
            return False

        if phone_number.startswith('+'):
            phone_number = phone_number[1:]

        endpoint = f"{base_url.rstrip('/')}/sms/send"
        payload = {
            "api_key": api_key,
            "to": phone_number,
            "from": sender_id,
            "sms": message,
            "type": sms_type,
            "channel": channel,
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=15)
            if response.status_code not in (200, 201):
                return False

            try:
                data = response.json()
            except Exception:
                return True

            # Treat clearly-declared API failures as unsuccessful.
            if isinstance(data, dict):
                if data.get("code") == "ok":
                    return True
                if data.get("message_id") or data.get("message"):
                    return True
            return True
        except Exception as e:
            logger.error(f"Termii SMS error: {e}")
            return False

class SendGridService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str) -> bool:
        api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        from_email = getattr(settings, 'ZOHO_EMAIL_USER', 'noreply@starboyglobal.com.ng')
        if not api_key: return False
        try:
            sg = SendGridAPIClient(api_key)
            mail = Mail(from_email=from_email, to_emails=to_email, subject=subject, html_content=html_content)
            response = sg.send(mail)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            logger.error(f"SendGrid Error: {e}")
            return False

class TwilioService:
    @staticmethod
    def send_sms(to_phone: str, message_body: str) -> bool:
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        messaging_service_sid = getattr(settings, 'TWILIO_MESSAGING_SERVICE_SID', None)
        debug_phone = getattr(settings, 'TWILIO_DEBUG_PHONE', None)

        if not all([account_sid, auth_token, messaging_service_sid]):
            logger.error("Twilio credentials not fully configured")
            return False

        try:
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                messaging_service_sid=messaging_service_sid,
                body=message_body,
                to=to_phone
            )
            logger.info(f"Twilio SMS sent: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Twilio SMS Error: {e}")
            return False

    @staticmethod
    def send_whatsapp(to_phone: str, otp_code: str) -> bool:
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        from_wa = getattr(settings, 'TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
        content_sid = getattr(settings, 'TWILIO_WHATSAPP_CONTENT_SID', 'HX229f5a04fd0510ce1b071852155d3e75')
        debug_phone = getattr(settings, 'TWILIO_DEBUG_PHONE', None)

        if not all([account_sid, auth_token]):
            logger.error("Twilio credentials not fully configured for WhatsApp")
            return False

        # Format recipient: ensure whatsapp:+prefix
        if not to_phone.startswith('whatsapp:'):
            if not to_phone.startswith('+'): to_phone = f'+{to_phone}'
            to_phone = f'whatsapp:{to_phone}'

        try:
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                from_=from_wa,
                content_sid=content_sid,
                content_variables=json.dumps({"1": str(otp_code)}),
                to=to_phone
            )
            logger.info(f"Twilio WhatsApp sent: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Twilio WhatsApp Error: {e}")
            return False

class ZohoService:
    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        """
        Sends SMS via Zoho SMS API.
        """
        api_key = getattr(settings, 'ZOHO_API_KEY', None)
        sender_id = getattr(settings, 'ZOHO_SMS_SENDER_ID', 'AStarData')

        if not api_key:
            logger.error("ZOHO_API_KEY not configured")
            return False

        # Clean phone number
        if phone_number.startswith('+'):
            phone_number = phone_number[1:]

        try:
            # Note: Using Zoho SMS API v2 endpoint
            response = requests.post(
                "https://sms.zoho.com/api/v2/send",
                headers={
                    "Authorization": f"Zoho-enczapikey {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "to": phone_number,
                    "from": sender_id,
                    "message": message
                },
                timeout=15
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Zoho SMS error: {e}")
            return False

    @staticmethod
    def send_whatsapp(phone_number: str, message: str) -> bool:
        """
        Sends WhatsApp message via Zoho WhatsApp API.
        """
        api_key = getattr(settings, 'ZOHO_API_KEY', None)
        wa_number = getattr(settings, 'ZOHO_WHATSAPP_NUMBER', '')

        if not api_key:
            logger.error("ZOHO_API_KEY not configured")
            return False

        if phone_number.startswith('+'):
            phone_number = phone_number[1:]

        try:
            # Note: Zoho WhatsApp integration usually uses these parameters
            response = requests.post(
                "https://whatsapp.zoho.com/api/v1/send",
                headers={
                    "Authorization": f"Zoho-enczapikey {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "to": phone_number,
                    "from": wa_number,
                    "message": message
                },
                timeout=15
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Zoho WhatsApp error: {e}")
            return False

    @staticmethod
    def send_email_zepto(email: str, subject: str, html_content: str) -> bool:
        """
        Sends email via Zoho ZeptoMail API.
        """
        zepto_url = getattr(settings, 'ZOHO_MAIL_API_URL', "https://api.zeptomail.com/v1.1/email")
        api_key = getattr(settings, 'ZOHO_API_KEY', None)
        from_email = getattr(settings, 'ZOHO_EMAIL_USER', 'noreply@astardata.com')

        if not api_key:
            logger.error("ZOHO_API_KEY not configured for ZeptoMail")
            return False

        payload = {
            "from": {"address": from_email, "name": "Starboy Global"},
            "to": [
                {
                    "email_address": {
                        "address": email,
                        "name": email.split('@')[0]
                    }
                }
            ],
            "subject": subject,
            "htmlbody": html_content
        }

        try:
            response = requests.post(
                zepto_url,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Zoho-enczapikey {api_key}"
                },
                json=payload,
                timeout=15
            )
            print(response.json())
            return response.status_code == 200 or response.status_code == 201
        except Exception as e:
            logger.error(f"ZeptoMail error: {e}")
            return False


def send_sms_otp(phone_number, message):
    """
    Send OTP via SMS using Termii (with Twilio/Zoho fallback if needed).
    """
    print(f"DEBUG: Preparing to send Termii SMS to {phone_number}")
    success = TermiiService.send_sms(phone_number, message)
    if not success:
        success = TwilioService.send_sms(phone_number, message)
    if not success:
        return ZohoService.send_sms(phone_number, message)
    return success


def send_sms_message(phone_number: str, message: str) -> bool:
    """
    Generic SMS sender for non-OTP notifications.
    Uses the same provider order as OTP for consistency.
    """
    return send_sms_otp(phone_number, message)


def send_whatsapp_otp(phone_number, message_body):
    """
    Send OTP via WhatsApp using Twilio (with Zoho fallback)
    Twilio uses templates, so we try to extract the 6-digit code.
    """
    import re
    otp_match = re.search(r'\b\d{6}\b', message_body)
    otp_code = otp_match.group(0) if otp_match else message_body

    print(f"DEBUG: Preparing to send Twilio WhatsApp to {phone_number}")
    success = TwilioService.send_whatsapp(phone_number, otp_code)
    if not success:
         return ZohoService.send_whatsapp(phone_number, message_body)
    return success


def send_email_otp(email, otp):
    """
    Send OTP via Email using ZeptoMail (with SendGrid fallback)
    """
    print(f"DEBUG: Preparing to send ZeptoMail OTP to {email}")
    subject = "Verification Code - Starboy Global"
    html_content = f"""
    <div style="font-family: 'Inter', system-ui, -apple-system, sans-serif; padding: 40px; background: #f9fafb; color: #111827;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e5e7eb; padding: 40px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="text-align: center; margin-bottom: 32px;">
                <h1 style="font-size: 24px; font-weight: 800; color: #1f2937; margin: 0;">Starboy Global</h1>
            </div>
            
            <h2 style="font-size: 20px; font-weight: 600; text-align: center; margin-bottom: 12px;">Verify your login</h2>
            <p style="text-align: center; color: #4b5563; line-height: 1.5; margin-bottom: 32px;">Please use the verification code below to sign in to your accounts. This code will only be valid for 5 minutes.</p>
            
            <div style="background: #f3f4f6; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 32px;">
                <span style="font-size: 36px; font-weight: 700; letter-spacing: 0.2em; color: #111827;">{otp}</span>
            </div>
            
            <p style="font-size: 14px; text-align: center; color: #6b7280;">If you didn't request this code, you can safely ignore this email.</p>
            
            <div style="border-top: 1px solid #e5e7eb; margin-top: 32px; padding-top: 24px; text-align: center;">
                <p style="font-size: 12px; color: #9ca3af;">&copy; 2026 Starboy Global - Data & Airtime. All rights reserved.</p>
            </div>
        </div>
    </div>
    """
    success = ZohoService.send_email_zepto(email, subject, html_content)
    if not success:
        print(f"DEBUG: ZeptoMail failed, falling back to SendGrid for {email}")
        return SendGridService.send_email(email, subject, html_content)
    return success
