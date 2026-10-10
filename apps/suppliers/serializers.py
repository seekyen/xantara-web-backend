from decimal import Decimal
from rest_framework import serializers
from apps.inventory.models import Product
from .models import (
    Supplier, SupplierAddress, SupplierContact,
    SupplierBankDetail, SupplierProductCategory,
    PurchaseOrder, PurchaseOrderLine,
)

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Supplier
        fields = [
            'id', 'supplier_code', 'company_name', 'trade_name', 'legal_name',
            'tin', 'business_permit_no', 'is_vat_registered', 'payment_terms',
            'preferred_payment_method', 'currency', 'lead_time_days',
            'minimum_order_quantity', 'supplier_type', 'is_active', 'is_accredited',
            'rating', 'created_at', 'created_by', 'updated_at', 'updated_by',
        ]
        read_only_fields = ['created_at', 'created_by', 'updated_at', 'updated_by']


class SupplierAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SupplierAddress
        fields = [
            'id', 'supplier_id', 'address_type', 'unit_bldg_no', 'street',
            'subdivision', 'barangay', 'city', 'province', 'region',
            'postal_code', 'country', 'is_default',
        ]


class SupplierContactSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SupplierContact
        fields = ['id', 'supplier_id', 'contact_name', 'position', 'phone', 'email', 'is_primary']


class SupplierBankDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SupplierBankDetail
        fields = ['id', 'supplier_id', 'bank_name', 'account_name', 'account_number', 'is_default']


class SupplierProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = SupplierProductCategory
        fields = ['id', 'supplier_id', 'category_name']


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    total     = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()

    class Meta:
        model  = PurchaseOrderLine
        fields = [
            'id', 'product', 'product_name', 'quantity', 'unit_cost', 'expiry_date',
            'received_quantity', 'remaining', 'total',
        ]
        read_only_fields = ['product_name', 'received_quantity']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines          = PurchaseOrderLineSerializer(many=True, read_only=True)
    total_amount   = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier_id', 'status', 'status_display', 'notes',
            'lines', 'total_amount', 'created_at', 'created_by',
            'updated_at', 'updated_by', 'received_at',
        ]
        read_only_fields = [
            'po_number', 'status', 'created_at', 'created_by',
            'updated_at', 'updated_by', 'received_at',
        ]


class PurchaseOrderLineWriteSerializer(serializers.Serializer):
    product     = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(active=True))
    quantity    = serializers.IntegerField(min_value=1)
    unit_cost   = serializers.DecimalField(max_digits=11, decimal_places=2, min_value=Decimal('0'))
    expiry_date = serializers.DateField(required=False, allow_null=True)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(min_value=1)
    notes       = serializers.CharField(required=False, allow_blank=True)
    lines       = PurchaseOrderLineWriteSerializer(many=True)

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError('At least one line item is required.')
        return lines

    def validate_supplier_id(self, value):
        if not Supplier.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Supplier not found.')
        return value

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        request    = self.context['request']
        po = PurchaseOrder.objects.create(
            supplier_id=validated_data['supplier_id'],
            notes=validated_data.get('notes', ''),
            created_by=request.user,
            updated_by=request.user,
        )
        for line in lines_data:
            PurchaseOrderLine.objects.create(purchase_order=po, **line)
        return po


class PurchaseOrderReceiveLineSerializer(serializers.Serializer):
    id                = serializers.IntegerField(min_value=1)
    quantity_received = serializers.IntegerField(min_value=0)
    # The real expiry only becomes known once the goods physically arrive — this
    # overrides whatever guess (if any) was entered back when the PO was created.
    expiry_date       = serializers.DateField(required=False, allow_null=True)


class PurchaseOrderReceiveSerializer(serializers.Serializer):
    received_date = serializers.DateField(required=False)
    # Lines actually delivered this trip — a short shipment simply omits the missing
    # lines (or sends 0), it doesn't have to match every line on the PO.
    lines = PurchaseOrderReceiveLineSerializer(many=True)

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError('At least one line item is required.')
        return lines
