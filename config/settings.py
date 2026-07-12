from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url
import firebase_admin
from firebase_admin import credentials

load_dotenv() # This loads the variables from .env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-^pu^2d0rud-1_y+_bab)mm+d!nw$u9)k0z1w!!ml(s18$pd#(8'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

PRODUCTION = os.environ.get("PRODUCTION", "True").lower() == "true"

ALLOWED_HOSTS = []

allowed_host_addresses = os.environ.get("DJANGO_ALLOWED_HOSTS",None)

if allowed_host_addresses is not None:
    ALLOWED_HOSTS += [i for i in allowed_host_addresses.split(",")]

if DEBUG:
    ALLOWED_HOSTS+=['*']

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_ALL_HEADERS = True   # Allow every request header (incl. X-API-KEY)

# Explicit allow-list kept as a safety reference; CORS_ALLOW_ALL_HEADERS supersedes it.
from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-api-key",
]

CSRF_TRUSTED_ORIGINS = [
    'https://data-app-backend.onrender.com',
    'https://data-app-backend-9yxa.onrender.com',
    'https://z9trades-backend-production.up.railway.app',
    'https://a-star-backend-staging.up.railway.app',
    'https://backend.stardata.com.ng',
    'https://stardata.com.ng',
    'https://admin.stardata.com.ng'
]

csrf_origins_env = os.environ.get("CSRF_TRUSTED_ORIGINS", None)
if csrf_origins_env:
    CSRF_TRUSTED_ORIGINS += [origin.strip() for origin in csrf_origins_env.split(",") if origin.strip()]

# Application definition

INSTALLED_APPS = [
    # Force runserver to use WhiteNoise instead of Django static handler
    'whitenoise.runserver_nostatic',

    # >custom template for admin
    'jazzmin',


    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'django.contrib.humanize',

    # 3rd party apps
    'drf_spectacular',
    'corsheaders',

    # custom apps
    'users',
    'orders',
    'wallet',
    'payments',
    'summary',
    'notifications',
    'admin_api',
    'support',
    'developer_api',
    'django_filters',
]


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Starboy Global VTU API Server',
    'DESCRIPTION': (
        'Comprehensive API Documentation for the Starboy Global VTU Backend.\n\n'
        'This API serves the mobile and web client, handling user authentication, '
        'wallets, data/airtime/electricity purchases, referrals, and admin functionality. '
        'Interact with the live or local test environments using the server toggles below.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': True,
    'CONTACT': {
        'name': 'API Support Team',
        'email': 'support@astar.com',
    },
    'SERVERS': [
        {'url': 'https://backend.stardata.com.ng', 'description': 'Production Environment'},
        {'url': 'http://localhost:8000', 'description': 'Local Test Environment'},
    ],
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'displayRequestDuration': True,
        'filter': True,
        'syntaxHighlight.theme': 'monokai',  # Dark theme for syntax highlighting
        'defaultModelsExpandDepth': -1,  # Hide models at the bottom by default to keep it clean
        'defaultModelRendering': 'example',
    },
    'COMPONENT_SPLIT_REQUEST': True,
}


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=365),  
    'REFRESH_TOKEN_LIFETIME': timedelta(days=365), 
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

AUTH_USER_MODEL = "users.User"


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
     'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

if PRODUCTION:
    DATABASES = {
     'default':  dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600
        )
    }
        


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'users.validators.DigitsOnlyValidator',
        'OPTIONS': {
            'min_length': 6,
        },
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

WHITENOISE_MANIFEST_STRICT = False
# Allow WhiteNoise to discover static files via finders in all environments.
# This keeps static serving consistent even when DEBUG/PRODUCTION flags differ.
WHITENOISE_USE_FINDERS = True

# Backward compatibility for packages that still read legacy static settings
# (e.g. cloudinary_storage's collectstatic hook).
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'


DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage' if PRODUCTION else 'django.core.files.storage.FileSystemStorage'

# Media Files (Cloudinary Setup for Production, Local for Dev)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage" if PRODUCTION else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

if PRODUCTION:
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME', ''),
        'API_KEY': os.getenv('CLOUDINARY_API_KEY', ''),
        'API_SECRET': os.getenv('CLOUDINARY_API_SECRET', ''),
    }

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ----------------------------- Zoho Configurations -----------------------------

ZOHO_EMAIL_USER = os.getenv("ZOHO_EMAIL_USER", "")
ZOHO_SMS_SENDER_ID = os.getenv("ZOHO_SMS_SENDER_ID", "")
ZOHO_WHATSAPP_NUMBER = os.getenv("ZOHO_WHATSAPP_NUMBER", "")
ZOHO_API_KEY = os.getenv("ZOHO_API_KEY", "")
ZOHO_MAIL_API_URL = os.getenv("ZOHO_MAIL_API_URL", "https://api.zeptomail.com/v1.1/email") # Typically used for Zoho ZeptoMail

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = ZOHO_EMAIL_USER or "noreply@yourdomain.com"

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


# Payment & Notification credentials will be configured via Admin Dashboard



# Provider & SMS credentials moved to database config

# ----------------------------- Firebase Configuration -----------------------------

FIREBASE_CREDS = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN", "googleapis.com"),
}

# Only initialize if the project_id is available (prevents local crashes if env variables are missing)
if FIREBASE_CREDS.get("project_id"):
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(FIREBASE_CREDS)
        firebase_admin.initialize_app(cred)


# ----------------------------- ClubKonnect Configuration -----------------------------

CLUBKONNECT_BASE_URL = "https://www.nellobytesystems.com"
CLUBKONNECT_TIMEOUT = 30

# Endpoints
CLUBKONNECT_ENDPOINTS = {
    # wallet balance
    "balance": "/APIWalletBalanceV1.asp",

    # airtime
    "airtime_networks": "/APIAirtimeDiscountV2.asp",
    "buy_airtime": "/APIAirtimeV1.asp",
   
    # data
    "buy_data": "/APIDatabundleV1.asp",
    "data_plans": "/APIDatabundlePlansV2.asp",
    "query": "/APIQueryV1.asp",
    "cancel": "/APICancelV1.asp",

    # Internet
    "verify_internet": "/APIVerifySmileV1.asp",
    "buy_internet": "/APISmileV1.asp",
    "internet_packages": "/APISmilePackagesV2.asp",

    # Cable
    "buy_cable": "/APICableTVV1.asp",
    "verify_cable": "/APIVerifyCableTVV1.0.asp",
    "cable_packages": "/APICableTVPackagesV2.asp",

    # Electricity
    "buy_electricity": "/APIElectricityV1.asp",
    "verify_electricity": "/APIVerifyElectricityV1.asp",
    "electricity_discos": "/APIElectricityDiscosV2.asp",
}

# ----------------------------- End ClubKonnect Configuration -----------------------------
# ----------------------------- Jazzmin Configuration -----------------------------

JAZZMIN_SETTINGS = {
    "site_title": "A-Star Data App",
    "site_header": "A-Star Data",
    "site_brand": "A-Star",
    "site_logo": "img/logo.png",
    "welcome_sign": "Welcome to A-Star Data App",
    "copyright": "A-Star Data App Ltd",
    "search_model": ["users.User"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"model": "users.User"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": ["users.OTP", "authtoken.Token"],
    "order_with_respect_to": ["summary", "users", "orders", "wallet", "payments"],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "users.User": "fas fa-user-friends",
        "users.Group": "fas fa-users",
        "wallet.Wallet": "fas fa-wallet",
        "wallet.VirtualAccount": "fas fa-id-card",
        "wallet.WalletTransaction": "fas fa-exchange-alt",
        "payments.Deposit": "fas fa-money-bill-wave",
        "payments.Withdrawal": "fas fa-hand-holding-usd",
        "orders.Purchase": "fas fa-shopping-cart",
        "orders.DataService": "fas fa-wifi",
        "orders.DataVariation": "fas fa-signal",
        "orders.ElectricityService": "fas fa-bolt",
        "orders.ElectricityVariation": "fas fa-plug",
        "orders.TVService": "fas fa-tv",
        "orders.TVVariation": "fas fa-satellite-dish",
        "orders.InternetVariation": "fas fa-internet",
        "orders.AirtimeNetwork": "fas fa-phone",
        "summary.SummaryDashboard": "fas fa-chart-pie",
        "summary.SiteConfig": "fas fa-cogs",
        "summary.SystemTransaction": "fas fa-exchange-alt",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_js": "js/jazzmin_fix.js",
    "custom_css": "css/admin_custom.css",
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {},
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-indigo",
    "accent": "accent-indigo",
    "navbar": "navbar-indigo navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-indigo",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}

# Twilio & SendGrid Notifications
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
TWILIO_WHATSAPP_CONTENT_SID = os.environ.get("TWILIO_WHATSAPP_CONTENT_SID")
TWILIO_DEBUG_PHONE = os.environ.get("TWILIO_DEBUG_PHONE")

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

# Firebase Cloud Messaging
FCM_SERVER_KEY = os.environ.get("FCM_SERVER_KEY")

# Termii SMS (primary SMS provider)
TERMII_API_KEY = os.environ.get("TERMII_API_KEY")
TERMII_SENDER_ID = os.environ.get("TERMII_SENDER_ID", "AStarData")
TERMII_SMS_BASE_URL = os.environ.get("TERMII_SMS_BASE_URL", "https://api.ng.termii.com/api")
TERMII_SMS_TYPE = os.environ.get("TERMII_SMS_TYPE", "plain")
TERMII_CHANNEL = os.environ.get("TERMII_CHANNEL", "generic")
