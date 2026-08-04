import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_sync_job():
    from django.core.management import call_command
    from summary.models import SiteConfig

    config = SiteConfig.objects.first()
    if config and config.auto_sync_enabled:
        logger.info("APScheduler: Triggering provider plan auto-sync...")
        try:
            call_command('sync_provider_plans')
        except Exception as e:
            logger.error(f"APScheduler: Error running sync_provider_plans: {e}")

def start():
    try:
        from summary.models import SiteConfig
        config = SiteConfig.objects.first()
        if not config or not config.auto_sync_enabled:
            return

        if not scheduler.get_job('auto_sync_plans'):
            try:
                scheduler.add_jobstore(DjangoJobStore(), "default")
            except Exception:
                pass # jobstore may already be added

            scheduler.add_job(
                run_sync_job,
                trigger='interval',
                hours=config.auto_sync_frequency or 24,
                id='auto_sync_plans',
                replace_existing=True,
                misfire_grace_time=300
            )

        if not scheduler.running:
            scheduler.start()
            logger.info("APScheduler: Started auto-sync scheduler daemon.")
    except Exception as e:
        logger.warning(f"APScheduler init deferred or skipped: {e}")

def update_scheduler_config():
    """Dynamically update scheduler job parameters or remove job if disabled."""
    try:
        from summary.models import SiteConfig
        config = SiteConfig.objects.first()

        if not config or not config.auto_sync_enabled:
            if scheduler.get_job('auto_sync_plans'):
                scheduler.remove_job('auto_sync_plans')
                logger.info("APScheduler: Removed auto-sync job (disabled).")
            return

        if not scheduler.running:
            start()
        else:
            scheduler.add_job(
                run_sync_job,
                trigger='interval',
                hours=config.auto_sync_frequency or 24,
                id='auto_sync_plans',
                replace_existing=True,
                misfire_grace_time=300
            )
            logger.info(f"APScheduler: Rescheduled auto-sync job every {config.auto_sync_frequency} hours.")
    except Exception as e:
        logger.error(f"APScheduler config update failed: {e}")
