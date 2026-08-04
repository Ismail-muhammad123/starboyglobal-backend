from django.apps import AppConfig
import sys


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        # Start background scheduler if running dev server or WSGI/ASGI application
        is_server = any(cmd in sys.argv[0] for cmd in ['runserver', 'gunicorn', 'uvicorn', 'wsgi', 'asgi']) or 'runserver' in sys.argv
        if is_server:
            from . import scheduler
            scheduler.start()

