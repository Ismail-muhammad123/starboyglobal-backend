from decimal import Decimal, ROUND_HALF_UP

def apply_margin(cost: Decimal, margin_value: Decimal, margin_type: str) -> Decimal:
    """
    Compute selling price from cost + configured margin.

    Args:
        cost:         Raw cost price from provider.
        margin_value: The margin amount (flat ₦ or % value).
        margin_type:  'flat' | 'percentage'

    Returns:
        Decimal selling price. If margin_value == 0, returns cost unchanged.
    """
    try:
        cost = Decimal(str(cost))
    except Exception:
        cost = Decimal('0.00')

    try:
        margin_value = Decimal(str(margin_value))
    except Exception:
        margin_value = Decimal('0.00')

    if margin_value == Decimal('0.00'):
        return cost

    if margin_type == 'percentage':
        addition = (cost * margin_value / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    else:  # flat
        addition = margin_value

    return cost + addition


def get_provider_service_config(provider, service_type: str):
    """
    Retrieve or synthesize a ProviderServiceConfig dictionary for a given provider × service pair.
    Falls back to SiteConfig global margins if no ProviderServiceConfig row exists.
    """
    from orders.models import ProviderServiceConfig
    from summary.models import SiteConfig

    if provider:
        config_obj = ProviderServiceConfig.objects.filter(
            provider=provider, service_type=service_type
        ).first()

        if config_obj:
            return {
                'catalogue_source': config_obj.catalogue_source,
                'live_cache_ttl_seconds': config_obj.live_cache_ttl_seconds,
                'customer_margin_type': config_obj.customer_margin_type,
                'customer_margin_value': config_obj.customer_margin_value,
                'agent_margin_type': config_obj.agent_margin_type,
                'agent_margin_value': config_obj.agent_margin_value,
                'developer_margin_type': config_obj.developer_margin_type,
                'developer_margin_value': config_obj.developer_margin_value,
            }

    # Synthesize a default config from SiteConfig global margins
    site = SiteConfig.objects.first()
    fallback_margin = getattr(site, f"{service_type}_margin", Decimal('0.00')) if site else Decimal('0.00')

    return {
        'catalogue_source': 'db',
        'live_cache_ttl_seconds': 300,
        'customer_margin_type': 'flat',
        'customer_margin_value': fallback_margin,
        'agent_margin_type': 'flat',
        'agent_margin_value': Decimal('0.00'),
        'developer_margin_type': 'flat',
        'developer_margin_value': Decimal('0.00'),
    }


def resolve_margin_for_role(config_dict: dict, role: str):
    """
    Returns (margin_type, margin_value) for a user role.
    """
    if role == 'agent':
        return config_dict.get('agent_margin_type', 'flat'), config_dict.get('agent_margin_value', Decimal('0.00'))
    elif role == 'developer':
        return config_dict.get('developer_margin_type', 'flat'), config_dict.get('developer_margin_value', Decimal('0.00'))
    else:
        return config_dict.get('customer_margin_type', 'flat'), config_dict.get('customer_margin_value', Decimal('0.00'))
