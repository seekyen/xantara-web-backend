from rest_framework import serializers
from django.db import transaction as db_transaction
from .models import Transaction, TransactionItem
from apps.inventory.models import Product

class TransactionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model        = TransactionItem
        fields       = ['id','product','name','sku','qty','price','line_total']
        read_only_fields = ['line_total','name','sku']

class TransactionSerializer(serializers.ModelSerializer):
    items          = TransactionItemSerializer(many=True, read_only=True)
    cashier_name   = serializers.CharField(source='cashier.name',           read_only=True)
    customer_name  = serializers.CharField(source='customer.name',          read_only=True)
    branch_name    = serializers.CharField(source='branch.name',            read_only=True)
    status_display = serializers.CharField(source='get_status_display',     read_only=True)
    pay_display    = serializers.CharField(source='get_pay_method_display', read_only=True)

    class Meta:
        model  = Transaction
        fields = [
            'id','txn_no','customer','customer_name','cashier','cashier_name',
            'branch','branch_name','items','subtotal','discount','tax','total',
            'pay_method','pay_display','status','status_display','notes','created_at',
        ]
        read_only_fields = ['txn_no','subtotal','tax','total','created_at']

class TransactionItemWriteSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(active=True), source='product'
    )
    qty = serializers.IntegerField(min_value=1)

class TransactionCreateSerializer(serializers.Serializer):
    from apps.customers.models import Customer as C
    customer   = serializers.PrimaryKeyRelatedField(queryset=C.objects.all(),
                                                    required=False, allow_null=True)
    items      = TransactionItemWriteSerializer(many=True)
    discount   = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    pay_method = serializers.ChoiceField(choices=['cash','card','gcash','maya'])
    notes      = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError('At least one item required')
        return items

    @db_transaction.atomic
    def create(self, validated_data):
        from django.utils import timezone
        items_data = validated_data.pop('items')
        request    = self.context['request']
        TAX_RATE   = 0.12

        for item_data in items_data:
            product = item_data['product']
            if product.stock_sa < item_data['qty']:
                raise serializers.ValidationError(
                    f'Insufficient stock for {product.descshort}'
                )

        txn = Transaction.objects.create(
            cashier    = request.user,
            branch     = request.user.branch,
            discount   = validated_data.get('discount', 0),
            pay_method = validated_data['pay_method'],
            customer   = validated_data.get('customer'),
            notes      = validated_data.get('notes', ''),
        )

        subtotal = 0
        for item_data in items_data:
            product = item_data['product']
            qty     = item_data['qty']
            TransactionItem.objects.create(
                transaction=txn, product=product,
                name=product.descshort, sku=product.itemcode,
                qty=qty, price=product.sell_price_rp,
            )
            subtotal         += product.sell_price_rp * qty
            product.stock_sa -= qty
            product.save()

        taxable      = subtotal - txn.discount
        txn.subtotal = subtotal
        txn.tax      = round(taxable * TAX_RATE, 2)
        txn.total    = taxable + txn.tax
        txn.status   = 'completed'
        txn.save()

        if txn.customer:
            c = txn.customer
            c.total_spent    += txn.total
            c.total_orders   += 1
            c.loyalty_points += int(txn.total // 100)
            c.last_visit      = timezone.now().date()
            c.save()

        request.user.sales_count += 1
        request.user.save(update_fields=['sales_count'])

        return txn
