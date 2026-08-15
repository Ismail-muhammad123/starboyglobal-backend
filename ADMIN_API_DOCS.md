# Admin API Documentation

**Base URL:** `/api/admin/`

All endpoints require authentication via Bearer token. Staff or superuser privileges are enforced through granular permission classes.

> 💡 **Upgrading a Legacy Admin FE App?** Check out the step-by-step [Admin FE App API Update Guide](file:///c:/Users/Newton/Desktop/projects/starboy/starboyglobal-backend/ADMIN_FE_UPDATE_GUIDE.md) for quick integration of the latest Data Plans, Tier Margins, and Auto-Sync APIs.

---

## Table of Contents

- [Permissions Reference](#permissions-reference)
- [1. Dashboard](#1-dashboard)
- [2. Quick Actions](#2-quick-actions)
- [3. User Management](#3-user-management)
- [4. Wallet & Transactions](#4-wallet--transactions)
- [5. Payments – Deposits](#5-payments--deposits)
- [6. Payments – Withdrawals](#6-payments--withdrawals)
- [7. Purchases (VTU Orders)](#7-purchases-vtu-orders)
- [8. VTU Provider Config](#8-vtu-provider-config)
- [9. Service Routing Config](#9-service-routing-config)
- [10. VTU Control Panel](#10-vtu-control-panel)
- [11. Pricing & Plans](#11-pricing--plans)
- [12. Automation](#12-automation)
- [13. Support Tickets](#13-support-tickets)
- [14. Notifications](#14-notifications)
- [15. Administrative Transfers](#15-administrative-transfers)
- [16. Transaction Charges](#16-transaction-charges)
- [17. Management Commands](#17-management-commands)

---

## Permissions Reference

| Permission Class | Condition | Grants Access To |
|---|---|---|
| `IsAuthenticated` | Any logged-in user | Dashboard, Quick Actions |
| `CanManageUsers` | `staff_permissions.can_manage_users` or superuser | User CRUD, KYC, roles |
| `CanManageWallets` | `staff_permissions.can_manage_wallets` or superuser | Wallet transactions, adjustments |
| `CanManagePayments` | `staff_permissions.can_manage_payments` or superuser | Deposits, Withdrawals |
| `CanManageVTU` | `staff_permissions.can_manage_vtu` or superuser | Purchases, Providers, Pricing, VTU Control |
| `CanManageSiteConfig` | `staff_permissions.can_manage_site_config` or superuser | Automation, global settings |
| `CanInitiateTransfers` | `staff_permissions.can_initiate_transfers` or superuser | Admin bank transfers |
| `IsSuperUserOnly` | `is_superuser = True` | Notification provider config |

> All permission classes extend `StaffPermissionBase`, which requires `user.role == 'staff'` or `user.is_staff == True`.

---

## Standard Response Formats

**Success Response:**
```json
{
  "status": "SUCCESS",
  "message": "Human-readable result message"
}
```

**Error Response:**
```json
{
  "error": "Error message describing the failure"
}
```

---

## 1. Dashboard

### `GET /api/admin/stats/`

Returns comprehensive dashboard statistics including business metrics, service health, provider balances, alerts, and site configuration state.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{
  "business_metrics": {
    "total_users": 1520,
    "active_users_today": 87,
    "total_wallet_balance": 4500000.00,
    "total_transaction_volume": 12000000.00,
    "profit": {
      "today": 15000.00,
      "weekly": 95000.00,
      "monthly": 380000.00
    }
  },
  "service_health": {
    "network_status": { "mtn": "up", "glo": "up", "airtel": "degraded" },
    "provider_performances": [
      { "name": "clubkonnect", "is_active": true, "success_rate": 0.97, "total_transactions": 5420 }
    ],
    "bill_system_success_rate": 0.95
  },
  "provider_balances": {
    "vtu": 250000.00,
    "payment_gateway": 1200000.00,
    "sms": 45000.00
  },
  "alerts": {
    "failed_transactions": [
      { "id": 102, "ref": "TXN_ABC123", "type": "data", "amount": 500.00, "beneficiary": "08012345678", "time": "2026-04-02T10:30:00Z", "error": "Provider timeout" }
    ],
    "low_balance_warnings": ["VTU balance below ₦50,000"]
  },
  "quick_actions": {
    "maintenance_mode": false,
    "services": { "airtime": true, "data": true, "tv": true, "electricity": true, "education": true }
  },
  "finances": {
    "deposits": { "total_amount": 5000000.00, "success_count": 320, "pending_count": 5, "failed_count": 12 },
    "withdrawals": { "total_amount": 1200000.00, "approved_count": 85, "pending_count": 3 }
  }
}
```

---

## 2. Quick Actions

### `POST /api/admin/maintenance-mode/`

Toggle maintenance mode for the entire platform.

**Permission:** `IsAuthenticated`

**Request:**
```json
{ "enabled": true }
```

**Response `200`:**
```json
{ "status": "SUCCESS", "message": "Maintenance mode turned ON." }
```

---

### `POST /api/admin/refresh-services/`

Force refresh all provider balances and service status checks.

**Permission:** `IsAuthenticated`

**Response `200`:**
```json
{
  "status": "SUCCESS",
  "message": "All services refreshed successfully.",
  "balances": {
    "vtu_balance": 250000.00,
    "payment_gateway_balance": 1200000.00,
    "sms_balance": 45000.00
  }
}
```

---

### `POST /api/admin/pause-service/`

Pause or resume a specific service type across the platform.

**Permission:** `IsAuthenticated`

**Request:**
```json
{
  "service": "data",
  "active": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `service` | string | Yes | One of: `airtime`, `data`, `tv`, `electricity`, `education` |
| `active` | boolean | Yes | `true` to resume, `false` to pause |

**Response `200`:**
```json
{ "status": "SUCCESS", "message": "Service 'data' paused." }
```

---

## 3. User Management

All user endpoints require **`CanManageUsers`** permission.

### `GET /api/admin/users/`

List all users with pagination, filters, and search.

**Query Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `search` | string | Search by phone, name, email, or referral code |
| `role` | string | Filter by role: `customer`, `agent`, `staff` |
| `is_active` | boolean | Filter by active status |
| `is_kyc_verified` | boolean | Filter by KYC status |
| `is_closed` | boolean | Filter by blocked/closed status |
| `ordering` | string | Order by: `created_at`, `first_name`, `last_name`, `role` |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 100, max: 100) |

**Response `200`:** Paginated list of:
```json
{
  "count": 1520,
  "next": "/api/admin/users/?page=2",
  "results": [
    {
      "id": 1,
      "phone_number": "08012345678",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "role": "customer",
      "is_active": true,
      "is_verified": true,
      "is_kyc_verified": true,
      "is_staff": false,
      "is_closed": false,
      "referral_code": "ABC123",
      "wallet_balance": "15000.00",
      "created_at": "2026-01-15T08:30:00Z"
    }
  ]
}
```

---

### `POST /api/admin/users/`

Create a new user.

**Request:**
```json
{
  "phone_number": "08098765432",
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane@example.com",
  "password": "securepass123",
  "role": "customer",
  "is_active": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `phone_number` | string | Yes | Unique phone number |
| `password` | string | Yes | Login password/PIN |
| `first_name` | string | No | First name |
| `last_name` | string | No | Last name |
| `email` | string | No | Email address |
| `role` | string | No | `customer` (default), `agent`, or `staff` |
| `is_active` | boolean | No | Default `true` |

**Response `201`:** Full user detail object (see `GET /users/{id}/`)

---

### `GET /api/admin/users/{id}/`

Get full user details including wallet, KYC, virtual account, beneficiaries, and recent activity.

**Response `200`:**
```json
{
  "id": 1,
  "phone_number": "08012345678",
  "first_name": "John",
  "last_name": "Doe",
  "middle_name": null,
  "email": "john@example.com",
  "phone_country_code": "+234",
  "role": "customer",
  "agent_commission_rate": 0.0,
  "is_active": true,
  "is_verified": true,
  "is_kyc_verified": true,
  "is_staff": false,
  "is_superuser": false,
  "is_closed": false,
  "closed_at": null,
  "closed_reason": null,
  "referral_code": "ABC123",
  "referral_earnings_count": 5,
  "referral_earnings_amount": "2500.00",
  "transaction_pin_set": true,
  "two_factor_enabled": false,
  "profile_picture_url": null,
  "wallet_balance": "15000.00",
  "kyc": {
    "id": 1,
    "status": "APPROVED",
    "bvn": "****5678",
    "nin": "****1234",
    "time_accepted": "2026-02-10T14:00:00Z",
    "remarks": "Approved by Admin",
    "processed_by_name": "09087654321"
  },
  "staff_permissions": null,
  "virtual_account": {
    "account_number": "0123456789",
    "bank_name": "Wema Bank",
    "account_name": "John Doe"
  },
  "beneficiaries": [
    { "id": 1, "service_type": "bank", "identifier": "0123456789", "nickname": "My GTBank" }
  ],
  "purchase_beneficiaries": [
    { "id": 1, "service_type": "data", "identifier": "08098765432", "nickname": "Mom's Phone" }
  ],
  "transfer_beneficiaries": [
    { "id": 1, "bank_name": "GTBank", "account_number": "0987654321", "account_name": "Jane Doe", "nickname": "Sister" }
  ],
  "recent_transactions": [
    { "id": 50, "type": "credit", "amount": 5000.00, "balance_after": 15000.00, "description": "Wallet funding", "reference": "WTX_123", "timestamp": "2026-04-01T09:00:00Z" }
  ],
  "recent_purchases": [
    { "id": 30, "type": "data", "amount": 500.00, "beneficiary": "08012345678", "status": "success", "reference": "PUR_456", "time": "2026-04-01T10:30:00Z" }
  ],
  "created_at": "2026-01-15T08:30:00Z",
  "upgraded_at": null
}
```

---

### `POST /api/admin/users/{id}/activate/`

Activate a user account.

**Response `200`:**
```json
{ "status": "SUCCESS", "message": "User 08012345678 activated." }
```

---

### `POST /api/admin/users/{id}/deactivate/`

Deactivate a user account (user cannot log in).

**Response `200`:**
```json
{ "status": "SUCCESS", "message": "User 08012345678 deactivated." }
```

---

### `POST /api/admin/users/{id}/block/`

Block a user (close their account).

**Request:**
```json
{ "reason": "Fraudulent activity detected" }
```

**Response `200`:**
```json
{ "status": "SUCCESS", "message": "User 08012345678 blocked." }
```

---

### `POST /api/admin/users/{id}/unblock/`

Unblock a previously blocked user.

**Response `200`:**
```json
{ "status": "SUCCESS", "message": "User 08012345678 unblocked." }
```

---

### `POST /api/admin/users/{id}/approve-kyc/`

Approve a user's KYC verification.

**Request:**
```json
{ "reason": "Documents verified successfully" }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | string | No | Reason for approval |

---

### `POST /api/admin/users/{id}/reject-kyc/`

Reject a user's KYC verification.

**Request:**
```json
{ "reason": "BVN does not match submitted name" }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | string | No | Reason for rejection (displayed to user) |

---

### `POST /api/admin/users/{id}/reset-pin/`

Reset or change a user's transaction PIN.

**Request:**
```json
{ "new_pin": "1234" }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `new_pin` | string | Yes | New PIN (4–6 digits) |

---

### `POST /api/admin/users/{id}/set-role/`

Change a user's role (customer, agent, or staff).

**Request:**
```json
{
  "role": "agent",
  "commission_rate": 2.5
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `role` | string | Yes | `customer`, `agent`, or `staff` |
| `commission_rate` | float | No | Commission rate (only relevant for `agent`) |

> When upgrading to `staff`, a `StaffPermission` record is auto-created. When downgrading from staff, `is_staff` is set to `false`.

---

### `POST /api/admin/users/{id}/set-permissions/`

Update granular permissions for a staff user.

**Request:**
```json
{
  "can_manage_users": true,
  "can_manage_wallets": true,
  "can_manage_vtu": false,
  "can_manage_payments": true,
  "can_manage_notifications": false,
  "can_manage_site_config": false,
  "can_initiate_transfers": false
}
```

> Returns `400` if the user is not a staff member.

---

### `GET /api/admin/users/{id}/agent-performance/`

View agent (or any user) performance and commission statistics.

**Response `200`:**
```json
{
  "user_id": 5,
  "phone": "08055555555",
  "role": "agent",
  "commission_rate": 2.5,
  "referral_earnings_count": 12,
  "referral_earnings_amount": 6000.00,
  "total_sales": 1500000.00,
  "total_transactions": 342,
  "today_sales": 25000.00,
  "today_transactions": 8,
  "by_service": [
    { "purchase_type": "data", "count": 200, "total": 800000.00 },
    { "purchase_type": "airtime", "count": 142, "total": 700000.00 }
  ]
}
```

---

### `POST /api/admin/users/{id}/upgrade-to-agent/`

Legacy endpoint to upgrade a user to agent role.

**Request:**
```json
{ "commission_rate": 2.0 }
```

---

## 4. Wallet & Transactions

All wallet endpoints require **`CanManageWallets`** permission.

### `GET /api/admin/wallet/transactions/`

List all wallet transactions (read-only) with filters.

**Query Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `user` | integer | Filter by user ID |
| `transaction_type` | string | Filter by type: `credit`, `debit` |
| `initiator` | string | Filter by: `self`, `admin`, `system` |

**Response `200`:** Paginated list of wallet transactions with `user_phone` included.

---

### `GET /api/admin/wallet/transactions/{id}/`

Retrieve a single wallet transaction.

---

### `POST /api/admin/wallet/transactions/manual-adjustment/`

Manually credit or debit a user's wallet.

**Request:**
```json
{
  "user_id": 5,
  "amount": 5000.00,
  "type": "credit",
  "reason": "Compensation for failed transaction"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | integer | Yes | Target user ID |
| `amount` | decimal | Yes | Amount to credit or debit |
| `type` | string | Yes | `credit` or `debit` |
| `reason` | string | No | Reason for the adjustment (default: "Admin Adjustment") |

---

## 5. Payments – Deposits

All deposit endpoints require **`CanManagePayments`** permission.

### `GET /api/admin/payments/deposits/`

List all deposits.

### `GET /api/admin/payments/deposits/{id}/`

Retrieve a single deposit record.

### `POST /api/admin/payments/deposits/{id}/mark-success/`

Manually confirm a deposit and credit the user's wallet.

**Request:**
```json
{ "reason": "Bank transfer confirmed via bank statement" }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | string | No | Admin remark (default: "Manually confirmed by Admin") |

**Response `400`:** If the deposit has already been marked successful.

---

## 6. Payments – Withdrawals

All withdrawal endpoints require **`CanManagePayments`** permission.

### `GET /api/admin/payments/withdrawals/`

List all withdrawal requests.

### `GET /api/admin/payments/withdrawals/{id}/`

Retrieve a single withdrawal record.

### `POST /api/admin/payments/withdrawals/{id}/approve/`

Approve a pending withdrawal request.

**Request:**
```json
{
  "otp": "123456",
  "reason": "Approved"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `otp` | string | Conditional | Admin 2FA OTP (required if admin has 2FA enabled) |
| `reason` | string | No | Reason for approval |

**Response `403`:** If OTP is invalid or missing when 2FA is enabled.
**Response `400`:** If withdrawal is not in `PENDING` state.

---

### `POST /api/admin/payments/withdrawals/{id}/reject/`

Reject a pending withdrawal and refund the user's wallet.

**Request:**
```json
{
  "reason": "Suspicious destination account"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | string | No | Reason for rejection |

---

## 7. Purchases (VTU Orders)

All purchase endpoints require **`CanManageVTU`** permission.

### `GET /api/admin/purchases/`

List all purchases (orders) with `user_phone` included.

### `GET /api/admin/purchases/{id}/`

Retrieve a single purchase record.

### `POST /api/admin/purchases/`

Initiate a purchase on behalf of a user.

**Request:**
```json
{
  "user_id": 5,
  "purchase_type": "data",
  "amount": 500.00,
  "beneficiary": "08012345678",
  "action": "buy_data",
  "extra_kwargs": { "plan_id": "MTN-1GB" }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | integer | Yes | User to purchase for |
| `purchase_type` | string | Yes | `data`, `airtime`, `electricity`, `tv`, `internet`, `education` |
| `amount` | decimal | Yes | Amount in Naira |
| `beneficiary` | string | Yes | Phone/meter/smartcard number |
| `action` | string | Yes | Action name e.g. `buy_data`, `buy_airtime` |
| `extra_kwargs` | object | No | Additional parameters for the purchase |

---

### `POST /api/admin/purchases/{id}/retry/`

Retry a failed purchase through the provider router with fallback.

**Response `400`:** If purchase status is not `failed`.

---

### `POST /api/admin/purchases/{id}/refund/`

Refund a purchase amount back to the user's wallet.

**Response `400`:** If purchase has already been refunded.

---

### `POST /api/admin/purchases/{id}/cancel/`

Cancel a pending purchase, mark it as failed, and refund the user.

**Response `400`:** If purchase status is not `pending`.

---

## 8. VTU Provider Config

Full CRUD for VTU provider configurations. Requires **`CanManageVTU`** permission.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/vtu/providers/` | List all providers |
| `POST` | `/api/admin/vtu/providers/` | Add a new provider |
| `GET` | `/api/admin/vtu/providers/{id}/` | Get provider details |
| `PUT` | `/api/admin/vtu/providers/{id}/` | Full update provider |
| `PATCH` | `/api/admin/vtu/providers/{id}/` | Partial update provider |
| `DELETE` | `/api/admin/vtu/providers/{id}/` | Delete a provider |

### `POST /api/admin/vtu/providers/{id}/funding-config/`

Update funding configuration for a specific provider.

**Request:**
```json
{
  "account_name": "ClubKonnect Ltd",
  "bank_name": "GTBank",
  "account_number": "0123456789",
  "bank_code": "058",
  "min_funding_balance": 50000.00,
  "auto_funding_enabled": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `account_name` | string | No | Provider bank account name |
| `bank_name` | string | No | Provider bank name |
| `account_number` | string | No | Provider bank account number |
| `bank_code` | string | No | Provider bank code |
| `min_funding_balance` | decimal | No | Balance threshold for low-balance alerts |
| `auto_funding_enabled` | boolean | No | Whether to enable auto-funding (requires account info) |

---

## 9. Service Routing Config

Full CRUD for per-service routing configurations. Requires **`CanManageVTU`** permission.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/vtu/routings/` | List all service routings |
| `POST` | `/api/admin/vtu/routings/` | Create routing |
| `GET` | `/api/admin/vtu/routings/{id}/` | Get routing details |
| `PUT` | `/api/admin/vtu/routings/{id}/` | Full update |
| `PATCH` | `/api/admin/vtu/routings/{id}/` | Partial update |
| `DELETE` | `/api/admin/vtu/routings/{id}/` | Delete routing |

**Response includes:** `service`, `primary_provider`, `primary_provider_name`, and `fallbacks` (ordered list with priority).

---

## 10. VTU Control Panel

All VTU control endpoints require **`CanManageVTU`** permission.

### `GET /api/admin/vtu/overview/`

Get a consolidated overview of all providers and services, including real-time balances, success rates, and variation counts.

**Response `200`:**
```json
{
  "providers": [
    {
      "id": 1,
      "name": "clubkonnect",
      "is_active": true,
      "balance": 250000.00,
      "account_name": "ClubKonnect Ltd",
      "bank_name": "GTBank",
      "account_number": "0123456789",
      "bank_code": "058",
      "min_funding_balance": 50000.00,
      "auto_funding_enabled": true
    }
  ],
  "services_summary": [
    {
      "service": "data",
      "is_active": true,
      "routing": {
        "id": 1,
        "service": "data",
        "primary_provider": 1,
        "primary_provider_name": "ClubKonnect",
        "fallbacks": []
      },
      "success_rate": 0.97,
      "total_variations": 45
    }
  ]
}
```

---

### `GET /api/admin/vtu/providers/{id}/balance/`

Fetch the real-time wallet balance for a specific provider from the provider's API.

**Response `200`:**
```json
{ "balance": 250000.00 }
```

---

### `POST /api/admin/vtu/fetch-from-provider/`

Fetch available services and variations from a provider's API and save them to the local database.

**Request:**
```json
{
  "provider_id": 1,
  "service_type": "data"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `provider_id` | integer | Yes | ID of the VTU provider |
| `service_type` | string | Yes | `airtime`, `data`, `tv`, `electricity`, `internet`, `education` |

---

### `POST /api/admin/vtu/variations/{pk}/update-price/{service_type}/`

Update the selling price and agent price for a specific variation.

**URL Parameters:** `pk` (variation ID), `service_type` (`data`, `tv`, `internet`, `education`)

**Request:**
```json
{
  "selling_price": 550.00,
  "agent_price": 480.00
}
```

---

### `POST /api/admin/vtu/variations/bulk-update-price/{service_type}/`

Bulk update prices for multiple variations in a single atomic operation.

**URL Parameters:** `service_type` (`data`, `tv`, `internet`, `education`)

**Request:**
```json
{
  "variations": [
    { "id": 1, "selling_price": 550.00, "agent_price": 480.00 },
    { "id": 2, "selling_price": 1100.00, "agent_price": 950.00 },
    { "id": 3, "selling_price": 2200.00, "agent_price": 1900.00 }
  ]
}
```

---

### `POST /api/admin/vtu/variations/{pk}/toggle/{service_type}/`

Enable or disable a specific variation (plan/package).

**URL Parameters:** `pk` (variation ID), `service_type` (`data`, `airtime`, `tv`, `electricity`, `internet`, `education`)

**Request:**
```json
{ "is_active": false }
```

---

### `POST /api/admin/vtu/services/{service_type}/toggle/`

Enable or disable an entire service type across the platform.

**URL Parameters:** `service_type` (`airtime`, `data`, `tv`, `electricity`, `education`)

**Request:**
```json
{ "is_active": false }
```

---

## 11. Pricing & Plans

Full CRUD for all service variations and promo codes. All require **`CanManageVTU`** permission.

| Resource | Endpoint |
|---|---|
| Airtime Networks | `/api/admin/pricing/airtime/networks/` |
| Data Networks | `/api/admin/pricing/data/networks/` |
| Data Plans | `/api/admin/pricing/data/plans/` |
| TV Networks | `/api/admin/pricing/tv/networks/` |
| TV Plans | `/api/admin/pricing/tv/plans/` |
| Internet Networks | `/api/admin/pricing/internet/networks/` |
| Internet Plans | `/api/admin/pricing/internet/plans/` |
| Education Networks | `/api/admin/pricing/education/networks/` |
| Education Plans | `/api/admin/pricing/education/plans/` |
| Electricity Networks | `/api/admin/pricing/electricity/networks/` |
| Electricity Plans | `/api/admin/pricing/electricity/plans/` |

Each supports standard CRUD methods: `GET` (list), `POST` (create), `GET /{id}/` (detail), `PATCH /{id}/` (partial update), `DELETE /{id}/` (destroy). 
*Note: Any GET query for Plans/Variations returns their corresponding parent network object inside the `service_details` JSON property.*

---

## 12. Automation

All automation endpoints require **`CanManageSiteConfig`** permission.

### `GET /api/admin/automation/config/`

Get the full automation configuration overview — both global settings and per-service settings.

**Response `200`:**
```json
{
  "global_settings": {
    "auto_retry_enabled": true,
    "auto_refund_enabled": true,
    "notify_admin_on_failure": true,
    "delayed_tx_detection_enabled": true,
    "delayed_tx_timeout_minutes": 15
  },
  "services": [
    {
      "id": 1,
      "service": "data",
      "primary_provider": 1,
      "primary_provider_name": "ClubKonnect",
      "retry_enabled": true,
      "retry_count": 3,
      "auto_refund_enabled": true,
      "fallback_enabled": true,
      "pricing_mode": "fixed_margin",
      "customer_margin": "50.00",
      "agent_margin": "20.00"
    }
  ]
}
```

---

### `POST /api/admin/automation/global-settings/`

Update global automation toggles.

**Request:**
```json
{
  "auto_retry_enabled": true,
  "auto_refund_enabled": true,
  "notify_admin_on_failure": true,
  "delayed_tx_detection_enabled": true,
  "delayed_tx_timeout_minutes": 15
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `auto_retry_enabled` | boolean | Yes | Enable automatic retries for failed transactions globally |
| `auto_refund_enabled` | boolean | Yes | Enable automatic refunds for permanently failed transactions |
| `notify_admin_on_failure` | boolean | Yes | Send admin notifications on transaction failures |
| `delayed_tx_detection_enabled` | boolean | Yes | Enable detection of stuck/pending transactions |
| `delayed_tx_timeout_minutes` | integer | Yes | Minutes before a pending transaction is considered delayed (min: 1) |

---

### `POST /api/admin/automation/service/{service}/retry/`

Configure retry behavior for a specific service type.

**URL Parameter:** `service` — e.g. `data`, `airtime`, `tv`, `electricity`, `internet`, `education`

**Request:**
```json
{
  "enabled": true,
  "count": 3
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `enabled` | boolean | Yes | Enable retries for this service |
| `count` | integer | Yes | Maximum retry attempts (0–10) |

---

### `POST /api/admin/automation/service/{service}/fallback/`

Enable or disable fallback to alternative providers for a specific service.

**Request:**
```json
{ "enabled": true }
```

> If `enabled` is omitted, the current value is toggled.

---

### `POST /api/admin/automation/service/{service}/auto-refund/`

Enable or disable auto-refund for a specific service.

**Request:**
```json
{ "enabled": true }
```

> If `enabled` is omitted, the current value is toggled.

---

### `POST /api/admin/automation/service/{service}/pricing-mode/`

Set the pricing strategy for a service.

**Request (Fixed Margin):**
```json
{
  "mode": "fixed_margin",
  "customer_margin": 50.00,
  "agent_margin": 20.00
}
```

**Request (Defined Pricing):**
```json
{
  "mode": "defined"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | string | Yes | `fixed_margin` or `defined` |
| `customer_margin` | decimal | Conditional | Required when mode is `fixed_margin`. Added to `cost_price` for user pricing |
| `agent_margin` | decimal | Conditional | Required when mode is `fixed_margin`. Added to `cost_price` for agent pricing |

**Pricing Behavior:**
- **`fixed_margin`**: Selling prices are automatically calculated as `cost_price + margin`. Both `customer_margin` and `agent_margin` must be defined.
- **`defined`**: Uses the `selling_price` and `agent_price` values set manually on each variation.

---

### `POST /api/admin/automation/detect-delayed/`

Manually trigger detection of delayed (stuck) transactions.

**Response `200`:** Array of delayed transactions:
```json
[
  {
    "id": 45,
    "ref": "TXN_XYZ789",
    "type": "data",
    "beneficiary": "08012345678",
    "time": "2026-04-02T10:00:00Z",
    "minutes_since": 25
  }
]
```

---

## 13. Support Tickets

All support endpoints require **`IsAuthenticated`** permission.

### `GET /api/admin/support/`

List all support tickets ordered by newest first.

### `GET /api/admin/support/{id}/`

Retrieve a ticket with all messages.

### `POST /api/admin/support/{id}/reply/`

Reply to a support ticket as an admin.

**Request:**
```json
{ "message": "We have resolved your issue. Please check your wallet." }
```

> Automatically transitions ticket status from `open` to `in_progress`.

---

## 14. Notifications

### Notification Logs

**Permission:** `IsAuthenticated`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/notifications/logs/` | List all notification logs |

**Filters:** `user`, `channel`, `status`

---

### Announcements

**Permission:** `IsAuthenticated`

Full CRUD at `/api/admin/notifications/announcements/`

---

### Notification Provider Config

**Permission:** `IsSuperUserOnly`

Full CRUD at `/api/admin/notifications/providers/`

> Only superusers can manage notification provider configurations (API keys, etc.).

---

## 15. Administrative Transfers

All transfer endpoints require **`CanInitiateTransfers`** permission.

### Beneficiary Management

Full CRUD at `/api/admin/transfer/beneficiaries/`

---

### `POST /api/admin/transfer/initiate/`

Initiate a bank transfer to an admin beneficiary.

**Request:**
```json
{
  "beneficiary_id": 1,
  "amount": 50000.00,
  "otp": "123456"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `beneficiary_id` | integer | Yes | Admin beneficiary ID |
| `amount` | decimal | Yes | Transfer amount in Naira |
| `otp` | string | Conditional | Admin 2FA OTP (required if 2FA is enabled) |

---

### `GET /api/admin/transfer/logs/`

View all administrative transfer logs.

---

## 16. Transaction Charges

Configure fee and charge rules for transactions (`deposit`, `transfer_others`, `transfer_p2p`).

Charges are deducted separately from the user's wallet as linked `WalletTransaction` records (`charge_for`). All charges associated with a transaction are automatically refunded if the transaction fails or is rejected.

### `GET /api/admin/settings/transaction-charges/`

List all transaction charge rules. Supports filtering by `transaction_type`, `charge_type`, `is_active`, and `block_if_insufficient`.

**Permission:** `CanManageSiteConfig`

---

### `POST /api/admin/settings/transaction-charges/`

Create a new transaction charge rule.

**Request:**
```json
{
  "name": "Deposit Processing Fee",
  "transaction_type": "deposit",
  "charge_type": "percentage",
  "amount": "1.50",
  "cap": "200.00",
  "min_transaction_amount": "100.00",
  "max_transaction_amount": "50000.00",
  "block_if_insufficient": false,
  "is_active": true
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Human-readable name for the charge rule |
| `transaction_type` | string | Yes | One of: `deposit`, `transfer_others`, `transfer_p2p` |
| `charge_type` | string | Yes | One of: `flat`, `percentage` |
| `amount` | decimal | Yes | Flat fee amount in Naira or percentage rate (0–100) |
| `cap` | decimal | No | Maximum fee cap when `charge_type=percentage` (`null` = no cap) |
| `min_transaction_amount` | decimal | No (default: 0) | Minimum transaction amount required to apply this charge |
| `max_transaction_amount` | decimal | No (`null`) | Maximum transaction amount to apply this charge (`null` = no maximum) |
| `block_if_insufficient` | boolean | No (default: false) | If `true`, prevents transaction if wallet balance is insufficient for amount + charge. If `false`, charge is waived/skipped if balance is insufficient. |
| `is_active` | boolean | No (default: true) | Toggle rule on or off |

---

### `GET /api/admin/settings/transaction-charges/{id}/`

Retrieve details of a transaction charge rule.

---

### `PUT / PATCH /api/admin/settings/transaction-charges/{id}/`

Update a transaction charge rule.

---

### `DELETE /api/admin/settings/transaction-charges/{id}/`

Delete a transaction charge rule.

---

### `POST /api/admin/settings/transaction-charges/calculate/`

Preview and calculate applicable charges for any transaction type and amount.

**Request:**
```json
{
  "transaction_type": "transfer_others",
  "amount": "5000.00"
}
```

**Response `200`:**
```json
{
  "transaction_type": "transfer_others",
  "amount": "5000.00",
  "charges": [
    {
      "id": 1,
      "name": "Bank Transfer Fee",
      "charge_type": "percentage",
      "rate_or_amount": "2.00",
      "cap": "200.00",
      "computed_amount": "100.00",
      "block_if_insufficient": true
    },
    {
      "id": 2,
      "name": "Transfer Stamp Duty",
      "charge_type": "flat",
      "rate_or_amount": "50.00",
      "cap": null,
      "computed_amount": "50.00",
      "block_if_insufficient": false
    }
  ],
  "total_charge": "150.00",
  "net_amount": "4850.00"
}
```

---

## 17. Management Commands

### `python manage.py vtu_automation`

Periodic automation command designed to be run via cron (recommended: every 5 minutes).

**Tasks performed:**
1. **Detect Delayed Transactions** — Flags pending transactions older than the configured timeout.
2. **Auto-Retry Failed Transactions** — Retries failures from the last 30 minutes (respects per-service retry limits).
3. **Check Provider Balances** — Alerts when balances fall below configured minimums. Logs eligible providers for auto-funding.

**Example cron entry:**
```
*/5 * * * * cd /path/to/backend && source env/bin/activate && python manage.py vtu_automation
```

---

### `python manage.py sync_clubkonnect`

Sync services and variations from the ClubKonnect provider.

**Options:**

| Flag | Description |
|---|---|
| `--service airtime` | Sync airtime networks only |
| `--service data` | Sync data plans only |
| `--service cable` | Sync TV/cable packages only |
| `--service electricity` | Sync electricity services only |
| `--service internet` | Sync Internet sub packages only |
| _(no flag)_ | Sync all services |

---

## Appendix: Permission Matrix

| Endpoint Group | Permission Required |
|---|---|
| Dashboard (`/stats/`) | `IsAuthenticated` |
| Quick Actions (`/maintenance-mode/`, `/refresh-services/`, `/pause-service/`) | `IsAuthenticated` |
| Users (`/users/`) | `CanManageUsers` |
| Wallet Transactions (`/wallet/transactions/`) | `CanManageWallets` |
| Deposits (`/payments/deposits/`) | `CanManagePayments` |
| Withdrawals (`/payments/withdrawals/`) | `CanManagePayments` |
| Purchases (`/purchases/`) | `CanManageVTU` |
| VTU Providers (`/vtu/providers/`) | `CanManageVTU` |
| VTU Routings (`/vtu/routings/`) | `CanManageVTU` |
| VTU Control Panel (`/vtu/overview/`, `/vtu/fetch-from-provider/`, etc.) | `CanManageVTU` |
| Pricing & Plans (`/pricing/*`) | `CanManageVTU` |
| Automation (`/automation/*`) | `CanManageSiteConfig` |
| Support (`/support/`) | `IsAuthenticated` |
| Notification Logs & Announcements (`/notifications/logs/`, `/notifications/announcements/`) | `IsAuthenticated` |
| Notification Provider Config (`/notifications/providers/`) | `IsSuperUserOnly` |
| Administrative Transfers (`/transfer/*`) | `CanInitiateTransfers` |
| Transaction Charges (`/settings/transaction-charges/`) | `CanManageSiteConfig` |
