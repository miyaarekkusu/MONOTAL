"""
取引中止関連ビュー
Cancellation Related Views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.core.paginator import Paginator
from .models import (
    CancellationReason, CancellationStatus, CancellationRequest,
    RentalHistory, RentalStatus, ProductStatus,
)


# ステータス定数
CANCELLATION_STATUS_PENDING = 1    # 申請中
CANCELLATION_STATUS_APPROVED = 2   # 承認
CANCELLATION_STATUS_REJECTED = 3   # 却下

RENTAL_STATUS_CANCELLATION_REQUESTED = 10
RENTAL_STATUS_CANCELLATION_APPROVED = 11

# 中止申請可能なレンタルステータス
CANCELLABLE_STATUSES = [1]  # 発送準備中のみ中止申請可能


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ユーザー側ビュー / User Side Views                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required(login_url='/monotal/login/')
def cancellation_request_submit(request, rental_history_id):
    """
    取引中止申請API (POST Ajax)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)

    try:
        rental_history = RentalHistory.objects.select_related(
            'lender_user', 'renter_user'
        ).get(rental_history_id=rental_history_id)
    except RentalHistory.DoesNotExist:
        return JsonResponse({'success': False, 'message': '取引が見つかりません'}, status=404)

    # アクセス権チェック（貸主または借り手のみ）
    is_lender = request.user == rental_history.lender_user
    is_renter = request.user == rental_history.renter_user
    if not is_lender and not is_renter:
        return JsonResponse({'success': False, 'message': 'アクセス権限がありません'}, status=403)

    # ステータスチェック
    if rental_history.rental_status_id not in CANCELLABLE_STATUSES:
        return JsonResponse({'success': False, 'message': '現在のステータスでは中止申請できません'})

    # 既に中止申請中かチェック
    existing = CancellationRequest.objects.filter(
        rental_history=rental_history,
        cancellation_status_id=CANCELLATION_STATUS_PENDING
    ).exists()
    if existing:
        return JsonResponse({'success': False, 'message': '既に中止申請中です'})

    # バリデーション
    reason_id = request.POST.get('cancellation_reason_id')
    detail = request.POST.get('detail', '').strip()

    if not reason_id:
        return JsonResponse({'success': False, 'message': '中止理由を選択してください'})

    try:
        reason = CancellationReason.objects.get(cancellation_reason_id=reason_id)
    except CancellationReason.DoesNotExist:
        return JsonResponse({'success': False, 'message': '無効な中止理由です'})

    # 中止申請作成
    previous_status = rental_history.rental_status_id
    CancellationRequest.objects.create(
        rental_history=rental_history,
        requester_user=request.user,
        cancellation_reason=reason,
        cancellation_status_id=CANCELLATION_STATUS_PENDING,
        detail=detail,
        previous_rental_status_id=previous_status,
    )

    # レンタルステータスを「中止申請中」に変更
    rental_history.rental_status_id = RENTAL_STATUS_CANCELLATION_REQUESTED
    rental_history.save()

    # 取引相手に通知
    partner = rental_history.renter_user if is_lender else rental_history.lender_user
    _send_cancellation_requested_notification(rental_history, partner)

    return JsonResponse({'success': True, 'message': '取引中止を申請しました。運営の審査をお待ちください。'})


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  通知ヘルパー / Notification Helpers                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def _send_cancellation_requested_notification(rental_history, partner_user):
    """中止申請時: 取引相手に通知"""
    try:
        from .views import create_notification
        product_name = rental_history.product.product_name
        link_url = reverse('transaction', kwargs={'rental_history_id': rental_history.rental_history_id})

        create_notification(
            notification_type_id=1,
            title='取引中止が申請されました',
            detail=f'「{product_name}」の取引について中止申請がありました。運営の審査をお待ちください。',
            link_url=link_url,
            target_users=[partner_user]
        )
    except Exception:
        pass


def _send_cancellation_approved_notification(rental_history, requester, lender, renter):
    """中止承認時: 双方に通知"""
    try:
        from .views import create_notification
        product_name = rental_history.product.product_name
        link_url = reverse('transaction', kwargs={'rental_history_id': rental_history.rental_history_id})

        create_notification(
            notification_type_id=1,
            title='取引が中止されました',
            detail=f'「{product_name}」の取引が運営により中止されました。',
            link_url=link_url,
            target_users=[lender, renter]
        )
    except Exception:
        pass


def _send_cancellation_rejected_notification(rental_history, requester):
    """中止却下時: 申請者に通知"""
    try:
        from .views import create_notification
        product_name = rental_history.product.product_name
        link_url = reverse('transaction', kwargs={'rental_history_id': rental_history.rental_history_id})

        create_notification(
            notification_type_id=1,
            title='中止申請が却下されました',
            detail=f'「{product_name}」の取引中止申請が却下されました。取引を続行してください。',
            link_url=link_url,
            target_users=[requester]
        )
    except Exception:
        pass
