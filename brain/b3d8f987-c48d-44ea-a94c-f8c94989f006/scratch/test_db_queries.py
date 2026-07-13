import os
import django
import sys

# Set up django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from orders.models import (
    DataVariation, AirtimeNetwork, ElectricityVariation, TVVariation, 
    InternetVariation, EducationVariation, Purchase
)
from orders.serializers import PurchaseSerializer
from orders.serializers.variations import DataVariationSerializer

try:
    print("Testing PurchaseSerializer...")
    # Fetch a purchase if it exists, or serialize None
    purchases = Purchase.objects.all()[:5]
    print(f"Found {len(purchases)} purchases")
    for p in purchases:
        try:
            ser = PurchaseSerializer(p)
            data = ser.data
            print(f"Serialized purchase {p.id}: {data.get('service_details')}")
        except Exception as ex:
            print(f"Error serializing purchase {p.id}: {ex}")
            import traceback
            traceback.print_exc()

    print("\nTesting DataVariationSerializer...")
    plans = DataVariation.objects.all()[:5]
    print(f"Found {len(plans)} plans")
    for p in plans:
        try:
            ser = DataVariationSerializer(p)
            data = ser.data
            print(f"Serialized plan {p.id}: selling_price={data.get('selling_price')}, agent_price={data.get('agent_price')}, developer_price={data.get('developer_price')}")
        except Exception as ex:
            print(f"Error serializing plan {p.id}: {ex}")
            import traceback
            traceback.print_exc()

except Exception as e:
    print(f"Global error: {e}")
    import traceback
    traceback.print_exc()
