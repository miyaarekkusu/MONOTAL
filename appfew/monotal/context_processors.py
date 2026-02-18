from django.db.models import Q
from .models import RentalRequest, NotificationTargetUser, NotificationRead


def rental_context(request):
    """
    レンタル関連のコンテキストを全テンプレートに渡す
    """
    context = {
        'pending_rental_count': 0,
    }

    if request.user.is_authenticated:
        # 受け取った申請 + 送った申請のうち、完了・拒否・キャンセル以外の件数
        qs = RentalRequest.objects.filter(
            Q(requested_user=request.user) | Q(requester_user=request.user),
        ).exclude(
            rental_request_status_id__in=[3, 4, 5]  # 拒否・キャンセル・完了を除外
        )
        context['pending_rental_count'] = qs.count()
        import sys
        print(f"[rental_context] user={request.user.user_name} count={qs.count()} query={qs.query}", file=sys.stderr)

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
