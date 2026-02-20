"""
管理者パネル ビュー
Admin Panel Views
"""

import base64
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseNotFound
from django.utils import timezone
from django.urls import reverse
from django.core.paginator import Paginator
from django.db import transaction

ADMIN_LOGIN_URL = '/admin-panel/login/'

from monotal.models import (
    IdentityVerification, IdentityVerificationStatus, IdentityVerificationImage,
    UserPersonalInfo, UserStatus,
    CancellationReason, CancellationStatus, CancellationRequest,
    RentalHistory, RentalStatus, ProductStatus,
    Insurance, InsuranceEnrollment, InsuranceCoveragePeriod,
    InsuranceClaim, InsuranceClaimImage, InsuranceClaimStatus,
)
from monotal.views import create_notification


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  定数 / Constants                                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# 本人確認ステータス
IDENTITY_STATUS_PENDING = 0
IDENTITY_STATUS_APPROVED = 1
IDENTITY_STATUS_REJECTED = 2

# 通知タイプ
NOTIFICATION_TYPE_SYSTEM = 1

# 取引中止ステータス
CANCELLATION_STATUS_PENDING = 1
CANCELLATION_STATUS_APPROVED = 2
CANCELLATION_STATUS_REJECTED = 3

RENTAL_STATUS_CANCELLATION_REQUESTED = 10
RENTAL_STATUS_CANCELLATION_APPROVED = 11


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ログイン・ログアウト / Login & Logout                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def admin_login(request):
    """管理者ログイン"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        errors = []

        if not username:
            errors.append('電話番号を入力してください')
        if not password:
            errors.append('パスワードを入力してください')

        if not errors:
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                next_url = request.GET.get('next', reverse('admin_dashboard'))
                return redirect(next_url)
            else:
                errors.append('管理者アカウントの認証に失敗しました')

        return render(request, 'admin_panel/login.html', {
            'errors': errors,
            'username': username,
        })

    return render(request, 'admin_panel/login.html')


def admin_logout(request):
    """管理者ログアウト"""
    logout(request)
    return redirect('admin_login')


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ダッシュボード / Dashboard                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required(login_url=ADMIN_LOGIN_URL)
def admin_dashboard(request):
    """管理者ダッシュボード"""
    if not request.user.is_staff:
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    # 各審査の未処理件数
    verification_pending = IdentityVerification.objects.filter(
        identity_verification_status_id=IDENTITY_STATUS_PENDING
    ).count()

    cancellation_pending = CancellationRequest.objects.filter(
        cancellation_status_id=CANCELLATION_STATUS_PENDING
    ).count()

    insurance_pending = InsuranceClaim.objects.filter(
        insurance_claim_status_id=1  # 審査中
    ).count()

    context = {
        'verification_pending': verification_pending,
        'cancellation_pending': cancellation_pending,
        'insurance_pending': insurance_pending,
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  本人確認審査 / Identity Verification                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class AdminVerificationListView(LoginRequiredMixin, View):
    """
    本人確認審査一覧ページ（管理者用）
    未確認の申請を古い順に表示
    """
    login_url = ADMIN_LOGIN_URL

    def get(self, request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, '権限がありません')
            return redirect('index')

        verifications = IdentityVerification.objects.filter(
            identity_verification_status_id=IDENTITY_STATUS_PENDING
        ).select_related('user').order_by('register_datetime')

        paginator = Paginator(verifications, 20)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        context = {
            'verifications': page_obj,
            'total_count': verifications.count(),
            'page_obj': page_obj,
        }

        return render(request, 'admin_panel/verification_list.html', context)


class AdminVerificationDetailView(LoginRequiredMixin, View):
    """
    本人確認審査詳細ページ（管理者用）
    画像確認と承認/却下処理
    """
    login_url = ADMIN_LOGIN_URL

    def get(self, request, verification_id, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, '権限がありません')
            return redirect('index')

        try:
            verification = IdentityVerification.objects.select_related(
                'user', 'identity_verification_status'
            ).prefetch_related('images').get(
                identity_verification_id=verification_id
            )
        except IdentityVerification.DoesNotExist:
            messages.error(request, '申請が見つかりません')
            return redirect('admin_verification_list')

        images = []
        for img in verification.images.all():
            images.append({
                'data': base64.b64encode(img.image_data).decode('utf-8'),
                'id': img.identity_verification_image_id
            })

        context = {
            'verification': verification,
            'images': images,
        }

        return render(request, 'admin_panel/verification_detail.html', context)

    def post(self, request, verification_id, *args, **kwargs):
        if not request.user.is_staff:
            return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)

        action = request.POST.get('action')

        if action not in ['approve', 'reject']:
            return JsonResponse({'success': False, 'message': '不正な操作です'}, status=400)

        try:
            with transaction.atomic():
                verification = IdentityVerification.objects.select_for_update().get(
                    identity_verification_id=verification_id
                )

                if action == 'approve':
                    try:
                        approved_status = IdentityVerificationStatus.objects.get(
                            identity_verification_status_id=IDENTITY_STATUS_APPROVED
                        )
                    except IdentityVerificationStatus.DoesNotExist:
                        approved_status = IdentityVerificationStatus.objects.create(
                            identity_verification_status_id=IDENTITY_STATUS_APPROVED,
                            status_name='承認'
                        )

                    verification.identity_verification_status = approved_status
                    verification.approval_datetime = timezone.now()
                    verification.save()

                    if verification.last_name and verification.first_name:
                        UserPersonalInfo.objects.update_or_create(
                            user=verification.user,
                            defaults={
                                'last_name': verification.last_name,
                                'first_name': verification.first_name,
                                'last_name_kana': verification.last_name_kana,
                                'first_name_kana': verification.first_name_kana,
                                'birth_date': verification.birth_date,
                                'gender': verification.gender
                            }
                        )

                    try:
                        user_approved_status = UserStatus.objects.get(user_status_id=2)
                    except UserStatus.DoesNotExist:
                        user_approved_status = UserStatus.objects.create(
                            user_status_id=2,
                            status_name='承認済みユーザー'
                        )

                    verification.user.user_status = user_approved_status
                    verification.user.save()

                    create_notification(
                        notification_type_id=NOTIFICATION_TYPE_SYSTEM,
                        title='本人確認が完了しました',
                        detail='本人確認が承認されました。すべての機能をご利用いただけます。',
                        link_url='/monotal/mypage/listing/',
                        target_users=[verification.user]
                    )

                    message = '承認しました'

                elif action == 'reject':
                    try:
                        rejected_status = IdentityVerificationStatus.objects.get(
                            identity_verification_status_id=IDENTITY_STATUS_REJECTED
                        )
                    except IdentityVerificationStatus.DoesNotExist:
                        rejected_status = IdentityVerificationStatus.objects.create(
                            identity_verification_status_id=IDENTITY_STATUS_REJECTED,
                            status_name='却下'
                        )

                    verification.identity_verification_status = rejected_status
                    verification.rejection_datetime = timezone.now()
                    verification.save()

                    create_notification(
                        notification_type_id=NOTIFICATION_TYPE_SYSTEM,
                        title='本人確認が承認されませんでした',
                        detail='本人確認書類を確認できませんでした。お手数ですが再度申請をお願いいたします。',
                        link_url='/monotal/identity-verification/',
                        target_users=[verification.user]
                    )

                    message = '却下しました'

            return JsonResponse({'success': True, 'message': message})

        except IdentityVerification.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申請が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'エラー: {str(e)}'}, status=500)


class VerificationImageView(LoginRequiredMixin, View):
    """
    本人確認画像取得API（管理者用）
    """
    login_url = ADMIN_LOGIN_URL

    def get(self, request, image_id, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden()

        try:
            image = IdentityVerificationImage.objects.get(
                identity_verification_image_id=image_id
            )
            return HttpResponse(image.image_data, content_type='image/jpeg')
        except IdentityVerificationImage.DoesNotExist:
            return HttpResponseNotFound()


# as_view() エイリアス
admin_verification_list = AdminVerificationListView.as_view()
admin_verification_detail = AdminVerificationDetailView.as_view()
verification_image = VerificationImageView.as_view()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  取引中止審査 / Cancellation Review                                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required(login_url=ADMIN_LOGIN_URL)
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

    total_count = all_requests.count()
    pending_count = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_PENDING).count()
    approved_count = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_APPROVED).count()
    rejected_count = all_requests.filter(cancellation_status_id=CANCELLATION_STATUS_REJECTED).count()

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
    return render(request, 'admin_panel/cancellation_list.html', context)


@login_required(login_url=ADMIN_LOGIN_URL)
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
            cancellation_request.cancellation_status_id = CANCELLATION_STATUS_APPROVED
            cancellation_request.approval_datetime = timezone.now()
            admin_note = request.POST.get('admin_note', '').strip()
            if admin_note:
                cancellation_request.admin_note = admin_note
            cancellation_request.save()

            rental_history.rental_status_id = RENTAL_STATUS_CANCELLATION_APPROVED
            rental_history.save()

            product = rental_history.product
            product.product_status_id = 1  # 貸出可能
            product.save()

            _send_cancellation_approved_notification(
                rental_history,
                cancellation_request.requester_user,
                rental_history.lender_user,
                rental_history.renter_user
            )
            return JsonResponse({'success': True, 'message': '中止申請を承認しました'})

        elif action == 'reject':
            cancellation_request.cancellation_status_id = CANCELLATION_STATUS_REJECTED
            cancellation_request.rejection_datetime = timezone.now()
            admin_note = request.POST.get('admin_note', '').strip()
            if admin_note:
                cancellation_request.admin_note = admin_note
            cancellation_request.save()

            rental_history.rental_status_id = cancellation_request.previous_rental_status_id
            rental_history.save()

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
    return render(request, 'admin_panel/cancellation_detail.html', context)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  補償申請審査 / Insurance Claims Review                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@login_required(login_url=ADMIN_LOGIN_URL)
def admin_insurance_claims(request):
    """
    補償申請一覧（管理者）
    """
    if not request.user.is_staff:
        messages.error(request, '管理者権限が必要です')
        return redirect('index')

    all_claims = InsuranceClaim.objects.all().select_related(
        'user', 'product', 'rental_history', 'insurance_claim_status'
    ).order_by('-claim_datetime')

    total_count = all_claims.count()
    pending_count = all_claims.filter(insurance_claim_status_id=1).count()
    approved_count = all_claims.filter(insurance_claim_status_id=2).count()
    rejected_count = all_claims.filter(insurance_claim_status_id=3).count()

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
    return render(request, 'admin_panel/insurance_claims.html', context)


@login_required(login_url=ADMIN_LOGIN_URL)
def admin_insurance_claim_detail(request, claim_id):
    """
    補償申請詳細（管理者）
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
            return JsonResponse({'success': False, 'message': 'この補償申請は既に審査済みです'})

        if action == 'approve':
            claim.insurance_claim_status_id = 2
            claim.approval_datetime = timezone.now()
            claim.save()

            enrollment = _get_active_enrollment(claim.user)
            if enrollment:
                cp = _ensure_coverage_period(enrollment)
                cp.used_amount += claim.repair_cost
                cp.save()

            _send_claim_notification(claim, approved=True)
            return JsonResponse({'success': True, 'message': '補償申請を承認しました'})
        elif action == 'reject':
            claim.insurance_claim_status_id = 3
            claim.rejection_datetime = timezone.now()
            claim.rejection_reason = request.POST.get('reason', '')
            claim.save()
            _send_claim_notification(claim, approved=False)
            return JsonResponse({'success': True, 'message': '補償申請を却下しました'})
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
    return render(request, 'admin_panel/insurance_claim_detail.html', context)


@login_required(login_url=ADMIN_LOGIN_URL)
def insurance_claim_approve(request, claim_id):
    """
    補償申請承認処理（管理者）
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

    enrollment = _get_active_enrollment(claim.user)
    if enrollment:
        cp = _ensure_coverage_period(enrollment)
        cp.used_amount += claim.repair_cost
        cp.save()

    _send_claim_notification(claim, approved=True)

    messages.success(request, '補償申請を承認しました')
    return redirect('admin_insurance_claims')


@login_required(login_url=ADMIN_LOGIN_URL)
def insurance_claim_reject(request, claim_id):
    """
    補償申請却下処理（管理者）
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

    messages.success(request, '補償申請を却下しました')
    return redirect('admin_insurance_claims')


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  ヘルパー関数 / Helper Functions                                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def _get_active_enrollment(user):
    """加入中の enrollment を取得"""
    return InsuranceEnrollment.objects.filter(
        user=user,
        insurance_enrollment_status_id=2,
        insurance_end_datetime__isnull=True,
    ).first()


def _ensure_coverage_period(enrollment):
    """InsuranceEnrollment に対応する InsuranceCoveragePeriod を取得/作成"""
    from dateutil.relativedelta import relativedelta

    insurance = enrollment.insurance
    coverage_limit = int(insurance.coverage_limit) if insurance else 50000

    try:
        cp = enrollment.coverage_period
    except InsuranceCoveragePeriod.DoesNotExist:
        cp = None

    now = timezone.now()

    if cp is None:
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
        if enrollment.insurance_enrollment_status_id == 3:
            return cp

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


def _send_cancellation_approved_notification(rental_history, requester, lender, renter):
    """中止承認時: 双方に通知"""
    try:
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


def _send_claim_notification(claim, approved):
    """補償申請審査結果の通知を申請者に送信"""
    try:
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
            notification_type_id=1,
            title=title,
            detail=detail,
            link_url=link_url,
            target_users=[claim.user]
        )
    except Exception:
        pass
