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

# 中止申請可能なレンタルステータス (1〜4, 7〜9)
CANCELLABLE_STATUSES = [1, 2, 3, 4, 7, 8, 9]


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
# ║  管理者側ビュー / Admin Side Views                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required(login_url='/monotal/login/')
def admin_cancellation_list(request):
    """
    中止申請一覧（管理者）
    """
    if not request.user.is_staff:
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    all_requests = CancellationRequest.objects.all().select_related(
        'rental_history', 'rental_history__product',
        'rental_history__lender_user', 'rental_history__renter_user',
        'requester_user', 'cancellation_reason', 'cancellation_status'
    ).order_by('-request_datetime')

    # カウント集計
    total_count = all_requests.count()
    pending_count = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_PENDING).count()
    approved_count = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_APPROVED).count()
    rejected_count = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_REJECTED).count()

    # フィルター適用
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'pending':
        requests_qs = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_PENDING)
    elif status_filter == 'approved':
        requests_qs = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_APPROVED)
    elif status_filter == 'rejected':
        requests_qs = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_REJECTED)
    else:
        requests_qs = all_requests
        status_filter = 'all'

    # ページネーション
    paginator = Paginator(requests_qs, 20)
    page = paginator.get_page(request.GET.get('page', 1))

    context = {
        'requests': page,
        'current_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'admin/cancellation_list.html', context)


@login_required(login_url='/monotal/login/')
def admin_cancellation_detail(request, cancellation_request_id):
    """
    中止申請詳細（管理者）
    GETで詳細表示、POSTでAjax承認/却下処理
    """
    if not request.user.is_staff:
        if request.method == 'POST':
            return JsonResponse({'success': False, 'message': '管理者権限が必要です'}, status=403)
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    cancellation_request = get_object_or_404(
        CancellationRequest.objects.select_related(
            'rental_history', 'rental_history__product',
            'rental_history__lender_user', 'rental_history__renter_user',
            'requester_user', 'cancellation_reason', 'cancellation_status'
        ),
        cancellation_request_id=cancellation_request_id
    )

    # POST: Ajax承認/却下処理
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        action = request.POST.get('action')

        if cancellation_request.cancellation_status_id != CANCELLATION_STATUS_PENDING:
            return JsonResponse({'success': False, 'message': 'この中止申請は既に審査済みです'})

        rental_history = cancellation_request.rental_history

        if action == 'approve':
            # 承認: 中止ステータス→承認、レンタルステータス→中止済み、商品→貸出可能
            cancellation_request.cancellation_status_id = CANCELLATION_STATUS_APPROVED
            cancellation_request.approval_datetime = timezone.now()
            admin_note = request.POST.get('admin_note', '').strip()
            if admin_note:
                cancellation_request.admin_note = admin_note
            cancellation_request.save()

            rental_history.rental_status_id = RENTAL_STATUS_CANCELLATION_APPROVED
            rental_history.save()

            # 商品ステータスを貸出可能(1)に戻す
            product = rental_history.product
            product.product_status_id = 1  # 貸出可能
            product.save()

            # 双方に通知
            _send_cancellation_approved_notification(
                rental_history,
                cancellation_request.requester_user,
                rental_history.lender_user,
                rental_history.renter_user
            )
            return JsonResponse({'success': True, 'message': '中止申請を承認しました'})

        elif action == 'reject':
            # 却下: 中止ステータス→却下、レンタルステータス→元に復元
            cancellation_request.cancellation_status_id = CANCELLATION_STATUS_REJECTED
            cancellation_request.rejection_datetime = timezone.now()
            admin_note = request.POST.get('admin_note', '').strip()
            if admin_note:
                cancellation_request.admin_note = admin_note
            cancellation_request.save()

            rental_history.rental_status_id = cancellation_request.previous_rental_status_id
            rental_history.save()

            # 申請者に通知
            _send_cancellation_rejected_notification(
                rental_history,
                cancellation_request.requester_user
            )
            return JsonResponse({'success': True, 'message': '中止申請を却下しました'})

        else:
            return JsonResponse({'success': False, 'message': '不正なアクションです'})

    # GET: 詳細表示
    context = {
        'cr': cancellation_request,
        'rental_history': cancellation_request.rental_history,
    }
    return render(request, 'admin/cancellation_detail.html', context)


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
