from rest_framework import serializers
from .models import Product, Category

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ['id','name','product_count','created_at']

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

class ProductSerializer(serializers.ModelSerializer):
    category_name  = serializers.CharField(source='category.name', read_only=True)
    total_value    = serializers.ReadOnlyField()
    profit_margin  = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    stock_percent  = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id','name','sku','category','category_name','price','cost',
            'stock','max_stock','status','status_display','sold',
            'total_value','profit_margin','stock_percent','is_active',
            'created_at','updated_at',
        ]
        read_only_fields = ['status','sold','created_at','updated_at']

    def get_stock_percent(self, obj):
        if obj.max_stock == 0:
            return 0
        return round((obj.stock / obj.max_stock) * 100)

class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Product
        fields = ['name','sku','category','price','cost','stock','max_stock','is_active']

class StockAdjustSerializer(serializers.Serializer):
    adjustment = serializers.IntegerField()
    reason     = serializers.CharField(max_length=255, required=False)
