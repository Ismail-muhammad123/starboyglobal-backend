import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

import sys

def _ensure_jobstore():
    if 'test' in sys.argv:
        return
    try:
        scheduler.add_jobstore(DjangoJobStore(), "default")
    except Exception:
        pass



def sync_all_schedules():
    """Register/reschedule all active AutoSyncSchedule records in APScheduler."""
    if 'test' in sys.argv:
        return
    _ensure_jobstore()
    from orders.models import AutoSyncSchedule
    from orders.utils.sync_runner import execute_sync_schedule

    try:
        schedules = AutoSyncSchedule.objects.all()
        for sched in schedules:
            job_id = f"auto_sync_schedule_{sched.id}"
            if not sched.is_active:
                if scheduler.get_job(job_id):
                    scheduler.remove_job(job_id)
                    logger.info(f"APScheduler: Removed disabled job {job_id}")
                continue

            start_dt = sched.start_date_time
            if sched.frequency == 'hourly':
                trigger_kwargs = {'trigger': 'interval', 'hours': 1}
            elif sched.frequency == 'weekly':
                trigger_kwargs = {'trigger': 'interval', 'weeks': 1}
            elif sched.frequency == 'monthly':
                trigger_kwargs = {'trigger': 'interval', 'days': 30}
            else:  # daily
                trigger_kwargs = {'trigger': 'interval', 'days': 1}

            if start_dt:
                trigger_kwargs['start_date'] = start_dt

            scheduler.add_job(
                execute_sync_schedule,
                args=[sched.id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=600,
                **trigger_kwargs
            )
            logger.info(f"APScheduler: Registered schedule job '{sched.name}' ({job_id}) frequency={sched.frequency}")
    except Exception as e:
        logger.warning(f"APScheduler sync_all_schedules deferred or error: {e}")


def start():
    if 'test' in sys.argv:
        return
    try:
        _ensure_jobstore()
        sync_all_schedules()
        if not scheduler.running:
            scheduler.start()
            logger.info("APScheduler daemon started successfully.")
    except Exception as e:
        logger.warning(f"APScheduler daemon start error: {e}")



def update_schedule_job(schedule_id: int):
    """Re-sync single AutoSyncSchedule job when created, updated or toggled."""
    if 'test' in sys.argv:
        return
    _ensure_jobstore()

    from orders.models import AutoSyncSchedule
    from orders.utils.sync_runner import execute_sync_schedule

    job_id = f"auto_sync_schedule_{schedule_id}"
    try:
        sched = AutoSyncSchedule.objects.get(pk=schedule_id)
        if not sched.is_active:
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            return

        start_dt = sched.start_date_time
        if sched.frequency == 'hourly':
            trigger_kwargs = {'trigger': 'interval', 'hours': 1}
        elif sched.frequency == 'weekly':
            trigger_kwargs = {'trigger': 'interval', 'weeks': 1}
        elif sched.frequency == 'monthly':
            trigger_kwargs = {'trigger': 'interval', 'days': 30}
        else:
            trigger_kwargs = {'trigger': 'interval', 'days': 1}

        if start_dt:
            trigger_kwargs['start_date'] = start_dt

        if not scheduler.running:
            start()
        else:
            scheduler.add_job(
                execute_sync_schedule,
                args=[sched.id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=600,
                **trigger_kwargs
            )
            logger.info(f"APScheduler: Updated job '{sched.name}' ({job_id})")
    except AutoSyncSchedule.DoesNotExist:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
    except Exception as e:
        logger.error(f"Error updating schedule job {job_id}: {e}")
