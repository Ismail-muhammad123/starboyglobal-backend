# Starboy Global Backend

A enterprise-grade Django-based telecommunications, utility billing, and wallet automation platform. It features multi-provider routing (FlowPay, Ketamency, ClubKonnect, VTPass), automatic background plan synchronization, tier-based margin management, developer API integrations, and dual administration interfaces (Full HTML Portal & RESTful Admin API).

---

## 🚀 Overview & Key Capabilities

- **User & Developer Tier Ecosystem**:
  - Multi-role support (`customer`, `agent`, `developer`, `staff`, `admin`).
  - Single-key API key rotation, instant auto-provisioning, and prioritized pricing transparency.
- **Data Plans & VTU Infrastructure**:
  - Categorized plan types (`sme`, `corporate`, `gifting`, `direct`, `general`).
  - Tiered pricing fields per plan (`selling_price`, `agent_price`, `developer_price`).
  - **Restricted Provider Sync**: Automatically updates provider cost price and plan names while preserving custom selling prices, agent prices, developer prices, and active state toggles.
- **Provider Routing & Multi-Tier Margins**:
  - Flexible provider selection per service with fallback failover support.
  - Per-provider per-service catalogue sources (`live` API fetching with cache vs `db` cached catalogue).
  - Tier margin controls (flat or percentage mark-ups for Customer, Agent, and Developer roles).
- **Background Auto-Sync Scheduler**:
  - Background scheduler (`APScheduler`) running periodic plan/network updates from providers.
  - Custom management command (`python manage.py sync_provider_plans`) for cron jobs.
  - Full CRUD schedule management and execution audit logs.
- **Dual Administration Interfaces**:
  - **Admin Web Portal**: Modern HTML/CSS/JS dashboard accessible at `/admin-portal/`.
  - **Admin RESTful API**: DRF API accessible under `/api/admin/` with OpenAPI documentation.

---

## 🛠 Technology Stack

- **Framework**: [Django](https://www.djangoproject.com/) 5.2.x
- **API Engine**: [Django REST Framework](https://www.django-rest-framework.org/) (DRF)
- **Background Scheduler**: `apscheduler`
- **Documentation**: [DRF Spectacular](https://drf-spectacular.readthedocs.io/) (OpenAPI 3.0)
- **Database**: SQLite (Development) / PostgreSQL (Production ready)
- **Payment & Telecommunication Integrations**:
  - FlowPay, Ketamency, ClubKonnect, VTPass
  - Paystack (Virtual accounts & Webhooks)
  - Termii (SMS, Email & OTP)

---

## 📥 Installation and Setup

### 1. Environment Setup
```bash
# Clone the repository and navigate to root directory
cd starboyglobal-backend

# Create and activate virtual environment
python -m venv env
source env/Scripts/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration (`.env`)
Create a `.env` file in the root directory:
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3

# Payment & Telecommunications
PAYSTACK_SECRET_KEY=sk_test_...
FLOWPAY_API_KEY=...
KETAMENCY_API_KEY=...
```

### 3. Database Initialization & Portal Permissions
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_portal_permissions
python manage.py createsuperuser
```

### 4. Running the Development Server
```bash
python manage.py runserver
```

---

## ⚙ Background Auto-Sync Scheduler

To run provider catalogue plan synchronization automatically or via background cron:

```bash
# Run provider plan sync (Dry Run Preview)
python manage.py sync_provider_plans --dry-run

# Run full provider plan sync
python manage.py sync_provider_plans
```

---

## 📖 API Documentation & Frontend Guides

- **Admin FE Update Guide (Legacy FE App Migration)**: See [ADMIN_FE_UPDATE_GUIDE.md](file:///c:/Users/Newton/Desktop/projects/starboy/starboyglobal-backend/ADMIN_FE_UPDATE_GUIDE.md)
- **Full Admin API Reference**: See [ADMIN_API_DOCS.md](file:///c:/Users/Newton/Desktop/projects/starboy/starboyglobal-backend/ADMIN_API_DOCS.md)
- **Developer API Reference**: See [DEVELOPER_API_DOCS.md](file:///c:/Users/Newton/Desktop/projects/starboy/starboyglobal-backend/DEVELOPER_API_DOCS.md)
- **Interactive OpenAPI Documentation**:
  - **Swagger UI**: [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
  - **Schema File**: `schema.yml`

---

## 📄 License
This project is proprietary. All rights reserved.
