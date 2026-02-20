from django.core.management.base import BaseCommand
from django.utils import timezone
from monotal.models import QAQuestion, Notification, NotificationType, NotificationTargetUser


class Command(BaseCommand):
    help = '受付期限を過ぎたQ&A質問を「期限切れ終了」に自動更新し、質問者に通知する'

    def handle(self, *args, **options):
        expired_questions = list(
            QAQuestion.objects.filter(
                status_id=1,
                expires_at__lt=timezone.now(),
            ).select_related('user')
        )

        if not expired_questions:
            self.stdout.write(self.style.SUCCESS('No expired questions found.'))
            return

        try:
            notification_type = NotificationType.objects.get(notification_type_id=4)
        except NotificationType.DoesNotExist:
            self.stdout.write(self.style.WARNING('Notification type 4 not found. Skipping notifications.'))
            notification_type = None

        count = 0
        for question in expired_questions:
            question.status_id = 3
            question.save(update_fields=['status_id', 'updated_at'])
            count += 1

            if notification_type:
                community_url = f'/monotal/community/?tab=qa&qa={question.question_id}'
                notification = Notification.objects.create(
                    notification_type=notification_type,
                    notification_title='質問の受付が終了しました',
                    notification_detail=f'「{question.title}」の回答受付期限が切れました',
                    link_url=community_url,
                )
                NotificationTargetUser.objects.create(
                    notification=notification,
                    user=question.user,
                )

        self.stdout.write(self.style.SUCCESS(f'Updated {count} expired questions.'))
