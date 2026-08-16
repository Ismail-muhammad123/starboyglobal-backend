# User-Facing API Documentation

**Base URL:** `/api/`

All endpoints (unless otherwise noted) require authentication via Bearer token (`Authorization: Bearer <access_token>`). Public endpoints are explicitly marked.

---

## Table of Contents

- [1. Authentication](#1-authentication)
- [2. Profile](#2-profile)
- [3. Login PIN Management](#3-login-pin-management)
- [4. Transaction PIN Management](#4-transaction-pin-management)
- [5. Referrals](#5-referrals)
- [6. Push Notifications (FCM)](#6-push-notifications-fcm)
- [7. Account Management](#7-account-management)
- [8. Wallet](#8-wallet)
- [9. Wallet Funding](#9-wallet-funding)
- [10. Wallet-to-Wallet (P2P) Transfers](#10-wallet-to-wallet-p2p-transfers)
- [11. Bank Withdrawals](#11-bank-withdrawals)
- [12. Transfer Beneficiaries](#12-transfer-beneficiaries)
- [13. Banking Utilities](#13-banking-utilities)
- [14. Orders – Data Services](#14-orders--data-services)
- [15. Orders – Airtime](#15-orders--airtime)
- [16. Orders – Electricity](#16-orders--electricity)
- [17. Orders – Cable TV](#17-orders--cable-tv)
- [18. Orders – Internet Subscription](#18-orders--internet-subscription)
- [19. Orders – Education](#19-orders--education)
- [20. Customer Verification](#20-customer-verification)
- [21. Purchase History](#21-purchase-history)
- [22. Repeat Purchase](#22-repeat-purchase)
- [23. Purchase Beneficiaries](#23-purchase-beneficiaries)
- [24. Payments & Charges](#24-payments--charges)
- [25. Summary Dashboard](#25-summary-dashboard)
- [26. Support Tickets](#26-support-tickets)
- [27. Webhooks](#27-webhooks)

---

## Standard Response Formats

**Success Message:**
```json
{ "message": "Human-readable success message" }
```

**Error Response:**
```json
{ "error": "Error message describing the failure" }
```

---

## 1. Authentication

### `POST /api/account/signup/` — **Public**

Register a new user account.

**Request:**
```json
{
  "phone_country_code": "+234",
  "phone_number": "8012345678",
  "pin": "1234",
  "first_name": "John",
  "last_name": "Doe",
  "middle_name": "O",
  "email": "john@example.com",
  "referral_code": "ABC123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `phone_country_code` | string | Yes | Country code e.g. `+234` |
| `phone_number` | string | Yes | Phone number (unique, without leading 0) |
| `pin` | string | Yes | Login PIN (4–6 digits) |
| `first_name` | string | No | First name |
| `last_name` | string | No | Last name |
| `middle_name` | string | No | Middle name |
| `email` | string | No | Email address |
| `referral_code` | string | No | Referral code from another user |

**Response `201`:** Created user object.

> If a valid `referral_code` is provided and the referral program is active in `signup` mode, the referrer receives an automatic wallet bonus.

---

### `POST /api/account/activate-account/` — **Public**

Activate an account using OTP sent during registration.

**Request:**
```json
{
  "identifier": "8012345678",
  "otp": "123456"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `identifier` | string | Yes | Phone number |
| `otp` | string | Yes | OTP code received via SMS/email |

**Response `200`:**
```json
{ "message": "Account activated successfully." }
```

---

### `POST /api/account/resend-activation-code/` — **Public**

Resend the activation OTP.

**Request:**
```json
{
  "identifier": "8012345678",
  "channel": "sms"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `identifier` | string | Yes | Phone number |
| `channel` | string | No | Preferred channel: `sms`, `email`, or `whatsapp` |

---

### `POST /api/account/login/` — **Public**

Login with phone number and PIN.

**Request:**
```json
{
  "phone_number": "8012345678",
  "pin": "1234"
}
```

**Response `200`:**
```json
{
  "refresh": "eyJ0eXAi...",
  "access": "eyJ0eXAi...",
  "user": {
    "id": 1,
    "phone_country_code": "+234",
    "phone_number": "8012345678",
    "first_name": "John",
    "last_name": "Doe",
    "middle_name": "O",
    "email": "john@example.com",
    "is_verified": true,
    "email_verified": false,
    "phone_number_verified": true,
    "is_active": true,
    "role": "customer",
    "referral_code": "ABC123",
    "profile_picture_url": null,
    "transaction_pin_set": true,
    "created_at": "2026-01-15T08:30:00Z"
  }
}
```

**Response `401`:** `{ "error": "Invalid credentials" }`
**Response `403`:** `{ "error": "Account not active" }`

---

### `POST /api/account/refresh-token/` — **Public**

Obtain a new access token using a refresh token.

**Request:**
```json
{ "refresh": "eyJ0eXAi..." }
```

**Response `200`:**
```json
{ "access": "eyJ0eXAi..." }
```

---

### `POST /api/account/logout/`

Logout and blacklist the refresh token.

**Permission:** `IsAuthenticated`

**Request:**
```json
{ "refresh": "eyJ0eXAi..." }
```

**Response `200`:**
```json
{ "message": "Logged out successfully" }
```

---

## 2. Profile

### `GET /api/account/profile/`

Get the authenticated user's profile.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{
  "id": 1,
  "phone_country_code": "+234",
  "phone_number": "8012345678",
  "first_name": "John",
  "last_name": "Doe",
  "middle_name": "O",
  "email": "john@example.com",
  "is_verified": true,
  "email_verified": false,
  "phone_number_verified": true,
  "is_active": true,
  "role": "customer",
  "referral_code": "ABC123",
  "profile_picture_url": null,
  "transaction_pin_set": true,
  "created_at": "2026-01-15T08:30:00Z"
}
```

---

### `POST /api/account/profile/`

Update the authenticated user's profile.

**Permission:** `IsAuthenticated`

**Request (partial update):**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "middle_name": "Oluwaseun",
  "email": "john.new@example.com",
  "profile_picture_url": "https://..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `first_name` | string | No | First name |
| `last_name` | string | No | Last name |
| `middle_name` | string | No | Middle name |
| `email` | string | No | New email (must be unique among verified users) |
| `profile_picture_url` | string | No | URL of new profile picture |

---

## 3. Login PIN Management

### `POST /api/account/change-pin/`

Change the login PIN.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "old_pin": "1234",
  "new_pin": "5678"
}
```

---

### `POST /api/account/reset-password/` — **Public**

Request an OTP for login PIN reset.

**Request:**
```json
{ "identifier": "8012345678" }
```

**Response `200`:**
```json
{ "message": "OTP sent for password reset" }
```

---

### `POST /api/account/confirm-reset-password/` — **Public**

Confirm the PIN reset using OTP.

**Request:**
```json
{
  "identifier": "8012345678",
  "otp_code": "123456",
  "new_pin": "5678"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `identifier` | string | Yes | Phone number |
| `otp_code` | string | Yes | OTP received |
| `new_pin` | string | Yes | New login PIN (4–6 digits) |

---

## 4. Transaction PIN Management

### `POST /api/account/set-transaction-pin/`

Set the transaction PIN for the first time.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "pin": "1234",
  "confirm_pin": "1234"
}
```

**Response `400`:** If PIN is already set (`"Transaction PIN already set. Use the change PIN endpoint."`).

---

### `POST /api/account/change-transaction-pin/`

Change the existing transaction PIN.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "old_pin": "1234",
  "new_pin": "5678",
  "confirm_pin": "5678"
}
```

---

### `POST /api/account/request-transaction-pin-reset/`

Request an OTP for transaction PIN reset.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{ "message": "OTP sent for transaction PIN reset." }
```

---

### `POST /api/account/reset-transaction-pin/`

Reset the transaction PIN using OTP.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "otp_code": "123456",
  "new_pin": "5678",
  "confirm_pin": "5678"
}
```

---

### `POST /api/account/verify-transaction-pin/`

Verify if a transaction PIN is correct (without performing an action).

**Permission:** `IsAuthenticated`

**Request:**
```json
{ "pin": "1234" }
```

**Response `200`:**
```json
{ "valid": true }
```

---

## 5. Referrals

### `GET /api/account/referrals/`

List all users referred by the current user.

**Permission:** `IsAuthenticated`

**Response `200`:** Paginated list of:
```json
[
  {
    "id": 1,
    "referred_phone": "8098765432",
    "referred_name": "Jane Smith",
    "bonus_paid": true,
    "bonus_amount": "500.00",
    "created_at": "2026-02-01T10:00:00Z"
  }
]
```

---

### `GET /api/account/referral-stats/`

Get referral statistics.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{
  "referral_code": "ABC123",
  "total_referrals": 12,
  "total_bonus_earned": 6000.00
}
```

---

## 6. Push Notifications (FCM)

### `POST /api/account/register-fcm-token/`

Register or update the FCM device token for push notifications.

**Permission:** `IsAuthenticated`

**Request:**
```json
{ "token": "fJlD9k2T..." }
```

**Response `200`:**
```json
{ "message": "FCM token registered successfully." }
```

---

## 7. Account Management

### `POST /api/account/close-account/`

Close the user's account and deactivate their virtual account.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{ "message": "Account closed successfully" }
```

---

### `POST /api/account/generate-virtual-account/`

Generate a dedicated virtual bank account for wallet funding.

**Permission:** `IsAuthenticated`

> Requires `first_name`, `last_name`, and `email` to be set on the user profile.

**Response `200`:**
```json
{ "success": true, "message": "Virtual account created" }
```

**Response `400`:**
```json
{ "success": false, "error": "User already has a virtual account" }
```

---

## 8. Wallet

### `GET /api/wallet/`

Get the authenticated user's wallet balance.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{
  "id": 1,
  "balance": "15000.00"
}
```

---

### `GET /api/wallet/transactions/`

List all wallet transactions (credits and debits), ordered by newest first.

**Permission:** `IsAuthenticated`

**Response `200`:** Paginated list of:
```json
[
  {
    "id": 50,
    "amount": "5000.00",
    "transaction_type": "credit",
    "description": "Wallet Top-Up",
    "timestamp": "2026-04-01T09:00:00Z",
    "initiator": "self"
  }
]
```

---

### `GET /api/wallet/transactions/{id}/`

Get details of a specific wallet transaction.

**Permission:** `IsAuthenticated`

---

### `GET /api/wallet/charges/` or `POST /api/wallet/charges/`

Retrieve and calculate all applicable charges and fee breakdown for a given transaction type (`deposit`, `transfer_others`, or `transfer_p2p`) and amount.

**Permission:** `IsAuthenticated`

**Query Parameters (`GET`) or Body (`POST`):**
| Field | Type | Required | Description |
|---|---|---|---|
| `transaction_type` | string | Yes | One of `deposit`, `transfer_others`, or `transfer_p2p` |
| `amount` | decimal | Yes | Transaction amount in Naira (e.g. `5000.00`) |

**Example Request (`GET`):**
```http
GET /api/wallet/charges/?transaction_type=transfer_p2p&amount=5000.00
Authorization: Bearer <token>
```

**Example Request (`POST`):**
```json
{
  "transaction_type": "transfer_p2p",
  "amount": 5000.00
}
```

**Response `200`:**
```json
{
  "transaction_type": "transfer_p2p",
  "amount": "5000.00",
  "charges": [
    {
      "id": 1,
      "name": "P2P Transfer Fee",
      "charge_type": "flat",
      "rate_or_amount": "25.00",
      "cap": null,
      "computed_amount": "25.00",
      "block_if_insufficient": true
    }
  ],
  "total_charge": "25.00",
  "total_required": "5025.00"
}
```

---


## 9. Wallet Funding

### `POST /api/wallet/deposit/`

Initiate a wallet funding via Paystack payment.

**Permission:** `IsAuthenticated`

**Request:**
```json
{ "amount": 5000.00 }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `amount` | decimal | Yes | Amount in Naira (minimum ₦100) |

**Response `200`:**
```json
{
  "message": "Funding initiated",
  "response": {
    "authorization_url": "https://checkout.paystack.com/...",
    "access_code": "abc123",
    "reference": "DEP-ABC12345DEF"
  }
}
```

> Redirect the user to `authorization_url` to complete payment. Wallet is credited automatically via webhook on success.

---

### `GET /api/wallet/virtual-account/`

Get the user's dedicated virtual bank account details for direct bank transfer funding.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{
  "id": 1,
  "account_number": "0123456789",
  "bank_name": "Wema Bank",
  "account_name": "John Doe",
  "status": "ACTIVE",
  "created_at": "2026-01-20T12:00:00Z"
}
```

---

## 10. Wallet-to-Wallet (P2P) Transfers

### `GET /api/wallet/p2p-verify/?phone_number=08098765432`

Verify a recipient before sending money.

**Permission:** `IsAuthenticated`

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `phone_number` | string | Yes | Recipient phone number |

**Response `200`:**
```json
{
  "full_name": "Jane Smith",
  "phone_number": "8098765432",
  "profile_image": "https://..." 
}
```

**Response `404`:** `{ "error": "User with this phone number not found." }`

---

### `POST /api/wallet/transfer-p2p/`

Instantly transfer money to another user's wallet.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "recipient_phone": "08098765432",
  "amount": 2000.00,
  "description": "For lunch",
  "transaction_pin": "1234"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `recipient_phone` | string | Yes | Recipient phone number |
| `amount` | decimal | Yes | Amount in Naira (must be > 0) |
| `description` | string | No | Transfer narration |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |

**Response `200`:**
```json
{ "success": true, "message": "Successfully transferred ₦2000.00 to Jane Smith." }
```

> Both sender and recipient receive push notifications.

---

## 11. Bank Withdrawals

### `POST /api/wallet/withdraw-to-bank/`

Initiate a withdrawal to a bank account. Creates a pending withdrawal request.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "amount": 10000.00,
  "bank_name": "GTBank",
  "bank_code": "058",
  "account_number": "0987654321",
  "account_name": "John Doe",
  "transaction_pin": "1234"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `amount` | decimal | Yes | Withdrawal amount in Naira |
| `bank_name` | string | Yes | Destination bank name |
| `bank_code` | string | Yes | Bank sort code |
| `account_number` | string | Yes | Destination account number |
| `account_name` | string | Yes | Account holder name |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |

**Response `201`:**
```json
{
  "message": "Withdrawal initiated successfully.",
  "reference": "WTH-ABC12345DEF"
}
```

> The wallet is debited immediately. Admin must approve the withdrawal before bank transfer is executed.

---

## 12. Transfer Beneficiaries

### `GET /api/wallet/beneficiaries/`

List saved bank transfer beneficiaries.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
[
  {
    "id": 1,
    "bank_name": "GTBank",
    "bank_code": "058",
    "account_number": "0987654321",
    "account_name": "Jane Doe",
    "nickname": "Sister",
    "created_at": "2026-02-01T10:00:00Z"
  }
]
```

---

### `POST /api/wallet/beneficiaries/`

Save a new bank transfer beneficiary.

**Request:**
```json
{
  "bank_name": "GTBank",
  "bank_code": "058",
  "account_number": "0987654321",
  "account_name": "Jane Doe",
  "nickname": "Sister"
}
```

---

### `DELETE /api/wallet/beneficiaries/{id}/`

Delete a saved bank transfer beneficiary.

---

## 13. Banking Utilities

### `GET /api/wallet/banks/`

List all supported banks for withdrawals and account resolution.

**Permission:** `IsAuthenticated`

**Response `200`:** Array of bank objects from Paystack:
```json
[
  { "name": "GTBank", "code": "058" },
  { "name": "Access Bank", "code": "044" }
]
```

---

### `POST /api/wallet/resolve-account/`

Verify a bank account number and get the account holder's name.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "account_number": "0987654321",
  "bank_code": "058"
}
```

**Response `200`:**
```json
{
  "account_number": "0987654321",
  "account_name": "JOHN DOE"
}
```

---

## 14. Orders – Data Services

### `GET /api/orders/data-networks/`

List available data networks/services for the active provider.

**Permission:** `IsAuthenticated`

**Response `200`:** Array of data services:
```json
[
  {
    "id": 1,
    "service_id": "mtn-data",
    "service_name": "MTN Data",
    "provider": 1,
    "is_active": true
  }
]
```

---

### `GET /api/orders/data-plans/?service_id=1`

List available data plans. Optionally filter by service (network).

**Permission:** `IsAuthenticated`

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `service_id` | integer | No | Filter by data service/network ID |

**Response `200`:** Array of data variations:
```json
[
  {
    "id": 1,
    "name": "MTN 1GB – 30 Days",
    "service": { "id": 1, "service_id": "mtn-data", "service_name": "MTN Data" },
    "variation_id": "mtn-1gb",
    "selling_price": 550.00,
    "agent_price": 480.00,
    "plan_type": "monthly",
    "is_active": true
  }
]
```

> Prices are dynamically calculated based on the admin pricing mode (`fixed_margin` vs. `defined`).

---

### `POST /api/orders/buy-data/`

Purchase a data bundle.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "plan_id": 1,
  "phone_number": "08012345678",
  "transaction_pin": "1234",
  "promo_code": "SAVE10"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `plan_id` | integer | Yes | ID of the data variation/plan |
| `phone_number` | string | Yes | Beneficiary phone number |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |
| `promo_code` | string | No | Optional promo code for discount |

**Response `201`:** Purchase object (see [Purchase History](#21-purchase-history)).
**Response `403`:** `{ "error": "Invalid transaction PIN." }`
**Response `400`:** `{ "error": "Invalid or inactive plan." }`

---

## 15. Orders – Airtime

### `GET /api/orders/airtime-networks/`

List available airtime networks for the active provider.

**Permission:** `IsAuthenticated`

**Response `200`:** Array of airtime networks with discount info.

---

### `POST /api/orders/buy-airtime/`

Purchase airtime.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "service_id": "mtn",
  "amount": 1000.00,
  "phone_number": "08012345678",
  "transaction_pin": "1234",
  "promo_code": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `service_id` | string | Yes | Network service ID e.g. `mtn`, `glo`, `airtel` |
| `amount` | decimal | Yes | Airtime amount in Naira |
| `phone_number` | string | Yes | Beneficiary phone number |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |
| `promo_code` | string | No | Optional promo code |

> The actual amount debited factors in the user's discount (regular or agent).

**Response `201`:** Purchase object.

---

## 16. Orders – Electricity

### `GET /api/orders/electricity-services/`

List available electricity distribution companies (DISCOs).

**Permission:** `IsAuthenticated`

**Response `200`:** Array of electricity services.

---

### `POST /api/orders/buy-electricity/`

Purchase an electricity token.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "amount": 5000.00,
  "service_id": "ikedc-postpaid",
  "variation_id": "prepaid",
  "customer_id": "12345678901",
  "transaction_pin": "1234",
  "promo_code": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `amount` | decimal | Yes | Amount in Naira |
| `service_id` | string | Yes | DISCO service ID e.g. `ikedc-postpaid` |
| `variation_id` | string | Yes | Variation ID e.g. `prepaid`, `postpaid` |
| `customer_id` | string | Yes | Meter number |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |
| `promo_code` | string | No | Optional promo code |

> Discount is applied based on user role (regular or agent).

**Response `201`:** Purchase object.

---

## 17. Orders – Cable TV

### `GET /api/orders/tv-services/`

List available TV services (DSTV, GOTV, Startimes).

**Permission:** `IsAuthenticated`

---

### `GET /api/orders/tv-packages/?service_id=dstv`

List available TV bouquet packages. Filter by service.

**Permission:** `IsAuthenticated`

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `service_id` | string | No | Filter by TV service ID e.g. `dstv`, `gotv` |

---

### `POST /api/orders/buy-tv-subscription/`

Subscribe to a Cable TV bouquet.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "amount": 21000.00,
  "service_id": "dstv",
  "variation_id": "dstv-compact-plus",
  "customer_id": "7012345678",
  "subscription_type": "renew",
  "transaction_pin": "1234",
  "promo_code": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `amount` | decimal | Yes | Subscription amount in Naira |
| `service_id` | string | Yes | TV service ID |
| `variation_id` | string | Yes | TV package variation ID |
| `customer_id` | string | Yes | Smartcard / IUC number |
| `subscription_type` | string | Yes | e.g. `renew`, `change` |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |
| `promo_code` | string | No | Optional promo code |

**Response `201`:** Purchase object.

---

## 18. Orders – Internet Subscription

### `GET /api/orders/smile-packages/`

> **Note:** This endpoint currently serves Smile packages but will expand to include other internet subscription providers (Kirani, Ratel, etc.) in future updates.

List available internet subscription packages (Smile, Kirani, Ratel, etc.).

**Permission:** `IsAuthenticated`

---

### `POST /api/orders/buy-smile-subscription/`

Buy an internet subscription package (Smile, Kirani, Ratel, etc.).

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "plan_id": 5,
  "phone_number": "08012345678",
  "transaction_pin": "1234",
  "promo_code": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `plan_id` | integer | Yes | ID of the internet subscription variation/plan |
| `phone_number` | string | Yes | Beneficiary account phone number |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |
| `promo_code` | string | No | Optional promo code |

**Response `201`:** Purchase object.

---

## 19. Orders – Education

### `GET /api/orders/education-services/`

List available education services (WAEC, NECO, NABTEB, JAMB).

**Permission:** `IsAuthenticated`

---

### `GET /api/orders/education-plans/?service_id=waec`

List available education PIN variations. Filter by service.

**Permission:** `IsAuthenticated`

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `service_id` | string | No | Filter by education service ID e.g. `waec` |

---

### `POST /api/orders/buy-education/`

Purchase an education exam PIN.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "service_id": "waec",
  "variation_id": "waec-result-checker",
  "amount": 3500.00,
  "transaction_pin": "1234",
  "promo_code": null
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `service_id` | string | Yes | Education service ID e.g. `waec`, `neco` |
| `variation_id` | string | Yes | Education variation ID |
| `amount` | decimal | Yes | PIN price in Naira |
| `transaction_pin` | string | Yes | 4-digit transaction PIN |
| `promo_code` | string | No | Optional promo code |

**Response `200`:** Purchase result object.

---

## 20. Customer Verification

### `POST /api/orders/verify-customer/`

Verify a customer's identity before purchasing (TV smartcard, electricity meter, Smile account).

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "service_id": "dstv",
  "customer_id": "7012345678",
  "purchase_type": "tv"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `service_id` | string | Yes | Provider service ID e.g. `dstv`, `ikedc-prepaid` |
| `customer_id` | string | Yes | Smartcard number, meter number, or account ID |
| `purchase_type` | string | No | `tv` (default), `electricity`, or `smile` |

**Response `200`:**
```json
{
  "account_name": "JOHN DOE",
  "raw_response": { ... }
}
```

---

## 21. Purchase History

### `GET /api/orders/purchase-history/`

List all purchases made by the authenticated user, ordered by most recent.

**Permission:** `IsAuthenticated`

**Response `200`:** Paginated list of:
```json
[
  {
    "id": 30,
    "purchase_type": "data",
    "reference": "202604021030-AB12",
    "amount": "500.00",
    "beneficiary": "08012345678",
    "status": "success",
    "initiator": "self",
    "time": "2026-04-01T10:30:00Z",
    "remarks": null,
    "airtime_service": null,
    "data_variation": 1,
    "electricity_service": null,
    "electricity_variation": null,
    "tv_variation": null,
    "smile_variation": null,
    "education_variation": null
  }
]
```

---

### `GET /api/orders/purchase-history/{id}/`

Get full details of a specific purchase.

**Permission:** `IsAuthenticated`

**Response `404`:** `{ "error": "Purchase not found." }`

---

### `GET /api/orders/purchase-status/{id}/`

Re-query the VTU provider for the latest status of a purchase.

**Permission:** `IsAuthenticated`

> If the provider confirms success, the purchase is marked successful. If confirmed failed, the user receives an automatic refund.

**Response `200`:** Updated purchase object.

---

## 22. Repeat Purchase

### `POST /api/orders/repeat-purchase/`

Re-trigger a previous transaction using the same beneficiary and plan.

**Permission:** `IsAuthenticated`

**Request:**
```json
{ "purchase_id": 30 }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `purchase_id` | integer | Yes | ID of the original purchase to repeat |

**Response `201`:** New purchase object.
**Response `404`:** `{ "error": "Original purchase not found." }`
**Response `400`:** `{ "error": "This data plan is no longer available." }`

---

## 23. Purchase Beneficiaries

### `GET /api/orders/beneficiaries/?type=data`

List saved purchase beneficiaries (e.g., saved phone numbers, meter numbers, smartcard IDs).

**Permission:** `IsAuthenticated`

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `type` | string | No | Filter by service type: `data`, `airtime`, `tv`, `electricity`, `smile`, `education` |

**Response `200`:**
```json
[
  {
    "id": 1,
    "service_type": "data",
    "identifier": "08098765432",
    "nickname": "Mom's Phone",
    "created_at": "2026-02-01T10:00:00Z"
  }
]
```

---

### `POST /api/orders/beneficiaries/`

Save a new purchase beneficiary.

**Request:**
```json
{
  "service_type": "data",
  "identifier": "08098765432",
  "nickname": "Mom's Phone"
}
```

---

### `DELETE /api/orders/beneficiaries/{id}/`

Delete a saved purchase beneficiary.

---

## 24. Payments & Charges

### `GET /api/payment/charges-config/`

Get the current deposit and withdrawal charge configuration.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{
  "withdrawal_charge": 50.00,
  "deposit_charge": 0.00
}
```

---

### `POST /api/payment/webhook/` — **Public (Paystack)**

Paystack webhook endpoint for receiving payment event callbacks. Verified via `X-Paystack-Signature` header.

**Handled Events:**

| Event | Action |
|---|---|
| `charge.success` | Credit user wallet (minus deposit charge) |
| `dedicatedaccount.assign.success` | Create virtual account record for user |
| `transfer.success` | Mark withdrawal as successful |
| `transfer.failed` | Mark withdrawal as failed, refund user wallet |
| `transfer.reversed` | Mark withdrawal as reversed, refund user wallet |

> This endpoint is called by Paystack servers and should not be called by client apps.

---

## 25. Summary Dashboard

### `GET /api/summary/?start=2026-01-01&end=2026-03-31`

Get system-wide dashboard statistics and financial analytics. Supports date-range filtering.

**Permission:** `IsAuthenticated`

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `start` | string (date) | No | Start date for analytics range |
| `end` | string (date) | No | End date for analytics range |

**Response `200`:** Summary dashboard data (structure defined by `SummaryDashboard.summary()`).

---

## 26. Support Tickets

### `GET /api/support/`

List all support tickets for the authenticated user, ordered by newest first.

**Permission:** `IsAuthenticated`

**Response `200`:** Paginated list of tickets.

---

### `POST /api/support/`

Create a new support ticket.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "subject": "Failed Transaction",
  "message": "My data purchase REF-123 failed but I was debited."
}
```

---

### `GET /api/support/{id}/`

Get details of a specific support ticket with all messages.

**Permission:** `IsAuthenticated`

---

### `POST /api/support/{ticket_id}/messages/`

Send a message on an existing support ticket.

**Permission:** `IsAuthenticated`

**Request:**
```json
{ "message": "Can you provide more details about the refund timeline?" }
```

**Response `201`:** Created message object.
**Response `404`:** `{ "error": "Ticket not found." }`

---

## 27. Webhooks

### `POST /api/orders/clubkonnect-callback/` — **Public**

ClubKonnect VTU provider callback endpoint for receiving transaction status updates.

> This endpoint is called by ClubKonnect servers and should not be called by client apps.

---

## Appendix: API Routes Quick Reference

| Prefix | Module | Description |
|---|---|---|
| `/api/account/` | Users | Auth, profile, PINs, referrals |
| `/api/wallet/` | Wallet | Balance, transactions, P2P, withdrawals |
| `/api/payment/` | Payments | Webhook, charges config |
| `/api/orders/` | Orders | VTU purchases, services, history |
| `/api/summary/` | Summary | Analytics dashboard |
| `/api/support/` | Support | Ticket management |
| `/api/admin/` | Admin | Admin-only operations ([see ADMIN_API_DOCS.md](ADMIN_API_DOCS.md)) |
| `/api/swagger/` | Schema | Interactive Swagger UI |
| `/api/schema/` | Schema | OpenAPI 3.0 JSON schema |
