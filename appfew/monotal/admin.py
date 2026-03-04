from django.contrib import admin
from .models import ProductCategory, ProductStatus
from .models import Coupon, CouponTargetCategory, UserCoupon
from .models import Quest, QuestMission, UserCompletedQuest

# Register your models here.

admin.site.register(ProductCategory)
admin.site.register(ProductStatus)
admin.site.register(Coupon)
admin.site.register(CouponTargetCategory)
admin.site.register(UserCoupon)
admin.site.register(Quest)
admin.site.register(QuestMission)
admin.site.register(UserCompletedQuest)
