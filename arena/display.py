"""Formatting for human reports; raw statistical values remain machine-readable."""
import math


def los_percent(value):
    if value is None or not math.isfinite(value):return '—'
    if value<=.05:return '<0.1%'
    if value>=99.95:return '>99.9%'
    return f'{value:.1f}%'
