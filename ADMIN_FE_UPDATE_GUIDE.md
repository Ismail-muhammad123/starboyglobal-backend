# Admin FE App API Update Guide

This guide details all API changes, new endpoints, payload updates, and integration steps required to update the legacy **Admin Frontend (FE) Application** to support the latest **Data Plans & VTU Infrastructure** updates.

---

## 📌 Executive Summary of Changes

| Feature | Legacy Behavior | Updated API Behavior | Key Endpoint(s) |
|---|---|---|---|
| **Variation Pricing** | Only `selling_price` and `agent_price` supported | Supports `selling_price`, `agent_price`, **and `developer_price`** across all service types (data, airtime, tv, electricity, internet, education) | `/api/admin/vtu/variations/<id>/update-price/<service_type>/`<br>`/api/admin/vtu/variations/bulk-update-price/<service_type>/` |
| **Plan Categories (`plan_type`)** | General list only | Support filtering variations by `plan_type`: `sme`, `corporate`, `gifting`, `direct`, `general` | `/api/admin/pricing/data/plans/?plan_type=sme` |
| **Provider Tier Margins & Source** | Global pricing mode only | Per-provider, per-service margin configurations for Customer, Agent, and Developer tiers + Catalogue Source (`live` or `db`) | `/api/admin/vtu/provider-service-configs/` |
| **Live Catalogue Preview** | Not available | Preview live provider plans with role-based price calculations (`customer`, `agent`, `developer`) | `/api/admin/vtu/live-catalogue/` |
| **Auto-Sync Jobs & Scheduler** | Manual fetch only | Schedule recurring background auto-sync jobs (Daily, Weekly, Hourly, etc.) per service & provider with execution audit logs | `/api/admin/automation/schedules/`<br>`/api/admin/automation/logs/` |
| **Restricted Provider Sync** | Sync replaced local data | Sync updates only cost price & name, preserving custom `selling_price`, `agent_price`, `developer_price`, and `is_active` toggle | System-wide sync manager |

---

## 🛠 Detailed Endpoint & Integration Guide

### 1. Variation Price Updates (Single & Bulk)

#### Single Variation Price Update
**`POST /api/admin/vtu/variations/{id}/update-price/{service_type}/`**

* **Supported `service_type` values**: `data`, `airtime`, `tv`, `electricity`, `internet`, `education`

**Request Payload:**
```json
{
  "selling_price": 280.00,
  "agent_price": 270.00,
  "developer_price": 265.00
}
```
*Note: All fields are optional. Pass only the fields you wish to update.*

**Response `200 OK`:**
```json
{
  "status": "SUCCESS",
  "message": "Price updated."
}
```

---

#### Bulk Variation Price Update
**`POST /api/admin/vtu/variations/bulk-update-price/{service_type}/`**

* **Supported `service_type` values**: `data`, `airtime`, `tv`, `electricity`, `internet`, `education`

**Request Payload:**
```json
{
  "variations": [
    {
      "id": 12,
      "selling_price": 280.00,
      "agent_price": 270.00,
      "developer_price": 265.00
    },
    {
      "id": 13,
      "selling_price": 550.00,
      "agent_price": 530.00,
      "developer_price": 520.00
    }
  ]
}
```

**Response `200 OK`:**
```json
{
  "status": "SUCCESS",
  "message": "Bulk update for data variations completed."
}
```

---

### 2. Pricing & Data Plan Categorization (`plan_type`)

#### List Data Plans with Filters
**`GET /api/admin/pricing/data/plans/`**

**Query Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `service` | integer | Data network service ID (e.g. `1` for MTN) |
| `plan_type` | string | Filter by plan category: `sme`, `corporate`, `gifting`, `direct`, `general` |
| `is_active` | boolean | `true` or `false` |
| `search` | string | Search by plan name or `variation_id` |

**Example Request:**
`GET /api/admin/pricing/data/plans/?service=1&plan_type=sme&is_active=true`

**Response Item Schema includes `developer_price` & `plan_type`:**
```json
[
  {
    "id": 101,
    "name": "1.0 GB SME Data (30 Days)",
    "variation_id": "500",
    "cost_price": "240.00",
    "selling_price": "280.00",
    "agent_price": "270.00",
    "developer_price": "265.00",
    "plan_type": "sme",
    "is_active": true,
    "service": 1,
    "provider_name": "flowpay"
  }
]
```

---

### 3. Provider Service Config & Multi-Tier Margins

Manage per-provider and per-service margin configurations and catalogue sources (`live` API fetching vs `db` cached catalogue).

#### List / Create Provider Service Configs
**`GET /api/admin/vtu/provider-service-configs/`**
**`POST /api/admin/vtu/provider-service-configs/`**

**Request Payload (Create / Update):**
```json
{
  "provider": 1,
  "service_type": "data",
  "catalogue_source": "live",
  "live_cache_ttl_seconds": 300,
  "customer_margin_type": "flat",
  "customer_margin_value": 20.00,
  "agent_margin_type": "flat",
  "agent_margin_value": 10.00,
  "developer_margin_type": "flat",
  "developer_margin_value": 5.00
}
```

* **`catalogue_source`**: `live` (fetch directly from provider with cache) or `db` (use stored variations table).
* **`margin_type` options**: `flat` (fixed currency addition) or `percentage` (percentage mark-up).

---

### 4. Live Catalogue Preview API

Preview live provider plan offerings with automatically calculated prices for any user role tier.

**`GET /api/admin/vtu/live-catalogue/`**

**Query Parameters:**
| Parameter | Required | Description |
|---|---|---|
| `provider_id` | Yes | ID of the VTU Provider Config |
| `service_type` | Yes | `data`, `airtime`, `tv`, `electricity`, `internet`, `education` |
| `role` | No | Target role tier preview: `customer`, `agent`, or `developer` (default: `customer`) |

**Example Request:**
`GET /api/admin/vtu/live-catalogue/?provider_id=1&service_type=data&role=developer`

**Response `200 OK`:**
```json
{
  "provider": "FlowPay",
  "service_type": "data",
  "role_preview": "developer",
  "margin_applied": { "type": "flat", "value": 5.0 },
  "total_items": 42,
  "items": [
    {
      "variation_id": "1000",
      "name": "1GB SME",
      "cost_price": 240.0,
      "selling_price": 245.0,
      "customer_price": 260.0,
      "agent_price": 250.0,
      "developer_price": 245.0
    }
  ]
}
```

---

### 5. Background Auto-Sync Schedules & Audit Logs

Manage automatic background plan/network synchronizations and monitor execution logs.

#### List / Create Auto-Sync Schedules
**`GET /api/admin/automation/schedules/`**
**`POST /api/admin/automation/schedules/`**

**Request Payload:**
```json
{
  "name": "Daily MTN & Glo Data Sync",
  "provider": 1,
  "service_type": "data",
  "frequency": "daily",
  "start_date_time": "2026-08-07T02:00:00Z",
  "is_active": true
}
```
* **`service_type`**: `all`, `airtime`, `data`, `tv`, `electricity`, `internet`, `education`
* **`frequency`**: `hourly`, `every_6_hours`, `every_12_hours`, `daily`, `weekly`

#### Toggle Schedule Active Status
**`POST /api/admin/automation/schedules/{id}/toggle/`**

#### Trigger Immediate Schedule Run
**`POST /api/admin/automation/schedules/{id}/run-now/`**

#### Audit Logs of Auto-Sync Runs
**`GET /api/admin/automation/logs/`**

**Query Filters:** `status` (`SUCCESS`, `FAILED`), `service_type`, `provider_name`, `schedule`.

---

## 📑 FE UI Checklist for Upgrading the Legacy Admin FE App

- [ ] **Price Editing Forms**: Add an input field for `Developer Price` alongside `Selling Price` (Customer) and `Agent Price`.
- [ ] **Data Plans Table**: Add a column and dropdown filter for **Plan Type** (`SME`, `Corporate`, `Gifting`, `Direct`, `General`).
- [ ] **Bulk Price Update Modal**: Include `developer_price` input column in bulk edit modals.
- [ ] **Provider Management Tab**: Integrate the **Provider Service Config** settings (Catalogue Source toggle: Live vs DB, and Margin Tiers for Customer/Agent/Developer).
- [ ] **Live Catalogue Preview View**: Create a preview drawer/modal calling `/api/admin/vtu/live-catalogue/` with a role selector dropdown.
- [ ] **Auto-Sync Jobs Dashboard**: Add a schedule manager component using `/api/admin/automation/schedules/` and log history viewer using `/api/admin/automation/logs/`.
