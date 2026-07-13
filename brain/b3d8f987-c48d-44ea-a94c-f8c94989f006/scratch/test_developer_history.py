import os
import django
import sys

# Set up django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from developer_api.models import DeveloperProfile, APIKey
from orders.models import Purchase
from rest_framework.test import APIRequestFactory, force_authenticate
from developer_api.views.purchase import DeveloperPurchaseHistoryView, DeveloperPurchaseDetailsView

User = get_user_model()

def test_endpoints():
    print("Initializing test data...")
    # Create or get users
    dev_user, _ = User.objects.get_or_create(
        phone_number="2348000000001",
        defaults={
            "email": "dev1@example.com",
            "first_name": "Dev",
            "last_name": "One",
            "role": "developer",
            "is_active": True
        }
    )
    # Ensure they have transaction pin set
    dev_user.set_transaction_pin("1234")
    dev_user.save()

    other_user, _ = User.objects.get_or_create(
        phone_number="2348000000002",
        defaults={
            "email": "other@example.com",
            "first_name": "Other",
            "last_name": "User",
            "role": "customer",
            "is_active": True
        }
    )

    # Developer Profile
    profile, _ = DeveloperProfile.objects.get_or_create(user=dev_user, defaults={"is_active": True})
    
    # API key
    key_val = APIKey.generate_key(mode='live')
    api_key, _ = APIKey.objects.get_or_create(
        profile=profile,
        mode='live',
        defaults={"key": key_val, "is_active": True}
    )

    # Let's clean existing purchases for this test to be reproducible
    Purchase.objects.filter(user__in=[dev_user, other_user]).delete()

    # Create purchases for developer
    p1 = Purchase.objects.create(
        user=dev_user,
        purchase_type="airtime",
        reference="REF-DEV-001",
        amount=100.0,
        beneficiary="08012345678",
        status="success",
        initiator="api"
    )
    p2 = Purchase.objects.create(
        user=dev_user,
        purchase_type="data",
        reference="REF-DEV-002",
        amount=500.0,
        beneficiary="08012345678",
        status="pending",
        initiator="api"
    )

    # Create purchase for other user (to test IDOR)
    p_other = Purchase.objects.create(
        user=other_user,
        purchase_type="airtime",
        reference="REF-OTHER-001",
        amount=200.0,
        beneficiary="08098765432",
        status="success",
        initiator="self"
    )

    factory = APIRequestFactory()

    print("\n--- Testing DeveloperPurchaseHistoryView ---")
    # Test listing without API Key header (Authentication)
    request = factory.get('/api/v1/developer/purchase/history/')
    view = DeveloperPurchaseHistoryView.as_view()
    response = view(request)
    print(f"No auth header status: {response.status_code} (Expected: 401/403)")

    # Test listing with correct key
    request = factory.get('/api/v1/developer/purchase/history/', HTTP_X_API_KEY=api_key.key)
    response = view(request)
    print(f"Correct key status: {response.status_code} (Expected: 200)")
    if response.status_code == 200:
        data = response.data
        results = data.get('results', data) # if paginated
        print(f"Returned {len(results)} items")
        for item in results:
            print(f"  - Ref: {item.get('reference')}, Type: {item.get('purchase_type')}, Amount: {item.get('amount')}, Status: {item.get('status')}")
        references = [item.get('reference') for item in results]
        assert "REF-DEV-001" in references
        assert "REF-DEV-002" in references
        assert "REF-OTHER-001" not in references, "IDOR: Other user's purchase returned in list!"
        print("  History list verification: PASSED (No leakage of other users' purchases)")

    print("\n--- Testing DeveloperPurchaseDetailsView ---")
    detail_view = DeveloperPurchaseDetailsView.as_view()

    # Test detail for developer's own purchase
    request = factory.get(f'/api/v1/developer/purchase/{p1.id}/', HTTP_X_API_KEY=api_key.key)
    response = detail_view(request, pk=p1.id)
    print(f"Detail status for own purchase: {response.status_code} (Expected: 200)")
    if response.status_code == 200:
        print(f"  Details: {response.data}")
        assert response.data.get('reference') == "REF-DEV-001"
        print("  Own purchase detail verification: PASSED")

    # Test detail (IDOR) for other user's purchase
    request = factory.get(f'/api/v1/developer/purchase/{p_other.id}/', HTTP_X_API_KEY=api_key.key)
    response = detail_view(request, pk=p_other.id)
    print(f"Detail status for other user's purchase (IDOR test): {response.status_code} (Expected: 404)")
    assert response.status_code == 404, f"IDOR Vulnerability: Developer accessed other user's purchase detail! Status: {response.status_code}"
    print("  IDOR test detail: PASSED (Returns 404 as expected)")

if __name__ == "__main__":
    test_endpoints()
