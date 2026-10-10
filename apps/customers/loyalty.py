"""Loyalty points: earned only inside a promo period, on a sale's amount excluding VAT.

Each promo sets its own rate: every `spend_per_point` pesos of net sales earns one whole point
(any remainder earns nothing). If promos overlap on the sale's date, the one that gives the
customer the most points applies. Awarding and reversing are idempotent per transaction.
"""
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Customer, LoyaltyEntry, LoyaltyPromo


def net_of_vat(txn):
    """What the customer paid without VAT (the sale total already includes the tax)."""
    return Decimal(str(txn.total)) - Decimal(str(txn.tax))


def points_for(net, spend_per_point):
    if net <= 0 or spend_per_point <= 0:
        return 0
    return int(net // spend_per_point)


def best_promo(day, net):
    """(promo, points) for the promo running on `day` (dates inclusive) that earns the most on
    `net`; ties go to the earlier-starting promo. (None, 0) when no promo earns anything."""
    best, best_points = None, 0
    for promo in LoyaltyPromo.objects.filter(is_active=True, start_date__lte=day, end_date__gte=day).order_by('start_date', 'id'):
        points = points_for(net, promo.spend_per_point)
        if points > best_points:
            best, best_points = promo, points
    return best, best_points


@db_transaction.atomic
def award_points(txn):
    """Record the points a completed sale earns; a no-op without a customer, outside every promo,
    when nothing is earned, or when this sale was already awarded. Returns the entry or None."""
    if not txn.customer_id:
        return None
    if LoyaltyEntry.objects.filter(transaction=txn, kind='earn').exists():
        return None
    net = net_of_vat(txn)
    promo, points = best_promo(timezone.localdate(txn.created_at), net)
    if promo is None:
        return None
    entry = LoyaltyEntry.objects.create(
        customer_id=txn.customer_id, transaction=txn, kind='earn', points=points, net_amount=net,
        spend_per_point=promo.spend_per_point, promo=promo, promo_name=promo.name)
    Customer.objects.filter(pk=txn.customer_id).update(loyalty_points=F('loyalty_points') + points)
    return entry


def _reverse(earned):
    """Reverse one earn row (never below the customer's balance); once per earn row."""
    link = {'transaction': earned.transaction} if earned.transaction_id else {'sync_event': earned.sync_event}
    if LoyaltyEntry.objects.filter(kind='reversal', **link).exists():
        return None
    customer = Customer.objects.select_for_update().get(pk=earned.customer_id)
    points = min(earned.points, customer.loyalty_points)
    if points <= 0:
        return None
    entry = LoyaltyEntry.objects.create(
        customer=customer, kind='reversal', points=-points, net_amount=earned.net_amount,
        spend_per_point=earned.spend_per_point, promo=earned.promo, promo_name=earned.promo_name, **link)
    Customer.objects.filter(pk=customer.pk).update(loyalty_points=F('loyalty_points') - points)
    return entry


@db_transaction.atomic
def reverse_points(txn):
    """Take back what a refunded web sale earned."""
    earned = LoyaltyEntry.objects.filter(transaction=txn, kind='earn').first()
    return _reverse(earned) if earned else None


# ---- POS invoices arriving as sync events ---------------------------------------------------
# The device sends `customerId` (the backend customer id it downloaded), `totalCentavos`,
# `taxSummary.vatAmountCentavos` and `issuedAt`. Money is recomputed here; the device's own
# estimate is never trusted. A bad or unknown customer id just means no points: it must never
# stop the invoice's inventory from syncing.

def _whole(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _event_customer(payload):
    try:
        customer_id = int(str(payload.get('customerId', '')).strip())
    except ValueError:
        return None
    return Customer.objects.filter(pk=customer_id).first()


def _event_amounts(payload):
    """(total, vat) in centavos, or None when the payload does not carry usable money."""
    total = _whole(payload.get('totalCentavos'))
    summary = payload.get('taxSummary')
    vat = _whole(summary.get('vatAmountCentavos')) if isinstance(summary, dict) else None
    if total is None or vat is None or vat > total:
        return None
    return total, vat


def _event_day(event):
    issued = parse_datetime(str(event.payload.get('issuedAt') or ''))
    if issued is None or timezone.is_naive(issued):
        issued = event.device_created_at
    return timezone.localdate(issued)


@db_transaction.atomic
def award_points_for_event(event):
    """Attach a synced POS invoice to its customer: totals, and points from the promo running on
    the invoice date (Asia/Manila). Runs once per accepted `invoice.issued` event."""
    payload = event.payload if isinstance(event.payload, dict) else {}
    customer = _event_customer(payload)
    amounts = _event_amounts(payload)
    if customer is None or amounts is None:
        return None
    total, vat = amounts
    day = _event_day(event)
    Customer.objects.filter(pk=customer.pk).update(
        total_spent=F('total_spent') + Decimal(total) / 100, total_orders=F('total_orders') + 1)
    Customer.objects.filter(pk=customer.pk).filter(Q(last_visit__isnull=True) | Q(last_visit__lt=day)).update(last_visit=day)
    if LoyaltyEntry.objects.filter(sync_event=event, kind='earn').exists():
        return None
    net = Decimal(total - vat) / 100
    promo, points = best_promo(day, net)
    if promo is None:
        return None
    entry = LoyaltyEntry.objects.create(
        customer=customer, sync_event=event, kind='earn', points=points, net_amount=net,
        spend_per_point=promo.spend_per_point, promo=promo, promo_name=promo.name)
    Customer.objects.filter(pk=customer.pk).update(loyalty_points=F('loyalty_points') + points)
    return entry


@db_transaction.atomic
def reverse_points_for_event(issued_event):
    """A voided POS invoice: take the customer's totals and earned points back (once)."""
    payload = issued_event.payload if isinstance(issued_event.payload, dict) else {}
    customer = _event_customer(payload)
    amounts = _event_amounts(payload)
    if customer is None or amounts is None:
        return None
    earned = LoyaltyEntry.objects.filter(sync_event=issued_event, kind='earn').first()
    locked = Customer.objects.select_for_update().get(pk=customer.pk)
    locked.total_spent = max(Decimal(0), locked.total_spent - Decimal(amounts[0]) / 100)
    locked.total_orders = max(0, locked.total_orders - 1)
    locked.save(update_fields=['total_spent', 'total_orders', 'updated_at'])
    return _reverse(earned) if earned else None
