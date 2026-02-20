import json
import re
from datetime import timedelta
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .models import *
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Case, When, Value, IntegerField
from django.db import transaction
#from .models import User, UserStatus, EmailVerificationToken


def send_verification_email(email, user_name, phone_number, password, request, is_google_auth=False):
    """
    認証メールを送信（ユーザー作成前）
    登録情報をトークンに保存し、認証後にユーザーを作成する
    """
    # 同じメールアドレスの未使用トークンを削除
    EmailVerificationToken.objects.filter(email=email, is_used=False).delete()

    # パスワードをハッシュ化（Google認証の場合は空）
    password_hash = make_password(password) if password else ''

    # 新しいトークン作成（24時間有効）
    token = EmailVerificationToken.objects.create(
        email=email,
        user_name=user_name,
        phone_number=phone_number,
        password_hash=password_hash,
        is_google_auth=is_google_auth,
        expires_at=timezone.now() + timedelta(hours=24)
    )

    # 認証URL作成
    verify_url = f"{request.scheme}://{request.get_host()}/monotal/verify/{token.token}/"

    # メール送信
    send_mail(
        subject='【monotal】メールアドレスの確認',
        message=f'''
{user_name} 様

monotalへのご登録ありがとうございます。

以下のリンクをクリックして、メールアドレスの確認を完了してください。
このリンクは24時間有効です。

{verify_url}

このメールに心当たりがない場合は、無視してください。

monotal
''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


class IndexView(View):
    def get(self, request, *args, **kwargs):
        context = {}

        # 閲覧履歴（ログインユーザーのみ）
        if request.user.is_authenticated:
            browsing_histories = BrowsingHistory.objects.filter(
                user=request.user,
                product__delete_datetime__isnull=True
            ).exclude(
                product__product_status_id__in=[PRODUCT_STATUS_PAUSED, PRODUCT_STATUS_DELETED]
            ).select_related(
                'product', 'product__product_status'
            ).prefetch_related(
                'product__images', 'product__rental_plans'
            ).order_by('-register_datetime')[:20]
            context['browsing_histories'] = browsing_histories

        # おすすめ商品
        if request.user.is_authenticated:
            recommended_products = self._get_personalized_recommendations(request.user)
        else:
            recommended_products = Product.objects.filter(
                delete_datetime__isnull=True
            ).exclude(
                product_status_id__in=[PRODUCT_STATUS_PAUSED, PRODUCT_STATUS_DELETED]
            ).select_related(
                'product_category', 'product_status'
            ).prefetch_related(
                'images', 'rental_plans'
            ).annotate(
                bookmark_count=Count('bookmark')
            ).order_by('-register_datetime')[:40]
        context['recommended_products'] = recommended_products

        # カテゴリー一覧（親カテゴリーのみ、Nav用）
        categories = ProductCategory.objects.filter(
            parent_product_category__isnull=True
        ).order_by('product_category_id')
        context['categories'] = categories

        return render(request, 'home.html', context)

    def _get_personalized_recommendations(self, user):
        """ユーザーの行動データに基づくパーソナライズされたおすすめ商品を取得"""
        from collections import defaultdict

        # カテゴリ階層マップを構築
        all_categories = ProductCategory.objects.all()
        parent_to_children = defaultdict(list)
        child_to_parent = {}
        for cat in all_categories:
            if cat.parent_product_category_id:
                parent_to_children[cat.parent_product_category_id].append(cat.product_category_id)
                child_to_parent[cat.product_category_id] = cat.parent_product_category_id

        # カテゴリごとのスコアを計算
        category_scores = defaultdict(int)

        # 閲覧履歴: 1点/件
        browsing_counts = (
            BrowsingHistory.objects.filter(user=user)
            .values('product__product_category_id')
            .annotate(cnt=Count('browsing_history_id'))
        )
        for row in browsing_counts:
            category_scores[row['product__product_category_id']] += row['cnt'] * 1

        # ブックマーク: 5点/件
        bookmark_counts = (
            Bookmark.objects.filter(user=user)
            .values('product__product_category_id')
            .annotate(cnt=Count('bookmark_id'))
        )
        for row in bookmark_counts:
            category_scores[row['product__product_category_id']] += row['cnt'] * 5

        # 興味カテゴリ: 50点/カテゴリ
        hobby_categories = UserHobby.objects.filter(user=user).values_list(
            'product_category_id', flat=True
        )
        for cat_id in hobby_categories:
            category_scores[cat_id] += 50

        # スコアデータがない場合は新着順にフォールバック
        if not category_scores:
            return Product.objects.filter(
                delete_datetime__isnull=True
            ).exclude(
                product_status_id__in=[PRODUCT_STATUS_PAUSED, PRODUCT_STATUS_DELETED]
            ).exclude(
                user=user
            ).select_related(
                'product_category', 'product_status'
            ).prefetch_related(
                'images', 'rental_plans'
            ).annotate(
                bookmark_count=Count('bookmark')
            ).order_by('-register_datetime')[:40]

        # 階層間でスコアを展開
        expanded_scores = defaultdict(int, category_scores)

        # 子→親への伝播
        for cat_id, score in category_scores.items():
            if cat_id in child_to_parent:
                expanded_scores[child_to_parent[cat_id]] += score

        # 親→子への伝播
        for cat_id, score in category_scores.items():
            if cat_id in parent_to_children:
                for child_id in parent_to_children[cat_id]:
                    expanded_scores[child_id] += score

        # Case/WhenでProductにスコアをannotate
        whens = [
            When(product_category_id=cat_id, then=Value(score))
            for cat_id, score in expanded_scores.items()
            if score > 0
        ]

        return Product.objects.filter(
            delete_datetime__isnull=True
        ).exclude(
            product_status_id__in=[PRODUCT_STATUS_PAUSED, PRODUCT_STATUS_DELETED]
        ).exclude(
            user=user
        ).select_related(
            'product_category', 'product_status'
        ).prefetch_related(
            'images', 'rental_plans'
        ).annotate(
            bookmark_count=Count('bookmark'),
            recommendation_score=Case(
                *whens,
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-recommendation_score', '-register_datetime')[:40]


class LoginView(View):
    def get(self, request, *args, **kwargs):
        # 既にログイン済みの場合はリダイレクト
        if request.user.is_authenticated:
            return redirect('index')
        return render(request, 'login.html')

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            if is_ajax:
                data = json.loads(request.body)
                username = data.get('username')  # 電話番号
                password = data.get('password')
            else:
                username = request.POST.get('username')
                password = request.POST.get('password')

            errors = {}

            if not username:
                errors['username'] = '電話番号を入力してください'
            if not password:
                errors['password'] = 'パスワードを入力してください'

            if errors:
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': errors}, status=400)
                return render(request, 'login.html', {'errors': list(errors.values())})

            # 認証
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # ログイン日時を更新
                user.last_login_datetime = timezone.now()
                user.login_attempt_count = 0
                user.save(update_fields=['last_login_datetime', 'login_attempt_count'])

                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'ログインしました',
                        'redirect_url': '/monotal/'
                    })
                return redirect('index')
            else:
                # ログイン失敗
                error_message = '電話番号またはパスワードが正しくありません'

                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'errors': {'general': error_message}
                    }, status=400)
                return render(request, 'login.html', {
                    'errors': [error_message],
                    'username': username
                })

        except json.JSONDecodeError:
            if is_ajax:
                return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)
            return render(request, 'login.html', {'errors': ['不正なリクエストです']})


class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, 'ログアウトしました')
        return redirect('index')


class RegisterView(View):
    """会員登録ページ - 方法選択画面"""
    def get(self, request, *args, **kwargs):
        return render(request, 'register.html')


class RegisterFormView(View):
    """通常のフォーム入力による会員登録"""
    def get(self, request, *args, **kwargs):
        return render(request, 'register_form.html')

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            if is_ajax:
                data = json.loads(request.body)
                email = data.get('email')
                user_name = data.get('user_name')
                phone_number = data.get('phone_number')
                password = data.get('password')
                password_confirm = data.get('password_confirm')
            else:
                email = request.POST.get('email')
                user_name = request.POST.get('user_name')
                phone_number = request.POST.get('phone_number')
                password = request.POST.get('password')
                password_confirm = request.POST.get('password_confirm')

            errors = {}

            # 重複チェック
            # メールアドレス: 重複OK（複数アカウント可）
            if not email:
                errors['email'] = 'メールアドレスは必須です'
            if not user_name:
                errors['user_name'] = 'ユーザー名は必須です'
            elif not re.match(r'^[a-zA-Z0-9_]+$', user_name):
                errors['user_name'] = 'ユーザー名は半角英数字とアンダースコア(_)のみで入力してください'
            elif len(user_name) < 4 or len(user_name) > 15:
                errors['user_name'] = 'ユーザー名は4〜15文字で入力してください'
            elif User.objects.filter(user_name=user_name, user_status_id__in=[1, 2, 3]).exists():
                errors['user_name'] = 'このユーザー名は既に使用されています'
            if not phone_number:
                errors['phone_number'] = '電話番号は必須です'
            elif not re.match(r'^[0-9]+$', phone_number):
                errors['phone_number'] = '電話番号は数字のみで入力してください'
            elif User.objects.filter(phone_number=phone_number, user_status_id__in=[1, 2, 3]).exists():
                errors['phone_number'] = 'この電話番号は既に使用されています'
            if not password:
                errors['password'] = 'パスワードは必須です'
            elif len(password) < 8:
                errors['password'] = 'パスワードは8文字以上で入力してください'
            if password != password_confirm:
                errors['password_confirm'] = 'パスワードが一致しません'

            if errors:
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': errors}, status=400)
                return render(request, 'register_form.html', {
                    'errors': list(errors.values()),
                    'email': email,
                    'user_name': user_name,
                    'phone_number': phone_number,
                })

            # 認証メール送信（ユーザーは作成しない）
            send_verification_email(email, user_name, phone_number, password, request)

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '認証メールを送信しました。メールを確認してください。',
                    'redirect_url': '/monotal/register/sent/'
                })

            messages.success(request, '認証メールを送信しました。メールを確認してください。')
            return redirect('register_sent')

        except json.JSONDecodeError:
            if is_ajax:
                return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)
            return render(request, 'register_form.html', {'errors': ['不正なリクエストです']})


class RegisterCompleteView(View):
    """Google OAuth後の追加情報入力"""
    def get(self, request, *args, **kwargs):
        google_data = request.session.get('google_user_data', {})
        return render(request, 'register_complete.html', {
            'email': google_data.get('email', ''),
            'google_name': google_data.get('name', ''),
        })

    def post(self, request, *args, **kwargs):
        google_data = request.session.get('google_user_data', {})

        user_name = request.POST.get('user_name')
        phone_number = request.POST.get('phone_number')
        email = google_data.get('email') or request.POST.get('email')

        # 重複チェック
        # メールアドレス: 重複OK（複数アカウント可）
        # ユーザー名・電話番号: ステータス1,2,3で重複不可（4:削除済みのみ再利用可）
        errors = []
        if not email:
            errors.append('メールアドレスが取得できません。再度Googleログインしてください。')
        if not user_name:
            errors.append('ユーザー名は必須です')
        elif not re.match(r'^[a-zA-Z0-9_]+$', user_name):
            errors.append('ユーザー名は半角英数字とアンダースコア(_)のみで入力してください')
        elif len(user_name) < 4 or len(user_name) > 15:
            errors.append('ユーザー名は4〜15文字で入力してください')
        elif User.objects.filter(user_name=user_name, user_status_id__in=[1, 2, 3]).exists():
            errors.append('このユーザー名は既に使用されています')
        if not phone_number:
            errors.append('電話番号は必須です')
        elif not re.match(r'^[0-9]+$', phone_number):
            errors.append('電話番号は数字のみで入力してください')
        elif User.objects.filter(phone_number=phone_number, user_status_id__in=[1, 2, 3]).exists():
            errors.append('この電話番号は既に使用されています')

        if errors:
            return render(request, 'register_complete.html', {
                'errors': errors,
                'email': email,
                'user_name': user_name,
                'phone_number': phone_number,
                'google_name': google_data.get('name', ''),
            })

        # 認証メール送信（ユーザーは作成しない、Google認証フラグをTrue）
        send_verification_email(email, user_name, phone_number, None, request, is_google_auth=True)

        if 'google_user_data' in request.session:
            del request.session['google_user_data']

        messages.success(request, '認証メールを送信しました。メールを確認してください。')
        return redirect('register_sent')


class TermsOfServiceView(View):
    """利用規約ページ"""
    def get(self, request, *args, **kwargs):
        return render(request, 'terms_of_service.html')


class PrivacyPolicyView(View):
    """プライバシーポリシーページ"""
    def get(self, request, *args, **kwargs):
        return render(request, 'privacy_policy.html')


class RegisterSentView(View):
    """認証メール送信完了画面"""
    def get(self, request, *args, **kwargs):
        return render(request, 'register_sent.html')


class EmailVerifyView(View):
    """メール認証リンクの処理 - 認証後にユーザーを作成"""
    def get(self, request, token, *args, **kwargs):
        try:
            verification = EmailVerificationToken.objects.get(token=token)

            if not verification.is_valid():
                return render(request, 'verify_failed.html', {
                    'message': '認証リンクの有効期限が切れています。再度登録してください。'
                })

            # トークンを使用済みに
            verification.is_used = True
            verification.save()

            # ステータス1（本登録）を取得または作成
            try:
                active_status = UserStatus.objects.get(user_status_id=1)
            except UserStatus.DoesNotExist:
                active_status = UserStatus.objects.create(user_status_id=1, status_name='本登録')

            # ユーザー作成
            user = User(
                email=verification.email,
                user_name=verification.user_name,
                display_name=verification.user_name,  # 初期値としてuser_nameを使用
                phone_number=verification.phone_number,
                user_status=active_status,
            )

            # パスワード設定（Google認証の場合は使用不可パスワード）
            if verification.password_hash:
                user.password = verification.password_hash
            else:
                user.set_unusable_password()

            user.save()

            # ログイン
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, '会員登録が完了しました。興味のある趣味を選んでください。')
            return redirect('register_done')

        except EmailVerificationToken.DoesNotExist:
            return render(request, 'verify_failed.html', {
                'message': '無効な認証リンクです。'
            })


class RegisterDoneView(LoginRequiredMixin, View):
    """会員登録完了ページ"""
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        return render(request, 'register_done.html')


class ProfileView(View):
    """ユーザープロフィール閲覧ページ（公開）"""
    def get(self, request, username, *args, **kwargs):
        try:
            user = User.objects.get(user_name=username, user_status_id__in=[1, 2, 3])
        except User.DoesNotExist:
            messages.error(request, 'ユーザーが見つかりません。')
            return redirect('index')

        # ユーザーの出品商品を取得（画像も一緒に取得）
        user_products = Product.objects.filter(
            user=user,
            delete_datetime__isnull=True
        ).select_related(
            'product_status',
            'product_category'
        ).prefetch_related(
            'images'
        )

        # 商品ステータスフィルタ
        product_status_filter = request.GET.get('status', 'all')
        if product_status_filter == 'available':
            user_products = user_products.filter(product_status_id=1)
        elif product_status_filter == 'renting':
            user_products = user_products.filter(product_status_id=2)

        # 商品ソート
        product_sort = request.GET.get('product_sort', '-register_datetime')
        if product_sort not in ['-register_datetime', 'register_datetime']:
            product_sort = '-register_datetime'
        user_products = user_products.order_by(product_sort)

        # ブックマーク商品を取得（本人のみ表示）
        bookmarked_products = []
        bookmarks_count = 0
        if request.user.is_authenticated and request.user == user:
            bookmarked_products = Product.objects.filter(
                bookmark__user=user,
                delete_datetime__isnull=True
            ).select_related(
                'product_status',
                'product_category',
                'user'
            ).prefetch_related(
                'images'
            ).order_by('-bookmark__register_datetime')
            bookmarks_count = bookmarked_products.count()

        # 本人確認ステータスを取得
        # user_status_id=2 は承認済みユーザー
        identity_status = None  # None: 未申請, 0: 審査中, 1: 承認, 2: 却下
        if user.user_status_id == 2:
            identity_status = 1  # 承認済み
        else:
            # IdentityVerificationから最新の申請を確認
            latest_verification = IdentityVerification.objects.filter(
                user=user
            ).order_by('-register_datetime').first()
            if latest_verification:
                identity_status = latest_verification.identity_verification_status_id

        # フォロー関連データ
        follower_count = Follow.objects.filter(followed_user=user).count()  # フォロワー数
        following_count = Follow.objects.filter(follower_user=user).count()  # フォロー中
        is_following = False
        is_blocked = False
        is_blocked_by = False
        if request.user.is_authenticated and request.user != user:
            is_following = Follow.objects.filter(
                follower_user=request.user,
                followed_user=user
            ).exists()
            is_blocked = Block.objects.filter(
                blocker_user=request.user,
                blocked_user=user
            ).exists()
            is_blocked_by = Block.objects.filter(
                blocker_user=user,
                blocked_user=request.user
            ).exists()

        # 出品通知購読状態
        is_listing_notified = False
        if request.user.is_authenticated and request.user != user:
            is_listing_notified = ListingNotification.objects.filter(
                subscriber_user=request.user,
                target_user=user
            ).exists()

        # ユーザーの趣味（登録済みカテゴリ）を取得
        user_hobbies = UserHobby.objects.filter(
            user=user
        ).select_related('product_category').order_by('product_category_id')

        # レビュー関連データ
        review_qs = UserReview.objects.filter(reviewed_user=user)
        review_count = review_qs.count()
        review_avg_data = review_qs.aggregate(avg=Avg('review_score'))
        review_avg = review_avg_data['avg']  # None if no reviews

        # レビューソート
        sort_param = request.GET.get('sort', '-register_datetime')
        valid_sorts = ['-register_datetime', 'register_datetime', '-review_score', 'review_score']
        if sort_param not in valid_sorts:
            sort_param = '-register_datetime'

        reviews = review_qs.select_related(
            'reviewer_user', 'rental_history__product'
        ).order_by(sort_param)

        context = {
            'profile_user': user,
            'user_products': user_products,
            'user_products_count': user_products.count(),
            'bookmarked_products': bookmarked_products,
            'bookmarks_count': bookmarks_count,
            'identity_status': identity_status,
            'is_own_profile': request.user.is_authenticated and request.user == user,
            'follower_count': follower_count,
            'following_count': following_count,
            'is_following': is_following,
            'is_blocked': is_blocked,
            'is_blocked_by': is_blocked_by,
            'is_listing_notified': is_listing_notified,
            'user_hobbies': user_hobbies,
            'review_count': review_count,
            'review_avg': review_avg,
            'reviews': reviews,
            'review_sort': sort_param,
            'product_status_filter': product_status_filter,
            'product_sort': product_sort,
            'report_reasons': ReportReason.objects.all(),
        }

        return render(request, 'profile.html', context)


class ProfileSettingView(View):
    """プロフィール設定ページ（本人のみ）"""
    def get(self, request, username, *args, **kwargs):
        try:
            user = User.objects.get(user_name=username, user_status_id__in=[1, 2, 3])
        except User.DoesNotExist:
            messages.error(request, 'ユーザーが見つかりません。')
            return redirect('index')

        # 本人以外はプロフィール閲覧ページへリダイレクト
        if request.user != user:
            return redirect('profile', username=username)

        return render(request, 'profile_setting.html', {'profile_user': user})

    def post(self, request, username, *args, **kwargs):
        try:
            user = User.objects.get(user_name=username, user_status_id__in=[1, 2, 3])
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'ユーザーが見つかりません。'}, status=404)

        # 本人以外は更新不可
        if request.user != user:
            return JsonResponse({'success': False, 'message': '権限がありません。'}, status=403)

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # フォームデータ取得（multipart/form-data対応）
        display_name = request.POST.get('display_name', '').strip()
        bio = request.POST.get('bio', '').strip()
        user_image = request.FILES.get('user_image')

        errors = {}

        # バリデーション
        if not display_name:
            errors['display_name'] = '表示名は必須です'
        elif len(display_name) > 100:
            errors['display_name'] = '表示名は100文字以内で入力してください'

        if len(bio) > 160:
            errors['bio'] = '自己紹介は160文字以内で入力してください'

        if user_image:
            # 画像バリデーション（5MB以下、画像形式のみ）
            if user_image.size > 5 * 1024 * 1024:
                errors['user_image'] = '画像は5MB以下にしてください'
            if not user_image.content_type.startswith('image/'):
                errors['user_image'] = '画像ファイルを選択してください'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            return render(request, 'profile_setting.html', {
                'profile_user': user,
                'errors': errors
            })

        # 更新
        user.display_name = display_name
        user.bio = bio
        if user_image:
            user.user_image = user_image
        user.save()

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': 'プロフィールを更新しました',
                'data': {
                    'display_name': user.display_name,
                    'bio': user.bio,
                    'user_image': user.user_image.url if user.user_image else None
                }
            })

        messages.success(request, 'プロフィールを更新しました')
        return redirect('profile_setting', username=username)


# 出品ステータス定数（DBの値に合わせる）
PRODUCT_STATUS_LISTED = 1     # 貸出可能（出品中）
PRODUCT_STATUS_RENTING = 2    # 貸出中
PRODUCT_STATUS_PAUSED = 3     # 非公開
PRODUCT_STATUS_DELETED = 4    # 削除

# ユーザーステータス定数
USER_STATUS_UNVERIFIED = 1    # 未認証（本人確認未完了）
USER_STATUS_VERIFIED = 2      # 承認済み（本人確認完了）

# レンタルステータス定数（往復発送フロー対応）
RENTAL_STATUS_PREPARING = 1   # 発送準備中
RENTAL_STATUS_SHIPPING = 2    # 配送中（貸主→借り手）
RENTAL_STATUS_RENTING = 3     # レンタル中
RENTAL_STATUS_RETURNING = 4   # 返送中（借り手→貸主）
RENTAL_STATUS_COMPLETED = 5   # 返却済み（完了）
RENTAL_STATUS_CANCELLED = 6   # キャンセル
RENTAL_STATUS_RETURN_REQUESTED = 7  # 返品申請中
RENTAL_STATUS_RETURN_APPROVED = 8   # 返品承認済み
RENTAL_STATUS_RETURN_SHIPPING = 9   # 返品返送中
RENTAL_STATUS_CANCELLATION_REQUESTED = 10  # 中止申請中
RENTAL_STATUS_CANCELLATION_APPROVED = 11   # 中止済み


class VerificationRequiredView(View):
    """本人確認が必要なページ"""
    def get(self, request, *args, **kwargs):
        # コンテキストに応じてメッセージを変更
        context_type = request.GET.get('context', 'sell')
        product_id = request.GET.get('product_id', '')
        context = {
            'context_type': context_type,
            'product_id': product_id,
        }
        return render(request, 'verification_required.html', context)


class BankAccountRequiredView(View):
    """受取口座の登録が必要なページ"""
    def get(self, request, *args, **kwargs):
        next_url = request.GET.get('next', '')
        context_type = request.GET.get('context', 'sell')
        context = {
            'next_url': next_url,
            'context_type': context_type,
        }
        return render(request, 'bank_account_required.html', context)


class CreateSellView(View):
    """
    商品出品ページ

    アクセス条件:
    - ログイン必須
    - 本人確認完了（user_status_id = 2）必須
    """

    def get(self, request, *args, **kwargs):
        # ログインチェック
        if not request.user.is_authenticated:
            return redirect('/monotal/login/')

        # 本人確認チェック
        if request.user.user_status_id != USER_STATUS_VERIFIED:
            return redirect('verification_required')

        # 受取口座チェック
        if not BankAccount.objects.filter(user=request.user).exists():
            return redirect('bank_account_required')

        # マスターデータを取得
        categories = ProductCategory.objects.filter(
            parent_product_category__isnull=True
        ).prefetch_related('subcategories')
        conditions = ProductCondition.objects.all()
        prefectures = Prefecture.objects.all()
        shipping_days_list = ShippingDays.objects.all()
        shipping_burdens = ShippingBurden.objects.all()

        # ユーザーの登録住所を取得
        user_addresses = UserAddress.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('prefecture').order_by('-is_default', '-register_datetime')

        # デフォルト住所を取得
        default_address = user_addresses.filter(is_default=True).first()

        # ユーザーの受取口座を取得
        has_bank_account = BankAccount.objects.filter(user=request.user).exists()

        # 保険加入状態を取得
        has_insurance = InsuranceEnrollment.objects.filter(
            user=request.user,
            insurance_end_datetime__isnull=True
        ).exists()

        context = {
            'categories': categories,
            'conditions': conditions,
            'prefectures': prefectures,
            'shipping_days_list': shipping_days_list,
            'shipping_burdens': shipping_burdens,
            'user_addresses': user_addresses,
            'default_address': default_address,
            'has_bank_account': has_bank_account,
            'has_insurance': has_insurance,
        }

        return render(request, 'create_sell.html', context)

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # ログインチェック
        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'ログインが必要です',
                    'redirect_url': '/monotal/login/'
                }, status=401)
            return redirect('/monotal/login/')

        # 本人確認チェック
        if request.user.user_status_id != USER_STATUS_VERIFIED:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '本人確認が完了していません。本人確認を行ってください。',
                    'redirect_url': '/monotal/sell/verification-required/'
                }, status=403)
            return redirect('verification_required')

        # 受取口座チェック
        if not BankAccount.objects.filter(user=request.user).exists():
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '受取口座が登録されていません。口座を登録してください。',
                    'redirect_url': '/monotal/sell/bank-account-required/'
                }, status=403)
            return redirect('bank_account_required')

        try:
            # FormDataから取得
            product_name = request.POST.get('product_name', '').strip()
            product_category_id = request.POST.get('product_category', '')
            product_description = request.POST.get('product_description', '').strip()
            product_condition_id = request.POST.get('product_condition', '')
            shipping_days_id = request.POST.get('shipping_days', '')
            shipping_burden_id = request.POST.get('shipping_burden', '')

            # 住所情報（既存住所IDを使用）
            address_id = request.POST.get('address_id', '')

            # レンタルプラン
            rental_plans_json = request.POST.get('rental_plans', '[]')
            images = request.FILES.getlist('images')

            # rental_plansをパース
            try:
                rental_plans = json.loads(rental_plans_json)
            except json.JSONDecodeError:
                rental_plans = []

            errors = {}

            # ========================================
            # バリデーション
            # ========================================

            # 画像
            if not images:
                errors['images'] = '商品画像を1枚以上アップロードしてください'
            elif len(images) > 10:
                errors['images'] = '画像は最大10枚までです'

            # 商品名
            if not product_name:
                errors['product_name'] = '商品名は必須です'
            elif len(product_name) > 40:
                errors['product_name'] = '商品名は40文字以内で入力してください'

            # カテゴリー
            if not product_category_id:
                errors['product_category'] = 'カテゴリーを選択してください'

            # 商品の説明
            if not product_description:
                errors['product_description'] = '商品の説明は必須です'
            elif len(product_description) > 1000:
                errors['product_description'] = '商品の説明は1000文字以内で入力してください'

            # 商品の状態
            if not product_condition_id:
                errors['product_condition'] = '商品の状態を選択してください'

            # 発送までの日数
            if not shipping_days_id:
                errors['shipping_days'] = '発送までの日数を選択してください'

            # レンタルプランのバリデーション
            if not rental_plans or len(rental_plans) == 0:
                errors['rental_plans'] = '少なくとも1つのレンタルプランを設定してください'
            else:
                has_valid_plan = False
                for plan in rental_plans:
                    days = plan.get('days', 0)
                    price = plan.get('price', 0)

                    if days > 3650:
                        errors['rental_plans'] = '日数は3650日以下で設定してください'
                        break
                    elif price > 9999999:
                        errors['rental_plans'] = '金額は9,999,999円以下で設定してください'
                        break
                    elif days > 0 and price >= 100:
                        has_valid_plan = True
                    elif days > 0 and 0 < price < 100:
                        errors['rental_plans'] = '金額は100円以上で設定してください'
                        break

                if not has_valid_plan and 'rental_plans' not in errors:
                    errors['rental_plans'] = '日数と金額を正しく入力してください'

            # 住所バリデーション
            selected_address = None
            if address_id:
                try:
                    selected_address = UserAddress.objects.get(
                        user_address_id=address_id,
                        user=request.user
                    )
                except UserAddress.DoesNotExist:
                    errors['address'] = '選択された住所が見つかりません'
            else:
                errors['address'] = '発送元住所を選択してください'

            # 受取口座バリデーション
            if not BankAccount.objects.filter(user=request.user).exists():
                errors['bank_account'] = '受取口座を登録してください'

            if errors:
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': errors}, status=400)
                return render(request, 'create_sell.html', {
                    'errors': list(errors.values()),
                })

            # ========================================
            # マスターデータ取得
            # ========================================

            # カテゴリー
            category_obj = None
            if product_category_id:
                try:
                    category_obj = ProductCategory.objects.get(product_category_id=product_category_id)
                except ProductCategory.DoesNotExist:
                    pass

            # 商品状態
            condition_obj = None
            if product_condition_id:
                try:
                    condition_obj = ProductCondition.objects.get(product_condition_id=product_condition_id)
                except ProductCondition.DoesNotExist:
                    pass

            # 発送日数
            shipping_days_obj = None
            if shipping_days_id:
                try:
                    shipping_days_obj = ShippingDays.objects.get(shipping_days_id=shipping_days_id)
                except ShippingDays.DoesNotExist:
                    pass

            # 発送料負担
            shipping_burden_obj = None
            if shipping_burden_id:
                try:
                    shipping_burden_obj = ShippingBurden.objects.get(shipping_burden_id=shipping_burden_id)
                except ShippingBurden.DoesNotExist:
                    pass

            # 商品ステータス（貸出可能）
            try:
                status_obj = ProductStatus.objects.get(product_status_id=PRODUCT_STATUS_LISTED)
            except ProductStatus.DoesNotExist:
                status_obj = ProductStatus.objects.create(
                    product_status_id=PRODUCT_STATUS_LISTED,
                    status_name='貸出可能'
                )

            # ========================================
            # 商品作成（トランザクション使用）
            # ========================================

            # 最初のレンタルプランを取得（Productテーブル用）
            rental_days_value = 0
            rental_fee_value = 0
            for plan in rental_plans:
                if plan.get('days', 0) > 0 and plan.get('price', 0) >= 100:
                    rental_days_value = plan['days']
                    rental_fee_value = plan['price']
                    break

            # トランザクション開始
            with transaction.atomic():
                # 商品作成
                product = Product.objects.create(
                    product_name=product_name,
                    product_description=product_description or '',
                    shipping_days=shipping_days_obj,
                    shipping_burden=shipping_burden_obj,
                    product_condition=condition_obj,
                    product_status=status_obj,
                    product_category=category_obj,
                    rental_days=rental_days_value,
                    rental_fee=rental_fee_value,
                    user=request.user,
                    shipping_address=selected_address,
                    shipping_prefecture=selected_address.prefecture if selected_address else None
                )

                # 画像保存
                for index, image in enumerate(images):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        display_order=index
                    )

                # レンタルプラン保存
                for plan in rental_plans:
                    days = plan.get('days', 0)
                    price = plan.get('price', 0)
                    if days > 0 and price >= 100:
                        ProductRentalPlan.objects.create(
                            product=product,
                            rental_days=days,
                            rental_fee=price
                        )

                # 商品用チャットルーム作成
                chat_room_type, _ = ChatRoomType.objects.get_or_create(
                    chat_room_type_id=3,
                    defaults={'type_name': '商品チャット'}
                )
                ChatRoom.objects.create(
                    chat_room_type=chat_room_type,
                    product=product
                )

                # 選択された住所をデフォルトに設定
                if selected_address and not selected_address.is_default:
                    selected_address.is_default = True
                    selected_address.save()

            # 出品通知を購読者に送信
            subscribers = ListingNotification.objects.filter(
                target_user=request.user
            ).select_related('subscriber_user')
            if subscribers.exists():
                target_users = [s.subscriber_user for s in subscribers]
                create_notification(
                    notification_type_id=1,
                    title=f'{request.user.display_name}さんが新しい商品を出品しました',
                    detail=product.product_name,
                    link_url=f'/monotal/product/{product.product_id}/',
                    target_users=target_users
                )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '商品を出品しました',
                    'redirect_url': f'/monotal/product/{product.product_id}/'
                })

            messages.success(request, '商品を出品しました')
            return redirect('product_detail', product_id=product.product_id)

        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'エラーが発生しました: {str(e)}'}, status=500)
            return render(request, 'create_sell.html', {'errors': [f'エラーが発生しました: {str(e)}']})


class ProductListView(View):
    """
    商品一覧ページ
    フィルター機能付き
    """
    template_name = 'product_list.html'
    items_per_page = 20

    def get(self, request, *args, **kwargs):
        # 公開中の商品のみ取得（delete_datetimeがnullのもの、非公開・削除商品を除外）
        products = Product.objects.filter(
            delete_datetime__isnull=True
        ).exclude(
            product_status_id__in=[PRODUCT_STATUS_PAUSED, PRODUCT_STATUS_DELETED]  # 非公開(3)、削除(4)を除外
        ).select_related(
            'product_condition',
            'product_status',
            'product_category',
            'user'
        ).prefetch_related(
            'images'  # 商品画像も取得
        ).order_by('-register_datetime')

        # ログインユーザー自身の商品を除外
        if request.user.is_authenticated:
            products = products.exclude(user=request.user)

        # フィルター適用
        products = self.apply_filters(request, products)

        # ページネーション
        paginator = Paginator(products, self.items_per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # カテゴリ一覧（親カテゴリのみ、子カテゴリも取得）
        categories = ProductCategory.objects.filter(
            parent_product_category__isnull=True
        ).prefetch_related('subcategories')

        # 商品状態一覧
        conditions = ProductCondition.objects.all()

        context = {
            'products': page_obj,
            'categories': categories,
            'conditions': conditions,
            'page_obj': page_obj,
            'filters': self.get_active_filters(request),
        }

        return render(request, self.template_name, context)

    def apply_filters(self, request, queryset):
        """
        GETパラメータからフィルター適用
        """
        # カテゴリフィルター
        category_id = request.GET.get('category')
        if category_id:
            try:
                queryset = queryset.filter(
                    Q(product_category_id=int(category_id)) |
                    Q(product_category__parent_product_category_id=int(category_id))
                )
            except ValueError:
                pass

        # 価格フィルター（最小）- min_fee と min_price の両方に対応
        min_price = request.GET.get('min_price') or request.GET.get('min_fee')
        if min_price:
            try:
                queryset = queryset.filter(rental_plans__rental_fee__gte=int(min_price))
            except ValueError:
                pass

        # 価格フィルター（最大）- max_fee と max_price の両方に対応
        max_price = request.GET.get('max_price') or request.GET.get('max_fee')
        if max_price:
            try:
                queryset = queryset.filter(rental_plans__rental_fee__lte=int(max_price))
            except ValueError:
                pass

        # レンタル日数フィルター（最小）
        min_days = request.GET.get('min_days')
        if min_days:
            try:
                queryset = queryset.filter(rental_days__gte=int(min_days))
            except ValueError:
                pass

        # レンタル日数フィルター（最大）
        max_days = request.GET.get('max_days')
        if max_days:
            try:
                queryset = queryset.filter(rental_days__lte=int(max_days))
            except ValueError:
                pass

        # 商品状態フィルター
        conditions = request.GET.getlist('condition')
        if conditions:
            try:
                condition_ids = [int(c) for c in conditions]
                queryset = queryset.filter(product_condition_id__in=condition_ids)
            except ValueError:
                pass

        # テキスト検索（商品名、説明、カテゴリ名）
        search_query = request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(product_name__icontains=search_query) |
                Q(product_description__icontains=search_query) |
                Q(product_category__category_name__icontains=search_query)
            )

        return queryset

    def get_active_filters(self, request):
        """
        現在適用中のフィルター値を返す
        """
        return {
            'category': request.GET.get('category', ''),
            'min_fee': request.GET.get('min_price') or request.GET.get('min_fee', ''),
            'max_fee': request.GET.get('max_price') or request.GET.get('max_fee', ''),
            'min_price': request.GET.get('min_price') or request.GET.get('min_fee', ''),
            'max_price': request.GET.get('max_price') or request.GET.get('max_fee', ''),
            'min_days': request.GET.get('min_days', ''),
            'max_days': request.GET.get('max_days', ''),
            'conditions': request.GET.getlist('condition'),
            'q': request.GET.get('q', ''),
        }



class ProductDetailView(View):
    """
    商品詳細ページ
    """
    template_name = 'product_detail.html'

    def get(self, request, product_id, *args, **kwargs):
        try:
            # 商品を取得（削除されていないもの）
            product = Product.objects.select_related(
                'product_condition',
                'product_status',
                'product_category',
                'shipping_days',
                'shipping_burden',
                'shipping_prefecture',
                'user'
            ).prefetch_related(
                'images'  # 商品画像も一緒に取得
            ).get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            messages.error(request, '商品が見つかりません。')
            return redirect('product_list')

        # 非公開商品は出品者のみアクセス可能
        if product.product_status_id in (PRODUCT_STATUS_PAUSED, 4):
            if not request.user.is_authenticated or request.user != product.user:
                return render(request, 'product_unavailable.html')

        # 商品画像を取得
        product_images = list(product.images.all())

        # レンタルプランを取得（日数順）
        rental_plans = ProductRentalPlan.objects.filter(
            product=product
        ).order_by('rental_days')

        # 閲覧履歴を保存（ログインユーザーのみ、自分の商品は除外）
        if request.user.is_authenticated and product.user != request.user:
            # 既存の同一商品の閲覧履歴を削除して新規作成（最新日時に更新）
            BrowsingHistory.objects.filter(
                user=request.user,
                product=product
            ).delete()
            BrowsingHistory.objects.create(
                user=request.user,
                product=product
            )

        # ブックマーク情報を取得
        is_bookmarked = False
        if request.user.is_authenticated:
            is_bookmarked = Bookmark.objects.filter(
                user=request.user,
                product=product
            ).exists()

        # ブックマーク数を取得
        bookmark_count = Bookmark.objects.filter(product=product).count()

        # メッセージ数を取得
        message_count = 0
        try:
            chat_room = ChatRoom.objects.get(product=product)
            message_count = Message.objects.filter(chat_room=chat_room).count()
        except ChatRoom.DoesNotExist:
            pass

        # 現在のユーザーが出品者かどうか
        is_seller = request.user.is_authenticated and request.user == product.user

        # レンタル申請中または承認済みかチェック
        has_pending_request = False
        is_blocked_relation = False
        if request.user.is_authenticated and not is_seller:
            has_pending_request = RentalRequest.objects.filter(
                product=product,
                requester_user=request.user,
                rental_request_status_id__in=[RENTAL_REQUEST_STATUS_PENDING, RENTAL_REQUEST_STATUS_APPROVED]
            ).exists()
            # ブロック関係チェック（双方向）
            is_blocked_relation = Block.objects.filter(
                Q(blocker_user=request.user, blocked_user=product.user) |
                Q(blocker_user=product.user, blocked_user=request.user)
            ).exists()

        # 出品者のレビュー情報
        seller_review_qs = UserReview.objects.filter(reviewed_user=product.user)
        seller_review_count = seller_review_qs.count()
        seller_review_avg = seller_review_qs.aggregate(avg=Avg('review_score'))['avg']

        context = {
            'product': product,
            'product_images': product_images,
            'rental_plans': rental_plans,
            'is_bookmarked': is_bookmarked,
            'bookmark_count': bookmark_count,
            'message_count': message_count,
            'is_seller': is_seller,
            'has_pending_request': has_pending_request,
            'is_blocked_relation': is_blocked_relation,
            'seller_review_count': seller_review_count,
            'seller_review_avg': seller_review_avg,
        }

        return render(request, self.template_name, context)


class BookmarkToggleView(View):
    """
    ブックマーク（お気に入り）のトグルAPI
    POST: ブックマークを追加/削除
    """
    def post(self, request, product_id, *args, **kwargs):
        # ログインチェック
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'ログインが必要です'
            }, status=401)

        # 商品の存在確認
        try:
            product = Product.objects.get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '商品が見つかりません'
            }, status=404)

        # 自分の商品はブックマークできない
        if product.user == request.user:
            return JsonResponse({
                'success': False,
                'error': '自分の商品はブックマークできません'
            }, status=400)

        # ブックマークのトグル
        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:
            # 既に存在していた場合は削除
            bookmark.delete()
            is_bookmarked = False
        else:
            is_bookmarked = True

        # 最新のブックマーク数を取得
        bookmark_count = Bookmark.objects.filter(product=product).count()

        return JsonResponse({
            'success': True,
            'is_bookmarked': is_bookmarked,
            'bookmark_count': bookmark_count
        })


class ProductMessagesView(View):
    """
    商品のメッセージ一覧取得・送信API
    GET: メッセージ一覧を取得
    POST: 新規メッセージを送信
    """
    def get(self, request, product_id, *args, **kwargs):
        # 商品の存在確認
        try:
            product = Product.objects.get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '商品が見つかりません'
            }, status=404)

        # チャットルームを取得
        try:
            chat_room = ChatRoom.objects.get(product=product)
        except ChatRoom.DoesNotExist:
            # チャットルームがない場合は空のリストを返す
            return JsonResponse({
                'success': True,
                'messages': [],
                'total_count': 0
            })

        # メッセージを取得（古い順）
        messages_qs = Message.objects.filter(
            chat_room=chat_room
        ).select_related('user').order_by('register_datetime')

        # メッセージをシリアライズ
        messages_list = []
        for msg in messages_qs:
            messages_list.append({
                'message_id': msg.message_id,
                'user_id': msg.user.user_id,
                'user_name': msg.user.display_name or msg.user.user_name,
                'user_image': msg.user.user_image.url if msg.user.user_image else None,
                'content': msg.message_content,
                'created_at': msg.register_datetime.strftime('%Y-%m-%d %H:%M'),
                'is_owner': msg.user == product.user,
            })

        return JsonResponse({
            'success': True,
            'messages': messages_list,
            'total_count': len(messages_list)
        })

    def post(self, request, product_id, *args, **kwargs):
        # ログインチェック
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'ログインが必要です'
            }, status=401)

        # 商品の存在確認
        try:
            product = Product.objects.get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '商品が見つかりません'
            }, status=404)

        # チャットルームを取得または作成
        try:
            chat_room = ChatRoom.objects.get(product=product)
        except ChatRoom.DoesNotExist:
            # チャットルームがない場合は作成
            chat_room_type, _ = ChatRoomType.objects.get_or_create(
                chat_room_type_id=3,
                defaults={'type_name': '商品チャット'}
            )
            chat_room = ChatRoom.objects.create(
                chat_room_type=chat_room_type,
                product=product
            )

        # メッセージ内容を取得
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
        except json.JSONDecodeError:
            content = request.POST.get('content', '').strip()

        if not content:
            return JsonResponse({
                'success': False,
                'error': 'メッセージ内容を入力してください'
            }, status=400)

        if len(content) > 2000:
            return JsonResponse({
                'success': False,
                'error': 'メッセージは2000文字以内で入力してください'
            }, status=400)

        # メッセージを作成
        message = Message.objects.create(
            chat_room=chat_room,
            user=request.user,
            message_content=content
        )

        return JsonResponse({
            'success': True,
            'message': {
                'message_id': message.message_id,
                'user_id': request.user.user_id,
                'user_name': request.user.display_name or request.user.user_name,
                'user_image': request.user.user_image.url if request.user.user_image else None,
                'content': message.message_content,
                'created_at': message.register_datetime.strftime('%Y-%m-%d %H:%M'),
                'is_owner': request.user == product.user,
            }
        })


class ProductMessageDeleteView(LoginRequiredMixin, View):
    """
    商品コメント削除API（出品者のみ）
    DELETE: コメントを削除
    """
    login_url = '/monotal/login/'

    def delete(self, request, product_id, message_id, *args, **kwargs):
        # 商品の存在確認
        try:
            product = Product.objects.get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '商品が見つかりません'
            }, status=404)

        # 出品者かどうか確認
        if request.user != product.user:
            return JsonResponse({
                'success': False,
                'error': 'コメントを削除する権限がありません'
            }, status=403)

        # メッセージの存在確認
        try:
            chat_room = ChatRoom.objects.get(product=product)
            message = Message.objects.get(
                message_id=message_id,
                chat_room=chat_room
            )
        except (ChatRoom.DoesNotExist, Message.DoesNotExist):
            return JsonResponse({
                'success': False,
                'error': 'コメントが見つかりません'
            }, status=404)

        # メッセージを削除
        message.delete()

        # 残りのメッセージ数を取得
        remaining_count = Message.objects.filter(chat_room=chat_room).count()

        return JsonResponse({
            'success': True,
            'message_id': message_id,
            'remaining_count': remaining_count
        })

    def post(self, request, product_id, message_id, *args, **kwargs):
        # POSTでも削除を受け付ける（DELETEメソッドが使えない環境向け）
        return self.delete(request, product_id, message_id, *args, **kwargs)


class InterestSelectionView(LoginRequiredMixin, View):
    """
    趣味・興味のあるジャンル選択ページ
    GET: 親カテゴリ一覧を表示（既存選択をpre-select）
    POST: 選択されたカテゴリIDを保存
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        categories = ProductCategory.objects.filter(
            parent_product_category__isnull=True
        ).order_by('product_category_id')

        selected_ids = list(
            UserHobby.objects.filter(user=request.user)
            .values_list('product_category_id', flat=True)
        )

        return render(request, 'interest_selection.html', {
            'categories': categories,
            'selected_ids': selected_ids,
        })

    def post(self, request, *args, **kwargs):
        category_ids = request.POST.getlist('category_ids')
        UserHobby.objects.filter(user=request.user).delete()
        for cid in category_ids:
            UserHobby.objects.create(user=request.user, product_category_id=int(cid))

        next_url = request.GET.get('next', request.POST.get('next', ''))
        return redirect(next_url or 'mypage_browsing_history')


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  本人確認関連 / IDENTITY VERIFICATION                                         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# 本人確認ステータス定数
IDENTITY_STATUS_PENDING = 0   # 未確認（審査待ち）
IDENTITY_STATUS_APPROVED = 1  # 承認
IDENTITY_STATUS_REJECTED = 2  # 却下


class IdentityVerificationView(LoginRequiredMixin, View):
    """
    本人確認申請ページ（ユーザー向け）
    顔写真、身分証（表面）、身分証（裏面/厚み）の3枚をアップロード
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        context = {}

        # 既存の個人情報を取得（UserPersonalInfoから、なければ最新のIdentityVerificationから）
        try:
            personal_info = UserPersonalInfo.objects.get(user=request.user)
            context['personal_info'] = personal_info
        except UserPersonalInfo.DoesNotExist:
            # 最新の申請から個人情報を取得
            latest_verification = IdentityVerification.objects.filter(
                user=request.user
            ).order_by('-register_datetime').first()

            if latest_verification and latest_verification.last_name:
                # IdentityVerificationの個人情報をpersonal_infoとして渡す
                context['personal_info'] = latest_verification

        # ユーザーステータスで本人確認完了を判定（user_status_id=2が承認済み）
        if request.user.user_status_id == 2:
            context['existing_status'] = 1  # 承認済み表示
        else:
            # 申請中または却下の場合はIdentityVerificationを確認
            existing = IdentityVerification.objects.filter(
                user=request.user
            ).order_by('-register_datetime').first()

            if existing:
                context['existing_status'] = existing.identity_verification_status_id
                context['submitted_at'] = existing.register_datetime

        return render(request, 'identity_verification.html', context)

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # ユーザーステータスで本人確認完了を判定
        if request.user.user_status_id == 2:
            message = '既に本人確認が完了しています'
            if is_ajax:
                return JsonResponse({'success': False, 'message': message}, status=400)
            messages.error(request, message)
            return redirect('identity_verification')

        # 審査中の申請があるか確認
        existing = IdentityVerification.objects.filter(
            user=request.user,
            identity_verification_status_id=IDENTITY_STATUS_PENDING
        ).first()

        if existing:
            message = '現在審査中です。結果をお待ちください'

            if is_ajax:
                return JsonResponse({'success': False, 'message': message}, status=400)
            messages.error(request, message)
            return redirect('identity_verification')

        # 個人情報取得
        last_name = request.POST.get('last_name', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name_kana = request.POST.get('last_name_kana', '').strip()
        first_name_kana = request.POST.get('first_name_kana', '').strip()
        birth_date = request.POST.get('birth_date', '').strip()
        gender = request.POST.get('gender', '').strip()

        # 画像取得
        face_image = request.FILES.get('face_image')
        id_image = request.FILES.get('id_image')
        id_back_image = request.FILES.get('id_back_image')

        errors = {}

        # 個人情報バリデーション
        if not last_name:
            errors['last_name'] = '姓を入力してください'
        if not first_name:
            errors['first_name'] = '名を入力してください'
        if not birth_date:
            errors['birth_date'] = '生年月日を入力してください'
        if not gender:
            errors['gender'] = '性別を選択してください'

        # 画像バリデーション
        if not face_image:
            errors['face_image'] = '顔写真は必須です'
        elif face_image.size > 5 * 1024 * 1024:
            errors['face_image'] = '顔写真は5MB以下にしてください'
        elif not face_image.content_type.startswith('image/'):
            errors['face_image'] = '画像ファイルを選択してください'

        if not id_image:
            errors['id_image'] = '身分証明書（表面）は必須です'
        elif id_image.size > 5 * 1024 * 1024:
            errors['id_image'] = '身分証明書（表面）は5MB以下にしてください'
        elif not id_image.content_type.startswith('image/'):
            errors['id_image'] = '画像ファイルを選択してください'

        if not id_back_image:
            errors['id_back_image'] = '身分証明書（裏面/厚み）は必須です'
        elif id_back_image.size > 5 * 1024 * 1024:
            errors['id_back_image'] = '身分証明書（裏面/厚み）は5MB以下にしてください'
        elif not id_back_image.content_type.startswith('image/'):
            errors['id_back_image'] = '画像ファイルを選択してください'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            return render(request, 'identity_verification.html', {'errors': errors})

        try:
            # ステータス取得または作成
            try:
                pending_status = IdentityVerificationStatus.objects.get(
                    identity_verification_status_id=IDENTITY_STATUS_PENDING
                )
            except IdentityVerificationStatus.DoesNotExist:
                pending_status = IdentityVerificationStatus.objects.create(
                    identity_verification_status_id=IDENTITY_STATUS_PENDING,
                    status_name='未確認'
                )

            # トランザクション開始
            with transaction.atomic():
                # 個人情報を含めて本人確認レコード作成（承認時にUserPersonalInfoに移行）
                from datetime import datetime
                birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()

                verification = IdentityVerification.objects.create(
                    user=request.user,
                    identity_verification_status=pending_status,
                    last_name=last_name,
                    first_name=first_name,
                    last_name_kana=last_name_kana or None,
                    first_name_kana=first_name_kana or None,
                    birth_date=birth_date_obj,
                    gender=int(gender)
                )

                # 顔写真を保存
                IdentityVerificationImage.objects.create(
                    identity_verification=verification,
                    image_data=face_image.read()
                )

                # 身分証（表面）を保存
                IdentityVerificationImage.objects.create(
                    identity_verification=verification,
                    image_data=id_image.read()
                )

                # 身分証（裏面/厚み）を保存
                IdentityVerificationImage.objects.create(
                    identity_verification=verification,
                    image_data=id_back_image.read()
                )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '本人確認の申請が完了しました。審査結果をお待ちください。'
                })

            messages.success(request, '本人確認の申請が完了しました。審査結果をお待ちください。')
            return redirect('identity_verification')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('identity_verification')


class AdminVerificationListView(LoginRequiredMixin, View):
    """
    本人確認審査一覧ページ（管理者用）
    未確認の申請を古い順に表示
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # 管理者権限チェック
        if not request.user.is_staff:
            messages.error(request, '権限がありません')
            return redirect('index')

        # 未確認の申請を取得（古い順）
        verifications = IdentityVerification.objects.filter(
            identity_verification_status_id=IDENTITY_STATUS_PENDING
        ).select_related('user').order_by('register_datetime')

        # ページネーション
        paginator = Paginator(verifications, 20)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        context = {
            'verifications': page_obj,
            'total_count': verifications.count(),
            'page_obj': page_obj,
        }

        return render(request, 'admin/verification_list.html', context)


class AdminVerificationDetailView(LoginRequiredMixin, View):
    """
    本人確認審査詳細ページ（管理者用）
    画像確認と承認/却下処理
    """
    login_url = '/monotal/login/'

    def get(self, request, verification_id, *args, **kwargs):
        # 管理者権限チェック
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

        # 画像をBase64エンコード
        import base64
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

        return render(request, 'admin/verification_detail.html', context)

    def post(self, request, verification_id, *args, **kwargs):
        # 管理者権限チェック
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
                    # 承認ステータス取得または作成
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

                    # 個人情報をUserPersonalInfoに移行（作成または更新）
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

                    # ユーザーステータスを承認済み(2)に更新
                    try:
                        user_approved_status = UserStatus.objects.get(user_status_id=2)
                    except UserStatus.DoesNotExist:
                        user_approved_status = UserStatus.objects.create(
                            user_status_id=2,
                            status_name='承認済みユーザー'
                        )

                    verification.user.user_status = user_approved_status
                    verification.user.save()

                    # 承認通知を送信
                    create_notification(
                        notification_type_id=NOTIFICATION_TYPE_SYSTEM,
                        title='本人確認が完了しました',
                        detail='本人確認が承認されました。すべての機能をご利用いただけます。',
                        link_url='/monotal/mypage/listing/',
                        target_users=[verification.user]
                    )

                    message = '承認しました'

                elif action == 'reject':
                    # 却下ステータス取得または作成
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

                    # 却下通知を送信
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
    login_url = '/monotal/login/'

    def get(self, request, image_id, *args, **kwargs):
        # 管理者権限チェック
        if not request.user.is_staff:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()

        try:
            image = IdentityVerificationImage.objects.get(
                identity_verification_image_id=image_id
            )
            from django.http import HttpResponse
            return HttpResponse(image.image_data, content_type='image/jpeg')
        except IdentityVerificationImage.DoesNotExist:
            from django.http import HttpResponseNotFound
            return HttpResponseNotFound()


class FollowToggleView(View):
    """
    フォローのトグルAPI
    POST: フォローを追加/解除
    """
    def post(self, request, user_id, *args, **kwargs):
        # ログインチェック
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'ログインが必要です'
            }, status=401)

        # 対象ユーザーの存在確認
        try:
            target_user = User.objects.get(user_id=user_id, user_status_id__in=[1, 2, 3])
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'ユーザーが見つかりません'
            }, status=404)

        # 自分自身はフォローできない
        if request.user == target_user:
            return JsonResponse({
                'success': False,
                'error': '自分自身をフォローすることはできません'
            }, status=400)

        # ブロック関係がある場合はフォロー不可（双方向）
        if Block.objects.filter(
            Q(blocker_user=request.user, blocked_user=target_user) |
            Q(blocker_user=target_user, blocked_user=request.user)
        ).exists():
            return JsonResponse({
                'success': False,
                'error': 'ブロック関係があるためフォローできません'
            }, status=400)

        # フォロー状態をトグル
        existing_follow = Follow.objects.filter(
            follower_user=request.user,
            followed_user=target_user
        ).first()

        if existing_follow:
            # フォロー解除
            existing_follow.delete()
            is_following = False
        else:
            # フォロー追加
            Follow.objects.create(
                follower_user=request.user,
                followed_user=target_user
            )
            is_following = True

        # フォロワー数を取得
        follower_count = Follow.objects.filter(followed_user=target_user).count()

        return JsonResponse({
            'success': True,
            'is_following': is_following,
            'follower_count': follower_count
        })


class ListingNotificationToggleView(View):
    """
    出品通知購読のトグルAPI
    POST: 出品通知を追加/解除
    """
    def post(self, request, user_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'ログインが必要です'
            }, status=401)

        try:
            target_user = User.objects.get(user_id=user_id, user_status_id__in=[1, 2, 3])
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'ユーザーが見つかりません'
            }, status=404)

        if request.user == target_user:
            return JsonResponse({
                'success': False,
                'error': '自分自身の出品通知は設定できません'
            }, status=400)

        if Block.objects.filter(
            Q(blocker_user=request.user, blocked_user=target_user) |
            Q(blocker_user=target_user, blocked_user=request.user)
        ).exists():
            return JsonResponse({
                'success': False,
                'error': 'ブロック関係があるため設定できません'
            }, status=400)

        existing = ListingNotification.objects.filter(
            subscriber_user=request.user,
            target_user=target_user
        ).first()

        if existing:
            existing.delete()
            is_subscribed = False
        else:
            ListingNotification.objects.create(
                subscriber_user=request.user,
                target_user=target_user
            )
            is_subscribed = True

        return JsonResponse({
            'success': True,
            'is_subscribed': is_subscribed
        })


class BlockToggleView(View):
    """
    ブロックのトグルAPI
    POST: ブロックを追加/解除
    """
    def post(self, request, user_id, *args, **kwargs):
        # ログインチェック
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'ログインが必要です'
            }, status=401)

        # 対象ユーザーの存在確認
        try:
            target_user = User.objects.get(user_id=user_id, user_status_id__in=[1, 2, 3])
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'ユーザーが見つかりません'
            }, status=404)

        # 自分自身はブロックできない
        if request.user == target_user:
            return JsonResponse({
                'success': False,
                'error': '自分自身をブロックすることはできません'
            }, status=400)

        # ブロック状態をトグル
        existing_block = Block.objects.filter(
            blocker_user=request.user,
            blocked_user=target_user
        ).first()

        if existing_block:
            # ブロック解除
            existing_block.delete()
            is_blocked = False
        else:
            # ブロック追加
            Block.objects.create(
                blocker_user=request.user,
                blocked_user=target_user
            )
            is_blocked = True

            # ブロック時: 双方向のフォロー関係を削除
            Follow.objects.filter(
                follower_user=request.user,
                followed_user=target_user
            ).delete()
            Follow.objects.filter(
                follower_user=target_user,
                followed_user=request.user
            ).delete()

        # フォロワー数を取得（フォロー解除後の最新値）
        follower_count = Follow.objects.filter(followed_user=target_user).count()

        return JsonResponse({
            'success': True,
            'is_blocked': is_blocked,
            'follower_count': follower_count
        })


class ReportCreateView(View):
    """
    通報作成API
    POST: ユーザーを通報する
    """
    def post(self, request, user_id, *args, **kwargs):
        # ログインチェック
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'ログインが必要です'
            }, status=401)

        # 対象ユーザーの存在確認
        try:
            target_user = User.objects.get(user_id=user_id, user_status_id__in=[1, 2, 3])
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'ユーザーが見つかりません'
            }, status=404)

        # 自分自身は通報できない
        if request.user == target_user:
            return JsonResponse({
                'success': False,
                'error': '自分自身を通報することはできません'
            }, status=400)

        # リクエストデータ取得
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'リクエストが不正です'
            }, status=400)

        report_reason_id = data.get('report_reason_id')
        report_detail = data.get('report_detail', '').strip()

        # 通報理由の存在確認
        try:
            report_reason = ReportReason.objects.get(report_reason_id=report_reason_id)
        except ReportReason.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '通報理由を選択してください'
            }, status=400)

        # 通報を作成
        Report.objects.create(
            reporter_user=request.user,
            reported_user=target_user,
            report_reason=report_reason,
            report_detail=report_detail if report_detail else None,
            report_datetime=timezone.now()
        )

        return JsonResponse({'success': True})


class MyPageFollowListView(LoginRequiredMixin, View):
    """
    マイページ - フォローリスト
    ログインユーザーがフォローしているユーザー一覧を表示
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # フォローしているユーザーを取得
        following_users = User.objects.filter(
            followers__follower_user=request.user,
            user_status_id__in=[1, 2, 3]
        ).select_related('user_status').prefetch_related(
            'following',  # フォロワー数取得用
        ).order_by('-followers__register_datetime')

        # 各ユーザーの追加情報を取得
        following_list = []
        for user in following_users:
            # 出品数
            product_count = Product.objects.filter(
                user=user,
                delete_datetime__isnull=True
            ).count()
            # フォロワー数
            follower_count = Follow.objects.filter(followed_user=user).count()
            # 本人確認ステータス
            identity_status = None
            if user.user_status_id == 2:
                identity_status = 1
            else:
                latest_verification = IdentityVerification.objects.filter(
                    user=user
                ).order_by('-register_datetime').first()
                if latest_verification:
                    identity_status = latest_verification.identity_verification_status_id

            following_list.append({
                'user': user,
                'product_count': product_count,
                'follower_count': follower_count,
                'identity_status': identity_status,
            })

        # フォロー中の人数
        following_count = len(following_list)

        # ページネーション
        paginator = Paginator(following_list, 20)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        user_hobbies = UserHobby.objects.filter(
            user=request.user
        ).select_related('product_category').order_by('product_category_id')

        context = {
            'following_list': page_obj,
            'following_count': following_count,
            'page_obj': page_obj,
            'current_page': 'follow_list',
            'user_hobbies': user_hobbies,
        }

        return render(request, 'mypage/follow_list.html', context)


class MyPageBlockListView(LoginRequiredMixin, View):
    """
    マイページ - ブロックリスト
    ログインユーザーがブロックしているユーザー一覧を表示
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # ブロックしているユーザーを取得
        blocked_users = User.objects.filter(
            blocked_by__blocker_user=request.user,
            user_status_id__in=[1, 2, 3]
        ).order_by('-blocked_by__register_datetime')

        block_list = []
        for user in blocked_users:
            block_list.append({
                'user': user,
            })

        block_count = len(block_list)

        # ページネーション
        paginator = Paginator(block_list, 20)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        context = {
            'block_list': page_obj,
            'block_count': block_count,
            'page_obj': page_obj,
            'current_page': 'block_list',
        }

        return render(request, 'mypage/block_list.html', context)


class MyPageBookmarkListView(LoginRequiredMixin, View):
    """
    マイページ - ブックマーク一覧
    ログインユーザーがブックマークした商品一覧を表示
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # ブックマークした商品を取得
        bookmarked_products = Product.objects.filter(
            bookmark__user=request.user,
            delete_datetime__isnull=True
        ).select_related(
            'product_status',
            'product_category',
            'user'
        ).prefetch_related(
            'images'
        ).order_by('-bookmark__register_datetime')

        # ブックマーク数
        bookmark_count = bookmarked_products.count()

        # ページネーション
        paginator = Paginator(bookmarked_products, 20)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        user_hobbies = UserHobby.objects.filter(
            user=request.user
        ).select_related('product_category').order_by('product_category_id')

        context = {
            'bookmarked_products': page_obj,
            'bookmark_count': bookmark_count,
            'page_obj': page_obj,
            'current_page': 'bookmark_list',
            'user_hobbies': user_hobbies,
        }

        return render(request, 'mypage/bookmark_list.html', context)


class MyPageBrowsingHistoryView(LoginRequiredMixin, View):
    """
    マイページ - 閲覧履歴
    ログインユーザーの商品閲覧履歴を表示
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # 閲覧履歴を取得（最新順）
        browsing_history = BrowsingHistory.objects.filter(
            user=request.user,
            product__delete_datetime__isnull=True
        ).select_related(
            'product__product_status',
            'product__product_category',
            'product__user'
        ).prefetch_related(
            'product__images'
        ).order_by('-register_datetime')

        # 履歴数
        history_count = browsing_history.count()

        # ページネーション
        paginator = Paginator(browsing_history, 20)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        user_hobbies = UserHobby.objects.filter(
            user=request.user
        ).select_related('product_category').order_by('product_category_id')

        context = {
            'browsing_history': page_obj,
            'history_count': history_count,
            'page_obj': page_obj,
            'current_page': 'browsing_history',
            'user_hobbies': user_hobbies,
        }

        return render(request, 'mypage/browsing_history.html', context)


class MyPageListingView(LoginRequiredMixin, View):
    """
    マイページ - 出品一覧
    ログインユーザーが出品した商品一覧を表示
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # 出品した商品を取得（最新順）
        listing_products = Product.objects.filter(
            user=request.user,
            delete_datetime__isnull=True
        ).select_related(
            'product_status',
            'product_category'
        ).prefetch_related(
            'images'
        ).order_by('-register_datetime')

        # 出品数
        listing_count = listing_products.count()

        # ページネーション
        paginator = Paginator(listing_products, 20)
        page_obj = paginator.get_page(request.GET.get('page', 1))

        user_hobbies = UserHobby.objects.filter(
            user=request.user
        ).select_related('product_category').order_by('product_category_id')

        context = {
            'listing_products': page_obj,
            'listing_count': listing_count,
            'page_obj': page_obj,
            'current_page': 'listing',
            'user_hobbies': user_hobbies,
        }

        return render(request, 'mypage/listing.html', context)


class ProductEditView(LoginRequiredMixin, View):
    """
    商品編集ページ

    アクセス条件:
    - ログイン必須
    - 出品者本人のみアクセス可能
    """
    login_url = '/monotal/login/'

    def get(self, request, product_id, *args, **kwargs):
        # 商品を取得
        try:
            product = Product.objects.select_related(
                'product_condition',
                'product_status',
                'product_category',
                'shipping_days',
                'shipping_burden',
                'user'
            ).prefetch_related(
                'images',
                'rental_plans'
            ).get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            messages.error(request, '商品が見つかりません。')
            return redirect('product_list')

        # 出品者以外はアクセス拒否
        if request.user != product.user:
            messages.error(request, 'この商品を編集する権限がありません。')
            return redirect('product_detail', product_id=product_id)

        # 受取口座チェック
        if not BankAccount.objects.filter(user=request.user).exists():
            return redirect('bank_account_required')

        # マスターデータを取得
        categories = ProductCategory.objects.filter(
            parent_product_category__isnull=True
        ).prefetch_related('subcategories')
        conditions = ProductCondition.objects.all()
        prefectures = Prefecture.objects.all()
        shipping_days_list = ShippingDays.objects.all()
        shipping_burdens = ShippingBurden.objects.all()
        product_statuses = ProductStatus.objects.all()

        # レンタルプランを取得
        rental_plans = ProductRentalPlan.objects.filter(
            product=product
        ).order_by('rental_days')

        # ユーザーの登録住所を取得
        user_addresses = UserAddress.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('prefecture').order_by('-is_default', '-register_datetime')

        # デフォルト住所を取得
        default_address = user_addresses.filter(is_default=True).first()

        # ユーザーの受取口座を取得
        has_bank_account = BankAccount.objects.filter(user=request.user).exists()

        context = {
            'product': product,
            'product_images': list(product.images.all()),
            'rental_plans': list(rental_plans),
            'categories': categories,
            'conditions': conditions,
            'prefectures': prefectures,
            'shipping_days_list': shipping_days_list,
            'shipping_burdens': shipping_burdens,
            'product_statuses': product_statuses,
            'user_addresses': user_addresses,
            'default_address': default_address,
            'has_bank_account': has_bank_account,
        }

        return render(request, 'product_edit.html', context)

    def post(self, request, product_id, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # 商品を取得
        try:
            product = Product.objects.select_related('user').get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '商品が見つかりません'
                }, status=404)
            messages.error(request, '商品が見つかりません。')
            return redirect('product_list')

        # 出品者以外はアクセス拒否
        if request.user != product.user:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'この商品を編集する権限がありません'
                }, status=403)
            messages.error(request, 'この商品を編集する権限がありません。')
            return redirect('product_detail', product_id=product_id)

        # 受取口座チェック
        if not BankAccount.objects.filter(user=request.user).exists():
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '受取口座が登録されていません。口座を登録してください。',
                    'redirect_url': '/monotal/sell/bank-account-required/'
                }, status=403)
            return redirect('bank_account_required')

        try:
            # 編集可能項目のみ取得
            product_name = request.POST.get('product_name', '').strip()
            product_category_id = request.POST.get('product_category', '')
            product_description = request.POST.get('product_description', '').strip()
            product_condition_id = request.POST.get('product_condition', '')
            new_images = request.FILES.getlist('images')
            delete_image_ids_json = request.POST.get('delete_image_ids', '[]')

            try:
                delete_image_ids = json.loads(delete_image_ids_json)
            except json.JSONDecodeError:
                delete_image_ids = []

            errors = {}

            # ========================================
            # バリデーション
            # ========================================

            # 商品名
            if not product_name:
                errors['product_name'] = '商品名は必須です'
            elif len(product_name) > 40:
                errors['product_name'] = '商品名は40文字以内で入力してください'

            # カテゴリー
            category_obj = None
            if not product_category_id:
                errors['product_category'] = 'カテゴリーを選択してください'
            else:
                try:
                    category_obj = ProductCategory.objects.get(product_category_id=product_category_id)
                except ProductCategory.DoesNotExist:
                    errors['product_category'] = '選択されたカテゴリーが存在しません'

            # 商品の説明
            if not product_description:
                errors['product_description'] = '商品の説明は必須です'
            elif len(product_description) > 1000:
                errors['product_description'] = '商品の説明は1000文字以内で入力してください'

            # 商品の状態
            condition_obj = None
            if not product_condition_id:
                errors['product_condition'] = '商品の状態を選択してください'
            else:
                try:
                    condition_obj = ProductCondition.objects.get(product_condition_id=product_condition_id)
                except ProductCondition.DoesNotExist:
                    errors['product_condition'] = '選択された商品の状態が存在しません'

            # 画像チェック（既存 - 削除 + 新規 >= 1）
            current_image_count = ProductImage.objects.filter(product=product).count()
            remaining_count = current_image_count - len(delete_image_ids) + len(new_images)
            if remaining_count < 1:
                errors['images'] = '商品画像は1枚以上必要です'
            elif remaining_count > 10:
                errors['images'] = '商品画像は10枚までです'

            if errors:
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': errors}, status=400)
                messages.error(request, 'エラーがあります。入力内容を確認してください。')
                return redirect('product_edit', product_id=product_id)

            # ========================================
            # 更新（トランザクション使用）
            # ========================================

            with transaction.atomic():
                product.product_name = product_name
                product.product_description = product_description
                product.product_category = category_obj
                product.product_condition = condition_obj
                product.save()

                # 削除対象の画像を削除
                if delete_image_ids:
                    ProductImage.objects.filter(
                        product_image_id__in=delete_image_ids,
                        product=product
                    ).delete()

                # 新しい画像を追加
                max_order = ProductImage.objects.filter(product=product).count()
                for index, image in enumerate(new_images):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        display_order=max_order + index
                    )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '商品を更新しました',
                    'redirect_url': f'/monotal/product/{product_id}/'
                })

            messages.success(request, '商品を更新しました')
            return redirect('product_detail', product_id=product_id)

        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'エラーが発生しました: {str(e)}'}, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('product_edit', product_id=product_id)


index = IndexView.as_view()
login_view = LoginView.as_view()
logout_view = LogoutView.as_view()
register = RegisterView.as_view()
register_form = RegisterFormView.as_view()
register_complete = RegisterCompleteView.as_view()
register_sent = RegisterSentView.as_view()
email_verify = EmailVerifyView.as_view()
register_done = RegisterDoneView.as_view()
profile = ProfileView.as_view()
profile_setting = ProfileSettingView.as_view()
create_sell = CreateSellView.as_view()
verification_required = VerificationRequiredView.as_view()
bank_account_required = BankAccountRequiredView.as_view()
product_list = ProductListView.as_view()
product_detail = ProductDetailView.as_view()
bookmark_toggle = BookmarkToggleView.as_view()
product_messages = ProductMessagesView.as_view()
product_message_delete = ProductMessageDeleteView.as_view()
interest_selection = InterestSelectionView.as_view()
terms_of_service = TermsOfServiceView.as_view()
privacy_policy = PrivacyPolicyView.as_view()

# 本人確認関連
identity_verification = IdentityVerificationView.as_view()
admin_verification_list = AdminVerificationListView.as_view()
admin_verification_detail = AdminVerificationDetailView.as_view()
verification_image = VerificationImageView.as_view()

# フォロー関連
follow_toggle = FollowToggleView.as_view()
mypage_follow_list = MyPageFollowListView.as_view()

# 出品通知購読関連
listing_notification_toggle = ListingNotificationToggleView.as_view()

# ブロック関連
block_toggle = BlockToggleView.as_view()
mypage_block_list = MyPageBlockListView.as_view()

# 通報関連
report_create = ReportCreateView.as_view()

# マイページ関連
mypage_bookmark_list = MyPageBookmarkListView.as_view()
mypage_browsing_history = MyPageBrowsingHistoryView.as_view()
mypage_listing = MyPageListingView.as_view()

# 商品編集
product_edit = ProductEditView.as_view()


# 住所管理定数
MAX_USER_ADDRESSES = 3

# 銀行口座管理定数
MAX_BANK_ACCOUNTS = 1


class MyPageAddressListView(LoginRequiredMixin, View):
    """
    マイページ - 住所管理
    住所一覧表示、新規登録（POST、最大3件制限）
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # ユーザーの住所を取得
        user_addresses = UserAddress.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('prefecture').order_by('-is_default', '-register_datetime')

        # 都道府県リスト
        prefectures = Prefecture.objects.all()

        user_hobbies = UserHobby.objects.filter(
            user=request.user
        ).select_related('product_category').order_by('product_category_id')

        context = {
            'user_addresses': user_addresses,
            'address_count': user_addresses.count(),
            'max_addresses': MAX_USER_ADDRESSES,
            'can_add_address': user_addresses.count() < MAX_USER_ADDRESSES,
            'prefectures': prefectures,
            'current_page': 'address_list',
            'user_hobbies': user_hobbies,
        }

        return render(request, 'mypage/address_list.html', context)

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # 住所数チェック
        current_count = UserAddress.objects.filter(user=request.user, is_deleted=False).count()
        if current_count >= MAX_USER_ADDRESSES:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'住所は最大{MAX_USER_ADDRESSES}件までです'
                }, status=400)
            messages.error(request, f'住所は最大{MAX_USER_ADDRESSES}件までです')
            return redirect('mypage_address_list')

        # フォームデータ取得
        postal_code = request.POST.get('postal_code', '').strip().replace('-', '')
        prefecture_id = request.POST.get('prefecture', '')
        city = request.POST.get('city', '').strip()
        street_address = request.POST.get('street_address', '').strip()

        errors = {}

        # バリデーション
        if not postal_code or len(postal_code) != 7:
            errors['postal_code'] = '郵便番号は7桁で入力してください'
        if not prefecture_id:
            errors['prefecture'] = '都道府県を選択してください'
        if not city:
            errors['city'] = '市区町村・町域は必須です'
        if not street_address:
            errors['street_address'] = '番地・建物名は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            for msg in errors.values():
                messages.error(request, msg)
            return redirect('mypage_address_list')

        try:
            prefecture_obj = Prefecture.objects.get(prefecture_id=prefecture_id)

            # 最初の住所の場合はデフォルトに設定
            is_first_address = current_count == 0

            address = UserAddress.objects.create(
                user=request.user,
                postal_code=postal_code,
                prefecture=prefecture_obj,
                city=city,
                street_address=street_address,
                is_default=is_first_address
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '住所を追加しました',
                    'address': {
                        'id': address.user_address_id,
                        'postal_code': address.postal_code,
                        'prefecture': prefecture_obj.prefecture_name,
                        'city': address.city,
                        'street_address': address.street_address,
                        'is_default': address.is_default,
                        'full_address': address.full_address,
                    }
                })

            messages.success(request, '住所を追加しました')
            return redirect('mypage_address_list')

        except Prefecture.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '都道府県が無効です'
                }, status=400)
            messages.error(request, '都道府県が無効です')
            return redirect('mypage_address_list')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('mypage_address_list')


class AddressDeleteView(LoginRequiredMixin, View):
    """
    住所削除API
    """
    login_url = '/monotal/login/'

    def post(self, request, address_id, *args, **kwargs):
        try:
            address = UserAddress.objects.get(
                user_address_id=address_id,
                user=request.user
            )

            was_default = address.is_default
            address.is_deleted = True
            address.is_default = False
            address.save()

            # デフォルト住所を削除した場合、残りの最初の住所をデフォルトに
            if was_default:
                remaining = UserAddress.objects.filter(
                    user=request.user, is_deleted=False
                ).first()
                if remaining:
                    remaining.is_default = True
                    remaining.save()

            return JsonResponse({
                'success': True,
                'message': '住所を削除しました'
            })

        except UserAddress.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '住所が見つかりません'
            }, status=404)


class AddressEditView(LoginRequiredMixin, View):
    """
    住所編集API
    """
    login_url = '/monotal/login/'

    def post(self, request, address_id, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            address = UserAddress.objects.get(
                user_address_id=address_id,
                user=request.user
            )
        except UserAddress.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '住所が見つかりません'
                }, status=404)
            messages.error(request, '住所が見つかりません')
            return redirect('mypage_address_list')

        # フォームデータ取得
        postal_code = request.POST.get('postal_code', '').strip().replace('-', '')
        prefecture_id = request.POST.get('prefecture', '')
        city = request.POST.get('city', '').strip()
        street_address = request.POST.get('street_address', '').strip()

        errors = {}

        # バリデーション
        if not postal_code or len(postal_code) != 7:
            errors['postal_code'] = '郵便番号は7桁で入力してください'
        if not prefecture_id:
            errors['prefecture'] = '都道府県を選択してください'
        if not city:
            errors['city'] = '市区町村・町域は必須です'
        if not street_address:
            errors['street_address'] = '番地・建物名は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            for msg in errors.values():
                messages.error(request, msg)
            return redirect('mypage_address_list')

        try:
            prefecture_obj = Prefecture.objects.get(prefecture_id=prefecture_id)

            # 住所を更新
            address.postal_code = postal_code
            address.prefecture = prefecture_obj
            address.city = city
            address.street_address = street_address
            address.save()

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '住所を更新しました',
                    'address': {
                        'id': address.user_address_id,
                        'postal_code': address.postal_code,
                        'prefecture_id': prefecture_obj.prefecture_id,
                        'prefecture': prefecture_obj.prefecture_name,
                        'city': address.city,
                        'street_address': address.street_address,
                        'is_default': address.is_default,
                    }
                })

            messages.success(request, '住所を更新しました')
            return redirect('mypage_address_list')

        except Prefecture.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '都道府県が見つかりません'
                }, status=400)
            messages.error(request, '都道府県が見つかりません')
            return redirect('mypage_address_list')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('mypage_address_list')


# 住所管理関連
mypage_address_list = MyPageAddressListView.as_view()
address_edit = AddressEditView.as_view()
address_delete = AddressDeleteView.as_view()


class MyPageBankAccountListView(LoginRequiredMixin, View):
    """
    マイページ - 銀行口座管理
    口座一覧表示、新規登録（POST、最大3件制限）
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # ユーザーの銀行口座を取得
        bank_accounts = BankAccount.objects.filter(
            user=request.user
        ).order_by('-is_default', '-register_datetime')

        context = {
            'bank_accounts': bank_accounts,
            'account_count': bank_accounts.count(),
            'max_accounts': MAX_BANK_ACCOUNTS,
            'can_add_account': bank_accounts.count() < MAX_BANK_ACCOUNTS,
            'current_page': 'bank_account_list',
        }

        return render(request, 'mypage/bank_account_list.html', context)

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # 口座数チェック
        current_count = BankAccount.objects.filter(user=request.user).count()
        if current_count >= MAX_BANK_ACCOUNTS:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'口座は最大{MAX_BANK_ACCOUNTS}件までです'
                }, status=400)
            messages.error(request, f'口座は最大{MAX_BANK_ACCOUNTS}件までです')
            return redirect('mypage_bank_account_list')

        # フォームデータ取得
        bank_name = request.POST.get('bank_name', '').strip()
        branch_name = request.POST.get('branch_name', '').strip()
        account_type = request.POST.get('account_type', '1')
        account_number = request.POST.get('account_number', '').strip()
        account_holder = request.POST.get('account_holder', '').strip()

        errors = {}

        # バリデーション
        if not bank_name:
            errors['bank_name'] = '銀行名は必須です'
        if not branch_name:
            errors['branch_name'] = '支店名は必須です'
        if not account_number:
            errors['account_number'] = '口座番号は必須です'
        elif not account_number.isdigit():
            errors['account_number'] = '口座番号は数字のみ入力してください'
        if not account_holder:
            errors['account_holder'] = '口座名義は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            for msg in errors.values():
                messages.error(request, msg)
            return redirect('mypage_bank_account_list')

        try:
            # 最初の口座の場合はデフォルトに設定
            is_first_account = current_count == 0

            account = BankAccount.objects.create(
                user=request.user,
                bank_name=bank_name,
                branch_name=branch_name,
                account_type=int(account_type),
                account_number=account_number,
                account_holder=account_holder,
                is_default=is_first_account
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '口座を追加しました',
                    'account': {
                        'id': account.bank_account_id,
                        'bank_name': account.bank_name,
                        'branch_name': account.branch_name,
                        'account_type': account.account_type,
                        'account_type_display': account.account_type_display,
                        'account_number': account.masked_account_number,
                        'account_holder': account.account_holder,
                        'is_default': account.is_default,
                    }
                })

            messages.success(request, '口座を追加しました')
            return redirect('mypage_bank_account_list')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('mypage_bank_account_list')


class BankAccountEditView(LoginRequiredMixin, View):
    """
    銀行口座編集API
    """
    login_url = '/monotal/login/'

    def post(self, request, bank_account_id, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            account = BankAccount.objects.get(
                bank_account_id=bank_account_id,
                user=request.user
            )
        except BankAccount.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '口座が見つかりません'
                }, status=404)
            messages.error(request, '口座が見つかりません')
            return redirect('mypage_bank_account_list')

        # フォームデータ取得
        bank_name = request.POST.get('bank_name', '').strip()
        branch_name = request.POST.get('branch_name', '').strip()
        account_type = request.POST.get('account_type', '1')
        account_number = request.POST.get('account_number', '').strip()
        account_holder = request.POST.get('account_holder', '').strip()

        errors = {}

        # バリデーション
        if not bank_name:
            errors['bank_name'] = '銀行名は必須です'
        if not branch_name:
            errors['branch_name'] = '支店名は必須です'
        if not account_number:
            errors['account_number'] = '口座番号は必須です'
        elif not account_number.isdigit():
            errors['account_number'] = '口座番号は数字のみ入力してください'
        if not account_holder:
            errors['account_holder'] = '口座名義は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            for msg in errors.values():
                messages.error(request, msg)
            return redirect('mypage_bank_account_list')

        try:
            # 口座を更新
            account.bank_name = bank_name
            account.branch_name = branch_name
            account.account_type = int(account_type)
            account.account_number = account_number
            account.account_holder = account_holder
            account.save()

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '口座を更新しました',
                    'account': {
                        'id': account.bank_account_id,
                        'bank_name': account.bank_name,
                        'branch_name': account.branch_name,
                        'account_type': account.account_type,
                        'account_type_display': account.account_type_display,
                        'account_number': account.masked_account_number,
                        'account_holder': account.account_holder,
                        'is_default': account.is_default,
                    }
                })

            messages.success(request, '口座を更新しました')
            return redirect('mypage_bank_account_list')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('mypage_bank_account_list')


class BankAccountDeleteView(LoginRequiredMixin, View):
    """
    銀行口座削除API
    """
    login_url = '/monotal/login/'

    def post(self, request, bank_account_id, *args, **kwargs):
        try:
            account = BankAccount.objects.get(
                bank_account_id=bank_account_id,
                user=request.user
            )

            # 最後の1件を削除する場合、警告メッセージを追加
            is_last_account = BankAccount.objects.filter(user=request.user).count() == 1

            was_default = account.is_default
            account.delete()

            # デフォルト口座を削除した場合、残りの最初の口座をデフォルトに
            if was_default:
                remaining = BankAccount.objects.filter(user=request.user).first()
                if remaining:
                    remaining.is_default = True
                    remaining.save()

            message = '口座を削除しました'
            if is_last_account:
                message = '口座を削除しました。出品するには受取口座の登録が必要です。'

            return JsonResponse({
                'success': True,
                'message': message
            })

        except BankAccount.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '口座が見つかりません'
            }, status=404)


# 銀行口座管理関連
mypage_bank_account_list = MyPageBankAccountListView.as_view()
bank_account_edit = BankAccountEditView.as_view()
bank_account_delete = BankAccountDeleteView.as_view()


# クレジットカード管理定数
MAX_CREDIT_CARDS = 3


class MyPageCreditCardListView(LoginRequiredMixin, View):
    """
    マイページ - クレジットカード管理
    カード一覧表示、新規登録（POST、最大3件制限）
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # ユーザーのクレジットカードを取得
        credit_cards = CreditCard.objects.filter(
            user=request.user
        ).order_by('-is_default', '-register_datetime')

        context = {
            'credit_cards': credit_cards,
            'card_count': credit_cards.count(),
            'max_cards': MAX_CREDIT_CARDS,
            'can_add_card': credit_cards.count() < MAX_CREDIT_CARDS,
            'current_page': 'credit_card_list',
        }

        return render(request, 'mypage/credit_card_list.html', context)

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # カード数チェック
        current_count = CreditCard.objects.filter(user=request.user).count()
        if current_count >= MAX_CREDIT_CARDS:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'カードは最大{MAX_CREDIT_CARDS}件までです'
                }, status=400)
            messages.error(request, f'カードは最大{MAX_CREDIT_CARDS}件までです')
            return redirect('mypage_credit_card_list')

        # フォームデータ取得
        card_number = request.POST.get('card_number', '').replace(' ', '').replace('-', '')
        expiry_month = request.POST.get('expiry_month', '').strip()
        expiry_year = request.POST.get('expiry_year', '').strip()
        card_holder_name = request.POST.get('card_holder_name', '').strip()

        errors = {}

        # バリデーション
        if not card_number:
            errors['card_number'] = 'カード番号は必須です'
        elif not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
            errors['card_number'] = 'カード番号が正しくありません'

        if not expiry_month:
            errors['expiry_month'] = '有効期限（月）は必須です'
        elif not expiry_month.isdigit() or int(expiry_month) < 1 or int(expiry_month) > 12:
            errors['expiry_month'] = '有効期限（月）が正しくありません'

        if not expiry_year:
            errors['expiry_year'] = '有効期限（年）は必須です'
        elif not expiry_year.isdigit() or len(expiry_year) != 4:
            errors['expiry_year'] = '有効期限（年）は4桁で入力してください'

        if not card_holder_name:
            errors['card_holder_name'] = 'カード名義人は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            for msg in errors.values():
                messages.error(request, msg)
            return redirect('mypage_credit_card_list')

        try:
            # 最初のカードの場合はデフォルトに設定
            is_first_card = current_count == 0

            card = CreditCard.objects.create(
                user=request.user,
                card_number_last4=card_number[-4:],
                expiry_month=int(expiry_month),
                expiry_year=int(expiry_year),
                card_holder_name=card_holder_name,
                is_default=is_first_card
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'カードを追加しました',
                    'card': {
                        'id': card.credit_card_id,
                        'masked_card_number': card.masked_card_number,
                        'expiry_display': card.expiry_display,
                        'card_holder_name': card.card_holder_name,
                        'is_default': card.is_default,
                    }
                })

            messages.success(request, 'カードを追加しました')
            return redirect('mypage_credit_card_list')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('mypage_credit_card_list')


class CreditCardEditView(LoginRequiredMixin, View):
    """
    クレジットカード編集API
    """
    login_url = '/monotal/login/'

    def post(self, request, credit_card_id, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            card = CreditCard.objects.get(
                credit_card_id=credit_card_id,
                user=request.user
            )
        except CreditCard.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'カードが見つかりません'
                }, status=404)
            messages.error(request, 'カードが見つかりません')
            return redirect('mypage_credit_card_list')

        # フォームデータ取得
        card_number = request.POST.get('card_number', '').replace(' ', '').replace('-', '')
        expiry_month = request.POST.get('expiry_month', '').strip()
        expiry_year = request.POST.get('expiry_year', '').strip()
        card_holder_name = request.POST.get('card_holder_name', '').strip()

        errors = {}

        # バリデーション
        if not card_number:
            errors['card_number'] = 'カード番号は必須です'
        elif not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
            errors['card_number'] = 'カード番号が正しくありません'

        if not expiry_month:
            errors['expiry_month'] = '有効期限（月）は必須です'
        elif not expiry_month.isdigit() or int(expiry_month) < 1 or int(expiry_month) > 12:
            errors['expiry_month'] = '有効期限（月）が正しくありません'

        if not expiry_year:
            errors['expiry_year'] = '有効期限（年）は必須です'
        elif not expiry_year.isdigit() or len(expiry_year) != 4:
            errors['expiry_year'] = '有効期限（年）は4桁で入力してください'

        if not card_holder_name:
            errors['card_holder_name'] = 'カード名義人は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            for msg in errors.values():
                messages.error(request, msg)
            return redirect('mypage_credit_card_list')

        try:
            # カードを更新
            card.card_number_last4 = card_number[-4:]
            card.expiry_month = int(expiry_month)
            card.expiry_year = int(expiry_year)
            card.card_holder_name = card_holder_name
            card.save()

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'カードを更新しました',
                    'card': {
                        'id': card.credit_card_id,
                        'masked_card_number': card.masked_card_number,
                        'expiry_display': card.expiry_display,
                        'card_holder_name': card.card_holder_name,
                        'is_default': card.is_default,
                    }
                })

            messages.success(request, 'カードを更新しました')
            return redirect('mypage_credit_card_list')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('mypage_credit_card_list')


class CreditCardDeleteView(LoginRequiredMixin, View):
    """
    クレジットカード削除API
    """
    login_url = '/monotal/login/'

    def post(self, request, credit_card_id, *args, **kwargs):
        try:
            card = CreditCard.objects.get(
                credit_card_id=credit_card_id,
                user=request.user
            )

            was_default = card.is_default
            card.delete()

            # デフォルトカードを削除した場合、残りの最初のカードをデフォルトに
            if was_default:
                remaining = CreditCard.objects.filter(user=request.user).first()
                if remaining:
                    remaining.is_default = True
                    remaining.save()

            return JsonResponse({
                'success': True,
                'message': 'カードを削除しました'
            })

        except CreditCard.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'カードが見つかりません'
            }, status=404)


# クレジットカード管理関連
mypage_credit_card_list = MyPageCreditCardListView.as_view()
credit_card_edit = CreditCardEditView.as_view()
credit_card_delete = CreditCardDeleteView.as_view()


class SellAddressManageView(LoginRequiredMixin, View):
    """
    出品ページ用 - 住所管理
    戻るボタンで出品ページに戻る
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        user_addresses = UserAddress.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('prefecture').order_by('-is_default', '-register_datetime')

        prefectures = Prefecture.objects.all()

        context = {
            'user_addresses': user_addresses,
            'address_count': user_addresses.count(),
            'max_addresses': MAX_USER_ADDRESSES,
            'can_add_address': user_addresses.count() < MAX_USER_ADDRESSES,
            'prefectures': prefectures,
            'back_url': reverse('create_sell'),
            'page_title': '発送元住所の管理',
        }

        return render(request, 'sell_address_manage.html', context)

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        current_count = UserAddress.objects.filter(user=request.user, is_deleted=False).count()
        if current_count >= MAX_USER_ADDRESSES:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'住所は最大{MAX_USER_ADDRESSES}件までです'
                }, status=400)
            return redirect('sell_address_manage')

        postal_code = request.POST.get('postal_code', '').strip().replace('-', '')
        prefecture_id = request.POST.get('prefecture', '')
        city = request.POST.get('city', '').strip()
        street_address = request.POST.get('street_address', '').strip()

        errors = {}

        if not postal_code or len(postal_code) != 7:
            errors['postal_code'] = '郵便番号は7桁で入力してください'
        if not prefecture_id:
            errors['prefecture'] = '都道府県を選択してください'
        if not city:
            errors['city'] = '市区町村・町域は必須です'
        if not street_address:
            errors['street_address'] = '番地・建物名は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            return redirect('sell_address_manage')

        try:
            prefecture_obj = Prefecture.objects.get(prefecture_id=prefecture_id)
            is_first_address = current_count == 0

            address = UserAddress.objects.create(
                user=request.user,
                postal_code=postal_code,
                prefecture=prefecture_obj,
                city=city,
                street_address=street_address,
                is_default=is_first_address
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '住所を追加しました',
                    'address': {
                        'id': address.user_address_id,
                        'postal_code': address.postal_code,
                        'prefecture': prefecture_obj.prefecture_name,
                        'city': address.city,
                        'street_address': address.street_address,
                        'is_default': address.is_default,
                    }
                })

            return redirect('sell_address_manage')

        except Prefecture.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '都道府県が無効です'
                }, status=400)
            return redirect('sell_address_manage')


class EditAddressManageView(LoginRequiredMixin, View):
    """
    商品編集ページ用 - 住所管理
    戻るボタンで編集ページに戻る
    """
    login_url = '/monotal/login/'

    def get(self, request, product_id, *args, **kwargs):
        # 商品が存在し、所有者であることを確認
        product = get_object_or_404(Product, product_id=product_id, user=request.user)

        user_addresses = UserAddress.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('prefecture').order_by('-is_default', '-register_datetime')

        prefectures = Prefecture.objects.all()

        context = {
            'user_addresses': user_addresses,
            'address_count': user_addresses.count(),
            'max_addresses': MAX_USER_ADDRESSES,
            'can_add_address': user_addresses.count() < MAX_USER_ADDRESSES,
            'prefectures': prefectures,
            'back_url': reverse('product_edit', kwargs={'product_id': product_id}),
            'page_title': '発送元住所の管理',
            'product_id': product_id,
        }

        return render(request, 'sell_address_manage.html', context)

    def post(self, request, product_id, *args, **kwargs):
        # 商品が存在し、所有者であることを確認
        product = get_object_or_404(Product, product_id=product_id, user=request.user)

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        current_count = UserAddress.objects.filter(user=request.user, is_deleted=False).count()
        if current_count >= MAX_USER_ADDRESSES:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'住所は最大{MAX_USER_ADDRESSES}件までです'
                }, status=400)
            return redirect('edit_address_manage', product_id=product_id)

        postal_code = request.POST.get('postal_code', '').strip().replace('-', '')
        prefecture_id = request.POST.get('prefecture', '')
        city = request.POST.get('city', '').strip()
        street_address = request.POST.get('street_address', '').strip()

        errors = {}

        if not postal_code or len(postal_code) != 7:
            errors['postal_code'] = '郵便番号は7桁で入力してください'
        if not prefecture_id:
            errors['prefecture'] = '都道府県を選択してください'
        if not city:
            errors['city'] = '市区町村・町域は必須です'
        if not street_address:
            errors['street_address'] = '番地・建物名は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            return redirect('edit_address_manage', product_id=product_id)

        try:
            prefecture_obj = Prefecture.objects.get(prefecture_id=prefecture_id)
            is_first_address = current_count == 0

            address = UserAddress.objects.create(
                user=request.user,
                postal_code=postal_code,
                prefecture=prefecture_obj,
                city=city,
                street_address=street_address,
                is_default=is_first_address
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '住所を追加しました',
                    'address': {
                        'id': address.user_address_id,
                        'postal_code': address.postal_code,
                        'prefecture': prefecture_obj.prefecture_name,
                        'city': address.city,
                        'street_address': address.street_address,
                        'is_default': address.is_default,
                    }
                })

            return redirect('edit_address_manage', product_id=product_id)

        except Prefecture.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '都道府県が無効です'
                }, status=400)
            return redirect('edit_address_manage', product_id=product_id)


# 出品・編集用住所管理
sell_address_manage = SellAddressManageView.as_view()
edit_address_manage = EditAddressManageView.as_view()


class ProductStatusUpdateView(LoginRequiredMixin, View):
    """
    商品ステータス更新API
    """
    login_url = '/monotal/login/'

    def post(self, request, product_id, *args, **kwargs):
        try:
            product = Product.objects.get(product_id=product_id, user=request.user)

            data = json.loads(request.body)
            status_id = data.get('status_id')

            if status_id not in [1, 4]:  # 貸出可能(1) または 非公開(4) のみ許可
                return JsonResponse({
                    'success': False,
                    'message': '無効なステータスです'
                }, status=400)

            status_obj = ProductStatus.objects.get(product_status_id=status_id)
            product.product_status = status_obj
            product.save()

            return JsonResponse({
                'success': True,
                'message': 'ステータスを更新しました'
            })

        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '商品が見つかりません'
            }, status=404)

        except ProductStatus.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'ステータスが無効です'
            }, status=400)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'エラーが発生しました: {str(e)}'
            }, status=500)


class ProductDeleteView(LoginRequiredMixin, View):
    """
    商品削除API（論理削除）
    """
    login_url = '/monotal/login/'

    def post(self, request, product_id, *args, **kwargs):
        try:
            product = Product.objects.get(product_id=product_id, user=request.user)

            # 論理削除（delete_datetimeを設定 + ステータスを削除に変更）
            product.delete_datetime = timezone.now()
            product.product_status_id = PRODUCT_STATUS_DELETED
            product.save()

            return JsonResponse({
                'success': True,
                'message': '商品を削除しました',
                'redirect_url': reverse('mypage_listing')
            })

        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '商品が見つかりません'
            }, status=404)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'エラーが発生しました: {str(e)}'
            }, status=500)


# 商品ステータス・削除
product_status_update = ProductStatusUpdateView.as_view()
product_delete = ProductDeleteView.as_view()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  レンタル関連 / RENTAL                                                        ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# レンタル申請ステータス定数
RENTAL_REQUEST_STATUS_PENDING = 1    # 申請中
RENTAL_REQUEST_STATUS_APPROVED = 2   # 承認（レンタル開始待ち）
RENTAL_REQUEST_STATUS_REJECTED = 3   # 拒否
RENTAL_REQUEST_STATUS_CANCELLED = 4  # キャンセル
RENTAL_REQUEST_STATUS_COMPLETED = 5  # 完了（レンタル開始済み）


class RentalRequestView(LoginRequiredMixin, View):
    """
    レンタル申請API

    POSTでレンタル申請を作成
    アクセス条件:
    - ログイン必須
    - 本人確認完了（user_status_id = 2）必須
    """
    login_url = '/monotal/login/'

    def post(self, request, product_id, *args, **kwargs):
        # 本人確認チェック
        if request.user.user_status_id != USER_STATUS_VERIFIED:
            return redirect(f'/monotal/sell/verification-required/?context=rental&product_id={product_id}')

        # 商品を取得
        try:
            product = Product.objects.select_related('user').get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            messages.error(request, '商品が見つかりません')
            return redirect('product_list')

        # 自分の商品はレンタルできない
        if product.user == request.user:
            messages.error(request, '自分の商品はレンタルできません')
            return redirect('product_detail', product_id=product_id)

        # ブロック関係がある場合はレンタル申請不可（双方向）
        if Block.objects.filter(
            Q(blocker_user=request.user, blocked_user=product.user) |
            Q(blocker_user=product.user, blocked_user=request.user)
        ).exists():
            messages.error(request, 'このユーザーの商品にはレンタル申請できません')
            return redirect('product_detail', product_id=product_id)

        # 貸出中の商品は申請できない
        if product.product_status_id == PRODUCT_STATUS_RENTING:
            messages.error(request, 'この商品は現在貸出中のため申請できません')
            return redirect('product_detail', product_id=product_id)

        # 既に申請中または承認済みかチェック（キャンセル・完了・拒否以外）
        existing_request = RentalRequest.objects.filter(
            product=product,
            requester_user=request.user,
            rental_request_status_id__in=[RENTAL_REQUEST_STATUS_PENDING, RENTAL_REQUEST_STATUS_APPROVED]
        ).exists()

        if existing_request:
            messages.info(request, '既にこの商品に申請中または承認済みの申請があります')
            return redirect('product_detail', product_id=product_id)

        try:
            # 申請中ステータスを取得または作成
            pending_status, _ = RentalRequestStatus.objects.get_or_create(
                rental_request_status_id=RENTAL_REQUEST_STATUS_PENDING,
                defaults={'status_name': '申請中'}
            )

            # 選択されたプランを取得
            plan_id = request.POST.get('plan_id')
            selected_plan = None
            if plan_id:
                try:
                    selected_plan = ProductRentalPlan.objects.get(
                        product_rental_plan_id=plan_id,
                        product=product
                    )
                except ProductRentalPlan.DoesNotExist:
                    pass

            # レンタル申請を作成
            rental_request = RentalRequest.objects.create(
                product=product,
                requester_user=request.user,
                requested_user=product.user,
                rental_request_status=pending_status,
                product_rental_plan=selected_plan
            )

            # 出品者に通知を送信
            create_notification(
                notification_type_id=NOTIFICATION_TYPE_RENTAL,
                title='新しいレンタル申請があります',
                detail=f'「{product.product_name}」に{request.user.display_name}さんからレンタル申請がありました。',
                link_url=f'/monotal/mypage/rental-management/',
                target_users=[product.user]
            )

            # 申請完了画面へリダイレクト
            return redirect('rental_request_complete', product_id=product_id)

        except Exception as e:
            messages.error(request, f'申請に失敗しました: {str(e)}')
            return redirect('product_detail', product_id=product_id)


class RentalRequestCompleteView(LoginRequiredMixin, View):
    """
    レンタル申請完了画面
    """
    login_url = '/monotal/login/'

    def get(self, request, product_id, *args, **kwargs):
        try:
            product = Product.objects.select_related('user').prefetch_related('images').get(
                product_id=product_id,
                delete_datetime__isnull=True
            )
        except Product.DoesNotExist:
            return redirect('product_list')

        context = {
            'product': product,
        }
        return render(request, 'rental_request_complete.html', context)


class MyPageRentalManagementView(LoginRequiredMixin, View):
    """
    レンタル管理ページ
    出品者: 受け取った申請の承認/拒否、レンタル開始/キャンセル
    購入者: 自分の申請状況の確認
    """
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # 出品者として受け取った申請（自分が出品した商品への申請）
        received_base = RentalRequest.objects.filter(
            requested_user=request.user
        ).select_related(
            'product', 'product__product_status', 'requester_user', 'rental_request_status',
            'product_rental_plan'
        ).prefetch_related(
            'product__images'
        ).order_by('-register_datetime')

        # 受け取った申請: 承認待ち（削除済み商品は除く）
        received_pending = received_base.filter(
            rental_request_status_id=RENTAL_REQUEST_STATUS_PENDING
        ).exclude(product__product_status_id=PRODUCT_STATUS_DELETED)
        # 受け取った申請: 承認済み/完了（削除済み商品は除く）
        received_approved = received_base.filter(
            rental_request_status_id__in=[RENTAL_REQUEST_STATUS_APPROVED, RENTAL_REQUEST_STATUS_COMPLETED]
        ).exclude(product__product_status_id=PRODUCT_STATUS_DELETED)
        # 受け取った申請: 拒否（削除済み商品は除く）
        received_rejected = received_base.filter(
            rental_request_status_id=RENTAL_REQUEST_STATUS_REJECTED
        ).exclude(product__product_status_id=PRODUCT_STATUS_DELETED)
        # 受け取った申請: キャンセル（ステータス4 または 商品が削除された場合）
        received_cancelled = received_base.filter(
            Q(rental_request_status_id=RENTAL_REQUEST_STATUS_CANCELLED) |
            Q(product__product_status_id=PRODUCT_STATUS_DELETED)
        )

        # 購入者として送った申請（自分が申請したもの）
        sent_base = RentalRequest.objects.filter(
            requester_user=request.user
        ).select_related(
            'product', 'product__product_status', 'requested_user', 'rental_request_status',
            'product_rental_plan'
        ).prefetch_related(
            'product__images'
        ).order_by('-register_datetime')

        # 送った申請: 承認待ち（削除済み商品は除く）
        sent_pending = sent_base.filter(
            rental_request_status_id=RENTAL_REQUEST_STATUS_PENDING
        ).exclude(product__product_status_id=PRODUCT_STATUS_DELETED)
        # 送った申請: 承認済み/完了（削除済み商品は除く）
        sent_approved = sent_base.filter(
            rental_request_status_id__in=[RENTAL_REQUEST_STATUS_APPROVED, RENTAL_REQUEST_STATUS_COMPLETED]
        ).exclude(product__product_status_id=PRODUCT_STATUS_DELETED)
        # 送った申請: 拒否（削除済み商品は除く）
        sent_rejected = sent_base.filter(
            rental_request_status_id=RENTAL_REQUEST_STATUS_REJECTED
        ).exclude(product__product_status_id=PRODUCT_STATUS_DELETED)
        # 送った申請: キャンセル（ステータス4 または 商品が削除された場合）
        sent_cancelled = sent_base.filter(
            Q(rental_request_status_id=RENTAL_REQUEST_STATUS_CANCELLED) |
            Q(product__product_status_id=PRODUCT_STATUS_DELETED)
        )

        # 取引中（RentalHistory）: 出品者・購入者まとめて取得
        transactions_all = RentalHistory.objects.filter(
            Q(lender_user=request.user) | Q(renter_user=request.user),
            rental_status_id__in=[
                RENTAL_STATUS_PREPARING, RENTAL_STATUS_SHIPPING,
                RENTAL_STATUS_RENTING, RENTAL_STATUS_RETURNING,
                RENTAL_STATUS_RETURN_REQUESTED, RENTAL_STATUS_RETURN_APPROVED,
                RENTAL_STATUS_RETURN_SHIPPING,
                RENTAL_STATUS_CANCELLATION_REQUESTED
            ]
        ).select_related(
            'product', 'lender_user', 'renter_user', 'rental_status'
        ).prefetch_related(
            'product__images'
        ).order_by('-register_datetime')

        # カウント取得（ページネーション前）
        received_pending_count = received_pending.count()
        received_approved_active_count = received_approved.filter(
            rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
        ).count()
        sent_pending_count = sent_pending.count()
        sent_approved_active_count = sent_approved.filter(
            rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
        ).count()
        transactions_count = transactions_all.count()

        # ページネーション (10件/ページ)
        per_page = 10
        received_pending_page = Paginator(received_pending, per_page).get_page(request.GET.get('rp_page', 1))
        received_approved_page = Paginator(received_approved, per_page).get_page(request.GET.get('ra_page', 1))
        received_rejected_page = Paginator(received_rejected, per_page).get_page(request.GET.get('rr_page', 1))
        received_cancelled_page = Paginator(received_cancelled, per_page).get_page(request.GET.get('rc_page', 1))
        sent_pending_page = Paginator(sent_pending, per_page).get_page(request.GET.get('sp_page', 1))
        sent_approved_page = Paginator(sent_approved, per_page).get_page(request.GET.get('sa_page', 1))
        sent_rejected_page = Paginator(sent_rejected, per_page).get_page(request.GET.get('sr_page', 1))
        sent_cancelled_page = Paginator(sent_cancelled, per_page).get_page(request.GET.get('sc_page', 1))
        transactions_page = Paginator(transactions_all, per_page).get_page(request.GET.get('tx_page', 1))

        context = {
            'received_pending': received_pending_page,
            'received_approved': received_approved_page,
            'received_rejected': received_rejected_page,
            'received_cancelled': received_cancelled_page,
            'received_pending_count': received_pending_count,
            'received_approved_count': received_approved_active_count,
            'received_total_count': received_pending_count + received_approved_active_count,
            'sent_pending': sent_pending_page,
            'sent_approved': sent_approved_page,
            'sent_rejected': sent_rejected_page,
            'sent_cancelled': sent_cancelled_page,
            'sent_pending_count': sent_pending_count,
            'sent_approved_count': sent_approved_active_count,
            'sent_total_count': sent_pending_count + sent_approved_active_count,
            'transactions_all': transactions_page,
            'transactions_count': transactions_count,
            'current_page': 'rental_management',
        }
        return render(request, 'mypage/rental_management.html', context)


class RentalRequestApproveView(LoginRequiredMixin, View):
    """レンタル申請を承認"""
    login_url = '/monotal/login/'

    def post(self, request, request_id, *args, **kwargs):
        try:
            rental_request = RentalRequest.objects.select_related(
                'product', 'requester_user'
            ).get(
                rental_request_id=request_id,
                requested_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_PENDING
            )
            rental_request.rental_request_status_id = RENTAL_REQUEST_STATUS_APPROVED
            rental_request.approval_datetime = timezone.now()
            rental_request.save()

            # 申請者に通知を送信
            create_notification(
                notification_type_id=NOTIFICATION_TYPE_RENTAL,
                title='レンタル申請が承認されました',
                detail=f'「{rental_request.product.product_name}」のレンタル申請が承認されました。レンタル開始手続きを行ってください。',
                link_url=f'/monotal/rental-request/{request_id}/start/',
                target_users=[rental_request.requester_user]
            )

            return JsonResponse({'success': True, 'message': '申請を承認しました'})
        except RentalRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申請が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class RentalRequestRejectView(LoginRequiredMixin, View):
    """レンタル申請を拒否"""
    login_url = '/monotal/login/'

    def post(self, request, request_id, *args, **kwargs):
        try:
            rental_request = RentalRequest.objects.select_related(
                'product', 'requester_user'
            ).get(
                rental_request_id=request_id,
                requested_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_PENDING
            )
            rental_request.rental_request_status_id = RENTAL_REQUEST_STATUS_REJECTED
            rental_request.rejection_datetime = timezone.now()
            rental_request.save()

            # 申請者に通知を送信
            create_notification(
                notification_type_id=NOTIFICATION_TYPE_RENTAL,
                title='レンタル申請が拒否されました',
                detail=f'「{rental_request.product.product_name}」のレンタル申請が拒否されました。',
                link_url=f'/monotal/mypage/rental-management/',
                target_users=[rental_request.requester_user]
            )

            return JsonResponse({'success': True, 'message': '申請を拒否しました'})
        except RentalRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申請が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class RentalStartPageView(LoginRequiredMixin, View):
    """レンタル開始ページ（住所・カード選択）- 申請者（購入者）がアクセス"""
    login_url = '/monotal/login/'

    def get(self, request, request_id, *args, **kwargs):
        try:
            rental_request = RentalRequest.objects.select_related(
                'product', 'requested_user',
                'product__shipping_prefecture'
            ).prefetch_related('product__images').get(
                rental_request_id=request_id,
                requester_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
            )
        except RentalRequest.DoesNotExist:
            messages.error(request, '申請が見つかりません')
            return redirect('mypage_rental_management')

        # 自分（申請者）の住所一覧
        my_addresses = UserAddress.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('prefecture').order_by('-is_default', 'user_address_id')

        # 自分（申請者）のクレジットカード一覧
        my_cards = CreditCard.objects.filter(
            user=request.user
        ).order_by('-is_default', 'credit_card_id')

        # 商品に登録された発送元都道府県を取得
        shipping_prefecture = rental_request.product.shipping_prefecture

        context = {
            'rental_request': rental_request,
            'product': rental_request.product,
            'seller': rental_request.requested_user,
            'shipping_prefecture': shipping_prefecture,
            'my_addresses': my_addresses,
            'my_cards': my_cards,
        }
        return render(request, 'rental_start.html', context)


class RentalAddressManageView(LoginRequiredMixin, View):
    """
    レンタル開始ページ用 - 配送先住所管理
    戻るボタンでレンタル開始ページに戻る
    """
    login_url = '/monotal/login/'

    def get(self, request, request_id, *args, **kwargs):
        # レンタルリクエストの存在確認
        try:
            rental_request = RentalRequest.objects.get(
                rental_request_id=request_id,
                requester_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
            )
        except RentalRequest.DoesNotExist:
            messages.error(request, '申請が見つかりません')
            return redirect('mypage_rental_management')

        user_addresses = UserAddress.objects.filter(
            user=request.user, is_deleted=False
        ).select_related('prefecture').order_by('-is_default', '-register_datetime')

        prefectures = Prefecture.objects.all()

        context = {
            'user_addresses': user_addresses,
            'address_count': user_addresses.count(),
            'max_addresses': MAX_USER_ADDRESSES,
            'can_add_address': user_addresses.count() < MAX_USER_ADDRESSES,
            'prefectures': prefectures,
            'back_url': reverse('rental_start_page', kwargs={'request_id': request_id}),
            'back_text': '取引開始画面に戻る',
            'page_title': '配送先住所の管理',
            'request_id': request_id,
        }

        return render(request, 'sell_address_manage.html', context)

    def post(self, request, request_id, *args, **kwargs):
        # レンタルリクエストの存在確認
        try:
            rental_request = RentalRequest.objects.get(
                rental_request_id=request_id,
                requester_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
            )
        except RentalRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申請が見つかりません'}, status=404)

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        current_count = UserAddress.objects.filter(user=request.user, is_deleted=False).count()
        if current_count >= MAX_USER_ADDRESSES:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'住所は最大{MAX_USER_ADDRESSES}件までです'
                }, status=400)
            return redirect('rental_address_manage', request_id=request_id)

        postal_code = request.POST.get('postal_code', '').strip().replace('-', '')
        prefecture_id = request.POST.get('prefecture', '')
        city = request.POST.get('city', '').strip()
        street_address = request.POST.get('street_address', '').strip()

        errors = {}

        if not postal_code or len(postal_code) != 7:
            errors['postal_code'] = '郵便番号は7桁で入力してください'
        if not prefecture_id:
            errors['prefecture'] = '都道府県を選択してください'
        if not city:
            errors['city'] = '市区町村・町域は必須です'
        if not street_address:
            errors['street_address'] = '番地・建物名は必須です'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            return redirect('rental_address_manage', request_id=request_id)

        try:
            prefecture_obj = Prefecture.objects.get(prefecture_id=prefecture_id)
            is_first_address = current_count == 0

            address = UserAddress.objects.create(
                user=request.user,
                postal_code=postal_code,
                prefecture=prefecture_obj,
                city=city,
                street_address=street_address,
                is_default=is_first_address
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '住所を追加しました',
                    'address': {
                        'id': address.user_address_id,
                        'postal_code': address.postal_code,
                        'prefecture': prefecture_obj.prefecture_name,
                        'city': address.city,
                        'street_address': address.street_address,
                        'is_default': address.is_default,
                    }
                })

            return redirect('rental_address_manage', request_id=request_id)

        except Prefecture.DoesNotExist:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': '都道府県が無効です'
                }, status=400)
            return redirect('rental_address_manage', request_id=request_id)


class RentalCardManageView(LoginRequiredMixin, View):
    """
    レンタル開始ページ用 - 決済カード管理
    戻るボタンでレンタル開始ページに戻る
    """
    login_url = '/monotal/login/'

    def get(self, request, request_id, *args, **kwargs):
        # レンタルリクエストの存在確認
        try:
            rental_request = RentalRequest.objects.get(
                rental_request_id=request_id,
                requester_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
            )
        except RentalRequest.DoesNotExist:
            messages.error(request, '申請が見つかりません')
            return redirect('mypage_rental_management')

        credit_cards = CreditCard.objects.filter(
            user=request.user
        ).order_by('-is_default', '-register_datetime')

        context = {
            'credit_cards': credit_cards,
            'card_count': credit_cards.count(),
            'max_cards': MAX_CREDIT_CARDS,
            'can_add_card': credit_cards.count() < MAX_CREDIT_CARDS,
            'back_url': reverse('rental_start_page', kwargs={'request_id': request_id}),
            'back_text': '取引開始画面に戻る',
            'page_title': '決済カードの管理',
            'request_id': request_id,
            'current_page': 'rental_card_manage',
        }

        return render(request, 'rental_card_manage.html', context)

    def post(self, request, request_id, *args, **kwargs):
        # レンタルリクエストの存在確認
        try:
            rental_request = RentalRequest.objects.get(
                rental_request_id=request_id,
                requester_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
            )
        except RentalRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申請が見つかりません'}, status=404)

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        current_count = CreditCard.objects.filter(user=request.user).count()
        if current_count >= MAX_CREDIT_CARDS:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'カードは最大{MAX_CREDIT_CARDS}枚までです'
                }, status=400)
            return redirect('rental_card_manage', request_id=request_id)

        card_number = request.POST.get('card_number', '').strip().replace(' ', '')
        expiry_month = request.POST.get('expiry_month', '')
        expiry_year = request.POST.get('expiry_year', '')
        card_holder_name = request.POST.get('card_holder_name', '').strip().upper()

        errors = {}

        if not card_number or len(card_number) < 13 or len(card_number) > 19:
            errors['card_number'] = '有効なカード番号を入力してください'
        elif not card_number.isdigit():
            errors['card_number'] = 'カード番号は数字のみ入力してください'

        if not expiry_month or not expiry_year:
            errors['expiry'] = '有効期限を入力してください'
        else:
            try:
                month = int(expiry_month)
                year = int(expiry_year)
                if month < 1 or month > 12:
                    errors['expiry'] = '有効な月を入力してください'
            except ValueError:
                errors['expiry'] = '有効期限の形式が無効です'

        if not card_holder_name:
            errors['card_holder_name'] = 'カード名義を入力してください'

        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            return redirect('rental_card_manage', request_id=request_id)

        try:
            is_first_card = current_count == 0

            card = CreditCard.objects.create(
                user=request.user,
                card_number_last4=card_number[-4:],
                expiry_month=int(expiry_month),
                expiry_year=int(expiry_year),
                card_holder_name=card_holder_name,
                is_default=is_first_card
            )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'カードを追加しました',
                    'card': {
                        'id': card.credit_card_id,
                        'last4': card.card_number_last4,
                        'expiry_display': card.expiry_display,
                        'card_holder_name': card.card_holder_name,
                        'is_default': card.is_default,
                    }
                })

            return redirect('rental_card_manage', request_id=request_id)

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'エラーが発生しました: {str(e)}'
                }, status=500)
            return redirect('rental_card_manage', request_id=request_id)


class RentalRequestStartView(LoginRequiredMixin, View):
    """レンタルを開始（承認済み→完了、RentalHistoryを作成）- 申請者（購入者）が実行"""
    login_url = '/monotal/login/'

    def post(self, request, request_id, *args, **kwargs):
        try:
            rental_request = RentalRequest.objects.select_related('product', 'requested_user').get(
                rental_request_id=request_id,
                requester_user=request.user,
                rental_request_status_id=RENTAL_REQUEST_STATUS_APPROVED
            )

            # 住所とカードのバリデーション
            address_id = request.POST.get('address_id')
            card_id = request.POST.get('card_id')

            if not address_id or not card_id:
                messages.error(request, '住所とカードを選択してください')
                return redirect('rental_start_page', request_id=request_id)

            # 自分（申請者）の住所を確認
            try:
                address = UserAddress.objects.get(
                    user_address_id=address_id,
                    user=request.user
                )
            except UserAddress.DoesNotExist:
                messages.error(request, '選択された住所が見つかりません')
                return redirect('rental_start_page', request_id=request_id)

            # 自分（申請者）のカードを確認
            try:
                card = CreditCard.objects.get(
                    credit_card_id=card_id,
                    user=request.user
                )
            except CreditCard.DoesNotExist:
                messages.error(request, '選択されたカードが見つかりません')
                return redirect('rental_start_page', request_id=request_id)

            with transaction.atomic():
                # 1. RentalRequestを完了に
                rental_request.rental_request_status_id = RENTAL_REQUEST_STATUS_COMPLETED
                rental_request.save()

                # 2. RentalHistoryを作成（購入者の配送先住所を含む）
                rental_status, _ = RentalStatus.objects.get_or_create(
                    rental_status_id=1,
                    defaults={'status_name': '発送準備中'}
                )
                # レンタル日数をプランからコピー
                rental_days = None
                if rental_request.product_rental_plan:
                    rental_days = rental_request.product_rental_plan.rental_days

                rental_history = RentalHistory.objects.create(
                    product=rental_request.product,
                    lender_user=rental_request.requested_user,
                    renter_user=request.user,
                    rental_status=rental_status,
                    renter_address=address,
                    rental_days=rental_days
                )

                # 3. 商品のステータスをレンタル中に変更
                product = rental_request.product
                product.product_status_id = PRODUCT_STATUS_RENTING  # 貸出中
                product.save()

                # 4. チャットルームを作成（1対1、rental_history紐付け）
                chat_room_type, _ = ChatRoomType.objects.get_or_create(
                    chat_room_type_id=1,
                    defaults={'type_name': '1対1'}
                )
                chat_room = ChatRoom.objects.create(
                    chat_room_type=chat_room_type,
                    rental_history=rental_history
                )

                # 5. チャットルームに参加者を追加（貸し手と借り手）
                ChatRoomParticipant.objects.create(
                    chat_room=chat_room,
                    user=rental_request.requested_user  # 貸し手（出品者）
                )
                ChatRoomParticipant.objects.create(
                    chat_room=chat_room,
                    user=request.user  # 借り手（購入者）
                )

                # 6. 両ユーザーに取引開始の通知を送信
                tx_url = f'/monotal/transaction/{rental_history.rental_history_id}/'
                product_name = rental_request.product.product_name

                # 出品者（貸し手）への通知
                create_notification(
                    notification_type_id=NOTIFICATION_TYPE_RENTAL,
                    title='取引が開始されました',
                    detail=f'「{product_name}」の取引が開始されました。商品の発送準備をお願いします。',
                    link_url=tx_url,
                    target_users=[rental_request.requested_user],
                )

                # 購入者（借り手）への通知
                create_notification(
                    notification_type_id=NOTIFICATION_TYPE_RENTAL,
                    title='取引が開始されました',
                    detail=f'「{product_name}」の取引が開始されました。出品者からの発送をお待ちください。',
                    link_url=tx_url,
                    target_users=[request.user],
                )

            messages.success(request, 'レンタルを開始しました')
            return redirect('mypage_rental_management')

        except RentalRequest.DoesNotExist:
            messages.error(request, '申請が見つかりません')
            return redirect('mypage_rental_management')
        except Exception as e:
            messages.error(request, f'エラーが発生しました: {str(e)}')
            return redirect('rental_start_page', request_id=request_id)


class RentalRequestCancelView(LoginRequiredMixin, View):
    """申請をキャンセル - 申請者は申請中・承認済みでキャンセル可能"""
    login_url = '/monotal/login/'

    def post(self, request, request_id, *args, **kwargs):
        try:
            rental_request = RentalRequest.objects.select_related(
                'product', 'requested_user'
            ).get(rental_request_id=request_id)

            # 申請者のみキャンセル可能
            if rental_request.requester_user != request.user:
                return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)

            # 申請中または承認済みの場合のみキャンセル可能
            if rental_request.rental_request_status_id not in [RENTAL_REQUEST_STATUS_PENDING, RENTAL_REQUEST_STATUS_APPROVED]:
                return JsonResponse({'success': False, 'message': 'この申請はキャンセルできません'}, status=400)

            rental_request.rental_request_status_id = RENTAL_REQUEST_STATUS_CANCELLED
            rental_request.save()

            # 出品者に通知を送信
            create_notification(
                notification_type_id=NOTIFICATION_TYPE_RENTAL,
                title='レンタル申請がキャンセルされました',
                detail=f'「{rental_request.product.product_name}」へのレンタル申請が申請者によりキャンセルされました。',
                link_url=f'/monotal/mypage/rental-management/',
                target_users=[rental_request.requested_user]
            )

            return JsonResponse({'success': True, 'message': 'キャンセルしました'})
        except RentalRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申請が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class RentalRequestCancelSellerView(LoginRequiredMixin, View):
    """申請をキャンセル - 出品者は承認済みでキャンセル可能"""
    login_url = '/monotal/login/'

    def post(self, request, request_id, *args, **kwargs):
        try:
            rental_request = RentalRequest.objects.select_related(
                'product', 'requester_user'
            ).get(rental_request_id=request_id)

            # 出品者のみキャンセル可能
            if rental_request.requested_user != request.user:
                return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)

            # 承認済みの場合のみキャンセル可能
            if rental_request.rental_request_status_id != RENTAL_REQUEST_STATUS_APPROVED:
                return JsonResponse({'success': False, 'message': 'この申請はキャンセルできません'}, status=400)

            rental_request.rental_request_status_id = RENTAL_REQUEST_STATUS_CANCELLED
            rental_request.save()

            # 申請者に通知を送信
            create_notification(
                notification_type_id=NOTIFICATION_TYPE_RENTAL,
                title='レンタルがキャンセルされました',
                detail=f'「{rental_request.product.product_name}」のレンタルが出品者によりキャンセルされました。',
                link_url=f'/monotal/mypage/rental-management/',
                target_users=[rental_request.requester_user]
            )

            return JsonResponse({'success': True, 'message': 'キャンセルしました'})
        except RentalRequest.DoesNotExist:
            return JsonResponse({'success': False, 'message': '申請が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


# レンタル関連
rental_request = RentalRequestView.as_view()
rental_request_complete = RentalRequestCompleteView.as_view()
mypage_rental_management = MyPageRentalManagementView.as_view()
rental_request_approve = RentalRequestApproveView.as_view()
rental_request_reject = RentalRequestRejectView.as_view()
rental_start_page = RentalStartPageView.as_view()
rental_address_manage = RentalAddressManageView.as_view()
rental_card_manage = RentalCardManageView.as_view()
rental_request_start = RentalRequestStartView.as_view()
rental_request_cancel = RentalRequestCancelView.as_view()
rental_request_cancel_seller = RentalRequestCancelSellerView.as_view()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  通知関連 / NOTIFICATION                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# 通知タイプ定数
NOTIFICATION_TYPE_SYSTEM = 1      # システム通知
NOTIFICATION_TYPE_MESSAGE = 2     # メッセージ通知
NOTIFICATION_TYPE_RENTAL = 3      # レンタル通知
NOTIFICATION_TYPE_COMMUNITY = 4   # コミュニティ通知

# 通知既読ステータス定数
NOTIFICATION_READ_STATUS_UNREAD = 1  # 未読
NOTIFICATION_READ_STATUS_READ = 2    # 既読


def create_notification(notification_type_id, title, detail, link_url, target_users):
    """
    通知を作成するヘルパー関数

    Args:
        notification_type_id: 通知タイプID (1: システム, 2: メッセージ, 3: レンタル)
        title: 通知タイトル
        detail: 通知詳細
        link_url: リンクURL
        target_users: 通知対象ユーザーのリスト

    Returns:
        作成されたNotificationオブジェクト
    """
    notification_type = NotificationType.objects.get(notification_type_id=notification_type_id)

    notification = Notification.objects.create(
        notification_type=notification_type,
        notification_title=title,
        notification_detail=detail,
        link_url=link_url
    )

    # 対象ユーザーを登録
    for user in target_users:
        NotificationTargetUser.objects.create(
            notification=notification,
            user=user
        )

    return notification


class NotificationListView(LoginRequiredMixin, View):
    """通知一覧を取得するAPI"""
    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        # 自分宛ての通知を取得
        target_notifications = NotificationTargetUser.objects.filter(
            user=request.user
        ).select_related(
            'notification', 'notification__notification_type'
        ).order_by('-register_datetime')[:20]

        # 既読情報を取得
        read_notification_ids = set(
            NotificationRead.objects.filter(
                user=request.user,
                notification_read_status_id=NOTIFICATION_READ_STATUS_READ
            ).values_list('notification_id', flat=True)
        )

        notifications = []
        for target in target_notifications:
            notif = target.notification
            notifications.append({
                'notification_id': notif.notification_id,
                'type': notif.notification_type.notification_type_name,
                'title': notif.notification_title,
                'detail': notif.notification_detail,
                'link_url': notif.link_url,
                'is_read': notif.notification_id in read_notification_ids,
                'created_at': target.register_datetime.strftime('%Y/%m/%d %H:%M'),
            })

        return JsonResponse({
            'success': True,
            'notifications': notifications,
        })


class NotificationMarkReadView(LoginRequiredMixin, View):
    """通知を既読にするAPI"""
    login_url = '/monotal/login/'

    def post(self, request, notification_id, *args, **kwargs):
        try:
            # 自分宛ての通知か確認
            target = NotificationTargetUser.objects.get(
                notification_id=notification_id,
                user=request.user
            )

            read_status = NotificationReadStatus.objects.get(
                notification_read_status_id=NOTIFICATION_READ_STATUS_READ
            )

            # 既読レコードを作成または更新
            NotificationRead.objects.update_or_create(
                notification_id=notification_id,
                user=request.user,
                defaults={
                    'notification_read_status': read_status,
                    'read_datetime': timezone.now()
                }
            )

            return JsonResponse({'success': True})

        except NotificationTargetUser.DoesNotExist:
            return JsonResponse({'success': False, 'message': '通知が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    """すべての通知を既読にするAPI"""
    login_url = '/monotal/login/'

    def post(self, request, *args, **kwargs):
        try:
            # 自分宛ての通知IDを取得
            target_notification_ids = NotificationTargetUser.objects.filter(
                user=request.user
            ).values_list('notification_id', flat=True)

            read_status = NotificationReadStatus.objects.get(
                notification_read_status_id=NOTIFICATION_READ_STATUS_READ
            )

            # 各通知について既読レコードを作成または更新
            for notification_id in target_notification_ids:
                NotificationRead.objects.update_or_create(
                    notification_id=notification_id,
                    user=request.user,
                    defaults={
                        'notification_read_status': read_status,
                        'read_datetime': timezone.now()
                    }
                )

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


# 通知関連ビュー
notification_list = NotificationListView.as_view()
notification_mark_read = NotificationMarkReadView.as_view()
notification_mark_all_read = NotificationMarkAllReadView.as_view()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  取引画面関連ビュー / TRANSACTION VIEWS                                        ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class TransactionView(LoginRequiredMixin, View):
    """取引詳細画面"""
    login_url = '/monotal/login/'

    def get(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related(
                'product',
                'product__user',
                'product__shipping_address',
                'product__shipping_address__prefecture',
                'lender_user',
                'renter_user',
                'rental_status',
                'renter_address',
                'renter_address__prefecture'
            ).prefetch_related(
                'product__images'
            ).get(rental_history_id=rental_history_id)

            # アクセス権チェック（貸主または借り手のみ）
            is_lender = request.user == rental_history.lender_user
            is_renter = request.user == rental_history.renter_user

            if not is_lender and not is_renter:
                messages.error(request, 'この取引にアクセスする権限がありません')
                return redirect('mypage_rental_management')

            # 取引相手を特定
            partner_user = rental_history.renter_user if is_lender else rental_history.lender_user

            # チャットルームを取得
            chat_room = ChatRoom.objects.filter(rental_history=rental_history).first()

            # 相手の本人確認状態を確認
            partner_verified = partner_user.user_status_id == USER_STATUS_VERIFIED

            # 相手の個人情報（本人確認済みの場合のみ）
            partner_personal_info = None
            if partner_verified:
                try:
                    partner_personal_info = partner_user.personal_info
                except UserPersonalInfo.DoesNotExist:
                    pass

            # レンタル金額を取得（ProductRentalPlanから直接検索）
            rental_fee = None
            if rental_history.rental_days:
                plan = ProductRentalPlan.objects.filter(
                    product=rental_history.product,
                    rental_days=rental_history.rental_days
                ).first()
                if plan:
                    rental_fee = plan.rental_fee

            # 返品理由マスターを取得
            return_reasons = ReturnReason.objects.all()

            # 中止理由マスターと申請中の中止申請を取得
            from .models import CancellationReason, CancellationRequest
            cancellation_reasons = CancellationReason.objects.all()
            cancellation_request = CancellationRequest.objects.filter(
                rental_history=rental_history,
                cancellation_status_id=1  # 申請中
            ).select_related('cancellation_reason', 'requester_user').first()

            # レビュー情報を取得
            my_review = UserReview.objects.filter(
                reviewer_user=request.user, rental_history=rental_history
            ).first()
            partner_review = UserReview.objects.filter(
                reviewer_user=partner_user, rental_history=rental_history
            ).first()

            context = {
                'rental_history': rental_history,
                'product': rental_history.product,
                'chat_room': chat_room,
                'is_lender': is_lender,
                'is_renter': is_renter,
                'partner_user': partner_user,
                'partner_verified': partner_verified,
                'partner_personal_info': partner_personal_info,
                'return_reasons': return_reasons,
                'my_review': my_review,
                'partner_review': partner_review,
                # 貸主向け: 借り手の配送先住所
                'renter_address': rental_history.renter_address if is_lender else None,
                # 借り手向け: 発送元住所
                'shipping_address': rental_history.product.shipping_address if is_renter else None,
                # 配送追跡
                'has_shipping_tracking': bool(rental_history.shipping_tracking_number),
                'has_return_tracking': bool(rental_history.return_tracking_number),
                # レンタル期間
                'rental_days': rental_history.rental_days,
                'rental_fee': rental_fee,
                'rental_deadline': rental_history.rental_deadline,
                'rental_deadline_iso': rental_history.rental_deadline.isoformat() if rental_history.rental_deadline else None,
                'return_shipping_deadline': rental_history.return_shipping_deadline,
                'is_rental_overdue': (
                    rental_history.rental_status_id == RENTAL_STATUS_RENTING
                    and rental_history.rental_deadline
                    and timezone.now() > rental_history.rental_deadline
                ),
                'is_return_overdue': (
                    rental_history.rental_status_id == RENTAL_STATUS_RENTING
                    and rental_history.return_shipping_deadline
                    and timezone.now() > rental_history.return_shipping_deadline
                ),
                # 返品フロー
                'is_return_flow': rental_history.rental_status_id in [
                    RENTAL_STATUS_RETURN_REQUESTED, RENTAL_STATUS_RETURN_APPROVED, RENTAL_STATUS_RETURN_SHIPPING
                ],
                'return_reason_history': ReturnReasonHistory.objects.filter(
                    rental_history=rental_history
                ).select_related('return_reason').order_by('-return_request_datetime').first(),
                # 中止申請関連
                'cancellation_reasons': cancellation_reasons,
                'cancellation_request': cancellation_request,
            }

            return render(request, 'transaction.html', context)

        except RentalHistory.DoesNotExist:
            messages.error(request, '取引が見つかりません')
            return redirect('mypage_rental_management')


class TransactionMessagesView(LoginRequiredMixin, View):
    """取引チャットメッセージAPI"""
    login_url = '/monotal/login/'

    def get(self, request, rental_history_id, *args, **kwargs):
        """メッセージ一覧取得"""
        try:
            rental_history = RentalHistory.objects.get(rental_history_id=rental_history_id)

            # アクセス権チェック
            if request.user != rental_history.lender_user and request.user != rental_history.renter_user:
                return JsonResponse({'success': False, 'message': 'アクセス権限がありません'}, status=403)

            # チャットルームを取得
            chat_room = ChatRoom.objects.filter(rental_history=rental_history).first()
            if not chat_room:
                return JsonResponse({'success': True, 'messages': [], 'total_count': 0})

            # メッセージを取得（古い順）
            messages_qs = Message.objects.filter(chat_room=chat_room).select_related('user').order_by('register_datetime')

            messages_data = []
            for msg in messages_qs:
                messages_data.append({
                    'message_id': msg.message_id,
                    'user_id': msg.user.user_id,
                    'user_name': msg.user.display_name,
                    'user_image': msg.user.user_image.url if msg.user.user_image else None,
                    'content': msg.message_content,
                    'created_at': msg.register_datetime.strftime('%Y/%m/%d %H:%M'),
                    'is_mine': msg.user == request.user,
                })

            return JsonResponse({
                'success': True,
                'messages': messages_data,
                'total_count': len(messages_data),
            })

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つかりません'}, status=404)

    def post(self, request, rental_history_id, *args, **kwargs):
        """メッセージ送信"""
        try:
            rental_history = RentalHistory.objects.get(rental_history_id=rental_history_id)

            # アクセス権チェック
            if request.user != rental_history.lender_user and request.user != rental_history.renter_user:
                return JsonResponse({'success': False, 'message': 'アクセス権限がありません'}, status=403)

            # リクエストデータ取得
            try:
                data = json.loads(request.body)
                content = data.get('content', '').strip()
            except json.JSONDecodeError:
                content = request.POST.get('content', '').strip()

            if not content:
                return JsonResponse({'success': False, 'message': 'メッセージを入力してください'}, status=400)

            if len(content) > 2000:
                return JsonResponse({'success': False, 'message': 'メッセージは2000文字以内で入力してください'}, status=400)

            # チャットルームを取得（なければ作成）
            chat_room = ChatRoom.objects.filter(rental_history=rental_history).first()
            if not chat_room:
                chat_room_type, _ = ChatRoomType.objects.get_or_create(
                    chat_room_type_id=1,
                    defaults={'type_name': '1対1'}
                )
                chat_room = ChatRoom.objects.create(
                    chat_room_type=chat_room_type,
                    rental_history=rental_history
                )
                # 参加者を追加
                ChatRoomParticipant.objects.create(chat_room=chat_room, user=rental_history.lender_user)
                ChatRoomParticipant.objects.create(chat_room=chat_room, user=rental_history.renter_user)

            # メッセージを作成
            message = Message.objects.create(
                chat_room=chat_room,
                user=request.user,
                message_content=content
            )

            return JsonResponse({
                'success': True,
                'message': {
                    'message_id': message.message_id,
                    'user_id': request.user.user_id,
                    'user_name': request.user.display_name,
                    'user_image': request.user.user_image.url if request.user.user_image else None,
                    'content': message.message_content,
                    'created_at': message.register_datetime.strftime('%Y/%m/%d %H:%M'),
                    'is_mine': True,
                }
            })

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class TransactionShipView(LoginRequiredMixin, View):
    """貸主が商品を発送通知"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'renter_user').get(
                rental_history_id=rental_history_id,
                lender_user=request.user,
                rental_status_id=RENTAL_STATUS_PREPARING
            )

            # 追跡情報を取得（任意）
            try:
                body = json.loads(request.body) if request.body else {}
            except json.JSONDecodeError:
                body = {}
            tracking_number = body.get('tracking_number', '').strip()
            carrier_code = body.get('carrier_code', '').strip()

            # 追跡番号がある場合、17trackに事前登録を試みる
            if tracking_number:
                if not _register_tracking_17track(tracking_number, carrier_code):
                    return JsonResponse({
                        'success': False,
                        'message': '発送業者または追跡番号が正しくありません。'
                    }, status=400)

            with transaction.atomic():
                rental_history.rental_status_id = RENTAL_STATUS_SHIPPING
                rental_history.shipping_completed_datetime = timezone.now()

                if tracking_number:
                    rental_history.shipping_tracking_number = tracking_number
                if carrier_code:
                    rental_history.shipping_carrier_code = carrier_code

                rental_history.save()

                # 借り手に通知を送信
                self._send_notification(
                    rental_history.renter_user,
                    '商品が発送されました',
                    f'「{rental_history.product.product_name}」が発送されました。届きましたら受取完了をお願いします。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '発送を通知しました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、発送できる状態ではありません'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        """通知を送信"""
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(
                notification=notification,
                user=user
            )
        except Exception:
            pass  # 通知失敗は無視


class TransactionReceiveView(LoginRequiredMixin, View):
    """借り手が商品受取完了"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'lender_user').get(
                rental_history_id=rental_history_id,
                renter_user=request.user,
                rental_status_id=RENTAL_STATUS_SHIPPING
            )

            with transaction.atomic():
                rental_history.rental_status_id = RENTAL_STATUS_RENTING
                rental_history.rental_start_datetime = timezone.now()

                # レンタル期限・返送期限を計算
                if rental_history.rental_days:
                    rental_history.rental_deadline = timezone.now() + timedelta(days=rental_history.rental_days)
                    rental_history.return_shipping_deadline = rental_history.rental_deadline + timedelta(days=3)

                rental_history.save()

                # 貸主に通知を送信
                self._send_notification(
                    rental_history.lender_user,
                    '商品が受け取られました',
                    f'「{rental_history.product.product_name}」が借り手に届きました。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '受取を完了しました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、受取できる状態ではありません'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class TransactionReturnShipView(LoginRequiredMixin, View):
    """借り手が商品を返送"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'lender_user').get(
                rental_history_id=rental_history_id,
                renter_user=request.user,
                rental_status_id=RENTAL_STATUS_RENTING
            )

            # 追跡情報を取得（任意）
            try:
                body = json.loads(request.body) if request.body else {}
            except json.JSONDecodeError:
                body = {}
            tracking_number = body.get('tracking_number', '').strip()
            carrier_code = body.get('carrier_code', '').strip()

            # 追跡番号がある場合、17trackに事前登録を試みる
            if tracking_number:
                if not _register_tracking_17track(tracking_number, carrier_code):
                    return JsonResponse({
                        'success': False,
                        'message': '発送業者または追跡番号が正しくありません。'
                    }, status=400)

            with transaction.atomic():
                rental_history.rental_status_id = RENTAL_STATUS_RETURNING
                rental_history.rental_end_datetime = timezone.now()

                if tracking_number:
                    rental_history.return_tracking_number = tracking_number
                if carrier_code:
                    rental_history.return_carrier_code = carrier_code

                rental_history.save()

                # 貸主に通知を送信
                self._send_notification(
                    rental_history.lender_user,
                    '商品が返送されました',
                    f'「{rental_history.product.product_name}」が返送されました。届きましたら返却受取をお願いします。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '返送を通知しました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、返送できる状態ではありません'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class TransactionReturnReceiveView(LoginRequiredMixin, View):
    """貸主が返却を受取完了（通常返送: ステータス4→5、返品返送: ステータス9→6）"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'renter_user').get(
                rental_history_id=rental_history_id,
                lender_user=request.user,
                rental_status_id__in=[RENTAL_STATUS_RETURNING, RENTAL_STATUS_RETURN_SHIPPING]
            )

            is_return_flow = rental_history.rental_status_id == RENTAL_STATUS_RETURN_SHIPPING

            with transaction.atomic():
                if is_return_flow:
                    # 返品フロー: キャンセルに遷移
                    rental_history.rental_status_id = RENTAL_STATUS_CANCELLED
                    rental_history.receipt_completed_datetime = timezone.now()
                    rental_history.save()

                    # ReturnReasonHistoryのreturn_completed_datetimeを記録
                    return_reason_history = ReturnReasonHistory.objects.filter(
                        rental_history=rental_history
                    ).order_by('-return_request_datetime').first()
                    if return_reason_history:
                        return_reason_history.return_completed_datetime = timezone.now()
                        return_reason_history.return_status_id = RENTAL_STATUS_CANCELLED
                        return_reason_history.save()
                else:
                    # 通常フロー: 完了に遷移
                    rental_history.rental_status_id = RENTAL_STATUS_COMPLETED
                    rental_history.receipt_completed_datetime = timezone.now()
                    rental_history.save()

                # 商品のステータスを貸出可能に戻す
                product = rental_history.product
                product.product_status_id = PRODUCT_STATUS_LISTED
                product.save()

                if is_return_flow:
                    self._send_notification(
                        rental_history.renter_user,
                        '返品が完了しました',
                        f'「{rental_history.product.product_name}」の返品が完了しました。',
                        f'/monotal/transaction/{rental_history_id}/'
                    )
                    return JsonResponse({'success': True, 'message': '返品の受取を確認しました。取引はキャンセルとなりました。'})
                else:
                    self._send_notification(
                        rental_history.renter_user,
                        '返却が確認されました - 取引の評価をお願いします',
                        f'「{rental_history.product.product_name}」の返却が確認されました。取引画面から相手の評価をお願いします。',
                        f'/monotal/transaction/{rental_history_id}/'
                    )
                    return JsonResponse({'success': True, 'message': '返却を確認しました。取引の評価をお願いします。'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、返却確認できる状態ではありません'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class TransactionCancelView(LoginRequiredMixin, View):
    """取引をキャンセル"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'lender_user', 'renter_user').get(
                rental_history_id=rental_history_id
            )

            # アクセス権チェック
            is_lender = request.user == rental_history.lender_user
            is_renter = request.user == rental_history.renter_user

            if not is_lender and not is_renter:
                return JsonResponse({'success': False, 'message': 'アクセス権限がありません'}, status=403)

            # キャンセル可能な状態かチェック（発送準備中〜返送中）
            if rental_history.rental_status_id not in [
                RENTAL_STATUS_PREPARING, RENTAL_STATUS_SHIPPING,
                RENTAL_STATUS_RENTING, RENTAL_STATUS_RETURNING
            ]:
                return JsonResponse({'success': False, 'message': 'この取引はキャンセルできません'}, status=400)

            # リクエストデータ取得
            try:
                data = json.loads(request.body)
                return_reason_id = data.get('return_reason_id')
                return_reason_detail = data.get('return_reason_detail', '')
            except json.JSONDecodeError:
                return_reason_id = request.POST.get('return_reason_id')
                return_reason_detail = request.POST.get('return_reason_detail', '')

            if not return_reason_id:
                return JsonResponse({'success': False, 'message': 'キャンセル理由を選択してください'}, status=400)

            with transaction.atomic():
                # ReturnReasonHistoryを作成
                return_reason = ReturnReason.objects.get(return_reason_id=return_reason_id)
                ReturnReasonHistory.objects.create(
                    rental_history=rental_history,
                    return_reason=return_reason,
                    return_request_datetime=timezone.now(),
                    return_reason_detail=return_reason_detail[:1000] if return_reason_detail else None
                )

                # レンタル履歴をキャンセルに
                rental_history.rental_status_id = RENTAL_STATUS_CANCELLED
                rental_history.save()

                # 商品のステータスを貸出可能に戻す
                product = rental_history.product
                product.product_status_id = PRODUCT_STATUS_LISTED
                product.save()

                # 相手に通知を送信
                partner_user = rental_history.renter_user if is_lender else rental_history.lender_user
                self._send_notification(
                    partner_user,
                    '取引がキャンセルされました',
                    f'「{rental_history.product.product_name}」の取引がキャンセルされました。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '取引をキャンセルしました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つかりません'}, status=404)
        except ReturnReason.DoesNotExist:
            return JsonResponse({'success': False, 'message': '無効なキャンセル理由です'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class ReturnRequestView(LoginRequiredMixin, View):
    """借り手が返品を申請（ステータス3→7）"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'lender_user').get(
                rental_history_id=rental_history_id,
                renter_user=request.user,
                rental_status_id=RENTAL_STATUS_RENTING
            )

            try:
                data = json.loads(request.body)
                return_reason_id = data.get('return_reason_id')
                return_reason_detail = data.get('return_reason_detail', '')
            except json.JSONDecodeError:
                return_reason_id = request.POST.get('return_reason_id')
                return_reason_detail = request.POST.get('return_reason_detail', '')

            if not return_reason_id:
                return JsonResponse({'success': False, 'message': '返品理由を選択してください'}, status=400)

            with transaction.atomic():
                return_reason = ReturnReason.objects.get(return_reason_id=return_reason_id)
                ReturnReasonHistory.objects.create(
                    rental_history=rental_history,
                    return_reason=return_reason,
                    return_request_datetime=timezone.now(),
                    return_reason_detail=return_reason_detail[:1000] if return_reason_detail else None,
                    return_status_id=RENTAL_STATUS_RETURN_REQUESTED
                )

                rental_history.rental_status_id = RENTAL_STATUS_RETURN_REQUESTED
                rental_history.save()

                self._send_notification(
                    rental_history.lender_user,
                    '返品申請がありました',
                    f'「{rental_history.product.product_name}」の返品申請がありました。承認または拒否をお願いします。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '返品を申請しました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、返品申請できる状態ではありません'}, status=400)
        except ReturnReason.DoesNotExist:
            return JsonResponse({'success': False, 'message': '無効な返品理由です'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class ReturnApproveView(LoginRequiredMixin, View):
    """貸し手が返品を承認（ステータス7→8）"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'renter_user').get(
                rental_history_id=rental_history_id,
                lender_user=request.user,
                rental_status_id=RENTAL_STATUS_RETURN_REQUESTED
            )

            with transaction.atomic():
                rental_history.rental_status_id = RENTAL_STATUS_RETURN_APPROVED
                rental_history.save()

                # ReturnReasonHistoryのreturn_status_idを更新
                return_reason_history = ReturnReasonHistory.objects.filter(
                    rental_history=rental_history
                ).order_by('-return_request_datetime').first()
                if return_reason_history:
                    return_reason_history.return_status_id = RENTAL_STATUS_RETURN_APPROVED
                    return_reason_history.save()

                self._send_notification(
                    rental_history.renter_user,
                    '返品申請が承認されました',
                    f'「{rental_history.product.product_name}」の返品申請が承認されました。商品を返送してください。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '返品申請を承認しました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、承認できる状態ではありません'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class ReturnRejectView(LoginRequiredMixin, View):
    """貸し手が返品を拒否（ステータス7→3）"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'renter_user').get(
                rental_history_id=rental_history_id,
                lender_user=request.user,
                rental_status_id=RENTAL_STATUS_RETURN_REQUESTED
            )

            with transaction.atomic():
                rental_history.rental_status_id = RENTAL_STATUS_RENTING
                rental_history.save()

                # ReturnReasonHistoryのreturn_status_idを更新（拒否=レンタル中に戻す）
                return_reason_history = ReturnReasonHistory.objects.filter(
                    rental_history=rental_history
                ).order_by('-return_request_datetime').first()
                if return_reason_history:
                    return_reason_history.return_status_id = RENTAL_STATUS_RENTING
                    return_reason_history.save()

                self._send_notification(
                    rental_history.renter_user,
                    '返品申請が拒否されました',
                    f'「{rental_history.product.product_name}」の返品申請が拒否されました。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '返品申請を拒否しました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、拒否できる状態ではありません'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class ReturnShipView(LoginRequiredMixin, View):
    """借り手が返品商品を発送（ステータス8→9）"""
    login_url = '/monotal/login/'

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related('product', 'lender_user').get(
                rental_history_id=rental_history_id,
                renter_user=request.user,
                rental_status_id=RENTAL_STATUS_RETURN_APPROVED
            )

            try:
                body = json.loads(request.body) if request.body else {}
            except json.JSONDecodeError:
                body = {}
            tracking_number = body.get('tracking_number', '').strip()
            carrier_code = body.get('carrier_code', '').strip()

            if tracking_number:
                if not _register_tracking_17track(tracking_number, carrier_code):
                    return JsonResponse({
                        'success': False,
                        'message': '発送業者または追跡番号が正しくありません。'
                    }, status=400)

            with transaction.atomic():
                rental_history.rental_status_id = RENTAL_STATUS_RETURN_SHIPPING
                rental_history.rental_end_datetime = timezone.now()

                if tracking_number:
                    rental_history.return_tracking_number = tracking_number
                if carrier_code:
                    rental_history.return_carrier_code = carrier_code

                rental_history.save()

                # ReturnReasonHistoryのreturn_status_idを更新
                return_reason_history = ReturnReasonHistory.objects.filter(
                    rental_history=rental_history
                ).order_by('-return_request_datetime').first()
                if return_reason_history:
                    return_reason_history.return_status_id = RENTAL_STATUS_RETURN_SHIPPING
                    return_reason_history.save()

                self._send_notification(
                    rental_history.lender_user,
                    '返品商品が発送されました',
                    f'「{rental_history.product.product_name}」の返品商品が発送されました。届きましたら受取確認をお願いします。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '返品発送を通知しました'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つからないか、発送できる状態ではありません'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


class TransactionReviewView(LoginRequiredMixin, View):
    """取引レビュー画面"""
    login_url = '/monotal/login/'

    def get(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related(
                'product', 'product__user', 'lender_user', 'renter_user', 'rental_status'
            ).prefetch_related('product__images').get(rental_history_id=rental_history_id)

            is_lender = request.user == rental_history.lender_user
            is_renter = request.user == rental_history.renter_user

            if not is_lender and not is_renter:
                messages.error(request, 'この取引にアクセスする権限がありません')
                return redirect('mypage_rental_management')

            if rental_history.rental_status_id != RENTAL_STATUS_COMPLETED:
                messages.error(request, '返却済みの取引のみ評価できます')
                return redirect('transaction', rental_history_id=rental_history_id)

            # 既にレビュー済みか確認
            existing_review = UserReview.objects.filter(
                reviewer_user=request.user, rental_history=rental_history
            ).first()
            if existing_review:
                messages.info(request, 'この取引は既に評価済みです')
                return redirect('transaction', rental_history_id=rental_history_id)

            # 貸主の場合、口座登録チェック
            if is_lender:
                has_bank_account = BankAccount.objects.filter(user=request.user).exists()
                if not has_bank_account:
                    review_url = reverse('transaction_review', kwargs={'rental_history_id': rental_history_id})
                    return redirect(f"{reverse('bank_account_required')}?next={review_url}&context=transaction")

            partner_user = rental_history.renter_user if is_lender else rental_history.lender_user

            context = {
                'rental_history': rental_history,
                'product': rental_history.product,
                'partner_user': partner_user,
                'is_lender': is_lender,
            }
            return render(request, 'transaction_review.html', context)

        except RentalHistory.DoesNotExist:
            messages.error(request, '取引が見つかりません')
            return redirect('mypage_rental_management')

    def post(self, request, rental_history_id, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.select_related(
                'product', 'lender_user', 'renter_user'
            ).get(rental_history_id=rental_history_id)

            is_lender = request.user == rental_history.lender_user
            is_renter = request.user == rental_history.renter_user

            if not is_lender and not is_renter:
                return JsonResponse({'success': False, 'message': 'アクセス権限がありません'}, status=403)

            if rental_history.rental_status_id != RENTAL_STATUS_COMPLETED:
                return JsonResponse({'success': False, 'message': '返却済みの取引のみ評価できます'}, status=400)

            # 二重レビュー防止
            if UserReview.objects.filter(reviewer_user=request.user, rental_history=rental_history).exists():
                return JsonResponse({'success': False, 'message': 'この取引は既に評価済みです'}, status=400)

            # 貸主の場合、口座登録チェック
            if is_lender and not BankAccount.objects.filter(user=request.user).exists():
                return JsonResponse({'success': False, 'message': '取引を完了するには受取口座の登録が必要です'}, status=400)

            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)

            review_score = data.get('review_score')
            review_content = data.get('review_content', '').strip()

            # バリデーション
            try:
                review_score = int(review_score)
                if review_score < 1 or review_score > 5:
                    raise ValueError
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'message': '評価は1〜5の整数で入力してください'}, status=400)

            if len(review_content) > 1000:
                return JsonResponse({'success': False, 'message': 'コメントは1000文字以内で入力してください'}, status=400)

            partner_user = rental_history.renter_user if is_lender else rental_history.lender_user

            with transaction.atomic():
                UserReview.objects.create(
                    reviewer_user=request.user,
                    reviewed_user=partner_user,
                    rental_history=rental_history,
                    review_score=review_score,
                    review_content=review_content if review_content else None
                )

                # 相手に通知
                self._send_notification(
                    partner_user,
                    '取引の評価が届きました',
                    f'「{rental_history.product.product_name}」の取引であなたへの評価が送信されました。',
                    f'/monotal/transaction/{rental_history_id}/'
                )

            return JsonResponse({'success': True, 'message': '評価を送信しました。ありがとうございました。'})

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つかりません'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def _send_notification(self, user, title, detail, link_url):
        try:
            notification_type = NotificationType.objects.get(notification_type_id=1)
            notification = Notification.objects.create(
                notification_type=notification_type,
                notification_title=title,
                notification_detail=detail,
                link_url=link_url
            )
            NotificationTargetUser.objects.create(notification=notification, user=user)
        except Exception:
            pass


# 取引関連ビュー
def _register_tracking_17track(tracking_number, carrier_code=''):
    """17track APIに追跡番号を登録する。成功時True、失敗時False。"""
    import urllib.request
    import urllib.error

    api_key = settings.SEVENTEEN_TRACK_API_KEY
    if not api_key or not tracking_number:
        return True  # APIキー未設定時はスキップ（エラーにしない）

    try:
        payload = json.dumps([{
            'number': tracking_number,
            'carrier': int(carrier_code) if carrier_code and carrier_code.isdigit() else 0
        }])
        req = urllib.request.Request(
            'https://api.17track.net/track/v2.2/register',
            data=payload.encode('utf-8'),
            headers={
                '17token': api_key,
                'Content-Type': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            rejected = data.get('data', {}).get('rejected', [])
            if rejected:
                return False
        return True
    except Exception:
        return True  # 通信エラー時はブロックしない


class TransactionTrackingView(LoginRequiredMixin, View):
    """配送追跡情報API（17track連携）"""
    login_url = '/monotal/login/'

    def get(self, request, rental_history_id, tracking_type, *args, **kwargs):
        try:
            rental_history = RentalHistory.objects.get(rental_history_id=rental_history_id)

            # アクセス権チェック（貸主 or 借り手のみ）
            if request.user != rental_history.lender_user and request.user != rental_history.renter_user:
                return JsonResponse({'success': False, 'message': 'アクセス権限がありません'}, status=403)

            # 追跡番号と業者コードを取得
            if tracking_type == 'shipping':
                tracking_number = rental_history.shipping_tracking_number
                carrier_code = rental_history.shipping_carrier_code
            elif tracking_type == 'return':
                tracking_number = rental_history.return_tracking_number
                carrier_code = rental_history.return_carrier_code
            else:
                return JsonResponse({'success': False, 'message': '不正なタイプです'}, status=400)

            if not tracking_number:
                return JsonResponse({'success': False, 'message': '追跡番号が登録されていません'}, status=404)

            # 17track API呼び出し
            api_key = settings.SEVENTEEN_TRACK_API_KEY
            if not api_key:
                return JsonResponse({
                    'success': True,
                    'tracking_number': tracking_number,
                    'carrier_code': carrier_code or '',
                    'events': [],
                    'message': 'API KEYが未設定のため追跡情報を取得できません'
                })

            import urllib.request
            import urllib.error

            payload = json.dumps([{
                'number': tracking_number,
                'carrier': int(carrier_code) if carrier_code and carrier_code.isdigit() else 0
            }])

            req = urllib.request.Request(
                'https://api.17track.net/track/v2.2/gettrackinfo',
                data=payload.encode('utf-8'),
                headers={
                    '17token': api_key,
                    'Content-Type': 'application/json'
                }
            )

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    api_data = json.loads(resp.read().decode('utf-8'))
            except (urllib.error.URLError, urllib.error.HTTPError):
                return JsonResponse({
                    'success': True,
                    'tracking_number': tracking_number,
                    'carrier_code': carrier_code or '',
                    'events': [],
                    'message': '追跡情報の取得に失敗しました'
                })

            # レスポンスを整形
            events = []
            latest_status = ''
            accepted = api_data.get('data', {}).get('accepted', [])
            rejected = api_data.get('data', {}).get('rejected', [])

            if accepted:
                track = accepted[0]
                track_info = track.get('track_info', {})

                # 最新ステータス
                ls = track_info.get('latest_status', {})
                latest_status = ls.get('status', '')

                # イベント一覧（tracking.providers内のevents）
                tracking = track_info.get('tracking', {})
                providers = tracking.get('providers', [])
                for provider in providers:
                    for event in provider.get('events', []):
                        events.append({
                            'date': event.get('time_iso', ''),
                            'status': event.get('description', ''),
                            'location': event.get('location', ''),
                        })

            # 未登録の場合は自動登録を試みる
            if rejected:
                error_msg = rejected[0].get('error', {}).get('message', '')
                if 'register' in error_msg.lower():
                    _register_tracking_17track(tracking_number, carrier_code or '')
                    return JsonResponse({
                        'success': True,
                        'tracking_number': tracking_number,
                        'carrier_code': carrier_code or '',
                        'events': [],
                        'latest_status': '',
                        'message': '追跡番号を登録しました。しばらくしてから再度ご確認ください。'
                    })

            return JsonResponse({
                'success': True,
                'tracking_number': tracking_number,
                'carrier_code': carrier_code or '',
                'events': events,
                'latest_status': latest_status,
            })

        except RentalHistory.DoesNotExist:
            return JsonResponse({'success': False, 'message': '取引が見つかりません'}, status=404)


transaction_view = TransactionView.as_view()
transaction_messages = TransactionMessagesView.as_view()
transaction_ship = TransactionShipView.as_view()
transaction_receive = TransactionReceiveView.as_view()
transaction_return_ship = TransactionReturnShipView.as_view()
transaction_return_receive = TransactionReturnReceiveView.as_view()
transaction_cancel = TransactionCancelView.as_view()
transaction_review = TransactionReviewView.as_view()
transaction_tracking = TransactionTrackingView.as_view()
return_request = ReturnRequestView.as_view()
return_approve = ReturnApproveView.as_view()
return_reject = ReturnRejectView.as_view()
return_ship_refund = ReturnShipView.as_view()


class SearchAutocompleteView(View):
    """
    検索オートコンプリートAPI
    キーワードに基づいてカテゴリーと商品名の候補を返す
    """
    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '').strip()

        # 最低2文字以上
        if len(q) < 2:
            return JsonResponse({'suggestions': []})

        suggestions = []

        # カテゴリー候補（最大3件）
        categories = ProductCategory.objects.filter(
            category_name__icontains=q
        )[:3]

        for cat in categories:
            suggestions.append({
                'type': 'category',
                'text': cat.category_name,
                'value': cat.category_name,
                'category_id': cat.product_category_id,
                'icon': 'lucide:tag'
            })

        # 商品名候補（公開中の商品のみ、最大5件）
        products = Product.objects.filter(
            Q(product_name__icontains=q) | Q(product_description__icontains=q),
            delete_datetime__isnull=True,
            product_status_id=PRODUCT_STATUS_LISTED  # 貸出可能
        ).distinct()[:5]

        for prod in products:
            suggestions.append({
                'type': 'product',
                'text': prod.product_name,
                'value': prod.product_name,
                'product_id': prod.product_id,
                'icon': 'lucide:box'
            })

        return JsonResponse({
            'success': True,
            'suggestions': suggestions
        })


# 検索オートコンプリートビュー
search_autocomplete = SearchAutocompleteView.as_view()


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  保険関連ビュー / Insurance Related Views                                     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

from .views_insurance import (
    insurance_page,
    insurance_enroll_confirm,
    insurance_enroll,
    insurance_cancel,
    insurance_cancel_confirm,
    insurance_claim_page,
    insurance_claim_submit,
    admin_insurance_claims,
    admin_insurance_claim_detail,
    insurance_claim_approve,
    insurance_claim_reject,
)


# ===== 掲示板関連ビュー =====

def board_list(request):
    """掲示板一覧（HTMLおよびAJAX JSON対応）"""
    from django.db.models import Count
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    sort = request.GET.get('sort', 'new')  # 'new' | 'old' | 'members'

    if sort == 'old':
        order = 'created_at'
    elif sort == 'members':
        order = '-member_count'
    else:
        order = '-created_at'
    queryset = Community.objects.select_related('creator', 'category').annotate(
        member_count=Count('members', distinct=True)
    ).order_by(order)

    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat:
        try:
            queryset = queryset.filter(category_id=int(cat))
        except ValueError:
            pass

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # AJAXリクエストの場合はJSONで返す
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        joined_ids = set()
        if request.user.is_authenticated:
            joined_ids = set(
                CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True)
            )
        boards_data = []
        for b in page_obj:
            is_creator = b.creator == request.user if request.user.is_authenticated else False
            is_member = is_creator or (b.community_id in joined_ids)
            total_members = b.member_count + (1 if b.creator else 0)
            boards_data.append({
                'id': b.community_id,
                'name': b.name,
                'description': b.description,
                'category': b.category.name if b.category else None,
                'category_id': b.category_id,
                'creator_name': (b.creator.display_name or b.creator.user_name) if b.creator else None,
                'member_count': total_members,
                'created_at': b.created_at.strftime('%Y/%m/%d'),
                'url': reverse('board_detail', kwargs={'pk': b.community_id}),
                'join_url': reverse('board_join', kwargs={'pk': b.community_id}),
                'leave_url': reverse('board_leave', kwargs={'pk': b.community_id}),
                'user_is_creator': is_creator,
                'user_is_member': is_member,
            })
        return JsonResponse({
            'boards': boards_data,
            'has_next': page_obj.has_next(),
            'total': paginator.count,
        })

    try:
        selected_category_id = int(cat)
    except (ValueError, TypeError):
        selected_category_id = None

    return render(request, 'board_list.html', {
        'boards': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'categories': BoardCategory.objects.all().order_by('name'),
        'search_query': q,
        'selected_category_id': selected_category_id,
    })


@login_required(login_url='/monotal/login/')
def board_create(request):
    """掲示板作成"""
    if request.method == 'GET':
        return render(request, 'board_create.html', {
            'categories': BoardCategory.objects.all().order_by('name'),
        })

    # POST: JSON body
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    category_id = data.get('category_id')

    errors = {}
    if not name:
        errors['name'] = 'タイトルは必須です'
    elif len(name) > 100:
        errors['name'] = 'タイトルは100文字以内で入力してください'
    if not description:
        errors['description'] = '説明文は必須です'
    elif len(description) > 1000:
        errors['description'] = '説明文は1000文字以内で入力してください'

    category = None
    if not category_id:
        errors['category'] = 'カテゴリを選択してください'
    else:
        try:
            category = BoardCategory.objects.get(pk=category_id)
        except BoardCategory.DoesNotExist:
            errors['category'] = '無効なカテゴリです'

    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    with transaction.atomic():
        board = Community.objects.create(
            name=name,
            description=description,
            category=category,
            creator=request.user,
        )
        chat_room_type, _ = ChatRoomType.objects.get_or_create(
            chat_room_type_id=4,
            defaults={'type_name': 'コミュニティチャット'},
        )
        chat_room = ChatRoom.objects.create(chat_room_type=chat_room_type, community=board)
        ChatRoomParticipant.objects.create(chat_room=chat_room, user=request.user)

    return JsonResponse({
        'success': True,
        'message': '掲示板を作成しました',
        'board_id': board.pk,
        'board_name': board.name,
        'board_category_name': board.category.name if board.category else None,
        'board_url': reverse('board_detail', kwargs={'pk': board.pk}),
        'join_url': reverse('board_join', kwargs={'pk': board.pk}),
        'leave_url': reverse('board_leave', kwargs={'pk': board.pk}),
        'redirect_url': reverse('community') + f'?board={board.pk}',
    })


def board_detail(request, pk):
    """掲示板詳細・メッセージ投稿（未ログインは閲覧のみ）"""
    board = get_object_or_404(Community, pk=pk)
    chat_room = ChatRoom.objects.filter(community=board).first()

    if request.method == 'GET':
        msgs = (
            Message.objects
            .filter(chat_room=chat_room)
            .select_related('user', 'product_link')
            .prefetch_related('product_link__images')
            .order_by('register_datetime')
        ) if chat_room else []

        user_products = []
        if request.user.is_authenticated:
            user_products = (
                Product.objects
                .filter(user=request.user, delete_datetime__isnull=True, product_status_id=1)
                .prefetch_related('images')
                .order_by('-register_datetime')[:20]
            )

        # AJAXリクエストの場合はJSONを返す
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            is_creator = request.user.is_authenticated and board.creator == request.user
            is_member = is_creator or (request.user.is_authenticated and CommunityMember.objects.filter(community=board, user=request.user).exists())

            # メンバー一覧（作成者を先頭に）
            member_qs = CommunityMember.objects.filter(community=board).select_related('user').order_by('joined_at')
            member_list = []
            creator_added = False
            if board.creator:
                member_list.append({
                    'name': board.creator.display_name or board.creator.user_name,
                    'avatar': board.creator.user_image.url if board.creator.user_image else None,
                    'profile_url': reverse('profile', kwargs={'username': board.creator.user_name}),
                    'is_creator': True,
                })
                creator_added = True
            for m in member_qs:
                if creator_added and m.user == board.creator:
                    continue
                member_list.append({
                    'name': m.user.display_name or m.user.user_name,
                    'avatar': m.user.user_image.url if m.user.user_image else None,
                    'profile_url': reverse('profile', kwargs={'username': m.user.user_name}),
                    'is_creator': False,
                })

            def msg_to_dict(m):
                # システムメッセージ判定
                if m.message_content and m.message_content.startswith('__system__:'):
                    return {
                        'id': m.message_id,
                        'is_system': True,
                        'system_text': m.message_content[len('__system__:'):],
                        'content': None, 'image_url': None, 'product': None,
                        'user': {'name': '', 'avatar': None, 'profile_url': None},
                        'time': m.register_datetime.strftime('%m/%d %H:%M'),
                        'is_mine': False, 'delete_url': None,
                    }
                first_img = m.product_link.images.first() if m.product_link else None
                return {
                    'id': m.message_id,
                    'is_system': False,
                    'content': m.message_content,
                    'image_url': m.image.url if m.image else None,
                    'product': {
                        'id': m.product_link.pk,
                        'name': m.product_link.product_name,
                        'url': reverse('product_detail', kwargs={'product_id': m.product_link.pk}),
                        'image': first_img.image.url if first_img else None,
                    } if m.product_link else None,
                    'user': {
                        'name': m.user.user_name,
                        'avatar': m.user.user_image.url if m.user.user_image else None,
                        'profile_url': reverse('profile', kwargs={'username': m.user.user_name}),
                    },
                    'time': m.register_datetime.strftime('%m/%d %H:%M'),
                    'is_mine': m.user == request.user,
                    'delete_url': reverse('message_delete', kwargs={'pk': m.message_id}) if m.user == request.user else None,
                    'edit_url': reverse('message_edit', kwargs={'pk': m.message_id}) if m.user == request.user and m.message_content else None,
                    'reply': {
                        'id': m.reply_to.message_id,
                        'user_name': m.reply_to.user.user_name,
                        'content': m.reply_to.message_content if m.reply_to.message_content and not m.reply_to.message_content.startswith('__system__:') else None,
                        'image_url': m.reply_to.image.url if m.reply_to.image else None,
                        'product_name': m.reply_to.product_link.product_name if m.reply_to.product_link else None,
                    } if m.reply_to else None,
                }
            return JsonResponse({
                'board': {
                    'id': board.pk,
                    'name': board.name,
                    'description': board.description,
                    'category': board.category.name if board.category else None,
                    'creator': board.creator.user_name if board.creator else None,
                    'created_at': board.created_at.strftime('%Y/%m/%d'),
                },
                'is_creator': is_creator,
                'is_member': is_member,
                'join_url': reverse('board_join', kwargs={'pk': board.pk}),
                'leave_url': reverse('board_leave', kwargs={'pk': board.pk}),
                'delete_url': reverse('board_delete', kwargs={'pk': board.pk}) if is_creator else None,
                'member_count': len(member_list),
                'members': member_list,
                'messages': [msg_to_dict(m) for m in msgs],
                'user_products': [
                    {
                        'id': p.pk,
                        'name': p.product_name,
                        'image': p.images.first().image.url if p.images.exists() else None,
                        'fee': str(p.rental_fee),
                    }
                    for p in user_products
                ],
                'post_url': reverse('board_detail', kwargs={'pk': board.pk}),
            })

        # 通常GETはコミュニティページ（掲示板選択状態）にリダイレクト
        return redirect(reverse('community') + f'?board={pk}')

    # POST: ログイン必須
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'ログインが必要です'}, status=401)

    # POST: FormData（image対応）
    if not chat_room:
        return JsonResponse({'success': False, 'message': 'チャットルームが存在しません'}, status=400)

    content = request.POST.get('message_content', '').strip()
    product_link_id = request.POST.get('product_link_id', '').strip()
    reply_to_id = request.POST.get('reply_to_id', '').strip()
    image = request.FILES.get('image')

    errors = {}
    if not content and not image and not product_link_id:
        errors['message'] = 'メッセージ、画像、または商品リンクのいずれかを入力してください'
    elif content and len(content) > 2000:
        errors['message'] = 'メッセージは2000文字以内で入力してください'

    product_link = None
    if product_link_id:
        try:
            product_link = Product.objects.get(
                pk=int(product_link_id),
                delete_datetime__isnull=True,
            )
        except (Product.DoesNotExist, ValueError, TypeError):
            errors['product_link'] = '無効な商品です'

    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    reply_to = None
    if reply_to_id:
        reply_to = Message.objects.filter(pk=reply_to_id, chat_room=chat_room).first()

    msg = Message.objects.create(
        chat_room=chat_room,
        user=request.user,
        message_content=content or None,
        product_link=product_link,
        image=image,
        reply_to=reply_to,
    )

    first_img = msg.product_link.images.first() if msg.product_link else None
    return JsonResponse({'success': True, 'msg': {
        'id': msg.message_id,
        'content': msg.message_content,
        'image_url': msg.image.url if msg.image else None,
        'product': {
            'id': msg.product_link.pk,
            'name': msg.product_link.product_name,
            'url': reverse('product_detail', kwargs={'product_id': msg.product_link.pk}),
            'image': first_img.image.url if first_img else None,
        } if msg.product_link else None,
        'user': {
            'name': request.user.user_name,
            'avatar': request.user.user_image.url if request.user.user_image else None,
            'profile_url': reverse('profile', kwargs={'username': request.user.user_name}),
        },
        'time': msg.register_datetime.strftime('%m/%d %H:%M'),
        'is_mine': True,
        'delete_url': reverse('message_delete', kwargs={'pk': msg.message_id}),
        'edit_url': reverse('message_edit', kwargs={'pk': msg.message_id}) if content else None,
        'reply': {
            'id': reply_to.message_id,
            'user_name': reply_to.user.user_name,
            'content': reply_to.message_content if reply_to.message_content and not reply_to.message_content.startswith('__system__:') else None,
            'image_url': reply_to.image.url if reply_to.image else None,
            'product_name': reply_to.product_link.product_name if reply_to.product_link else None,
        } if reply_to else None,
    }})


@login_required(login_url='/monotal/login/')
def board_delete(request, pk):
    """グループチャット削除（作成者のみ）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)
    board = get_object_or_404(Community, pk=pk)
    if board.creator != request.user:
        return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)

    # 通知対象: メンバー全員（作成者除く）
    member_users = list(
        CommunityMember.objects.filter(community=board)
        .select_related('user')
        .values_list('user', flat=True)
    )
    target_users = list(User.objects.filter(pk__in=member_users))
    board_name = board.name
    link_url = reverse('community') + '?tab=chat'

    board.delete()  # CASCADE: メッセージ・メンバーも削除

    if target_users:
        try:
            create_notification(
                notification_type_id=4,
                title=f'「{board_name}」グループが削除されました',
                detail=f'参加していた「{board_name}」グループチャットが削除されました',
                link_url=link_url,
                target_users=target_users,
            )
        except Exception:
            pass

    return JsonResponse({'success': True})


@login_required(login_url='/monotal/login/')
def board_join(request, pk):
    """掲示板参加"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)
    board = get_object_or_404(Community, pk=pk)
    if board.creator == request.user:
        return JsonResponse({'success': False, 'message': '作成者はすでに参加しています'}, status=400)
    _, created = CommunityMember.objects.get_or_create(community=board, user=request.user)
    if created:
        chat_room = ChatRoom.objects.filter(community=board).first()
        if chat_room:
            display = request.user.display_name or request.user.user_name
            Message.objects.create(
                chat_room=chat_room,
                user=request.user,
                message_content=f'__system__:{display}が{board.name}グループチャットに参加しました',
            )
    return JsonResponse({'success': True})


@login_required(login_url='/monotal/login/')
def board_leave(request, pk):
    """掲示板退会"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)
    board = get_object_or_404(Community, pk=pk)
    if board.creator == request.user:
        return JsonResponse({'success': False, 'message': '作成者は退会できません'}, status=400)
    CommunityMember.objects.filter(community=board, user=request.user).delete()

    # 退会システムメッセージをチャットに追加
    system_msg = None
    chat_room = ChatRoom.objects.filter(community=board).first()
    if chat_room:
        display = request.user.display_name or request.user.user_name
        msg = Message.objects.create(
            chat_room=chat_room,
            user=request.user,
            message_content=f'__system__:{display}が{board.name}グループチャットから退会しました',
        )
        system_msg = {
            'id': msg.message_id,
            'is_system': True,
            'system_text': msg.message_content[len('__system__:'):],
            'content': None, 'image_url': None, 'product': None,
            'user': {'name': '', 'avatar': None, 'profile_url': None},
            'time': msg.register_datetime.strftime('%m/%d %H:%M'),
            'is_mine': False, 'delete_url': None,
        }
    return JsonResponse({'success': True, 'system_msg': system_msg})


@login_required(login_url='/monotal/login/')
def delete_message(request, pk):
    """メッセージ削除"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)
    msg = get_object_or_404(Message, pk=pk)
    if msg.user != request.user:
        return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)
    msg.delete()
    return JsonResponse({'success': True})


@login_required(login_url='/monotal/login/')
def edit_message(request, pk):
    """メッセージ編集（テキストのみ・本人のみ）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)
    msg = get_object_or_404(Message, pk=pk)
    if msg.user != request.user:
        return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)
    import json as _json
    try:
        body = _json.loads(request.body)
        content = body.get('content', '').strip()
    except Exception:
        content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'success': False, 'message': '内容を入力してください'}, status=400)
    if len(content) > 1000:
        return JsonResponse({'success': False, 'message': 'メッセージは1000文字以内にしてください'}, status=400)
    msg.message_content = content
    msg.save()
    return JsonResponse({'success': True, 'content': content})


def community(request):
    """コミュニティページ（未ログインは閲覧のみ）"""
    from django.db.models import Count, Exists, OuterRef
    qs = Community.objects.select_related('creator', 'category').annotate(
        member_count=Count('members', distinct=True)
    ).order_by('-created_at')[:20]

    # ログイン済みの場合、各掲示板の参加状態を付与
    joined_ids = set()
    if request.user.is_authenticated:
        joined_ids = set(
            CommunityMember.objects.filter(user=request.user).values_list('community_id', flat=True)
        )

    recent_boards = []
    for board in qs:
        board.user_is_creator = (board.creator == request.user) if request.user.is_authenticated else False
        board.user_is_member = board.user_is_creator or (board.community_id in joined_ids)
        recent_boards.append(board)

    categories = BoardCategory.objects.all().order_by('name')
    qa_categories = QACategory.objects.all().order_by('name')
    product_categories = ProductCategory.objects.filter(
        parent_product_category__isnull=True
    ).order_by('category_name')
    import json as _json
    qa_categories_json = _json.dumps(
        [{'id': c.id, 'name': c.name} for c in qa_categories]
    )
    categories_json = _json.dumps(
        [{'id': c.id, 'name': c.name} for c in categories]
    )
    product_categories_json = _json.dumps(
        [{'id': c.product_category_id, 'name': c.category_name} for c in product_categories]
    )
    return render(request, 'community.html', {
        'recent_boards': recent_boards,
        'categories': categories,
        'qa_categories': qa_categories,
        'qa_categories_json': qa_categories_json,
        'categories_json': categories_json,
        'product_categories_json': product_categories_json,
    })


@login_required(login_url='/monotal/login/')
def board_user_products(request):
    """商品リンク用: 全出品中商品を検索して返す"""
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category_id', '').strip()
    qs = Product.objects.filter(
        delete_datetime__isnull=True,
        product_status_id=1,
    ).select_related('user', 'product_category').prefetch_related('images').order_by('-register_datetime')
    if q:
        qs = qs.filter(Q(product_name__icontains=q) | Q(product_description__icontains=q))
    if category_id:
        try:
            qs = qs.filter(
                Q(product_category_id=int(category_id)) |
                Q(product_category__parent_product_category_id=int(category_id))
            )
        except (ValueError, TypeError):
            pass
    qs = qs[:30]
    return JsonResponse({
        'products': [
            {
                'id': p.pk,
                'name': p.product_name,
                'image': p.images.first().image.url if p.images.exists() else None,
                'owner': p.user.display_name or p.user.user_name,
            }
            for p in qs
        ]
    })


# ===== Q&A ビュー =====

def _auto_close_expired(qs):
    """受付中で期限切れの質問を自動的に「期限切れ終了」に更新する"""
    from django.utils import timezone
    qs.filter(status_id=1, expires_at__lt=timezone.now()).update(status_id=3)


def _send_qa_deadline_notifications():
    """受付期限まで24時間以内のQ&A質問の質問者に通知（重複送信なし）"""
    from django.utils import timezone as tz
    now = tz.now()
    soon = now + tz.timedelta(hours=24)

    expiring = QAQuestion.objects.filter(
        status_id=1,
        expires_at__gte=now,
        expires_at__lte=soon,
    ).select_related('user')

    for q in expiring:
        link = reverse('community') + f'?tab=qa&qa={q.question_id}'
        # 既に同じ通知が送信済みか確認
        already = NotificationTargetUser.objects.filter(
            user=q.user,
            notification__link_url=link,
            notification__notification_title='Q&A受付期限が近づいています',
        ).exists()
        if not already:
            try:
                create_notification(
                    notification_type_id=4,
                    title='Q&A受付期限が近づいています',
                    detail=f'「{q.title[:50]}」の受付期限まで24時間を切りました',
                    link_url=link,
                    target_users=[q.user],
                )
            except Exception:
                pass


def _answer_to_dict(answer, request_user):
    return {
        'id': answer.answer_id,
        'content': answer.content,
        'author': {
            'name': answer.user.display_name or answer.user.user_name,
            'avatar': answer.user.user_image.url if answer.user.user_image else None,
            'profile_url': reverse('profile', kwargs={'username': answer.user.user_name}),
        },
        'created_at': answer.created_at.strftime('%Y/%m/%d %H:%M'),
        'is_best_answer': answer.is_best_answer,
        'is_mine': request_user.is_authenticated and answer.user == request_user,
        'replies': [],
    }


def qa_list(request):
    """Q&A質問一覧（AJAX JSON、未ログインでも閲覧可）"""
    qs = QAQuestion.objects.select_related('user', 'category', 'status').annotate(
        answer_count=Count('answers', filter=Q(answers__parent_answer__isnull=True), distinct=True)
    )
    _auto_close_expired(qs)
    _send_qa_deadline_notifications()
    qs = qs.order_by('-created_at')[:50]

    questions = []
    for q in qs:
        questions.append({
            'id': q.question_id,
            'title': q.title,
            'status_id': q.status_id,
            'status_name': q.status.name,
            'category': q.category.name if q.category else None,
            'category_id': q.category_id,
            'author': q.user.display_name or q.user.user_name,
            'answer_count': q.answer_count,
            'created_at': q.created_at.strftime('%Y/%m/%d'),
            'expires_at': q.expires_at.strftime('%Y/%m/%d %H:%M'),
            'expires_at_raw': q.expires_at.isoformat(),
        })
    return JsonResponse({'questions': questions})


@login_required(login_url='/monotal/login/')
def qa_create(request):
    """Q&A質問作成（AJAX POST）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)

    from django.utils import timezone
    import json as _json

    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)

    title = body.get('title', '').strip()
    content = body.get('content', '').strip()
    category_id = body.get('category_id')

    errors = {}
    if not title:
        errors['title'] = 'タイトルを入力してください'
    elif len(title) > 200:
        errors['title'] = 'タイトルは200文字以内で入力してください'
    if not content:
        errors['content'] = '本文を入力してください'
    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    category = None
    if category_id:
        try:
            category = QACategory.objects.get(pk=category_id)
        except QACategory.DoesNotExist:
            pass

    question = QAQuestion.objects.create(
        user=request.user,
        category=category,
        title=title,
        content=content,
        status_id=1,
        expires_at=timezone.now() + timezone.timedelta(days=3),
    )
    return JsonResponse({'success': True, 'question_id': question.question_id})


def qa_detail(request, pk):
    """Q&A質問詳細（AJAX GET、未ログインでも閲覧可）"""
    question = get_object_or_404(QAQuestion.objects.select_related('user', 'category', 'status'), pk=pk)

    from django.utils import timezone
    if question.status_id == 1 and question.expires_at < timezone.now():
        question.status_id = 3
        question.save(update_fields=['status_id', 'updated_at'])

    # 回答ツリー（親回答 + replies を1クエリずつで取得）
    parent_answers = QAAnswer.objects.filter(
        question=question, parent_answer__isnull=True
    ).select_related('user').order_by('created_at')

    replies_qs = QAAnswer.objects.filter(
        question=question, parent_answer__isnull=False
    ).select_related('user').order_by('created_at')

    replies_map = {}
    for r in replies_qs:
        replies_map.setdefault(r.parent_answer_id, []).append(r)

    is_owner = request.user.is_authenticated and question.user == request.user
    is_closed = question.status_id != 1

    answers_data = []
    for ans in parent_answers:
        d = _answer_to_dict(ans, request.user)
        d['can_select_best'] = is_owner and not is_closed and not ans.is_best_answer and ans.user != request.user
        d['replies'] = [_answer_to_dict(r, request.user) for r in replies_map.get(ans.answer_id, [])]
        answers_data.append(d)

    return JsonResponse({
        'question': {
            'id': question.question_id,
            'title': question.title,
            'content': question.content,
            'status_id': question.status_id,
            'status_name': question.status.name,
            'category': question.category.name if question.category else None,
            'category_id': question.category_id,
            'author': {
                'name': question.user.display_name or question.user.user_name,
                'avatar': question.user.user_image.url if question.user.user_image else None,
                'profile_url': reverse('profile', kwargs={'username': question.user.user_name}),
            },
            'created_at': question.created_at.strftime('%Y/%m/%d'),
            'expires_at': question.expires_at.strftime('%Y/%m/%d %H:%M'),
            'expires_at_raw': question.expires_at.isoformat(),
            'is_owner': is_owner,
            'is_closed': is_closed,
            'edit_url': reverse('qa_edit', kwargs={'pk': question.question_id}) if is_owner and not is_closed else None,
        },
        'answers': answers_data,
        'post_url': reverse('qa_answer_post', kwargs={'pk': question.question_id}),
    })


@login_required(login_url='/monotal/login/')
def qa_answer_post(request, pk):
    """Q&A回答・返信投稿（AJAX POST）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)

    import json as _json
    question = get_object_or_404(QAQuestion, pk=pk)

    if question.status_id != 1:
        return JsonResponse({'success': False, 'message': 'この質問は受付を終了しています'}, status=400)

    if question.user == request.user:
        return JsonResponse({'success': False, 'message': '自分の質問には回答できません'}, status=403)

    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)

    content = body.get('content', '').strip()
    parent_answer_id = body.get('parent_answer_id')

    if not content:
        return JsonResponse({'success': False, 'message': '回答内容を入力してください'}, status=400)
    if len(content) > 2000:
        return JsonResponse({'success': False, 'message': '回答は2000文字以内で入力してください'}, status=400)

    parent_answer = None
    if parent_answer_id:
        try:
            parent_answer = QAAnswer.objects.get(pk=parent_answer_id, question=question, parent_answer__isnull=True)
        except QAAnswer.DoesNotExist:
            return JsonResponse({'success': False, 'message': '返信先の回答が見つかりません'}, status=400)

    answer = QAAnswer.objects.create(
        question=question,
        user=request.user,
        parent_answer=parent_answer,
        content=content,
    )
    d = _answer_to_dict(answer, request.user)
    d['parent_answer_id'] = parent_answer.answer_id if parent_answer else None
    return JsonResponse({'success': True, 'answer': d})


@login_required(login_url='/monotal/login/')
def qa_select_best(request, pk, answer_pk):
    """BAを選択（AJAX POST、質問者のみ）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)

    question = get_object_or_404(QAQuestion, pk=pk)
    if question.user != request.user:
        return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)
    if question.status_id != 1:
        return JsonResponse({'success': False, 'message': 'この質問は受付を終了しています'}, status=400)

    answer = get_object_or_404(QAAnswer, pk=answer_pk, question=question, parent_answer__isnull=True)

    with transaction.atomic():
        QAAnswer.objects.filter(question=question).update(is_best_answer=False)
        answer.is_best_answer = True
        answer.save(update_fields=['is_best_answer'])
        question.status_id = 2
        question.save(update_fields=['status_id', 'updated_at'])

    # 回答者にベストアンサー選択通知（自分以外）
    if answer.user != request.user:
        community_url = f'/monotal/community/?tab=qa&qa={question.question_id}'
        create_notification(
            NOTIFICATION_TYPE_COMMUNITY,
            'ベストアンサーに選ばれました',
            f'「{question.title}」の回答がベストアンサーに選ばれました',
            community_url,
            [answer.user],
        )

    return JsonResponse({'success': True})


@login_required(login_url='/monotal/login/')
def qa_edit(request, pk):
    """Q&A質問編集（AJAX POST、質問者のみ・受付中のみ）"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=405)

    import json as _json
    question = get_object_or_404(QAQuestion, pk=pk)

    if question.user != request.user:
        return JsonResponse({'success': False, 'message': '権限がありません'}, status=403)
    if question.status_id != 1:
        return JsonResponse({'success': False, 'message': '受付終了した質問は編集できません'}, status=400)

    try:
        body = _json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': '不正なリクエストです'}, status=400)

    title = body.get('title', '').strip()
    content = body.get('content', '').strip()
    category_id = body.get('category_id')

    if not title:
        return JsonResponse({'success': False, 'message': 'タイトルを入力してください'}, status=400)
    if not content:
        return JsonResponse({'success': False, 'message': '本文を入力してください'}, status=400)
    if len(title) > 200:
        return JsonResponse({'success': False, 'message': 'タイトルは200文字以内で入力してください'}, status=400)

    if category_id:
        try:
            question.category = QACategory.objects.get(pk=category_id)
        except QACategory.DoesNotExist:
            question.category = None
    else:
        question.category = None

    question.title = title
    question.content = content
    question.save(update_fields=['title', 'content', 'category', 'updated_at'])

    return JsonResponse({
        'success': True,
        'title': question.title,
        'content': question.content,
        'category': question.category.name if question.category else None,
        'category_id': question.category_id,
    })
