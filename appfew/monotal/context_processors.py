from .models import RentalRequest, NotificationTargetUser, NotificationRead


def rental_context(request):
    """
    レンタル関連のコンテキストを全テンプレートに渡す
    """
    context = {
        'pending_rental_count': 0,
    }

    if request.user.is_authenticated:
        # 出品者として受け取った申請中の件数
        context['pending_rental_count'] = RentalRequest.objects.filter(
            requested_user=request.user,
            rental_request_status_id=1  # 申請中
        ).count()

    return context


def notification_context(request):
    """
    通知関連のコンテキストを全テンプレートに渡す
    """
    context = {
        'unread_notification_count': 0,
    }

    if request.user.is_authenticated:
        # 自分宛ての通知のうち、未読のものをカウント
        # NotificationTargetUserに自分が含まれていて、NotificationReadが存在しないか未読のもの
        target_notification_ids = NotificationTargetUser.objects.filter(
            user=request.user
        ).values_list('notification_id', flat=True)

        # 既読の通知ID
        read_notification_ids = NotificationRead.objects.filter(
            user=request.user,
            notification_read_status_id=2  # 既読
        ).values_list('notification_id', flat=True)

        # 未読数 = 自分宛て通知 - 既読通知
        context['unread_notification_count'] = target_notification_ids.exclude(
            notification_id__in=read_notification_ids
        ).count()

    return context
