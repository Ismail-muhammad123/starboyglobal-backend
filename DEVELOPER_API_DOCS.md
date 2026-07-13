# Starboy Developer API — Documentation

> **Base URL:** `https://<your-domain>/api/v1/developer/`  
> **Version:** 1.0  
> **Authentication:** API Key (`X-API-KEY` header) or JWT Bearer Token  

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Getting Started](#getting-started)
4. [Pricing Tiers](#pricing-tiers)
5. [Endpoints Reference](#endpoints-reference)
   - [Auth & Account](#auth--account)
   - [Service Discovery](#service-discovery)
   - [Purchase](#purchase)
   - [Transaction Verification](#transaction-verification)
6. [Webhook Integration](#webhook-integration)
7. [Sandbox Mode](#sandbox-mode)
8. [Error Handling](#error-handling)
9. [Rate Limits & Best Practices](#rate-limits--best-practices)

---

## Overview

The Starboy Developer API allows third-party developers and resellers to programmatically access VTU (Virtual Top-Up) services including:

- **Airtime** top-up for all major Nigerian networks
- **Data** bundle purchases
- **Cable TV** (DSTV, GOTV, StarTimes) subscriptions
- **Electricity** token (prepaid meter) vending
- **Internet** subscriptions
- **Education** scratch card pins (WAEC, NECO, JAMB, etc.)

Developers enjoy **dedicated API pricing** which is separate from consumer and agent pricing, giving you room to set your own margins when reselling.

---

## Authentication

All endpoints (except `POST /login/`) require authentication via one of the following methods:

### Method 1: API Key Header (Recommended for server-to-server)

```http
X-API-KEY: ak_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

- Use `ak_live_` prefixed keys for **production** transactions.
- Use `ak_test_` prefixed keys for **sandbox/test** transactions.
- Both key types are provisioned automatically when you upgrade to developer.

### Method 2: JWT Bearer Token (For web/app sessions)

```http
Authorization: Bearer <access_token>
```

Obtain the JWT token from the `POST /login/` endpoint.

> **Note:** A request authenticated with an `ak_test_` key automatically operates in sandbox mode — no real transactions are processed.

---

## Getting Started

### Step 1: Create an Account & Fund Your Wallet

Register on the Starboy platform and fund your wallet. Your wallet balance is the source of funds for all API transactions.

**Wallet Funding Details** → `GET /funding-details/`

### Step 2: Upgrade to Developer

Send a `POST` request to `/upgrade/` while authenticated. A one-time upgrade fee may be charged from your wallet.

On success, two API keys are provisioned for you:
- **Live Key** (`ak_live_...`) — real transactions
- **Sandbox Key** (`ak_test_...`) — simulated testing

### Step 3: Retrieve Your API Keys

```http
GET /profile/
X-API-KEY: ak_live_...
```

### Step 4: Start Making Purchases

```http
POST /purchase/
X-API-KEY: ak_live_...
Content-Type: application/json

{
  "service_type": "data",
  "beneficiary": "08012345678",
  "plan_id": 42,
  "amount": 500
}
```

---

## Pricing Tiers

Starboy supports three pricing tiers:

| Tier        | Who             | Price Field         | Fallback           |
|-------------|-----------------|---------------------|--------------------|
| `customer`  | Regular users   | `selling_price`     | —                  |
| `agent`     | Resellers       | `agent_price`       | `selling_price`    |
| `developer` | API developers  | `developer_price`   | `selling_price`    |

> **How `developer_price` works:**  
> The admin sets a dedicated `developer_price` (or discount percentage) per variation. If not set, your transaction falls back to the standard `selling_price`. This ensures service availability is never broken.

All plan listing endpoints include both `normal_price` (consumer price) and `api_seller_price` (your developer price) in the response, so you can calculate your margin before offering the service to your customers.

---

## Endpoints Reference

---

### Auth & Account

#### `POST /login/`

Authenticate and receive a JWT token pair.

**Request Body:**
```json
{
  "phone_number": "08012345678",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

---

#### `POST /upgrade/`

Upgrade your account to Developer tier. Requires an active authenticated session (JWT).

An upgrade fee (if configured by admin) is deducted from your wallet.

**Request:** No body required.

**Response (200 OK):**
```json
{
  "message": "Successfully upgraded to developer.",
  "fee_deducted": 500.00
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Insufficient balance. Upgrade fee is ₦500.00."
}
```

---

#### `GET /profile/`

Returns your full developer profile including wallet balance, API keys, and webhook configuration.

**Headers:** `X-API-KEY` or `Authorization: Bearer <token>`

**Response (200 OK):**
```json
{
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "08012345678",
    "email": "john@example.com",
    "role": "developer",
    "is_active": true
  },
  "wallet_balance": 15000.00,
  "developer_profile": {
    "webhook_url": "https://yourapp.com/webhook/starboy",
    "webhook_secret": "abc123def456...",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00Z"
  },
  "api_keys": [
    {
      "key": "ak_live_xxxxxxxxxxxxxxxx",
      "mode": "live",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_used": "2024-01-20T14:22:00Z"
    },
    {
      "key": "ak_test_xxxxxxxxxxxxxxxx",
      "mode": "sandbox",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_used": null
    }
  ]
}
```

---

#### `GET /funding-details/`

Returns bank details for funding your Starboy wallet.

**Response (200 OK):**
```json
{
  "bank_name": "First Bank of Nigeria",
  "account_number": "3012345678",
  "account_name": "Starboy VTU Services"
}
```

---

#### `PATCH /webhook/update/`

Register or update your webhook URL. Starboy will POST transaction updates to this URL.

**Request Body:**
```json
{
  "webhook_url": "https://yourapp.com/webhook/starboy"
}
```

**Response (200 OK):**
```json
{
  "message": "Webhook URL updated successfully.",
  "webhook_url": "https://yourapp.com/webhook/starboy",
  "webhook_secret": "abc123def456..."
}
```

> Keep your `webhook_secret` safe. It is used to verify the authenticity of all incoming webhook payloads via HMAC-SHA256 signature.

---

#### `POST /keys/regenerate/`

Invalidates the current key and generates a new one for the specified mode.

> ⚠️ **Warning:** Once regenerated, the old key is immediately deactivated. Update your integration before regenerating.

**Request Body:**
```json
{
  "mode": "live"
}
```

`mode` must be `"live"` or `"sandbox"`.

**Response (200 OK):**
```json
{
  "key": "ak_live_yyyyyyyyyyyyyyyyyy",
  "mode": "live",
  "is_active": true,
  "created_at": "2024-02-01T08:00:00Z",
  "last_used": null
}
```

---

### Service Discovery

All discovery endpoints require authentication.

---

#### `GET /services/`

Returns all available service categories and their discovery endpoints.

**Response:**
```json
{
  "categories": [
    {"id": "airtime", "name": "Airtime Purchase", "endpoint": "/api/v1/developer/airtime/networks/"},
    {"id": "data", "name": "Data Bundles", "endpoint": "/api/v1/developer/data/networks/"},
    {"id": "electricity", "name": "Electricity Bills", "endpoint": "/api/v1/developer/electricity/services/"},
    {"id": "cable", "name": "Cable TV Subscription", "endpoint": "/api/v1/developer/tv/services/"},
    {"id": "internet", "name": "Internet Subscription", "endpoint": "/api/v1/developer/internet/services/"},
    {"id": "education", "name": "Education Pins", "endpoint": "/api/v1/developer/education/services/"}
  ]
}
```

---

#### `GET /airtime/networks/`

Lists all active airtime networks with pricing.

**Response:**
```json
[
  {
    "id": 1,
    "service_id": "mtn",
    "name": "MTN Nigeria",
    "min_amount": 50,
    "max_amount": 50000,
    "normal_price": null,
    "api_seller_price": null,
    "api_discount": 4.5
  }
]
```

> For airtime, pricing is percentage-based. The `api_discount` is the cashback/discount percentage you receive.  
> **Amount charged = face_value - (face_value × discount / 100)**

---

#### `GET /data/networks/`

Lists all active data network providers.

**Response:**
```json
[
  {"id": 1, "service_id": "mtn", "name": "MTN Data"}
]
```

---

#### `GET /data/networks/{network_id}/plans/`

Lists data plans for a given network provider.

**Response:**
```json
[
  {
    "id": 42,
    "variation_id": "mtn-1gb-30days",
    "name": "1GB — 30 Days",
    "normal_price": 350.00,
    "api_seller_price": 320.00,
    "api_discount": null,
    "plan_type": "data",
    "last_updated": "2026-07-13T22:15:30Z"
  }
]
```

---

#### `GET /tv/services/`

Lists all active Cable TV providers (DSTV, GOTV, StarTimes).

**Response:**
```json
[
  {"id": 1, "service_id": "dstv", "name": "DSTV"}
]
```

---

#### `GET /tv/services/{service_id}/packages/`

Lists cable TV subscription packages for a provider.

**Response:**
```json
[
  {
    "id": 10,
    "variation_id": "dstv-compact",
    "name": "DStv Compact",
    "normal_price": 9000.00,
    "api_seller_price": 8750.00,
    "api_discount": null,
    "last_updated": "2026-07-13T22:15:30Z"
  }
]
```

---

#### `GET /electricity/services/`

Lists all active electricity distribution companies (DISCOs).

**Response:**
```json
[
  {"id": 1, "service_id": "ekedc", "name": "Eko Electric (EKEDC)"}
]
```

---

#### `GET /electricity/services/{service_id}/variations/`

Lists meter types/variations for a DISCO (e.g. prepaid, postpaid).

**Response:**
```json
[
  {
    "id": 5,
    "variation_id": "ekedc-prepaid",
    "name": "EKEDC Prepaid",
    "min_amount": 500,
    "max_amount": 100000,
    "normal_price": null,
    "api_seller_price": null,
    "api_discount": 1.5,
    "last_updated": "2026-07-13T22:15:30Z"
  }
]
```

> For electricity, pricing is amount-based with a discount/margin. Pass the desired token amount in the `amount` field at purchase time.

---

#### `GET /internet/services/`

Lists all active internet service providers.

**Response:**
```json
[
  {"id": 1, "service_id": "smile", "name": "Smile Communications"}
]
```

---

#### `GET /internet/services/{service_id}/plans/`

Lists internet subscription plans.

**Response:**
```json
[
  {
    "id": 20,
    "variation_id": "smile-10gb",
    "name": "10GB Monthly Bundle",
    "normal_price": 4000.00,
    "api_seller_price": 3800.00,
    "api_discount": null,
    "last_updated": "2026-07-13T22:15:30Z"
  }
]
```

---

#### `GET /education/services/`

Lists available education exam pin types (WAEC, NECO, JAMB).

**Response:**
```json
[
  {"id": 1, "service_id": "waec", "name": "WAEC Result Checker"}
]
```

---

#### `GET /education/services/{service_id}/variations/`

Lists education pin variations (scratch card types/quantities).

**Response:**
```json
[
  {
    "id": 30,
    "variation_id": "waec-pins",
    "name": "WAEC Result Checker PIN",
    "normal_price": 3500.00,
    "api_seller_price": 3300.00,
    "api_discount": null,
    "last_updated": "2026-07-13T22:15:30Z"
  }
]
```

---

### Purchase

#### `POST /purchase/`

Unified purchase endpoint for all VTU services.

**Headers:**
```http
X-API-KEY: ak_live_...
Content-Type: application/json
```

**Common Fields:**

| Field           | Type    | Required | Description                                      |
|-----------------|---------|----------|--------------------------------------------------|
| `service_type`  | string  | ✅       | One of: `airtime`, `data`, `tv`, `electricity`, `internet`, `education` |
| `beneficiary`   | string  | ✅       | Phone number, smart card no., or meter number    |
| `amount`        | number  | ✅ *     | Token amount (for airtime & electricity only)    |
| `reference`     | string  | ❌       | Optional custom reference. Auto-generated if omitted |

**Service-specific fields:**

##### Airtime
```json
{
  "service_type": "airtime",
  "beneficiary": "08012345678",
  "network_id": 1,
  "amount": 500
}
```

##### Data
```json
{
  "service_type": "data",
  "beneficiary": "08012345678",
  "plan_id": 42,
  "amount": 0
}
```
> `amount` is ignored for data — price is determined by the selected `plan_id`.

##### Cable TV
```json
{
  "service_type": "tv",
  "beneficiary": "1234567890",
  "variation_id": 10,
  "amount": 0
}
```
> `beneficiary` = smart card / IUC number. `amount` is determined by the package.

##### Electricity
```json
{
  "service_type": "electricity",
  "beneficiary": "04123456789",
  "variation_id": 5,
  "amount": 5000
}
```
> `beneficiary` = meter number. `amount` = token face value in Naira.

##### Internet
```json
{
  "service_type": "internet",
  "beneficiary": "08012345678",
  "variation_id": 20,
  "amount": 0
}
```

##### Education
```json
{
  "service_type": "education",
  "beneficiary": "08012345678",
  "variation_id": 30,
  "quantity": 2,
  "amount": 0
}
```
> `quantity` defaults to `1`. Total amount = `api_seller_price × quantity`.

---

**Success Response (201 Created):**
```json
{
  "status": "success",
  "reference": "DEV-A1B2C3D4E5",
  "purchase_id": 1093,
  "message": "Transaction successful",
  "error": null
}
```

**Pending Response (201 Created):**
```json
{
  "status": "pending",
  "reference": "DEV-A1B2C3D4E5",
  "purchase_id": 1093,
  "message": "Transaction initiated",
  "error": null
}
```

> A `pending` status means the transaction was queued with the provider. Use the verify endpoint or await a webhook callback to get the final status.

**Failed Response (400 Bad Request):**
```json
{
  "status": "failed",
  "reference": "DEV-A1B2C3D4E5",
  "purchase_id": null,
  "message": "Transaction failed",
  "error": "Insufficient balance"
}
```

---

### Transaction Verification

#### `GET /verify/{reference}/`

Retrieve the current status and details of a past transaction.

**Response (200 OK):**
```json
{
  "reference": "DEV-A1B2C3D4E5",
  "status": "success",
  "amount": 320.00,
  "beneficiary": "08012345678",
  "type": "data",
  "created_at": "2024-02-01T10:45:00Z",
  "remarks": "1GB — 30 Days data purchased for 08012345678"
}
```

---

## Webhook Integration

Starboy sends real-time transaction status updates to your registered `webhook_url` for asynchronous flows (pending transactions, delayed provider confirmations).

### Payload Structure

```json
{
  "event": "transaction.update",
  "reference": "DEV-A1B2C3D4E5",
  "status": "success",
  "amount": 320.00,
  "beneficiary": "08012345678",
  "service_type": "data",
  "timestamp": "2024-02-01T10:50:00Z",
  "meta": {
    "token": "5283-1234-5678-9012"
  }
}
```

### Signature Verification

Every webhook request includes an `X-Starboy-Signature` header. **Always verify this signature** to ensure the payload is from Starboy and hasn't been tampered with.

**Algorithm:** HMAC-SHA256  
**Secret:** Your `webhook_secret` from `GET /profile/`

**Python Example:**

```python
import hmac
import hashlib
import json

def verify_webhook(request_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# In your Django/Flask view:
signature = request.headers.get("X-Starboy-Signature")
is_valid = verify_webhook(request.body, signature, YOUR_WEBHOOK_SECRET)

if not is_valid:
    return HttpResponse(status=401)  # Reject invalid payloads
```

**Node.js Example:**

```javascript
const crypto = require('crypto');

function verifyWebhook(rawBody, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(rawBody)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(expected),
    Buffer.from(signature)
  );
}
```

### Webhook Best Practices

- Respond with HTTP `200 OK` quickly (within 5 seconds). Process asynchronously if needed.
- Implement idempotency — you may receive duplicate deliveries for the same event.
- Log all incoming webhook events for auditing.
- Always verify the signature before processing.

---

## Sandbox Mode

Use your `ak_test_` API key (or pass your live key with sandbox intent) to test your integration without real transactions or wallet debits.

**Sandbox requests:**
- Return a simulated `success` response immediately.
- Do **not** debit your wallet.
- Do **not** call external VTU providers.
- Generate a reference prefixed with `SBX-`.

**Example Sandbox Response:**
```json
{
  "status": "success",
  "message": "Sandbox transaction successful (Simulated)",
  "reference": "SBX-F9E8D7C6B5",
  "amount": 500.0,
  "beneficiary": "08012345678",
  "mode": "sandbox"
}
```

> Sandbox mode is ideal for end-to-end integration testing before going live.

---

## Error Handling

All errors follow a consistent JSON format:

```json
{
  "error": "Human-readable error description"
}
```

### Common HTTP Status Codes

| Code | Meaning                                              |
|------|------------------------------------------------------|
| 200  | Request successful                                   |
| 201  | Resource created / transaction initiated             |
| 400  | Bad request — invalid input or business rule failure |
| 401  | Unauthenticated — invalid or missing API key         |
| 403  | Forbidden — account lacks developer privileges       |
| 404  | Resource not found                                   |
| 500  | Internal server error — retry or contact support     |

### Common Error Messages

| Error                          | Cause & Fix                                        |
|--------------------------------|----------------------------------------------------|
| `Insufficient balance`         | Fund your wallet before retrying                   |
| `Airtime service is inactive`  | The selected network is currently offline          |
| `Invalid or expired promo code`| The promo code has expired or doesn't exist        |
| `Developer profile not found`  | Your account is not yet upgraded to developer      |
| `Unsupported service type`     | `service_type` value is not recognized             |
| `Missing required fields`      | One of `service_type`, `beneficiary`, `amount` is absent |

---

## Rate Limits & Best Practices

- **Rate Limit:** 300 requests/minute per API key (subject to change).
- Always **check wallet balance** via `GET /profile/` before bulk operations.
- Store `reference` values from your purchase requests — use them to reconcile transactions if a network error occurs before the response is received.
- Use **sandbox mode** for all testing. Never test with live keys on non-production environments.
- Rotate API keys periodically using `POST /keys/regenerate/`. Update your configuration immediately after regeneration.
- Set up webhook to receive asynchronous updates instead of polling `GET /verify/{reference}/`.

---

## Support

For integration support or to report issues, contact the Starboy developer support team.

> **Tip:** When reporting issues, always include the `reference` ID of the affected transaction to speed up resolution.

---

*Documentation last updated: July 2026*
