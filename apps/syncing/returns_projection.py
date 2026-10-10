"""Validate append-only credit notes and project only explicitly restocked units."""
from collections import defaultdict
from .models import CloudSyncEvent


def project_credit_note(event):
    from .services import SyncProjectionError, _apply_quantities, _require_payload_branch
    _require_payload_branch(event, 'branchId')
    payload = event.payload
    original_id = payload.get('invoiceId')
    issued = CloudSyncEvent.objects.select_for_update().filter(
        business_id=event.business_id, aggregate_id=original_id,
        event_type='invoice.issued').first()
    if issued is None or issued.branch_id != event.branch_id or issued.installation_id != event.installation_id:
        raise SyncProjectionError('Original invoice is unavailable for this terminal.')
    if issued.payload.get('customerId'):
        raise SyncProjectionError('Loyalty returns require a separate settlement workflow.')
    if issued.payload.get('paymentMethod') != 'cash' or payload.get('settlement') != 'cashRefundRecorded':
        raise SyncProjectionError('Only linked cash-refund credit notes are supported.')
    if CloudSyncEvent.objects.filter(business_id=event.business_id, aggregate_id=original_id, event_type='invoice.voided').exists():
        raise SyncProjectionError('A voided invoice cannot be returned.')
    if payload.get('id') != event.aggregate_id or event.aggregate_type != 'credit_note':
        raise SyncProjectionError('Credit note identity mismatch.')
    prior = CloudSyncEvent.objects.filter(business_id=event.business_id,
        event_type='credit_note.issued', payload__invoiceId=original_id).exclude(pk=event.pk)
    used = defaultdict(int)
    for earlier in prior:
        if earlier.aggregate_id == event.aggregate_id or earlier.payload.get('number') == payload.get('number'):
            raise SyncProjectionError('Credit note was already recorded with another event key.')
        for line in earlier.payload.get('lines', []):
            used[line['productId']] += line['quantity']
    originals = {line['productId']: line for line in issued.payload.get('lines', [])}
    lines = payload.get('lines')
    if not isinstance(lines, list) or not lines:
        raise SyncProjectionError('Credit note lines are required.')
    restock = {}
    seen = set()
    totals = dict.fromkeys(['total', 'discount', 'vatRelief', 'vatable', 'vat', 'exempt', 'zero', 'nonVat'], 0)
    for line in lines:
        if not isinstance(line, dict):
            raise SyncProjectionError('Invalid credit note line.')
        product = line.get('productId')
        source = originals.get(product)
        quantity = line.get('quantity')
        if (source is None or product in seen or type(quantity) is not int or quantity <= 0
                or type(line.get('restock')) is not bool):
            raise SyncProjectionError('Invalid or duplicate return product/quantity.')
        seen.add(product)
        original_quantity = source.get('quantity')
        if (type(original_quantity) is not int or original_quantity <= 0
                or source.get('taxCategory') not in ('vat12', 'vatExempt', 'zeroRated', 'nonVat')
                or any(type(source.get(key, 0)) is not int or source.get(key, 0) < 0
                       for key in ('lineTotalCentavos', 'discountCentavos', 'vatReliefCentavos'))
                or 'lineTotalCentavos' not in source):
            raise SyncProjectionError('Original invoice lacks valid return allocation evidence.')
        already = used[product]
        if already + quantity > original_quantity:
            raise SyncProjectionError('Returned quantity exceeds the original invoice.')
        net = source['lineTotalCentavos']
        tax = source['taxCategory']
        def allocated(amount, count):
            return (amount * count + original_quantity // 2) // original_quantity
        def delta(amount):
            return allocated(amount, already + quantity) - allocated(amount, already)
        vat_base = (net * 10000 + 5600) // 11200 if tax == 'vat12' else 0
        def base_at(count):
            return (vat_base * allocated(net, count) + net // 2) // net if net else 0
        amount = delta(net)
        base = base_at(already + quantity) - base_at(already)
        expected = {'total': amount, 'discount': delta(source.get('discountCentavos', 0)),
            'vatRelief': delta(source.get('vatReliefCentavos', 0)), 'vatable': base,
            'vat': amount - base if tax == 'vat12' else 0,
            'exempt': amount if tax == 'vatExempt' else 0,
            'zero': amount if tax == 'zeroRated' else 0, 'nonVat': amount if tax == 'nonVat' else 0}
        if (line.get('amounts') != expected or line.get('taxCategory') != tax
                or any(type(v) is not int for v in line['amounts'].values())):
            raise SyncProjectionError('Credit note amounts must match the original invoice allocation.')
        for key, value in expected.items():
            totals[key] += value
        if line['restock']:
            restock[product] = quantity
    if payload.get('totals') != totals or totals['total'] <= 0:
        raise SyncProjectionError('Credit note totals do not reconcile.')
    _apply_quantities(event.branch.code, restock)
