from django.core.management.base import BaseCommand
from django.utils import timezone
from monotal.models import (
    RentalHistory, Notification, NotificationType, NotificationTargetUser
)


RENTAL_STATUS_RENTING = 3
NOTIFICATION_TYPE_RENTAL = 3


class Command(BaseCommand):
    help = '返送期限超過のレンタルを検出し、通知を送信する'

    def handle(self, *args, **options):
        now = timezone.now()

        # status=3(レンタル中), return_shipping_deadline超過, 未通知のレコード
        overdue_rentals = RentalHistory.objects.filter(
            rental_status_id=RENTAL_STATUS_RENTING,
            return_shipping_deadline__lt=now,
            overdue_notified_datetime__isnull=True
        ).select_related('product', 'lender_user', 'renter_user')

        count = 0
        for rental in overdue_rentals:
            try:
                notification_type = NotificationType.objects.get(
                    notification_type_id=NOTIFICATION_TYPE_RENTAL
                )

                # 借り手に通知
                renter_notification = Notification.objects.create(
                    notification_type=notification_type,
                    notification_title='返送期限を過ぎています',
                    notification_detail=f'「{rental.product.product_name}」の返送期限を過ぎています。早急に商品を返送してください。',
                    link_url=f'/monotal/transaction/{rental.rental_history_id}/'
                )
                NotificationTargetUser.objects.create(
                    notification=renter_notification,
                    user=rental.renter_user
                )

                # 貸主に通知
                lender_notification = Notification.objects.create(
                    notification_type=notification_type,
                    notification_title='返送期限が超過しています',
                    notification_detail=f'「{rental.product.product_name}」の返送期限が超過しています。借り手に連絡してください。',
                    link_url=f'/monotal/transaction/{rental.rental_history_id}/'
                )
                NotificationTargetUser.objects.create(
                    notification=lender_notification,
                    user=rental.lender_user
                )

                # 通知済みフラグを更新
                rental.overdue_notified_datetime = now
                rental.save(update_fields=['overdue_notified_datetime'])

                count += 1

            except Exception as e:
                self.stderr.write(f'通知送信エラー (rental_history_id={rental.rental_history_id}): {e}')

        self.stdout.write(self.style.SUCCESS(f'{count}件の超過通知を送信しました'))
