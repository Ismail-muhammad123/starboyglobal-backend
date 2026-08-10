import requests
import logging
from typing import Dict, Any, List, Optional
from ..interfaces import BaseVTUProvider

logger = logging.getLogger(__name__)

# =============================================================================
# Hardcoded plan catalogs — Arewa Global does not expose listing endpoints.
# Update plan IDs and prices from the Arewa Global dashboard as needed.
# =============================================================================

AIRTIME_NETWORKS_DATA = [
    {"service_id": "1", "service_name": "MTN", "min_amount": "50", "max_amount": "50000"},
    {"service_id": "2", "service_name": "Airtel", "min_amount": "50", "max_amount": "50000"},
    {"service_id": "3", "service_name": "Glo", "min_amount": "50", "max_amount": "50000"},
    {"service_id": "4", "service_name": "9mobile", "min_amount": "50", "max_amount": "50000"},
]

DATA_PLANS_BY_NETWORK = {
    # ── MTN (network id "1") ────────────────────────────────────────────
    "1": {
        "name": "MTN",
        "plans": [
            # SME
            {"plan_id": "284", "name": "MTN SME 500MB (30 Days)", "selling_price": 440, "plan_type": "sme"},
            {"plan_id": "282", "name": "MTN SME 1.0GB (30 Days)", "selling_price": 650, "plan_type": "sme"},
            {"plan_id": "283", "name": "MTN SME 2.0GB (30 Days)", "selling_price": 1300, "plan_type": "sme"},
            {"plan_id": "484", "name": "MTN SME 3.0GB (30 Days)", "selling_price": 2000, "plan_type": "sme"},
            {"plan_id": "483", "name": "MTN SME 5.0GB (30 Days)", "selling_price": 3000, "plan_type": "sme"},
            {"plan_id": "409", "name": "MTN SME 3.5GB (7 Days)", "selling_price": 1500, "plan_type": "sme"},
            {"plan_id": "499", "name": "MTN SME 3.5GB (1 Day)", "selling_price": 1200, "plan_type": "sme"},
            {"plan_id": "487", "name": "MTN SME 11.0GB (7 Days)", "selling_price": 4000, "plan_type": "sme"},
            {"plan_id": "500", "name": "MTN SME 11.0GB (30 Days)", "selling_price": 6000, "plan_type": "sme"},
            {"plan_id": "497", "name": "MTN SME 14.5GB (30 Days)", "selling_price": 5050, "plan_type": "sme"},
            {"plan_id": "488", "name": "MTN SME 20.0GB (7 Days)", "selling_price": 5500, "plan_type": "sme"},
            {"plan_id": "496", "name": "MTN SME 20.0GB (7 Days) Alt", "selling_price": 5050, "plan_type": "sme"},
            {"plan_id": "490", "name": "MTN SME 20.0GB + 10 Min Call (30 Days)", "selling_price": 8000, "plan_type": "sme"},
            {"plan_id": "498", "name": "MTN SME 36.0GB (7 Days)", "selling_price": 11500, "plan_type": "sme"},
            # Gifting
            {"plan_id": "260", "name": "MTN GIFTING 75MB (1 Day)", "selling_price": 80, "plan_type": "gifting"},
            {"plan_id": "375", "name": "MTN GIFTING 200MB Social (1 Day)", "selling_price": 120, "plan_type": "gifting"},
            {"plan_id": "376", "name": "MTN GIFTING 230MB (1 Day)", "selling_price": 210, "plan_type": "gifting"},
            {"plan_id": "377", "name": "MTN GIFTING 500MB (1 Day)", "selling_price": 350, "plan_type": "gifting"},
            {"plan_id": "380", "name": "MTN GIFTING 1GB + 1.5 Min Call (1 Day)", "selling_price": 500, "plan_type": "gifting"},
            {"plan_id": "378", "name": "MTN GIFTING 1.2GB Social (30 Days)", "selling_price": 450, "plan_type": "gifting"},
            {"plan_id": "382", "name": "MTN GIFTING 1.5GB (2 Days)", "selling_price": 600, "plan_type": "gifting"},
            {"plan_id": "386", "name": "MTN GIFTING 1.5GB (7 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "383", "name": "MTN GIFTING 2.0GB (2 Days)", "selling_price": 750, "plan_type": "gifting"},
            {"plan_id": "385", "name": "MTN GIFTING 2.5GB (2 Days)", "selling_price": 900, "plan_type": "gifting"},
            {"plan_id": "387", "name": "MTN GIFTING 3.2GB (2 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "379", "name": "MTN GIFTING 500MB (7 Days)", "selling_price": 500, "plan_type": "gifting"},
            {"plan_id": "381", "name": "MTN GIFTING 600MB (7 Days)", "selling_price": 550, "plan_type": "gifting"},
            {"plan_id": "384", "name": "MTN GIFTING 1.0GB (7 Days)", "selling_price": 800, "plan_type": "gifting"},
            {"plan_id": "388", "name": "MTN GIFTING 11.0GB (7 Days)", "selling_price": 3550, "plan_type": "gifting"},
            {"plan_id": "394", "name": "MTN GIFTING 11.0GB (7 Days) Alt", "selling_price": 3600, "plan_type": "gifting"},
            {"plan_id": "390", "name": "MTN GIFTING 6.0GB (7 Days)", "selling_price": 2500, "plan_type": "gifting"},
            {"plan_id": "389", "name": "MTN GIFTING 1.8GB (30 Days)", "selling_price": 1500, "plan_type": "gifting"},
            {"plan_id": "395", "name": "MTN GIFTING 14.5GB (30 Days)", "selling_price": 5000, "plan_type": "gifting"},
            {"plan_id": "391", "name": "MTN GIFTING 5.5GB (30 Days)", "selling_price": 3000, "plan_type": "gifting"},
            {"plan_id": "397", "name": "MTN GIFTING 7.0GB (30 Days)", "selling_price": 3500, "plan_type": "gifting"},
            {"plan_id": "399", "name": "MTN GIFTING 25.0GB (30 Days)", "selling_price": 9000, "plan_type": "gifting"},
            {"plan_id": "400", "name": "MTN GIFTING 36.0GB (30 Days)", "selling_price": 11000, "plan_type": "gifting"},
            {"plan_id": "398", "name": "MTN GIFTING 35.0GB (30 Days)", "selling_price": 7000, "plan_type": "gifting"},
            {"plan_id": "401", "name": "MTN GIFTING 65.0GB (30 Days)", "selling_price": 16000, "plan_type": "gifting"},
            {"plan_id": "402", "name": "MTN GIFTING 75.0GB (30 Days)", "selling_price": 18000, "plan_type": "gifting"},
            {"plan_id": "403", "name": "MTN GIFTING 90.0GB (30 Days)", "selling_price": 25000, "plan_type": "gifting"},
            # Direct
            {"plan_id": "373", "name": "MTN DIRECT 1.8GB + 35 Min + 150 SMS (30 Days)", "selling_price": 1550, "plan_type": "direct"},
            {"plan_id": "374", "name": "MTN DIRECT 5GB + 90 Min + 220 SMS (30 Days)", "selling_price": 3100, "plan_type": "direct"},
            {"plan_id": "486", "name": "MTN DIRECT 1GB + 250 Min + 75 SMS (30 Days)", "selling_price": 3100, "plan_type": "direct"},
            # Data (Voice + Data combos)
            {"plan_id": "470", "name": "MTN Voice 10 Min + 400MB + 5 SMS (7 Days)", "selling_price": 500, "plan_type": "general"},
            {"plan_id": "471", "name": "MTN Voice 20 Min + 1.2GB + 5 SMS (7 Days)", "selling_price": 1000, "plan_type": "general"},
            {"plan_id": "472", "name": "MTN Voice 40 Min + 2.5GB + 5 SMS (7 Days)", "selling_price": 2000, "plan_type": "general"},
            {"plan_id": "469", "name": "MTN Voice 100 Min + 12GB + 5 SMS (30 Days)", "selling_price": 5000, "plan_type": "general"},
            {"plan_id": "366", "name": "MTN DATA 2GB + 2 Min (30 Days)", "selling_price": 1600, "plan_type": "general"},
            {"plan_id": "367", "name": "MTN DATA 2.7GB + 2 Min (30 Days)", "selling_price": 2000, "plan_type": "general"},
            {"plan_id": "368", "name": "MTN DATA 3.5GB + 5 Min (30 Days)", "selling_price": 2500, "plan_type": "general"},
            {"plan_id": "372", "name": "MTN DATA 10GB + 10 Min (30 Days)", "selling_price": 4500, "plan_type": "general"},
            {"plan_id": "393", "name": "MTN 16.5GB + 10 Min (30 Days)", "selling_price": 6500, "plan_type": "general"},
        ]
    },

    # ── AIRTEL (network id "2") ─────────────────────────────────────────
    "2": {
        "name": "Airtel",
        "plans": [
            # Awoof (cheapest)
            {"plan_id": "443", "name": "Airtel Awoof 150MB (2 Days)", "selling_price": 70, "plan_type": "gifting"},
            {"plan_id": "444", "name": "Airtel Awoof 300MB (2 Days)", "selling_price": 140, "plan_type": "gifting"},
            {"plan_id": "450", "name": "Airtel GIFTING 200MB (1 Day)", "selling_price": 210, "plan_type": "gifting"},
            {"plan_id": "449", "name": "Airtel GIFTING 110MB (1 Day)", "selling_price": 105, "plan_type": "gifting"},
            {"plan_id": "451", "name": "Airtel GIFTING 300MB Social (3 Days)", "selling_price": 310, "plan_type": "gifting"},
            {"plan_id": "445", "name": "Airtel Awoof 600MB (2 Days)", "selling_price": 250, "plan_type": "gifting"},
            {"plan_id": "448", "name": "Airtel GIFTING 500MB (7 Days)", "selling_price": 481, "plan_type": "gifting"},
            {"plan_id": "446", "name": "Airtel Awoof 2.0GB (2 Days)", "selling_price": 700, "plan_type": "gifting"},
            {"plan_id": "453", "name": "Airtel GIFTING 1.5GB (2 Days)", "selling_price": 600, "plan_type": "gifting"},
            {"plan_id": "459", "name": "Airtel GIFTING 3.0GB (2 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "491", "name": "Airtel Awoof 3.0GB (7 Days)", "selling_price": 850, "plan_type": "gifting"},
            {"plan_id": "447", "name": "Airtel Awoof 1.5GB (7 Days)", "selling_price": 600, "plan_type": "gifting"},
            {"plan_id": "452", "name": "Airtel GIFTING 1.0GB (7 Days)", "selling_price": 800, "plan_type": "gifting"},
            {"plan_id": "454", "name": "Airtel GIFTING 1.5GB (7 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "461", "name": "Airtel GIFTING 3.5GB (7 Days)", "selling_price": 1500, "plan_type": "gifting"},
            {"plan_id": "460", "name": "Airtel GIFTING 5.0GB (5 Days)", "selling_price": 1700, "plan_type": "gifting"},
            {"plan_id": "465", "name": "Airtel GIFTING 6.0GB (7 Days)", "selling_price": 2500, "plan_type": "gifting"},
            {"plan_id": "467", "name": "Airtel GIFTING 10.0GB (7 Days)", "selling_price": 3000, "plan_type": "gifting"},
            {"plan_id": "462", "name": "Airtel GIFTING 2.0GB (30 Days)", "selling_price": 1500, "plan_type": "gifting"},
            {"plan_id": "463", "name": "Airtel GIFTING 3.0GB (30 Days)", "selling_price": 2000, "plan_type": "gifting"},
            {"plan_id": "464", "name": "Airtel GIFTING 4.0GB (30 Days)", "selling_price": 2500, "plan_type": "gifting"},
            {"plan_id": "466", "name": "Airtel GIFTING 8.0GB (30 Days)", "selling_price": 3000, "plan_type": "gifting"},
            {"plan_id": "492", "name": "Airtel Awoof 10.0GB (30 Days)", "selling_price": 3150, "plan_type": "gifting"},
            {"plan_id": "468", "name": "Airtel GIFTING 10.0GB (30 Days)", "selling_price": 4000, "plan_type": "gifting"},
        ]
    },

    # ── GLO (network id "3") ────────────────────────────────────────────
    "3": {
        "name": "Glo",
        "plans": [
            # Corporate Gifting (CG)
            {"plan_id": "124", "name": "Glo CG 200MB (30 Days)", "selling_price": 100, "plan_type": "corporate"},
            {"plan_id": "140", "name": "Glo CG 500MB (30 Days)", "selling_price": 230, "plan_type": "corporate"},
            {"plan_id": "141", "name": "Glo CG 1.024GB (30 Days)", "selling_price": 450, "plan_type": "corporate"},
            {"plan_id": "157", "name": "Glo CG 2.0GB (30 Days)", "selling_price": 900, "plan_type": "corporate"},
            {"plan_id": "158", "name": "Glo CG 3.072GB (30 Days)", "selling_price": 1350, "plan_type": "corporate"},
            {"plan_id": "159", "name": "Glo CG 5.12GB (30 Days)", "selling_price": 2250, "plan_type": "corporate"},
            # Daily / Short validity
            {"plan_id": "344", "name": "Glo GIFTING 45MB (1 Day)", "selling_price": 53, "plan_type": "gifting"},
            {"plan_id": "346", "name": "Glo GIFTING 750MB Night (1 Day)", "selling_price": 125, "plan_type": "gifting"},
            {"plan_id": "345", "name": "Glo GIFTING 750MB (1 Day)", "selling_price": 210, "plan_type": "gifting"},
            {"plan_id": "349", "name": "Glo GIFTING 1GB Night (1 Day)", "selling_price": 120, "plan_type": "gifting"},
            {"plan_id": "353", "name": "Glo GIFTING 1GB Special (1 Day)", "selling_price": 350, "plan_type": "gifting"},
            {"plan_id": "350", "name": "Glo GIFTING 1.5GB (1 Day)", "selling_price": 320, "plan_type": "gifting"},
            {"plan_id": "354", "name": "Glo GIFTING 2GB Special (1 Day)", "selling_price": 500, "plan_type": "gifting"},
            {"plan_id": "355", "name": "Glo GIFTING 3.55GB Special (1 Day)", "selling_price": 600, "plan_type": "gifting"},
            {"plan_id": "347", "name": "Glo GIFTING 105MB (1 Day)", "selling_price": 110, "plan_type": "gifting"},
            # 2–3 Day
            {"plan_id": "348", "name": "Glo GIFTING 235MB (2 Days)", "selling_price": 220, "plan_type": "gifting"},
            {"plan_id": "351", "name": "Glo GIFTING 2.5GB (2 Days)", "selling_price": 535, "plan_type": "gifting"},
            {"plan_id": "356", "name": "Glo GIFTING 5.1GB Special (2 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "476", "name": "Glo DATA 1GB (3 Days)", "selling_price": 285, "plan_type": "general"},
            {"plan_id": "478", "name": "Glo DATA 3GB (3 Days)", "selling_price": 855, "plan_type": "general"},
            {"plan_id": "479", "name": "Glo DATA 5GB (3 Days)", "selling_price": 1425, "plan_type": "general"},
            {"plan_id": "413", "name": "Glo GIFTING 1GB + 1 Hour My-G (3 Days)", "selling_price": 310, "plan_type": "gifting"},
            # 7–14 Day
            {"plan_id": "358", "name": "Glo GIFTING 3.5GB (7 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "357", "name": "Glo GIFTING 1.1GB (14 Days)", "selling_price": 750, "plan_type": "gifting"},
            {"plan_id": "352", "name": "Glo GIFTING 10GB (7 Days)", "selling_price": 2000, "plan_type": "gifting"},
            {"plan_id": "420", "name": "Glo GIFTING 5.9GB + 2GB Night (7 Days)", "selling_price": 1500, "plan_type": "gifting"},
            {"plan_id": "423", "name": "Glo GIFTING 8.5GB + 2.5GB Night (7 Days)", "selling_price": 2000, "plan_type": "gifting"},
            {"plan_id": "480", "name": "Glo DATA 1GB (7 Days)", "selling_price": 350, "plan_type": "general"},
            {"plan_id": "481", "name": "Glo DATA 3GB (7 Days)", "selling_price": 1050, "plan_type": "general"},
            {"plan_id": "482", "name": "Glo DATA 5GB (7 Days)", "selling_price": 1750, "plan_type": "general"},
            {"plan_id": "415", "name": "Glo GIFTING 1.5GB + 1 Hour My-G (7 Days)", "selling_price": 500, "plan_type": "gifting"},
            # 15–30 Day
            {"plan_id": "414", "name": "Glo GIFTING 1.8GB Social (15 Days)", "selling_price": 500, "plan_type": "gifting"},
            {"plan_id": "416", "name": "Glo GIFTING 2.6GB + 1.5GB Night (30 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "417", "name": "Glo GIFTING 4.2GB + 2GB Night (30 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "418", "name": "Glo GIFTING 3.5GB + 2GB Night (30 Days)", "selling_price": 1000, "plan_type": "gifting"},
            {"plan_id": "419", "name": "Glo GIFTING 5GB + 3GB Night (30 Days)", "selling_price": 1500, "plan_type": "gifting"},
            {"plan_id": "421", "name": "Glo GIFTING 6.15GB + 3GB Night (30 Days)", "selling_price": 2000, "plan_type": "gifting"},
            {"plan_id": "422", "name": "Glo GIFTING 9.8GB + 3.5GB Night (30 Days)", "selling_price": 2000, "plan_type": "gifting"},
            {"plan_id": "424", "name": "Glo GIFTING 7.25GB + 3GB Night (30 Days)", "selling_price": 2500, "plan_type": "gifting"},
            {"plan_id": "425", "name": "Glo GIFTING 10GB + 2GB Night (30 Days)", "selling_price": 3000, "plan_type": "gifting"},
        ]
    },

    # ── 9mobile (network id "4") ────────────────────────────────────────
    "4": {
        "name": "9mobile",
        "plans": [
            {"plan_id": "129", "name": "9mobile 500MB (30 Days)", "selling_price": 280, "plan_type": "general"},
            {"plan_id": "130", "name": "9mobile 1GB (30 Days)", "selling_price": 430, "plan_type": "general"},
            {"plan_id": "132", "name": "9mobile 2GB (30 Days)", "selling_price": 810, "plan_type": "general"},
            {"plan_id": "133", "name": "9mobile 3GB (30 Days)", "selling_price": 1500, "plan_type": "general"},
            {"plan_id": "134", "name": "9mobile 5GB (30 Days)", "selling_price": 2550, "plan_type": "general"},
            {"plan_id": "131", "name": "9mobile 10GB (30 Days)", "selling_price": 5000, "plan_type": "general"},
        ]
    },
}

INTERNET_SERVICES = {
    # ── Smile ──────────────────────────────────────────────────────────
    "smile": {
        "name": "Smile",
        "endpoint": "/api/smile-data/",
        "plans": [
            # Voice only
            {"plan_id": "11", "name": "SmileVoice ONLY 65 (30 Days)", "selling_price": 900},
            {"plan_id": "12", "name": "SmileVoice ONLY 135 (30 Days)", "selling_price": 1850},
            {"plan_id": "19", "name": "SmileVoice ONLY 150 (60 Days)", "selling_price": 2700},
            {"plan_id": "20", "name": "SmileVoice ONLY 175 (90 Days)", "selling_price": 3600},
            {"plan_id": "13", "name": "SmileVoice ONLY 430 (30 Days)", "selling_price": 5700},
            {"plan_id": "14", "name": "SmileVoice ONLY 450 (60 Days)", "selling_price": 7200},
            {"plan_id": "15", "name": "SmileVoice ONLY 500 (90 Days)", "selling_price": 9000},
            # Mini / Daily
            {"plan_id": "16", "name": "Smile mini 1GB + 1GB Streaming (1 Day)", "selling_price": 450},
            {"plan_id": "17", "name": "Smile mini 2.5GB + 1GB Streaming (1 Day)", "selling_price": 750},
            # Weekly
            {"plan_id": "18", "name": "Smile mini 1GB + 1GB Streaming (7 Days)", "selling_price": 750},
            {"plan_id": "46", "name": "Smile midi 3.5GB + 1GB Streaming (7 Days)", "selling_price": 1650},
            # Monthly — standard
            {"plan_id": "25", "name": "Smile midi 1.5GB + 3GB Streaming (30 Days)", "selling_price": 1550},
            {"plan_id": "50", "name": "Smile midi 2GB + 4GB Streaming (30 Days)", "selling_price": 1500},
            {"plan_id": "26", "name": "Smile midi 2GB + 4GB Streaming (30 Days) Alt", "selling_price": 1800},
            {"plan_id": "51", "name": "Smile midi 3GB + 5GB Streaming (30 Days)", "selling_price": 2000},
            {"plan_id": "77", "name": "Smile midi 3GB + 5GB Streaming (30 Days) B", "selling_price": 2000},
            {"plan_id": "49", "name": "Smile mini 6GB + 2GB Streaming (30 Days)", "selling_price": 2300},
            {"plan_id": "52", "name": "Smile midi 6GB + 5GB Streaming (30 Days)", "selling_price": 3000},
            {"plan_id": "28", "name": "Smile mini 5GB + 1GB Streaming (30 Days)", "selling_price": 3000},
            {"plan_id": "53", "name": "Smile midi 8GB + 5GB Streaming (30 Days)", "selling_price": 3500},
            {"plan_id": "29", "name": "Smile mini 6GB + 5GB Streaming (30 Days)", "selling_price": 3800},
            {"plan_id": "30", "name": "Smile midi 10GB + 5GB Streaming (30 Days)", "selling_price": 4600},
            {"plan_id": "54", "name": "Smile midi 13GB + 5GB Streaming (30 Days)", "selling_price": 5000},
            {"plan_id": "55", "name": "Smile midi 18GB + 5GB Streaming (30 Days)", "selling_price": 6000},
            {"plan_id": "37", "name": "Smile midi 20GB + 5GB Streaming (30 Days)", "selling_price": 7000},
            {"plan_id": "78", "name": "Smile midi 25GB + 5GB Streaming (30 Days)", "selling_price": 9000},
            {"plan_id": "60", "name": "Smile midi 40GB + 5GB Streaming (30 Days)", "selling_price": 12500},
            {"plan_id": "40", "name": "Smile midi 40GB + 5GB Streaming (Prm 30 Days)", "selling_price": 15500},
            {"plan_id": "61", "name": "Smile midi 65GB + 5GB Streaming (30 Days)", "selling_price": 15000},
            {"plan_id": "81", "name": "Smile Maxi Lite (30 Days)", "selling_price": 15000},
            {"plan_id": "62", "name": "Smile midi 100GB + 5GB Streaming (30 Days)", "selling_price": 20000},
            {"plan_id": "82", "name": "Smile Maxi Essential (30 Days)", "selling_price": 27700},
            {"plan_id": "64", "name": "Smile midi 130GB + 3GB Daily (30 Days)", "selling_price": 25000},
            {"plan_id": "83", "name": "Smile Maxi Home (30 Days)", "selling_price": 38500},
            {"plan_id": "84", "name": "Smile Maxi Office (30 Days)", "selling_price": 45000},
            {"plan_id": "65", "name": "Smile midi 210GB + 3GB Daily (30 Days)", "selling_price": 40000},
            {"plan_id": "85", "name": "Smile Maxi Data Flux (30 Days)", "selling_price": 61500},
            # 60-day
            {"plan_id": "66", "name": "Smile Jumbo 90GB (60 Days)", "selling_price": 25000},
            {"plan_id": "79", "name": "Smile Jumbo 300GB (90 Days)", "selling_price": 50000},
            {"plan_id": "68", "name": "Smile Jumbo 350GB (120 Days)", "selling_price": 60000},
            {"plan_id": "69", "name": "Smile Jumbo 500GB (180 Days)", "selling_price": 77000},
            # Annual
            {"plan_id": "70", "name": "Smile Annual 20GB (365 Days)", "selling_price": 14000},
            {"plan_id": "80", "name": "Smile Annual 20GB (365 Days) Alt", "selling_price": 14000},
            {"plan_id": "71", "name": "Smile Annual 50GB (365 Days)", "selling_price": 29000},
            {"plan_id": "72", "name": "Smile Annual 120GB (365 Days)", "selling_price": 49500},
            {"plan_id": "73", "name": "Smile Annual 250GB (365 Days)", "selling_price": 77000},
            {"plan_id": "74", "name": "Smile Annual 450GB (365 Days)", "selling_price": 107000},
            {"plan_id": "75", "name": "Smile Annual 700GB (365 Days)", "selling_price": 154000},
            {"plan_id": "76", "name": "Smile Annual 1TB (365 Days)", "selling_price": 180000},
        ]
    },

    # ── Alpha ───────────────────────────────────────────────────────────
    "alpha": {
        "name": "Alpha",
        "endpoint": "/api/alpha/",
        "plans": [
            {"plan_id": "9", "name": "Alpha N600 (30 Days)", "selling_price": 600},
            {"plan_id": "10", "name": "Alpha N1100 (30 Days)", "selling_price": 1100},
            {"plan_id": "11", "name": "Alpha N1600 (30 Days)", "selling_price": 1600},
            {"plan_id": "12", "name": "Alpha N2100 (30 Days)", "selling_price": 2100},
            {"plan_id": "13", "name": "Alpha N2600 (30 Days)", "selling_price": 2600},
            {"plan_id": "14", "name": "Alpha N3120 (30 Days)", "selling_price": 3120},
            {"plan_id": "15", "name": "Alpha N3620 (30 Days)", "selling_price": 3620},
            {"plan_id": "16", "name": "Alpha N4150 (30 Days)", "selling_price": 4150},
        ]
    },

    # ── Kirani ──────────────────────────────────────────────────────────
    "kirani": {
        "name": "Kirani",
        "endpoint": "/api/kirani/",
        "plans": [
            {"plan_id": "6", "name": "Kirani 30 Minutes (30 Days)", "selling_price": 470},
            {"plan_id": "12", "name": "Kirani 50 Minutes (30 Days)", "selling_price": 780},
            {"plan_id": "7", "name": "Kirani 70 Minutes (30 Days)", "selling_price": 1085},
            {"plan_id": "1", "name": "Kirani 100 Minutes (30 Days)", "selling_price": 1550},
            {"plan_id": "13", "name": "Kirani 150 Minutes (30 Days)", "selling_price": 2350},
            {"plan_id": "2", "name": "Kirani 200 Minutes (30 Days)", "selling_price": 3100},
            {"plan_id": "14", "name": "Kirani 250 Minutes (30 Days)", "selling_price": 3900},
            {"plan_id": "3", "name": "Kirani 300 Minutes (30 Days)", "selling_price": 4650},
            {"plan_id": "15", "name": "Kirani 350 Minutes (30 Days)", "selling_price": 5420},
            {"plan_id": "4", "name": "Kirani 400 Minutes (30 Days)", "selling_price": 6100},
            {"plan_id": "5", "name": "Kirani 500 Minutes (30 Days)", "selling_price": 7600},
            {"plan_id": "8", "name": "Kirani 600 Minutes (30 Days)", "selling_price": 9250},
            {"plan_id": "9", "name": "Kirani 700 Minutes (30 Days)", "selling_price": 10800},
            {"plan_id": "10", "name": "Kirani 800 Minutes (30 Days)", "selling_price": 12300},
            {"plan_id": "11", "name": "Kirani 900 Minutes (30 Days)", "selling_price": 13850},
        ]
    },
}


class ArewaGlobalProvider(BaseVTUProvider):
    """
    Arewa Global implementation of BaseVTUProvider.
    Documentation: https://arewaglobal.co/documentation.php
    """

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('api_key')
        self.base_url = (config.get('base_url') or 'https://arewaglobal.co').rstrip('/')
        
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    @property
    def provider_name(self) -> str:
        return "arewaglobal"

    @classmethod
    def get_supported_services(cls) -> List[str]:
        return ['airtime', 'data', 'internet']

    @classmethod
    def get_config_requirements(cls) -> List[Dict[str, Any]]:
        return [
            {
                'name': 'api_key', 
                'label': 'API Token', 
                'type': 'text', 
                'required': True,
                'help_text': 'Get this from your profile on arewaglobal.co'
            },
            {
                'name': 'base_url', 
                'label': 'Base URL', 
                'type': 'text', 
                'required': False, 
                'default': 'https://arewaglobal.co'
            }
        ]

    def _post(self, endpoint: str, data: dict) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            response.raise_for_status() 
            return response.json()
        except Exception as e:
            logger.error(f"ArewaGlobal request error: {str(e)}")
            raise Exception(f"ArewaGlobal API error: {str(e)}")

    # -------------------------------------------------------------------------
    # Purchase methods
    # -------------------------------------------------------------------------

    def buy_airtime(self, phone: str, network: str, amount: float, reference: str) -> Dict[str, Any]:
        network_map = {'mtn': '1', 'airtel': '2', 'glo': '3', '9mobile': '4'}
        network_id = network_map.get(network.lower(), '1')

        payload = {
            "phone": phone,
            "amount": int(amount),
            "network": network_id,
            "ported_number": "true"
        }
        
        res = self._post("/api/airtime/", payload)
        
        status = "SUCCESS" if res.get('status') == 'success' else "FAILED"
        return {
            "status": status,
            "provider_reference": res.get('id', reference),
            "message": res.get('msg'),
            "raw_response": res
        }

    def buy_data(self, phone: str, network: str, plan_id: str, amount: float, reference: str) -> Dict[str, Any]:
        network_map = {'mtn': '1', 'airtel': '2', 'glo': '3', '9mobile': '4'}
        network_id = network_map.get(network.lower(), '1')

        payload = {
            "phone": phone,
            "plan": plan_id,
            "network": network_id,
            "ported_number": "true"
        }
        
        res = self._post("/api/data/", payload)
        
        status = "SUCCESS" if res.get('status') == 'success' else "FAILED"
        return {
            "status": status,
            "provider_reference": res.get('id', reference),
            "message": res.get('msg'),
            "raw_response": res
        }

    def buy_tv(self, tv_id: str, package_id: str, smart_card_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """ArewaGlobal does not support TV."""
        return {"status": "FAILED", "message": "TV payments not supported on ArewaGlobal"}

    def buy_electricity(self, disco_id: str, plan_id: str, meter_number: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """ArewaGlobal does not support Electricity."""
        return {"status": "FAILED", "message": "Electricity payments not supported on ArewaGlobal"}

    def buy_education(self, exam_type: str, variation_id: str, quantity: int, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """ArewaGlobal does not support Education pins."""
        return {"status": "FAILED", "message": "Education payments not supported on ArewaGlobal"}

    def verify_internet(self, accountID: str, **kwargs) -> Dict[str, Any]:
        """
        ArewaGlobal does not have a dedicated internet verification endpoint.
        Return a stub response so the router does not crash.
        """
        return {"status": "SUCCESS", "account_name": accountID, "message": "Verification not required for this provider"}

    def buy_internet(self, plan_id: str, phone: str, amount: float, reference: str, **kwargs) -> Dict[str, Any]:
        """
        Internet subscription payment routed by service type to the correct Arewa endpoint.
        """
        # internet_variation kwarg may be an InternetVariation model object — extract its variation_id string safely.
        internet_variation = kwargs.get('internet_variation')
        if internet_variation is not None and not isinstance(internet_variation, str):
            # It's a model instance; use its variation_id attribute (e.g. "smile_25")
            internet_variation = getattr(internet_variation, 'variation_id', None) or plan_id

        # We need to extract the service key like smile, alpha from the variation_id
        # since we prepend it in sync: f"{service_key}_{plan_id}"
        if '_' in plan_id:
            service_key = plan_id.split('_')[0].lower()
            plan_id = plan_id.split('_', 1)[-1]
        elif internet_variation and '_' in internet_variation:
            service_key = internet_variation.split('_')[0].lower()
        else:
            service_key = (internet_variation or plan_id).lower()
        
        if service_key == 'smile':
            endpoint = "/api/smile-data/"
            payload = {
                "PhoneNumber": phone,
                "BundleTypeCode": plan_id,
                "actype": "PhoneNumber" if phone.startswith('234') else "AccountNumber"
            }
        elif service_key == 'alpha':
            endpoint = "/api/alpha/"
            payload = {"phone": phone, "planid": plan_id}
        elif service_key == 'kirani':
            endpoint = "/api/kirani/"
            payload = {"phone": phone, "planid": plan_id}
        else:
            raise ValueError(f"Unsupported internet service type for ArewaGlobal: {service_key}")

        res = self._post(endpoint, payload)
        
        status = "SUCCESS" if res.get('status') == 'success' else "FAILED"
        return {
            "status": status,
            "provider_reference": res.get('id'),
            "message": res.get('msg'),
            "raw_response": res
        }

    # -------------------------------------------------------------------------
    # Transaction & webhook handling
    # -------------------------------------------------------------------------

    def query_transaction(self, reference: str) -> Dict[str, Any]:
        res = self._post("/api/user/", {})
        return {"status": "UNKNOWN", "raw_response": res}

    def cancel_transaction(self, reference: str) -> Dict[str, Any]:
        """Not supported on ArewaGlobal."""
        return {"status": "FAILED", "message": "Cancellation not supported"}

    def handle_webhook(self, data: Dict[str, Any]) -> bool:
        return data.get("status") == "success"

    def handle_callback(self, data: Dict[str, Any]) -> bool:
        return self.handle_webhook(data)

    # -------------------------------------------------------------------------
    # Validation stubs (not supported by Arewa Global)
    # -------------------------------------------------------------------------

    def validate_meter(self, meter_number: str, service: str) -> Dict[str, Any]:
        return {"status": "FAILED", "account_name": "N/A", "raw_response": {}}

    def validate_cable_id(self, card_number: str, service: str) -> Dict[str, Any]:
        return {"status": "FAILED", "account_name": "N/A", "raw_response": {}}

    # -------------------------------------------------------------------------
    # Wallet
    # -------------------------------------------------------------------------

    def get_wallet_balance(self) -> float:
        res = self._post("/api/user/", {})
        try:
            return float(res.get('balance', 0))
        except (ValueError, TypeError):
            return 0.0

    def get_available_services(self) -> List[Dict[str, Any]]:
        return [
            {"type": "airtime", "endpoint": "/api/airtime/"},
            {"type": "data", "endpoint": "/api/data/"},
            {"type": "internet", "sub_services": list(INTERNET_SERVICES.keys())},
        ]

    # -------------------------------------------------------------------------
    # Airtime networks  (hardcoded — synced to DB)
    # -------------------------------------------------------------------------

    def sync_airtime(self) -> int:
        """
        Persists hardcoded airtime networks to the database.
        """
        from orders.models import AirtimeNetwork
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.airtime_margin if config else Decimal('0.00')
        base_100 = Decimal('100.00')

        created = []
        for net_data in AIRTIME_NETWORKS_DATA:
            net, _ = AirtimeNetwork.objects.update_or_create(
                service_id=net_data["service_id"],
                defaults={
                    "service_name": net_data["service_name"],
                    "min_amount": net_data["min_amount"],
                    "max_amount": net_data["max_amount"],
                    "cost_price": base_100,
                    "selling_price": base_100 + margin,
                    "agent_price": base_100,
                    "provider": getattr(self, "provider_config", None),
                }
            )
            created.append(net)
        if created:
            from orders.utils.sync_runner import deactivate_unreturned_items
            deactivate_unreturned_items(getattr(self, "provider_config", None) or "arewa_global", 'airtime', synced_pks=[n.pk for n in created])
        return len(created)

    # -------------------------------------------------------------------------
    # Data plans  (hardcoded — synced to DB)
    # -------------------------------------------------------------------------

    def sync_data(self) -> int:
        """
        Persists hardcoded data plans to the database.
        """
        from orders.models import DataService, DataVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.data_margin if config else Decimal('0.00')

        networks_to_sync = DATA_PLANS_BY_NETWORK

        created_variations = []
        for net_id, net_info in networks_to_sync.items():
            service, _ = DataService.objects.update_or_create(
                service_id=net_id,
                defaults={
                    "service_name": net_info["name"],
                    "provider": getattr(self, "provider_config", None),
                }
            )
            for plan in net_info["plans"]:
                p_amount = Decimal(str(plan["selling_price"]))
                variation, _ = DataVariation.objects.update_or_create(
                    variation_id=plan["plan_id"],
                    service=service,
                    defaults={
                        "name": plan["name"],
                        "cost_price": p_amount,
                        "selling_price": p_amount + margin,
                        "agent_price": p_amount,
                        "plan_type": plan.get("plan_type", "general"),
                        "is_active": True,
                    }
                )
                created_variations.append(variation)

        logger.info(f"ArewaGlobal: synced {len(created_variations)} data variations")
        if created_variations:
            from orders.utils.sync_runner import deactivate_unreturned_items
            deactivate_unreturned_items(getattr(self, "provider_config", None) or "arewa_global", 'data', synced_pks=[v.pk for v in created_variations])
        return len(created_variations)

    # -------------------------------------------------------------------------
    # Internet packages  (Smile, Kirani, Ratel, Alpha — synced to DB)
    # -------------------------------------------------------------------------

    def sync_internet(self) -> int:
        """
        Persists hardcoded internet service plans (Smile, Kirani, Ratel, Alpha).
        """
        from orders.models import InternetService, InternetVariation
        from summary.models import SiteConfig
        from decimal import Decimal
        config = SiteConfig.objects.first()
        margin = config.internet_margin if config else Decimal('0.00')

        created_variations = []
        for service_key, svc_data in INTERNET_SERVICES.items():
            service, _ = InternetService.objects.update_or_create(
                service_id=service_key,
                defaults={
                    "service_name": svc_data["name"],
                    "provider": getattr(self, "provider_config", None),
                }
            )
            for plan in svc_data["plans"]:
                p_amount = Decimal(str(plan["selling_price"]))
                variation, _ = InternetVariation.objects.update_or_create(
                    variation_id=f"{service_key}_{plan['plan_id']}",
                    defaults={
                        "name": plan["name"],
                        "service": service,
                        "cost_price": p_amount,
                        "selling_price": p_amount + margin,
                        "agent_price": p_amount,
                        "is_active": True,
                    }
                )
                created_variations.append(variation)

        logger.info(f"ArewaGlobal: synced {len(created_variations)} internet variations")
        if created_variations:
            from orders.utils.sync_runner import deactivate_unreturned_items
            deactivate_unreturned_items(getattr(self, "provider_config", None) or "arewa_global", 'internet', synced_pks=[v.pk for v in created_variations])
        return len(created_variations)

    # -------------------------------------------------------------------------
    # Unsupported service stubs
    # -------------------------------------------------------------------------

    def sync_cable(self) -> int:
        return 0

    def sync_electricity(self) -> int:
        return 0

    def sync_education(self) -> int:
        return 0
