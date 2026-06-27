import requests

url = "https://api.sendchamp.com/api/v1/verification/create"

payload = "channel=sms&sender=&token_type=numeric&token_length=5&expiration_time=30&customer_mobile_number=2348082668519&customer_email_address=&meta_data=&in_app_token=false"
headers = {
    "Accept": "application/json,text/plain,*/*",
    "Content-Type": "application/json",
    "Authorization": "Bearer sendchamp_live_$2a$10$JI8TsjEbBwjt7kOsZzcjA.7qlZATNx/nNk6t.lhC4SKrnrZZoBxNa"
}

response = requests.request("POST", url, data=payload, headers=headers)

print(response.text)