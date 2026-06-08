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
from .models import Insurance, InsuranceEnrollment, InsuranceCoveragePeriod, InsuranceClaim, InsuranceClaimImage, InsuranceClaimStatus, RentalHistory, CreditCard


def _get_active_enrollment(user):
    """加入中の enrollment を取得"""
    return InsuranceEnrollment.objects.filter(
        user=user,
        insurance_enrollment_status_id=2,  # 加入中
        insurance_end_datetime__isnull=True,
    ).first()


def _ensure_coverage_period(enrollment):
    """
    InsuranceEnrollment に対応する InsuranceCoveragePeriod が存在しなければ作成する。
    既存の場合は期間切れチェック→リセットして返す。
    解約済み(status=3)の場合はリセットしない。
    """
    from dateutil.relativedelta import relativedelta

    insurance = enrollment.insurance
    coverage_limit = int(insurance.coverage_limit) if insurance else 50000

    try:
        cp = enrollment.coverage_period
    except InsuranceCoveragePeriod.DoesNotExist:
        cp = None

    now = timezone.now()

    if cp is None:
        # 新規作成
        period_start = enrollment.insurance_start_datetime
        period_end = period_start + relativedelta(months=1)
        cp = InsuranceCoveragePeriod.objects.create(
            insurance_enrollment=enrollment,
            period_start_datetime=period_start,
            period_end_datetime=period_end,
            coverage_limit=coverage_limit,
            used_amount=0,
        )
    elif now >= cp.period_end_datetime:
        # 解約済み(status=3)の場合はリセットしない
        if enrollment.insurance_enrollment_status_id == 3:
            return cp

        # 期間切れ → リセット（遅延評価）
        # 次の期間開始を計算（加入日ベース）
        enroll_day = enrollment.insurance_start_datetime.day
        try:
            new_start = now.replace(day=enroll_day, hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(now.year, now.month)[1]
            new_start = now.replace(day=last_day, hour=0, minute=0, second=0, microsecond=0)

        if new_start > now:
            new_start = new_start - relativedelta(months=1)

        new_end = new_start + relativedelta(months=1)

        cp.period_start_datetime = new_start
        cp.period_end_datetime = new_end
        cp.used_amount = 0
        cp.coverage_limit = coverage_limit
        cp.save()

    return cp


def _get_coverage_period(user):
    """
    加入日ベースの補償期間を CoveragePeriod テーブルから取得。
    返り値: (period_start, reset_date, remaining)
    """
    enrollment = _get_active_enrollment(user)

    if not enrollment:
        return None, None, 0

    cp = _ensure_coverage_period(enrollment)
    return cp.period_start_datetime, cp.period_end_datetime, cp.remaining


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ユーザー側ビュー / User Side Views                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required
def insurance_page(request):
    """
    保険加入ページ表示
    Insurance enrollment page
    """
    # 保険加入状況を確認（加入中 or 解約予約）
    enrollment = _get_active_enrollment(request.user)

    # 保険プラン取得
    insurance_plan = Insurance.objects.first()

    context = {
        'enrollment': enrollment,
        'insurance_plan': insurance_plan,
        'current_page': 'insurance'
    }

    # 加入済みの場合: 補償残枠情報と審査中の申請を取得
    if enrollment:
        cp = _ensure_coverage_period(enrollment)
        context['coverage_period'] = cp
        context['monthly_remaining'] = cp.remaining
        context['coverage_limit'] = int(cp.coverage_limit)
        context['period_start'] = cp.period_start_datetime
        context['reset_date'] = cp.period_end_datetime

        # 審査中の補償申請一覧
        pending_claims = InsuranceClaim.objects.filter(
            user=request.user,
            insurance_claim_status_id=1  # 審査中
        ).select_related('product').order_by('-claim_datetime')
        context['pending_claims'] = pending_claims

        # 補償申請履歴（承認・却下）
        claim_history = InsuranceClaim.objects.filter(
            user=request.user,
            insurance_claim_status_id__in=[2, 3]  # 承認・却下
        ).select_related('product', 'insurance_claim_status').order_by('-claim_datetime')
        context['claim_history'] = claim_history

    return render(request, 'mypage/insurance.html', context)


@login_required
def insurance_enroll_confirm(request):
    """
    保険加入確認ページ（カード選択 + 利用規約同意）
    Insurance enrollment confirmation page
    """
    # 既に加入済みかチェック
    if _get_active_enrollment(request.user):
        messages.error(request, '既に保険に加入しています')
        return redirect('insurance_page')

    insurance_plan = Insurance.objects.first()
    my_cards = CreditCard.objects.filter(user=request.user).order_by('-is_default', '-register_datetime')

    context = {
        'insurance_plan': insurance_plan,
        'my_cards': my_cards,
        'current_page': 'insurance',
    }
    return render(request, 'mypage/insurance_enroll.html', context)


@login_required
def insurance_enroll(request):
    """
    保険加入処理（POST）
    Insurance enrollment process
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不正なリクエストです'})

    # 既に加入済みかチェック
    if _get_active_enrollment(request.user):
        return JsonResponse({'success': False, 'error': '既に加入済みです'})

    # カード選択チェック
    card_id = request.POST.get('card_id')
    if not card_id:
        return JsonResponse({'success': False, 'error': '決済カードを選択してください'})

    if not CreditCard.objects.filter(credit_card_id=card_id, user=request.user).exists():
        return JsonResponse({'success': False, 'error': '無効なカードです'})

    # 保険加入
    insurance = Insurance.objects.first()
    enrollment = InsuranceEnrollment.objects.create(
        user=request.user,
        insurance=insurance,
        insurance_start_datetime=timezone.now()
    )

    # 補償残枠レコードを作成
    _ensure_coverage_period(enrollment)

    return JsonResponse({'success': True})


@login_required
def insurance_cancel_confirm(request):
    """
    保険解約確認ページ（GET）
    Insurance cancellation confirmation page
    """
    enrollment = _get_active_enrollment(request.user)
    if not enrollment:
        messages.error(request, '保険に加入していません')
        return redirect('insurance_page')

    cp = _ensure_coverage_period(enrollment)

    context = {
        'enrollment': enrollment,
        'coverage_period': cp,
        'current_page': 'insurance',
    }
    return render(request, 'mypage/insurance_cancel.html', context)


@login_required
def insurance_cancel(request):
    """
    保険解約処理（POST）
    Insurance cancellation process - 即時解約
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不正なリクエストです'})

    enrollment = _get_active_enrollment(request.user)
    if not enrollment:
        return JsonResponse({'success': False, 'error': '保険に加入していません'})

    # 解約理由を取得
    cancel_reason = request.POST.get('cancel_reason', '').strip()
    cancel_reason_other = request.POST.get('cancel_reason_other', '').strip()

    if not cancel_reason:
        return JsonResponse({'success': False, 'error': '解約理由を選択してください'})

    # 「その他」の場合は自由記入を使用
    if cancel_reason == 'その他' and cancel_reason_other:
        cancel_reason = f'その他: {cancel_reason_other}'

    # 即時解約処理
    enrollment.insurance_enrollment_status_id = 3  # 解約済み
    enrollment.insurance_end_datetime = timezone.now()
    enrollment.cancel_reason = cancel_reason
    enrollment.save()

    # 通知送信
    _send_cancel_notification(enrollment)

    return JsonResponse({'success': True})



@login_required
def insurance_claim_page(request):
    """
    補償申請ページ
    Insurance claim application page
    """
    # 保険加入済みかチェック（加入中 or 解約予約）
    if not _get_active_enrollment(request.user):
        messages.error(request, '保険に加入していません')
        return redirect('insurance_page')

    # 補償申請済みのレンタル履歴IDを取得
    claimed_history_ids = InsuranceClaim.objects.filter(
        user=request.user
    ).values_list('rental_history_id', flat=True)

    # レンタル履歴取得（自分の商品が借りられた取引、キャンセル済み除外、補償申請済み除外）
    rental_histories = RentalHistory.objects.filter(
        lender_user=request.user
    ).exclude(
        rental_status_id=6  # キャンセルを除外
    ).exclude(
        rental_history_id__in=claimed_history_ids
    ).select_related('product').order_by('-rental_start_datetime')

    # 補償期間・残枠を計算
    period_start, reset_date, monthly_remaining = _get_coverage_period(request.user)
    insurance = Insurance.objects.first()
    coverage_limit = int(insurance.coverage_limit) if insurance else 50000

    context = {
        'rental_histories': rental_histories,
        'current_page': 'insurance',
        'monthly_remaining': monthly_remaining,
        'coverage_limit': coverage_limit,
        'period_start': period_start,
        'reset_date': reset_date,
    }
    return render(request, 'mypage/insurance_claim.html', context)


@login_required
def insurance_claim_submit(request):
    """
    補償申請処理（POST）
    Insurance claim submission process
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不正なリクエストです'})

    # 保険加入チェック（加入中 or 解約予約）
    if not _get_active_enrollment(request.user):
        return JsonResponse({'success': False, 'error': '保険に加入していません'})

    # レンタル履歴のバリデーション
    rental_history_id = request.POST.get('rental_history_id')
    if not rental_history_id:
        return JsonResponse({'success': False, 'field': 'rental_history_id', 'error': 'レンタル履歴を選択してください'})

    # 破損内容のバリデーション
    description = request.POST.get('description', '').strip()
    if not description:
        return JsonResponse({'success': False, 'field': 'description', 'error': '破損内容を入力してください'})

    # 補償残枠チェック（CoveragePeriod から取得）
    enrollment = _get_active_enrollment(request.user)
    cp = _ensure_coverage_period(enrollment)
    monthly_remaining = cp.remaining
    if monthly_remaining <= 0:
        return JsonResponse({'success': False, 'error': '今月の補償上限に達しています。次の補償期間にリセットされます。'})

    # 修理費用のバリデーション
    try:
        repair_cost = int(request.POST.get('repair_cost', 0))
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'field': 'repair_cost', 'error': '修理費用は数値で入力してください'})

    if repair_cost < 1:
        return JsonResponse({'success': False, 'field': 'repair_cost', 'error': '修理費用は1円以上で入力してください'})
    if repair_cost > monthly_remaining:
        return JsonResponse({'success': False, 'field': 'repair_cost', 'error': f'今月の補償残枠（¥{monthly_remaining:,}）を超えています'})

    # 画像が3枚すべてアップロードされているかチェック
    image_labels = {1: '破損した商品の画像', 2: '修理費用の領収書', 3: '修理後の商品の画像'}
    for image_type in [1, 2, 3]:
        if f'image_{image_type}' not in request.FILES:
            return JsonResponse({
                'success': False,
                'field': f'image_{image_type}',
                'error': f'{image_labels[image_type]}を選択してください'
            })

    # 同じレンタル履歴で既に補償申請済みかチェック
    if InsuranceClaim.objects.filter(
        user=request.user,
        rental_history_id=rental_history_id
    ).exists():
        return JsonResponse({'success': False, 'field': 'rental_history_id', 'error': 'このレンタル履歴は既に補償申請済みです'})

    try:
        # 補償申請作成
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

        # 申請受付通知を送信
        _send_claim_submitted_notification(claim)

        return JsonResponse({'success': True})

    except Exception:
        return JsonResponse({'success': False, 'error': '申請処理中にエラーが発生しました'})


def _send_claim_submitted_notification(claim):
    """
    補償申請受付通知を申請者に送信
    """
    try:
        from .views import create_notification
        product_name = claim.product.product_name
        link_url = reverse('insurance_page')

        create_notification(
            notification_type_id=1,  # システム通知
            title='補償申請を受け付けました',
            detail=f'「{product_name}」の補償申請（¥{claim.repair_cost:,.0f}）を受け付けました。審査結果をお待ちください。',
            link_url=link_url,
            target_users=[claim.user]
        )
    except Exception:
        pass  # 通知失敗は無視


def _send_cancel_notification(enrollment):
    """
    保険解約完了通知を送信
    """
    try:
        from .views import create_notification
        link_url = reverse('insurance_page')

        create_notification(
            notification_type_id=1,  # システム通知
            title='保険を解約しました',
            detail='保険の解約が完了しました。再度加入する場合は保険ページからお手続きください。',
            link_url=link_url,
            target_users=[enrollment.user]
        )
    except Exception:
        pass  # 通知失敗は無視


def _send_claim_notification(claim, approved):
    """
    補償申請審査結果の通知を申請者に送信
    """
    try:
        from .views import create_notification
        product_name = claim.product.product_name
        link_url = reverse('insurance_page')

        if approved:
            title = '補償申請が承認されました'
            detail = f'「{product_name}」の補償申請（¥{claim.repair_cost:,.0f}）が承認されました。'
        else:
            title = '補償申請が却下されました'
            detail = f'「{product_name}」の補償申請が却下されました。'
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
