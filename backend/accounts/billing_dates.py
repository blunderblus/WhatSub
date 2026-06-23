"""Billing-cycle helpers for subscription payment dates."""
import calendar
from datetime import date, timedelta


def add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def subtract_billing_cycle(d: date, billing_cycle: str) -> date:
    if billing_cycle == 'annual':
        return add_months(d, -12)
    if billing_cycle == 'weekly':
        return d - timedelta(weeks=1)
    return add_months(d, -1)


def add_billing_cycle(d: date, billing_cycle: str) -> date:
    if billing_cycle == 'annual':
        return add_months(d, 12)
    if billing_cycle == 'weekly':
        return d + timedelta(weeks=1)
    return add_months(d, 1)


def billing_anchor(sub) -> date | None:
    return sub.renewal_date or sub.start_date


def last_payment_on_or_before(sub, today: date) -> date | None:
    next_pay = next_payment_on_or_after(sub, today)
    if not next_pay:
        anchor = billing_anchor(sub)
        if not anchor:
            return None
        if anchor <= today:
            return anchor
        return subtract_billing_cycle(anchor, sub.billing_cycle)
    return subtract_billing_cycle(next_pay, sub.billing_cycle)


def next_payment_on_or_after(sub, today: date) -> date | None:
    anchor = billing_anchor(sub)
    if not anchor:
        return None
    d = anchor
    for _ in range(500):
        if d >= today:
            return d
        d = add_billing_cycle(d, sub.billing_cycle)
    return d


def default_renewal_date(start_date: date, billing_cycle: str) -> date:
    return add_billing_cycle(start_date, billing_cycle)


def iter_payment_dates(sub, range_start: date, range_end: date):
    anchor = billing_anchor(sub)
    if not anchor or range_end < range_start:
        return
    d = anchor
    for _ in range(500):
        if d <= range_start:
            break
        d = subtract_billing_cycle(d, sub.billing_cycle)
    for _ in range(500):
        if d > range_end:
            break
        if d >= range_start:
            yield d
        d = add_billing_cycle(d, sub.billing_cycle)


def subscription_period(sub, today: date) -> dict:
    next_pay = next_payment_on_or_after(sub, today)
    last_pay = subtract_billing_cycle(next_pay, sub.billing_cycle) if next_pay else None
    duration_days = None
    if last_pay and next_pay:
        duration_days = (next_pay - last_pay).days

    return {
        'last_payment_date': last_pay.isoformat() if last_pay else None,
        'next_payment_date': next_pay.isoformat() if next_pay else None,
        'period_start': last_pay.isoformat() if last_pay else None,
        'period_end': next_pay.isoformat() if next_pay else None,
        'remaining_start': today.isoformat(),
        'remaining_end': next_pay.isoformat() if next_pay else None,
        'duration_days': duration_days,
    }


def build_schedule_items(sub, today: date) -> list[dict]:
    range_start = add_months(today, -12)
    range_end = add_months(today, 12)
    base = {
        'subscription_id': sub.id,
        'platform_id': sub.platform_id,
        'platform_name': sub.platform.name,
        'plan_name': sub.plan_name,
        'amount': sub.payment_amount,
        'start_date': sub.start_date.isoformat() if sub.start_date else None,
        'renewal_date': sub.renewal_date.isoformat() if sub.renewal_date else None,
    }
    items = []
    for payment_date in iter_payment_dates(sub, range_start, range_end):
        is_future = payment_date > today
        items.append({
            'id': f'{sub.id}-{payment_date.isoformat()}',
            **base,
            'date': payment_date.isoformat(),
            'event_type': 'renewal' if is_future else 'payment',
            'status_label': '결제 예정' if is_future else '결제',
        })
    return items
