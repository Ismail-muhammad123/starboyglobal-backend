import logging
import time
from django.utils import timezone
from datetime import timedelta
from orders.models import AutoSyncSchedule, AutoSyncLog, VTUProviderConfig
from orders.router import ProviderRouter

logger = logging.getLogger(__name__)

SERVICE_SYNC_METHODS = {
    'airtime': 'sync_airtime',
    'data': 'sync_data',
    'tv': 'sync_cable',
    'electricity': 'sync_electricity',
    'internet': 'sync_internet',
    'education': 'sync_education',
}

def calculate_next_run(frequency: str, from_dt=None):
    from_dt = from_dt or timezone.now()
    if frequency == 'hourly':
        return from_dt + timedelta(hours=1)
    elif frequency == 'weekly':
        return from_dt + timedelta(weeks=1)
    elif frequency == 'monthly':
        return from_dt + timedelta(days=30)
    else:  # daily or default
        return from_dt + timedelta(days=1)


def deactivate_unreturned_items(provider_config, service_type, synced_pks=None, synced_variation_ids=None):
    """
    Deactivates any plans/variations/networks belonging to provider_config & service_type
    that were NOT present in the latest successful provider sync response.
    
    Only runs if synced_pks or synced_variation_ids is non-empty.
    """
    if not provider_config:
        return 0

    if isinstance(provider_config, str):
        from orders.models import VTUProviderConfig
        from django.db.models import Q
        provider_config = VTUProviderConfig.objects.filter(
            Q(name__iexact=provider_config) | Q(slug__iexact=provider_config)
        ).first()

    if not provider_config:
        return 0

    has_pks = bool(synced_pks and len(synced_pks) > 0)
    has_var_ids = bool(synced_variation_ids and len(synced_variation_ids) > 0)

    if not has_pks and not has_var_ids:
        return 0

    pks_set = set(synced_pks or [])
    var_ids_set = set(synced_variation_ids or [])

    count = 0
    from orders.models import (
        AirtimeNetwork, DataVariation, TVVariation,
        ElectricityVariation, InternetVariation, EducationVariation
    )

    if service_type == 'airtime':
        qs = AirtimeNetwork.objects.filter(provider=provider_config, is_active=True)
        if pks_set:
            qs = qs.exclude(pk__in=pks_set)
        if var_ids_set:
            qs = qs.exclude(service_id__in=var_ids_set)
        count = qs.update(is_active=False)

    elif service_type == 'data':
        qs = DataVariation.objects.filter(service__provider=provider_config, is_active=True)
        if pks_set:
            qs = qs.exclude(pk__in=pks_set)
        if var_ids_set:
            qs = qs.exclude(variation_id__in=var_ids_set)
        count = qs.update(is_active=False)

    elif service_type in ('tv', 'cable'):
        qs = TVVariation.objects.filter(service__provider=provider_config, is_active=True)
        if pks_set:
            qs = qs.exclude(pk__in=pks_set)
        if var_ids_set:
            qs = qs.exclude(variation_id__in=var_ids_set)
        count = qs.update(is_active=False)

    elif service_type == 'electricity':
        qs = ElectricityVariation.objects.filter(service__provider=provider_config, is_active=True)
        if pks_set:
            qs = qs.exclude(pk__in=pks_set)
        if var_ids_set:
            qs = qs.exclude(variation_id__in=var_ids_set)
        count = qs.update(is_active=False)

    elif service_type == 'internet':
        qs = InternetVariation.objects.filter(service__provider=provider_config, is_active=True)
        if pks_set:
            qs = qs.exclude(pk__in=pks_set)
        if var_ids_set:
            qs = qs.exclude(variation_id__in=var_ids_set)
        count = qs.update(is_active=False)

    elif service_type == 'education':
        qs = EducationVariation.objects.filter(service__provider=provider_config, is_active=True)
        if pks_set:
            qs = qs.exclude(pk__in=pks_set)
        if var_ids_set:
            qs = qs.exclude(variation_id__in=var_ids_set)
        count = qs.update(is_active=False)

    if count > 0:
        logger.info(f"Deactivated {count} un-returned {service_type} item(s) for provider {provider_config.get_name_display()}")

    return count



def execute_sync_schedule(schedule_id: int):
    """
    Executes a scheduled sync job identified by AutoSyncSchedule PK.
    Creates an immutable AutoSyncLog entry upon completion.
    """
    try:
        schedule = AutoSyncSchedule.objects.get(pk=schedule_id)
    except AutoSyncSchedule.DoesNotExist:
        logger.error(f"AutoSyncSchedule {schedule_id} does not exist.")
        return

    if not schedule.is_active:
        logger.info(f"AutoSyncSchedule '{schedule.name}' is disabled. Skipping execution.")
        return

    started_at = timezone.now()
    start_time_monotonic = time.monotonic()

    # Determine target providers
    if schedule.provider:
        providers = [schedule.provider] if schedule.provider.is_active else []
    else:
        providers = list(VTUProviderConfig.objects.filter(is_active=True))

    # Determine target service types
    if schedule.service_type and schedule.service_type != 'all':
        service_types = [schedule.service_type]
    else:
        service_types = list(SERVICE_SYNC_METHODS.keys())

    total_synced = 0
    details = {}
    errors = []

    for p in providers:
        impl = ProviderRouter.get_provider_implementation(p.name)
        if not impl:
            errors.append(f"Provider {p.name}: implementation unavailable")
            continue

        p_key = p.name
        details[p_key] = {}

        for s_type in service_types:
            method_name = SERVICE_SYNC_METHODS.get(s_type)
            if not method_name:
                continue

            sync_func = getattr(impl, method_name, None)
            if sync_func:
                try:
                    count = sync_func()
                    total_synced += count
                    details[p_key][s_type] = count
                except Exception as e:
                    err_msg = f"{p_key}.{s_type} error: {str(e)}"
                    errors.append(err_msg)
                    details[p_key][s_type] = f"Error: {str(e)}"

    finished_at = timezone.now()
    duration = round(time.monotonic() - start_time_monotonic, 2)

    if not providers:
        status_code = 'FAILED'
        error_str = "No active providers configured for this schedule."
    elif errors and total_synced == 0:
        status_code = 'FAILED'
        error_str = "; ".join(errors)
    elif errors:
        status_code = 'PARTIAL'
        error_str = "; ".join(errors)
    else:
        status_code = 'SUCCESS'
        error_str = None

    provider_name_str = schedule.provider.get_name_display() if schedule.provider else "All Providers"

    # Create immutable log record
    AutoSyncLog.objects.create(
        schedule=schedule,
        schedule_name=schedule.name,
        provider_name=provider_name_str,
        service_type=schedule.get_service_type_display(),
        status=status_code,
        items_synced=total_synced,
        details=details,
        error_message=error_str,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
    )

    # Update schedule execution timestamps
    schedule.last_run = started_at
    schedule.next_run = calculate_next_run(schedule.frequency, started_at)
    schedule.save(update_fields=['last_run', 'next_run'])

    logger.info(f"AutoSyncSchedule '{schedule.name}' executed: {status_code}, {total_synced} items synced in {duration}s.")
