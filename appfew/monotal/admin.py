from django.contrib import admin
from .models import ProductCategory, ProductCondition, ShippingMethod, ProductStatus

# Register your models here.

admin.site.register(ProductCategory)
admin.site.register(ProductCondition)
admin.site.register(ShippingMethod)
admin.site.register(ProductStatus)
