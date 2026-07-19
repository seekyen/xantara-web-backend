from rest_framework import serializers
from .models import Branch, Category, Product, ProductStock, StockMovement


# ---------------------------------------------------------------------------
# Branch
# ---------------------------------------------------------------------------

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Branch
        fields = ['id', 'code', 'name', 'address', 'active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ['id', 'name', 'created_at']


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductSerializer(serializers.ModelSerializer):
    is_on_promo = serializers.ReadOnlyField()

    class Meta:
        model  = Product
        fields = [
            'id', 'itemcode', 'itemcode2', 'itemcode3', 'itemcode3type',
            'desclong', 'descshort', 'querytext',
            'deptcode', 'classcode', 'categorycode', 'subcategorycode', 'group',
            'size', 'color', 'style', 'item_type', 'form',
            'sell_price_rp', 'sell_price_ws', 'sell_price2', 'sell_price3',
            'sell_price4', 'sell_price5', 'sell_lastdate',
            'sell_uom', 'sell_pack', 'sell_packconv', 'sell_dimension', 'sell_weight',
            'sell_quantity1', 'sell_quantity2', 'sell_quantity3', 'sell_quantity4',
            'pro_allowed', 'pro_datefr', 'pro_timefr', 'pro_dateto', 'pro_timeto',
            'pro_priceret', 'pro_pricewhl', 'pro_cost',
            'suppliercode',
            'markup_rp', 'markup_ws', 'acqcost', 'unitcost', 'unitcostave',
            'taxcode', 'glcode', 'invcode', 'pricetype', 'barcodetype',
            'trackinventory', 'active', 'withserial', 'generic', 'measured',
            'withalias', 'expirydate', 'lotnumber', 'withautoconv',
            'slowfactor', 'fastfactor', 'minwhlsaleqty',
            'picturefile', 'image', 'planerid', 'buyerid', 'printto', 'info1', 'info2', 'tag',
            'stock_sa', 'stock_book_sa', 'beg_balance_sa',
            'stock_sr', 'stock_book_sr', 'beg_balance_sr',
            'stock_reserved', 'stock_rop', 'stock_limit', 'stock_onorder', 'beg_cost',
            'createdby', 'createddate', 'updatedby', 'updateddate',
            'is_on_promo',
        ]
        read_only_fields = ['createdby', 'createddate', 'updatedby', 'updateddate']


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Product
        fields = [
            'itemcode', 'itemcode2', 'itemcode3', 'itemcode3type',
            'desclong', 'descshort', 'querytext',
            'deptcode', 'classcode', 'categorycode', 'subcategorycode', 'group',
            'size', 'color', 'style', 'item_type', 'form',
            'sell_price_rp', 'sell_price_ws', 'sell_price2', 'sell_price3',
            'sell_price4', 'sell_price5', 'sell_lastdate',
            'sell_uom', 'sell_pack', 'sell_packconv', 'sell_dimension', 'sell_weight',
            'sell_quantity1', 'sell_quantity2', 'sell_quantity3', 'sell_quantity4',
            'pro_allowed', 'pro_datefr', 'pro_timefr', 'pro_dateto', 'pro_timeto',
            'pro_priceret', 'pro_pricewhl', 'pro_cost',
            'suppliercode',
            'markup_rp', 'markup_ws', 'acqcost', 'unitcost', 'unitcostave',
            'taxcode', 'glcode', 'invcode', 'pricetype', 'barcodetype',
            'trackinventory', 'active', 'withserial', 'generic', 'measured',
            'withalias', 'expirydate', 'lotnumber', 'withautoconv',
            'slowfactor', 'fastfactor', 'minwhlsaleqty',
            'picturefile', 'image', 'planerid', 'buyerid', 'printto', 'info1', 'info2', 'tag',
            'stock_sa', 'stock_book_sa', 'beg_balance_sa',
            'stock_sr', 'stock_book_sr', 'beg_balance_sr',
            'stock_reserved', 'stock_rop', 'stock_limit', 'stock_onorder', 'beg_cost',
        ]


# ---------------------------------------------------------------------------
# ProductStock
# ---------------------------------------------------------------------------

class ProductStockSerializer(serializers.ModelSerializer):
    total_stock     = serializers.ReadOnlyField()
    available_stock = serializers.ReadOnlyField()
    is_below_rop    = serializers.ReadOnlyField()

    class Meta:
        model  = ProductStock
        fields = [
            'id', 'itemcode', 'branch_code',
            'stock_sa', 'stock_book_sa', 'beg_balance_sa',
            'stock_sr', 'stock_book_sr', 'beg_balance_sr',
            'stock_reserved', 'stock_rop', 'stock_limit', 'stock_onorder', 'beg_cost',
            'total_stock', 'available_stock', 'is_below_rop',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class ProductStockWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductStock
        fields = [
            'itemcode', 'branch_code',
            'stock_sa', 'stock_book_sa', 'beg_balance_sa',
            'stock_sr', 'stock_book_sr', 'beg_balance_sr',
            'stock_reserved', 'stock_rop', 'stock_limit', 'stock_onorder', 'beg_cost',
        ]

    def validate(self, data):
        # Enforce unique itemcode + branch_code on create
        if self.instance is None:
            exists = ProductStock.objects.filter(
                itemcode=data.get('itemcode'),
                branch_code=data.get('branch_code'),
            ).exists()
            if exists:
                raise serializers.ValidationError(
                    f"Stock record for {data.get('itemcode')} @ "
                    f"{data.get('branch_code')} already exists."
                )
        return data


# ---------------------------------------------------------------------------
# StockMovement
# ---------------------------------------------------------------------------

class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model  = StockMovement
        fields = [
            'id', 'itemcode', 'branch_code',
            'movement_type', 'location',
            'qty', 'qty_before', 'qty_after',
            'ref_no', 'remarks',
            'created_by', 'created_at',
        ]
        read_only_fields = [
            'qty_before', 'qty_after', 'created_at',
        ]


# ---------------------------------------------------------------------------
# Action serializers (used by views, not tied to a model directly)
# ---------------------------------------------------------------------------

class StockAdjustSerializer(serializers.Serializer):
    adjustment = serializers.FloatField()
    location   = serializers.ChoiceField(choices=['sa', 'sr'], default='sa')
    reason     = serializers.CharField(max_length=255, required=False, allow_blank=True)


class StockDeductSerializer(serializers.Serializer):
    itemcode    = serializers.CharField(max_length=15)
    branch_code = serializers.CharField(max_length=10)
    qty         = serializers.FloatField(min_value=0.001)
    location    = serializers.ChoiceField(choices=['sa', 'sr'], default='sa')
    ref_no      = serializers.CharField(max_length=30, required=False, allow_blank=True)
    remarks     = serializers.CharField(max_length=255, required=False, allow_blank=True)
    created_by  = serializers.CharField(max_length=8,  required=False, allow_blank=True)


class StockTransferSerializer(serializers.Serializer):
    itemcode         = serializers.CharField(max_length=15)
    from_branch_code = serializers.CharField(max_length=10)
    to_branch_code   = serializers.CharField(max_length=10)
    qty              = serializers.FloatField(min_value=0.001)
    location         = serializers.ChoiceField(choices=['sa', 'sr'], default='sa')
    ref_no           = serializers.CharField(max_length=30, required=False, allow_blank=True)
    remarks          = serializers.CharField(max_length=255, required=False, allow_blank=True)
    created_by       = serializers.CharField(max_length=8,  required=False, allow_blank=True)

    def validate(self, data):
        if data['from_branch_code'] == data['to_branch_code']:
            raise serializers.ValidationError(
                "from_branch_code and to_branch_code must be different."
            )
        return data