from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from monotal.models import QAQuestion, Notification, NotificationType, NotificationTargetUser


class Command(BaseCommand):
    help = '回答受付期限が1日以内に迫っているQ&A質問の質問者に事前通知を送信する'

    def handle(self, *args, **options):
        now = timezone.now()
        expiring_questions = list(
            QAQuestion.objects.filter(
                status_id=1,
                expires_at__gt=now,
                expires_at__lte=now + timedelta(days=1),
                expiry_notified_datetime__isnull=True,
            ).select_related('user')
        )

        if not expiring_questions:
            self.stdout.write(self.style.SUCCESS('No expiring questions found.'))
            return

        try:
            notification_type = NotificationType.objects.get(notification_type_id=4)
        except NotificationType.DoesNotExist:
            self.stdout.write(self.style.WARNING('Notification type 4 not found. Skipping notifications.'))
            notification_type = None

        count = 0
        for question in expiring_questions:
            if notification_type:
                community_url = f'/monotal/community/?tab=qa&qa={question.question_id}'
                notification = Notification.objects.create(
                    notification_type=notification_type,
                    notification_title='質問の受付期限が近づいています',
                    notification_detail=f'「{question.title}」の回答受付期限があと1日以内です',
                    link_url=community_url,
                )
                NotificationTargetUser.objects.create(
                    notification=notification,
                    user=question.user,
                )

            question.expiry_notified_datetime = now
            question.save(update_fields=['expiry_notified_datetime', 'updated_at'])
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Notified {count} expiring questions.'))
