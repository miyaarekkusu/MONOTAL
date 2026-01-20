import json
import re
from datetime import timedelta
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *
from django.core.paginator import Paginator
from django.db.models import Q
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
        return render(request, 'home.html')


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
                        'redirect_url': '/'
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

            messages.success(request, '会員登録が完了しました。プロフィールを設定してください。')
            return redirect('profile_setting', username=user.user_name)

        except EmailVerificationToken.DoesNotExist:
            return render(request, 'verify_failed.html', {
                'message': '無効な認証リンクです。'
            })


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
        ).order_by('-register_datetime')

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
        if request.user.is_authenticated and request.user != user:
            is_following = Follow.objects.filter(
                follower_user=request.user,
                followed_user=user
            ).exists()

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


# 出品ステータス定数
PRODUCT_STATUS_DRAFT = 1      # 下書き
PRODUCT_STATUS_LISTED = 2     # 出品中
PRODUCT_STATUS_RENTING = 3    # レンタル中
PRODUCT_STATUS_PAUSED = 4     # 出品停止
PRODUCT_STATUS_COMPLETED = 5  # 取引完了
PRODUCT_STATUS_DELETED = 6    # 削除済み

# ユーザーステータス定数
USER_STATUS_UNVERIFIED = 1    # 未認証（本人確認未完了）
USER_STATUS_VERIFIED = 2      # 承認済み（本人確認完了）


class VerificationRequiredView(View):
    """本人確認が必要なページ"""
    def get(self, request, *args, **kwargs):
        return render(request, 'verification_required.html')


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

        # マスターデータを取得
        categories = ProductCategory.objects.filter(
            parent_product_category__isnull=True
        ).prefetch_related('subcategories')
        conditions = ProductCondition.objects.all()
        prefectures = Prefecture.objects.all()
        shipping_days_list = ShippingDays.objects.all()

        context = {
            'categories': categories,
            'conditions': conditions,
            'prefectures': prefectures,
            'shipping_days_list': shipping_days_list,
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

        try:
            # FormDataから取得
            product_name = request.POST.get('product_name', '').strip()
            product_category_id = request.POST.get('product_category', '')
            product_description = request.POST.get('product_description', '').strip()
            product_condition_id = request.POST.get('product_condition', '')
            shipping_days_id = request.POST.get('shipping_days', '')

            # 住所情報
            postal_code = request.POST.get('postal_code', '').strip()
            prefecture_id = request.POST.get('prefecture', '')
            city = request.POST.get('city', '').strip()
            street_address = request.POST.get('street_address', '').strip()

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

                    if days > 0 and price >= 100:
                        has_valid_plan = True
                    elif days > 0 and 0 < price < 100:
                        errors['rental_plans'] = '金額は100円以上で設定してください'
                        break

                if not has_valid_plan and 'rental_plans' not in errors:
                    errors['rental_plans'] = '日数と金額を正しく入力してください'

            # 住所バリデーション
            if not postal_code:
                errors['postal_code'] = '郵便番号は必須です'
            elif len(postal_code.replace('-', '')) != 7:
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

            # 都道府県
            prefecture_obj = None
            if prefecture_id:
                try:
                    prefecture_obj = Prefecture.objects.get(prefecture_id=prefecture_id)
                except Prefecture.DoesNotExist:
                    pass

            # 発送日数
            shipping_days_obj = None
            if shipping_days_id:
                try:
                    shipping_days_obj = ShippingDays.objects.get(shipping_days_id=shipping_days_id)
                except ShippingDays.DoesNotExist:
                    pass

            # 配送方法（デフォルト: モノタル便）
            try:
                shipping_obj = ShippingMethod.objects.first()
                if not shipping_obj:
                    shipping_obj = ShippingMethod.objects.create(
                        shipping_method_name='モノタル便'
                    )
            except ShippingMethod.DoesNotExist:
                shipping_obj = ShippingMethod.objects.create(
                    shipping_method_name='モノタル便'
                )

            # 商品ステータス（出品中）
            try:
                status_obj = ProductStatus.objects.get(product_status_id=PRODUCT_STATUS_LISTED)
            except ProductStatus.DoesNotExist:
                status_obj = ProductStatus.objects.create(
                    product_status_id=PRODUCT_STATUS_LISTED,
                    status_name='出品中'
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
                    shipping_method=shipping_obj,
                    shipping_days=shipping_days_obj,
                    product_condition=condition_obj,
                    product_status=status_obj,
                    product_category=category_obj,
                    rental_days=rental_days_value,
                    rental_fee=rental_fee_value,
                    user=request.user
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

                # ユーザー住所保存（既存の住所を更新または新規作成）
                user_address, created = UserAddress.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'postal_code': postal_code.replace('-', ''),
                        'prefecture': prefecture_obj,
                        'city': city,
                        'street_address': street_address,
                    }
                )

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': '商品を出品しました',
                    'redirect_url': '/monotal/'
                })

            messages.success(request, '商品を出品しました')
            return redirect('index')

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
        # 公開中の商品のみ取得（delete_datetimeがnullのもの）
        products = Product.objects.filter(
            delete_datetime__isnull=True
        ).select_related(
            'product_condition',
            'product_status',
            'product_category',
            'user'
        ).prefetch_related(
            'images'  # 商品画像も取得
        ).order_by('-register_datetime')

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

        # 価格フィルター（最小）
        min_fee = request.GET.get('min_fee')
        if min_fee:
            try:
                queryset = queryset.filter(rental_fee__gte=int(min_fee))
            except ValueError:
                pass

        # 価格フィルター（最大）
        max_fee = request.GET.get('max_fee')
        if max_fee:
            try:
                queryset = queryset.filter(rental_fee__lte=int(max_fee))
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

        # テキスト検索
        search_query = request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(product_name__icontains=search_query) |
                Q(product_description__icontains=search_query)
            )

        return queryset

    def get_active_filters(self, request):
        """
        現在適用中のフィルター値を返す
        """
        return {
            'category': request.GET.get('category', ''),
            'min_fee': request.GET.get('min_fee', ''),
            'max_fee': request.GET.get('max_fee', ''),
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
            # 商品を取得（削除されていない、公開中のもの）
            product = Product.objects.select_related(
                'product_condition',
                'product_status',
                'product_category',
                'shipping_method',
                'shipping_days',
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

        # 商品画像を取得
        product_images = list(product.images.all())

        # レンタルプランを取得（日数順）
        rental_plans = ProductRentalPlan.objects.filter(
            product=product
        ).order_by('rental_days')

        # 出品者の住所（都道府県）を取得
        seller_address = None
        if product.user:
            seller_address = UserAddress.objects.filter(
                user=product.user
            ).select_related('prefecture').first()

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

        context = {
            'product': product,
            'product_images': product_images,
            'rental_plans': rental_plans,
            'seller_address': seller_address,
            'is_bookmarked': is_bookmarked,
            'bookmark_count': bookmark_count,
            'message_count': message_count,
            'is_seller': is_seller,
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


class InterestSelectionView(View):
    """
    趣味・興味のあるジャンル選択ページ
    画面表示のみ（データベース保存は後で実装）
    """
    def get(self, request, *args, **kwargs):
        return render(request, 'interest_selection.html')


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

        # 画像取得
        face_image = request.FILES.get('face_image')
        id_image = request.FILES.get('id_image')
        id_back_image = request.FILES.get('id_back_image')

        errors = {}

        # バリデーション
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
                # 本人確認レコード作成
                verification = IdentityVerification.objects.create(
                    user=request.user,
                    identity_verification_status=pending_status
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

        context = {
            'following_list': page_obj,
            'following_count': following_count,
            'page_obj': page_obj,
            'current_page': 'follow_list',
        }

        return render(request, 'mypage/follow_list.html', context)


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

        context = {
            'bookmarked_products': page_obj,
            'bookmark_count': bookmark_count,
            'page_obj': page_obj,
            'current_page': 'bookmark_list',
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

        context = {
            'browsing_history': page_obj,
            'history_count': history_count,
            'page_obj': page_obj,
            'current_page': 'browsing_history',
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

        context = {
            'listing_products': page_obj,
            'listing_count': listing_count,
            'page_obj': page_obj,
            'current_page': 'listing',
        }

        return render(request, 'mypage/listing.html', context)


index = IndexView.as_view()
login_view = LoginView.as_view()
logout_view = LogoutView.as_view()
register = RegisterView.as_view()
register_form = RegisterFormView.as_view()
register_complete = RegisterCompleteView.as_view()
register_sent = RegisterSentView.as_view()
email_verify = EmailVerifyView.as_view()
profile = ProfileView.as_view()
profile_setting = ProfileSettingView.as_view()
create_sell = CreateSellView.as_view()
verification_required = VerificationRequiredView.as_view()
product_list = ProductListView.as_view()
product_detail = ProductDetailView.as_view()
bookmark_toggle = BookmarkToggleView.as_view()
product_messages = ProductMessagesView.as_view()
product_message_delete = ProductMessageDeleteView.as_view()
interest_selection = InterestSelectionView.as_view()

# 本人確認関連
identity_verification = IdentityVerificationView.as_view()
admin_verification_list = AdminVerificationListView.as_view()
admin_verification_detail = AdminVerificationDetailView.as_view()
verification_image = VerificationImageView.as_view()

# フォロー関連
follow_toggle = FollowToggleView.as_view()
mypage_follow_list = MyPageFollowListView.as_view()

# マイページ関連
mypage_bookmark_list = MyPageBookmarkListView.as_view()
mypage_browsing_history = MyPageBrowsingHistoryView.as_view()
mypage_listing = MyPageListingView.as_view()
