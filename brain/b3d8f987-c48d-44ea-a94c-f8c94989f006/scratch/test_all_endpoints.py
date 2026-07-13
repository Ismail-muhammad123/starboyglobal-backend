import os
import django
import sys

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from orders.models import DataService, DataVariation, AirtimeNetwork

User = get_user_model()

def test_endpoints():
    print("Setting up data for endpoints test...")
    user, _ = User.objects.get_or_create(
        phone_number="2348011112222",
        defaults={
            "email": "user@example.com",
            "first_name": "Test",
            "last_name": "User",
            "role": "customer",
            "is_active": True
        }
    )
    user.set_password("password123")
    user.save()

    # Create dummy networks & plans if none exist
    if not AirtimeNetwork.objects.exists():
        AirtimeNetwork.objects.create(
            service_name="MTN Airtime",
            service_id="mtn",
            min_amount="50",
            max_amount="1000",
            discount="2.0",
            cost_price=100.0,
            selling_price=100.0
        )
    if not DataService.objects.exists():
        ds = DataService.objects.create(
            service_name="MTN Data",
            service_id="mtn-data",
            is_active=True
        )
        DataVariation.objects.create(
            service=ds,
            name="1GB",
            variation_id="mtn-1gb",
            cost_price=300.0,
            selling_price=350.0,
            is_active=True
        )

    client = APIClient()
    client.force_authenticate(user=user)

    # 1. Test Airtime Networks
    print("\nTesting: GET /api/orders/airtime-networks/")
    response = client.get('/api/orders/airtime-networks/')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.json() if response.status_code == 200 else response.content}")
    assert response.status_code == 200

    # 2. Test Data Plans
    print("\nTesting: GET /api/orders/data-plans/")
    response = client.get('/api/orders/data-plans/')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.json() if response.status_code == 200 else response.content}")
    assert response.status_code == 200

    # 3. Test User Purchase History
    print("\nTesting: GET /api/orders/purchase-history/")
    response = client.get('/api/orders/purchase-history/')
    print(f"Status: {response.status_code}")
    print(f"Data: {response.json() if response.status_code == 200 else response.content}")
    assert response.status_code == 200

    print("\nAll User endpoints respond correctly and successfully!")

if __name__ == "__main__":
    test_endpoints()
