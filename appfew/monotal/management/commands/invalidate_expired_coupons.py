from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from monotal.models import UserCoupon


class Command(BaseCommand):
    help = '期限切れまたは廃止されたクーポンを所持するユーザーの所持フラグを一括更新する'

    def handle(self, *args, **options):
        now = timezone.now()

        updated = UserCoupon.objects.filter(
            is_possessed=True,
        ).filter(
            Q(coupon__expires_at__lte=now) | Q(coupon__is_active=False)
        ).update(is_possessed=False)

        self.stdout.write(self.style.SUCCESS(f'Invalidated {updated} user coupons.'))
