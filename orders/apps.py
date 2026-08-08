from django.apps import AppConfig
import sys
import os


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        # Start background scheduler if running dev server or WSGI/ASGI application
        is_server = any(cmd in sys.argv[0] for cmd in ['runserver', 'gunicorn', 'uvicorn', 'wsgi', 'asgi']) or 'runserver' in sys.argv
        if is_server:
            # File lock to ensure only ONE worker process starts the background scheduler
            try:
                import fcntl
                lock_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.scheduler.lock')
                self._lock_file = open(lock_file_path, 'w')
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (ImportError, IOError, OSError):
                # Another worker process already owns the scheduler lock or OS does not support fcntl
                return

            import threading
            from . import scheduler
            # Defer scheduler start slightly so app initialization completes first without DB warning
            threading.Timer(2.0, scheduler.start).start()

