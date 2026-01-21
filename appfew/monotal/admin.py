from django.contrib import admin
from .models import ProductCategory, ProductCondition, ProductStatus

# Register your models here.

admin.site.register(ProductCategory)
admin.site.register(ProductCondition)
admin.site.register(ProductStatus)
