"""Display-based comparison values, kept separate from exact source metrics."""
from decimal import Decimal, InvalidOperation
import re

METRICS = ('views', 'likes', 'coins', 'favorites', 'comments', 'shares')
UNITS = {'': 1, '万': 10000, '亿': 100000000, 'k': 1000, 'm': 1000000, 'w': 10000}


def parse_display(display):
    if not isinstance(display, str):
        return None
    text = display.strip()
    # Separators are allowed only as conventional groups of three digits.
    if ',' in text:
        if not re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[万亿kKmMwW])?\+?', text):
            return None
        text = text.replace(',', '')
    match = re.fullmatch(r'(\d+(?:\.\d+)?)([万亿kKmMwW]?)(\+?)', text)
    if not match:
        return None
    if not match[2] and '.' in match[1]:
        return None
    try:
        value = Decimal(match[1]) * UNITS[match[2].lower()]
    except (InvalidOperation, KeyError):
        return None
    if not value.is_finite() or value < 0:
        return None
    number = int(value) if value == value.to_integral_value() else float(value)
    kind = 'lower_bound' if match[3] else 'approximate' if match[2] or '.' in match[1] else 'exact'
    return {'kind': kind, 'number': number, 'display': display.strip()}


def observe_metric(exact, display=None):
    parsed = parse_display(display)
    if exact is not None:
        if type(exact) is not int or exact < 0:
            raise ValueError('Exact metrics must be nonnegative integers')
        if parsed and (parsed['kind'] != 'exact' or parsed['number'] != exact):
            raise ValueError('Display precision/value conflicts with exact metric')
        if isinstance(display, str) and display.strip() and not parsed:
            raise ValueError('Unrecognized metric display')
        return {'kind': 'exact', 'exact_value': exact, 'comparison_value': exact,
                'lower_bound': None, 'display': display if isinstance(display, str) else str(exact)}
    if not parsed:
        return {'kind': 'missing', 'exact_value': None, 'comparison_value': None, 'lower_bound': None,
                'display': display if isinstance(display, str) else None}
    return {'kind': parsed['kind'], 'exact_value': parsed['number'] if parsed['kind'] == 'exact' else None,
            'comparison_value': None if parsed['kind'] == 'lower_bound' else parsed['number'],
            'lower_bound': parsed['number'] if parsed['kind'] == 'lower_bound' else None,
            'display': parsed['display']}


def observe_metrics(metrics, displays):
    return {name: observe_metric(metrics.get(name), displays.get(name)) for name in METRICS}
