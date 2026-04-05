import httpx
from fastapi import HTTPException

from app.config import settings


async def send_otp_sms(phone: str, code: str) -> bool:
    """Send OTP through SMS provider configured by SMS_API_URL and SMS_API_KEY."""
    # Dev/mock mode: no provider configured -> keep flow working.
    if not settings.SMS_API_URL or not settings.SMS_API_KEY:
        print(f"[DEV] OTP for {phone}: {code}")
        return True

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.SMS_API_URL,
                json={
                    "phone": phone,
                    "message": f"Verification code: {code}",
                    "api_key": settings.SMS_API_KEY,
                },
                timeout=10,
            )
        if response.status_code == 200:
            return True
    except Exception as e:
        print(f"SMS Error: {e}")
        raise HTTPException(status_code=500, detail="SMS send failed")

    raise HTTPException(status_code=500, detail="SMS provider error")
