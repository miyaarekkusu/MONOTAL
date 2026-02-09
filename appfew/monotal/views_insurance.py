"""
保険関連ビュー
Insurance Related Views
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from .models import Insurance, InsuranceEnrollment, InsuranceClaim, InsuranceClaimImage, InsuranceClaimStatus, RentalHistory
from .views import create_notification


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ユーザー側ビュー / User Side Views                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required
def insurance_page(request):
    """
    保険加入ページ表示
    Insurance enrollment page
    """
    # 保険加入状況を確認
    enrollment = InsuranceEnrollment.objects.filter(
        user=request.user,
        insurance_end_datetime__isnull=True  # 継続中
    ).first()

    # 保険プラン取得
    insurance_plan = Insurance.objects.first()

    context = {
        'enrollment': enrollment,
        'insurance_plan': insurance_plan,
        'current_page': 'insurance'
    }
    return render(request, 'mypage/insurance.html', context)


@login_required
def insurance_enroll(request):
    """
    保険加入処理（POST）
    Insurance enrollment process
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不正なリクエストです'})

    # 既に加入済みかチェック
    if InsuranceEnrollment.objects.filter(
        user=request.user,
        insurance_end_datetime__isnull=True
    ).exists():
        return JsonResponse({'success': False, 'error': '既に加入済みです'})

    # 保険加入
    insurance = Insurance.objects.first()
    InsuranceEnrollment.objects.create(
        user=request.user,
        insurance=insurance,
        insurance_start_datetime=timezone.now()
    )

    return JsonResponse({'success': True})


@login_required
def insurance_cancel(request):
    """
    保険解約処理（POST）
    Insurance cancellation process
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不正なリクエストです'})

    # 保険加入状況を取得
    enrollment = InsuranceEnrollment.objects.filter(
        user=request.user,
        insurance_end_datetime__isnull=True
    ).first()

    if not enrollment:
        return JsonResponse({'success': False, 'error': '保険に加入していません'})

    # 解約処理（レコードは削除せず、終了日時を設定）
    enrollment.insurance_end_datetime = timezone.now()
    enrollment.save()

    return JsonResponse({'success': True})


@login_required
def insurance_claim_page(request):
    """
    保険クレーム申請ページ
    Insurance claim application page
    """
    # 保険加入済みかチェック
    if not InsuranceEnrollment.objects.filter(
        user=request.user,
        insurance_end_datetime__isnull=True
    ).exists():
        messages.error(request, '保険に加入していません')
        return redirect('insurance_page')

    # クレーム済みのレンタル履歴IDを取得
    claimed_history_ids = InsuranceClaim.objects.filter(
        user=request.user
    ).values_list('rental_history_id', flat=True)

    # レンタル履歴取得（自分の商品が借りられた取引、キャンセル済み除外、クレーム済み除外）
    rental_histories = RentalHistory.objects.filter(
        lender_user=request.user
    ).exclude(
        rental_status_id=6  # キャンセルを除外
    ).exclude(
        rental_history_id__in=claimed_history_ids
    ).select_related('product').order_by('-rental_start_datetime')

    context = {
        'rental_histories': rental_histories,
        'current_page': 'insurance',
    }
    return render(request, 'mypage/insurance_claim.html', context)


@login_required
def insurance_claim_submit(request):
    """
    保険クレーム申請処理（POST）
    Insurance claim submission process
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不正なリクエストです'})

    # 保険加入チェック
    if not InsuranceEnrollment.objects.filter(
        user=request.user,
        insurance_end_datetime__isnull=True
    ).exists():
        return JsonResponse({'success': False, 'error': '保険に加入していません'})

    # レンタル履歴のバリデーション
    rental_history_id = request.POST.get('rental_history_id')
    if not rental_history_id:
        return JsonResponse({'success': False, 'field': 'rental_history_id', 'error': 'レンタル履歴を選択してください'})

    # 破損内容のバリデーション
    description = request.POST.get('description', '').strip()
    if not description:
        return JsonResponse({'success': False, 'field': 'description', 'error': '破損内容を入力してください'})

    # 修理費用のバリデーション
    try:
        repair_cost = int(request.POST.get('repair_cost', 0))
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'field': 'repair_cost', 'error': '修理費用は数値で入力してください'})

    if repair_cost < 1:
        return JsonResponse({'success': False, 'field': 'repair_cost', 'error': '修理費用は1円以上で入力してください'})
    if repair_cost > 50000:
        return JsonResponse({'success': False, 'field': 'repair_cost', 'error': '修理費用は補償上限の¥50,000以下で入力してください'})

    # 画像が3枚すべてアップロードされているかチェック
    image_labels = {1: '破損した商品の画像', 2: '修理費用の領収書', 3: '修理後の商品の画像'}
    for image_type in [1, 2, 3]:
        if f'image_{image_type}' not in request.FILES:
            return JsonResponse({
                'success': False,
                'field': f'image_{image_type}',
                'error': f'{image_labels[image_type]}を選択してください'
            })

    # 同じレンタル履歴で既にクレーム済みかチェック
    if InsuranceClaim.objects.filter(
        user=request.user,
        rental_history_id=rental_history_id
    ).exists():
        return JsonResponse({'success': False, 'field': 'rental_history_id', 'error': 'このレンタル履歴は既にクレーム申請済みです'})

    try:
        # クレーム作成
        claim = InsuranceClaim.objects.create(
            user=request.user,
            rental_history_id=rental_history_id,
            product_id=request.POST.get('product_id'),
            claim_description=description,
            repair_cost=repair_cost,
            insurance_claim_status_id=1  # 審査中
        )

        # 画像アップロード
        for image_type in [1, 2, 3]:  # 破損、領収書、修理後
            image = request.FILES.get(f'image_{image_type}')
            if image:
                InsuranceClaimImage.objects.create(
                    claim=claim,
                    image=image,
                    image_type=image_type
                )

        return JsonResponse({'success': True})

    except Exception:
        return JsonResponse({'success': False, 'error': '申請処理中にエラーが発生しました'})


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  管理者側ビュー / Admin Side Views                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required
def admin_insurance_claims(request):
    """
    保険クレーム一覧（管理者）
    Insurance claims list (Admin)
    """
    if not request.user.is_staff:
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    all_claims = InsuranceClaim.objects.all().select_related(
        'user', 'product', 'rental_history', 'insurance_claim_status'
    ).order_by('-claim_datetime')

    # カウント集計
    total_count = all_claims.count()
    pending_count = all_claims.filter(insurance_claim_status_id=1).count()
    approved_count = all_claims.filter(insurance_claim_status_id=2).count()
    rejected_count = all_claims.filter(insurance_claim_status_id=3).count()

    # フィルター適用
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'pending':
        claims = all_claims.filter(insurance_claim_status_id=1)
    elif status_filter == 'approved':
        claims = all_claims.filter(insurance_claim_status_id=2)
    elif status_filter == 'rejected':
        claims = all_claims.filter(insurance_claim_status_id=3)
    else:
        claims = all_claims
        status_filter = 'all'

    context = {
        'claims': claims,
        'current_filter': status_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'admin/insurance_claims.html', context)


@login_required
def admin_insurance_claim_detail(request, claim_id):
    """
    保険クレーム詳細（管理者）
    GETで詳細表示、POSTでAjax承認/却下処理
    """
    if not request.user.is_staff:
        if request.method == 'POST':
            return JsonResponse({'success': False, 'message': '管理者権限が必要です'}, status=403)
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    claim = get_object_or_404(
        InsuranceClaim.objects.select_related('user', 'product', 'rental_history', 'insurance_claim_status'),
        claim_id=claim_id
    )

    # POST: Ajax承認/却下処理
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        action = request.POST.get('action')

        if claim.insurance_claim_status_id != 1:
            return JsonResponse({'success': False, 'message': 'このクレームは既に審査済みです'})

        if action == 'approve':
            claim.insurance_claim_status_id = 2
            claim.approval_datetime = timezone.now()
            claim.save()
            _send_claim_notification(claim, approved=True)
            return JsonResponse({'success': True, 'message': 'クレームを承認しました'})
        elif action == 'reject':
            claim.insurance_claim_status_id = 3
            claim.rejection_datetime = timezone.now()
            claim.rejection_reason = request.POST.get('reason', '')
            claim.save()
            _send_claim_notification(claim, approved=False)
            return JsonResponse({'success': True, 'message': 'クレームを却下しました'})
        else:
            return JsonResponse({'success': False, 'message': '不正なアクションです'})

    # GET: 詳細表示
    images = {
        'damaged': claim.images.filter(image_type=1),
        'receipt': claim.images.filter(image_type=2),
        'repaired': claim.images.filter(image_type=3),
    }

    insurance_plan = Insurance.objects.first()

    context = {
        'claim': claim,
        'images': images,
        'insurance_plan': insurance_plan,
    }
    return render(request, 'admin/insurance_claim_detail.html', context)


@login_required
def insurance_claim_approve(request, claim_id):
    """
    クレーム承認処理（管理者）
    Claim approval process (Admin)
    """
    if request.method != 'POST':
        return redirect('admin_insurance_claims')

    if not request.user.is_staff:
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    claim = get_object_or_404(
        InsuranceClaim.objects.select_related('product'),
        claim_id=claim_id
    )
    claim.insurance_claim_status_id = 2  # 承認
    claim.approval_datetime = timezone.now()
    claim.save()

    _send_claim_notification(claim, approved=True)

    messages.success(request, 'クレームを承認しました')
    return redirect('admin_insurance_claims')


@login_required
def insurance_claim_reject(request, claim_id):
    """
    クレーム却下処理（管理者）
    Claim rejection process (Admin)
    """
    if request.method != 'POST':
        return redirect('admin_insurance_claims')

    if not request.user.is_staff:
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    claim = get_object_or_404(
        InsuranceClaim.objects.select_related('product'),
        claim_id=claim_id
    )
    claim.insurance_claim_status_id = 3  # 却下
    claim.rejection_datetime = timezone.now()
    claim.rejection_reason = request.POST.get('reason', '')
    claim.save()

    _send_claim_notification(claim, approved=False)

    messages.success(request, 'クレームを却下しました')
    return redirect('admin_insurance_claims')


def _send_claim_notification(claim, approved):
    """
    クレーム審査結果の通知を申請者に送信
    """
    try:
        product_name = claim.product.product_name
        link_url = reverse('insurance_page')

        if approved:
            title = '保険クレームが承認されました'
            detail = f'「{product_name}」の保険クレーム（¥{claim.repair_cost:,.0f}）が承認されました。'
        else:
            title = '保険クレームが却下されました'
            detail = f'「{product_name}」の保険クレームが却下されました。'
            if claim.rejection_reason:
                detail += f'（理由: {claim.rejection_reason}）'

        create_notification(
            notification_type_id=1,  # システム通知
            title=title,
            detail=detail,
            link_url=link_url,
            target_users=[claim.user]
        )
    except Exception:
        pass  # 通知失敗は無視
