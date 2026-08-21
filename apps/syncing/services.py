from collections import defaultdict

from apps.inventory.models import ProductStock

from .models import CloudSyncEvent, SyncInstallation


class SyncProjectionError(ValueError):
    pass


def project_inventory_event(event):
    handlers = {
        'invoice.issued': _project_invoice_issued,
        'invoice.voided': _project_invoice_voided,
        'inventory.transfer_dispatched': _project_transfer_dispatched,
        'inventory.transfer_received': _project_transfer_received,
        'inventory.transfer_cancelled': _project_transfer_cancelled,
    }
    handler = handlers.get(event.event_type)
    if handler is None:
        return False
    handler(event)
    return True


def _project_invoice_issued(event):
    _require_payload_branch(event, 'branchId')
    quantities = _invoice_quantities(event.payload)
    _apply_quantities(event.branch.code, quantities, subtract=True)


def _project_invoice_voided(event):
    _require_payload_branch(event, 'branchId')
    issued = (
        CloudSyncEvent.objects.filter(
            business_id=event.business_id,
            aggregate_id=event.aggregate_id,
            event_type='invoice.issued',
        )
        .exclude(pk=event.pk)
        .order_by('accepted_at', 'pk')
        .first()
    )
    if issued is None or issued.branch_id != event.branch_id:
        raise SyncProjectionError('The original invoice is not available for this branch.')
    if (
        CloudSyncEvent.objects.filter(
            business_id=event.business_id,
            aggregate_id=event.aggregate_id,
            event_type='invoice.voided',
        )
        .exclude(pk=event.pk)
        .exists()
    ):
        raise SyncProjectionError('The invoice was already voided.')
    _apply_quantities(event.branch.code, _invoice_quantities(issued.payload))


def _project_transfer_dispatched(event):
    payload = event.payload
    _require_payload_branch(event, 'sourceBranchId')
    _mapped_branch(event.business_id, payload.get('destinationBranchId'))
    _apply_quantities(
        event.branch.code,
        {_required_text(payload, 'productId'): _positive_int(payload, 'quantity')},
        subtract=True,
    )


def _project_transfer_received(event):
    payload = event.payload
    _require_payload_branch(event, 'destinationBranchId')
    _mapped_branch(event.business_id, payload.get('sourceBranchId'))
    _apply_quantities(
        event.branch.code,
        {_required_text(payload, 'productId'): _positive_int(payload, 'quantity')},
    )


def _project_transfer_cancelled(event):
    payload = event.payload
    _require_payload_branch(event, 'sourceBranchId')
    _mapped_branch(event.business_id, payload.get('destinationBranchId'))
    _apply_quantities(
        event.branch.code,
        {_required_text(payload, 'productId'): _positive_int(payload, 'quantity')},
    )


def _invoice_quantities(payload):
    lines = payload.get('lines') if isinstance(payload, dict) else None
    if not isinstance(lines, list) or not lines:
        raise SyncProjectionError('Invoice lines are required for inventory projection.')
    quantities = defaultdict(int)
    for line in lines:
        if not isinstance(line, dict):
            raise SyncProjectionError('Every invoice line must be an object.')
        quantities[_required_text(line, 'productId')] += _positive_int(line, 'quantity')
    return dict(quantities)


def _apply_quantities(branch_code, quantities, subtract=False):
    for itemcode in sorted(quantities):
        try:
            stock = ProductStock.objects.select_for_update().get(
                branch_code=branch_code,
                itemcode=itemcode,
            )
        except ProductStock.DoesNotExist as error:
            raise SyncProjectionError(
                f'Product {itemcode} is not mapped to branch {branch_code}.',
            ) from error
        delta = quantities[itemcode]
        next_stock = stock.stock_sa - delta if subtract else stock.stock_sa + delta
        if next_stock < 0:
            raise SyncProjectionError(
                f'Insufficient stock for product {itemcode} at branch {branch_code}.',
            )
        stock.stock_sa = next_stock
        stock.stock_book_sa = next_stock
        stock.save(update_fields=['stock_sa', 'stock_book_sa', 'updated_at'])


def _require_payload_branch(event, field):
    local_branch_id = _required_text(event.payload, field)
    if local_branch_id != event.local_branch_id:
        raise SyncProjectionError(f'{field} does not match the authorized branch.')
    return event.branch


def _mapped_branch(business_id, local_branch_id):
    if not isinstance(local_branch_id, str) or not local_branch_id.strip():
        raise SyncProjectionError('A mapped branch identifier is required.')
    installation = (
        SyncInstallation.objects.select_related('branch')
        .filter(
            business_id=business_id,
            local_branch_id=local_branch_id.strip(),
            is_active=True,
            sync_enabled=True,
            branch__active=True,
        )
        .first()
    )
    if installation is None:
        raise SyncProjectionError('The related transfer branch is not mapped.')
    return installation.branch


def _required_text(payload, field):
    value = payload.get(field) if isinstance(payload, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise SyncProjectionError(f'{field} is required.')
    return value.strip()


def _positive_int(payload, field):
    value = payload.get(field) if isinstance(payload, dict) else None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SyncProjectionError(f'{field} must be a positive integer.')
    return value
