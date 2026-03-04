from django.db.models import Q, Count
from .models import RentalRequest, RentalHistory, NotificationTargetUser, NotificationRead


def rental_context(request):
    """
    レンタル関連のコンテキストを全テンプレートに渡す
    （受け取った申請 + 送った申請 + 取引中の合計件数）
    """
    context = {
        'pending_rental_count': 0,
    }

    if request.user.is_authenticated:
        # 受け取った申請 + 送った申請のうち、完了・拒否・キャンセル以外の件数
        request_count = RentalRequest.objects.filter(
            Q(requested_user=request.user) | Q(requester_user=request.user),
        ).exclude(
            rental_request_status_id__in=[3, 4, 5]  # 拒否・キャンセル・完了を除外
        ).count()

        # 取引中（RentalHistory）の件数（返却済みはレビュー2件未満のみカウント）
        transaction_count = RentalHistory.objects.annotate(
            review_count=Count('reviews')
        ).filter(
            Q(lender_user=request.user) | Q(renter_user=request.user),
        ).filter(
            Q(rental_status_id__in=[1, 2, 3, 4, 7, 8, 9, 10]) |
            Q(rental_status_id=5, review_count__lt=2)
        ).count()

        context['pending_rental_count'] = request_count + transaction_count

    return context


def notification_context(request):
    """
    通知関連のコンテキストを全テンプレートに渡す
    """
    context = {
        'unread_notification_count': 0,
    }

    if request.user.is_authenticated:
        # 既読の通知ID
        read_notification_ids = NotificationRead.objects.filter(
            user=request.user,
            notification_read_status_id=2  # 既読
        ).values_list('notification_id', flat=True)

        # 自分宛ての全通知（未読数）
        target_notification_ids = NotificationTargetUser.objects.filter(
            user=request.user
        ).values_list('notification_id', flat=True)

        context['unread_notification_count'] = target_notification_ids.exclude(
            notification_id__in=read_notification_ids
        ).count()

    return context
