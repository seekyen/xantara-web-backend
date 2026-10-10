from .tests import SyncEventUploadTests
from rest_framework.test import APITestCase
from apps.inventory.models import ProductStock
from .models import CloudSyncEvent


class CreditNoteUploadTests(APITestCase):
    payload = SyncEventUploadTests.payload
    post_event = SyncEventUploadTests.post_event
    def setUp(self):
        SyncEventUploadTests.setUp(self)
        payload = self.payload(localEventId='original', aggregateType='invoice', aggregateId='invoice-1',
            eventType='invoice.issued', idempotencyKey='invoice.issued:invoice-1', payload={
                'invoiceId':'invoice-1','branchId':'branch-main','paymentMethod':'cash','totalCentavos':22400,
                'lines':[{'productId':'product-1','quantity':2,'unitPriceCentavos':11200,
                    'discountCentavos':0,'taxCategory':'vat12','lineTotalCentavos':22400}]})
        self.assertEqual(self.post_event(payload,HTTP_IDEMPOTENCY_KEY='invoice.issued:invoice-1').status_code,202)

    def credit(self, key='cn1', restock=True):
        amounts={'total':11200,'discount':0,'vatRelief':0,'vatable':10000,'vat':1200,'exempt':0,'zero':0,'nonVat':0}
        return self.payload(localEventId=key,aggregateType='credit_note',aggregateId=key,eventType='credit_note.issued',
            idempotencyKey=f'credit_note.issued:{key}',payload={'id':key,'number':key,'invoiceId':'invoice-1','branchId':'branch-main',
                'settlement':'cashRefundRecorded','totals':amounts,'lines':[{'productId':'product-1','quantity':1,
                    'restock':restock,'taxCategory':'vat12','amounts':amounts}]})

    def send(self,payload):
        return self.post_event(payload,HTTP_IDEMPOTENCY_KEY=payload['idempotencyKey'])

    def test_credit_restock_retry_and_excess_rejection(self):
        self.assertEqual(self.send(self.credit()).status_code,202)
        self.assertEqual(self.send(self.credit()).status_code,200)
        self.assertEqual(ProductStock.objects.get(itemcode='product-1',branch_code='MAIN').stock_sa,9)
        self.assertEqual(self.send(self.credit('cn2',False)).status_code,202)
        self.assertEqual(ProductStock.objects.get(itemcode='product-1',branch_code='MAIN').stock_sa,9)
        self.assertEqual(self.send(self.credit('cn3')).status_code,400)
        self.assertEqual(CloudSyncEvent.objects.filter(event_type='credit_note.issued').count(),2)

    def test_credit_rejects_forged_money_duplicate_identity_and_void(self):
        invalid=self.credit();invalid['payload']['lines'][0]['amounts']['vat']=0
        self.assertEqual(self.send(invalid).status_code,400)
        self.assertEqual(self.send(self.credit()).status_code,202)
        duplicate=self.credit();duplicate['idempotencyKey']='another-key';duplicate['localEventId']='another-event'
        self.assertEqual(self.send(duplicate).status_code,400)
        void=self.payload(localEventId='void',aggregateType='invoice',aggregateId='invoice-1',eventType='invoice.voided',
            idempotencyKey='invoice.voided:invoice-1',payload={'invoiceId':'invoice-1','branchId':'branch-main'})
        self.assertEqual(self.send(void).status_code,400)

    def test_historical_invoice_missing_allocation_evidence_is_rejected(self):
        original = CloudSyncEvent.objects.get(event_type='invoice.issued')
        payload = original.payload
        del payload['lines'][0]['lineTotalCentavos']
        original.payload = payload
        original.save(update_fields=['payload'])
        self.assertEqual(self.send(self.credit()).status_code, 400)
        self.assertFalse(CloudSyncEvent.objects.filter(event_type='credit_note.issued').exists())
