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

        context = {
            'profile_user': user,
            'user_products': user_products,
            'user_products_count': user_products.count(),
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


class CreateSellView(View):

#    login_url = '/monotal/login/'

    def get(self, request, *args, **kwargs):
        return render(request, 'create_sell.html')

    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        # ログインチェック(確認用ー後で削除)
        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'ログインが必要です',
                    'redirect_url': '/monotal/login/'
                }, status=401)
            return redirect('/monotal/login/')

        try:
            # FormDataから取得
            product_name = request.POST.get('product_name', '').strip()
            product_category_id = request.POST.get('product_category', '')
            brand = request.POST.get('brand', '').strip()
            product_description = request.POST.get('product_description', '').strip()
            product_condition_id = request.POST.get('product_condition', '')
            shipping_method_id = request.POST.get('shipping_method', '')
            shipping_area = request.POST.get('shipping_area', '')
            shipping_days = request.POST.get('shipping_days', '')
            rental_periods_json = request.POST.get('rental_periods', '[]')
            images = request.FILES.getlist('images')
            is_draft = request.POST.get('is_draft', 'false') == 'true'

            # rental_periodsをパース
            import json
            try:
                rental_periods = json.loads(rental_periods_json)
            except json.JSONDecodeError:
                rental_periods = []

            errors = {}

            # ========================================
            # バリデーション
            # ========================================

            if not is_draft:
                # 出品時は全て必須
                if not images:
                    errors['images'] = '商品画像を1枚以上アップロードしてください'
                elif len(images) > 10:
                    errors['images'] = '画像は最大10枚までです'

                if not product_name:
                    errors['product_name'] = '商品名は必須です'
                elif len(product_name) > 40:
                    errors['product_name'] = '商品名は40文字以内で入力してください'

                if not product_category_id:
                    errors['product_category'] = 'カテゴリーを選択してください'

                if not product_description:
                    errors['product_description'] = '商品の説明は必須です'
                elif len(product_description) > 1000:
                    errors['product_description'] = '商品の説明は1000文字以内で入力してください'

                if not product_condition_id:
                    errors['product_condition'] = '商品の状態を選択してください'

                if not shipping_method_id:
                    errors['shipping_method'] = '配送方法を選択してください'

                if not shipping_area:
                    errors['shipping_area'] = '発送元地域を選択してください'

                if not shipping_days:
                    errors['shipping_days'] = '発送までの日数を選択してください'

                # レンタル期間と価格のバリデーション
                if not rental_periods or len(rental_periods) == 0:
                    errors['rental_periods'] = '少なくとも1つのレンタル期間を選択してください'
                else:
                    has_valid_price = False
                    for period in rental_periods:
                        days = period.get('days', 0)
                        price = period.get('price', '')

                        if price and str(price).isdigit():
                            price_int = int(price)
                            if price_int > 0:
                                has_valid_price = True
                                if price_int < 100 or price_int > 9999999:
                                    errors[f'price_{days}'] = '料金は100円〜9,999,999円で設定してください'

                    if not has_valid_price:
                        errors['rental_periods'] = '少なくとも1つの期間に料金を設定してください'
            else:
                # 下書きの場合は商品名のみ必須
                if not product_name:
                    errors['product_name'] = '商品名は必須です'
                elif len(product_name) > 40:
                    errors['product_name'] = '商品名は40文字以内で入力してください'

            if errors:
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': errors}, status=400)
                return render(request, 'create_sell.html', {
                    'errors': list(errors.values()),
                })

            # ========================================
            # マスターデータ取得（registerと同じパターン）
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

            # 配送方法
            shipping_obj = None
            if shipping_method_id:
                try:
                    shipping_obj = ShippingMethod.objects.get(shipping_method_id=shipping_method_id)
                except ShippingMethod.DoesNotExist:
                    pass

            # 商品ステータス
            status_id = PRODUCT_STATUS_DRAFT if is_draft else PRODUCT_STATUS_LISTED
            try:
                status_obj = ProductStatus.objects.get(product_status_id=status_id)
            except ProductStatus.DoesNotExist:
                status_obj = ProductStatus.objects.create(
                    product_status_id=status_id,
                    status_name='下書き' if is_draft else '出品中'
                )

            # ========================================
            # 商品作成（トランザクション使用）
            # ========================================
            # rental_periodsから最初の有効な期間と価格を取得
            rental_days_value = 0
            rental_fee_value = 0

            if rental_periods:
                for period in rental_periods:
                    days = period.get('days', 0)
                    price = period.get('price', '')
                    if price and str(price).isdigit() and int(price) > 0:
                        rental_days_value = days
                        rental_fee_value = int(price)
                        break

            # トランザクション開始：エラーが発生したらすべてロールバック
            with transaction.atomic():
                product = Product.objects.create(
                    product_name=product_name,
                    product_description=product_description or '',
                    shipping_method=shipping_obj,
                    product_condition=condition_obj,
                    product_status=status_obj,
                    product_category=category_obj,
                    rental_days=rental_days_value,
                    rental_fee=rental_fee_value,
                    user=request.user
                )

                # 画像保存
                if images:
                    for index, image in enumerate(images):
                        ProductImage.objects.create(
                            product=product,
                            image=image,
                            display_order=index
                        )

            if is_ajax:
                if is_draft:
                    return JsonResponse({
                        'success': True,
                        'message': '下書きを保存しました',
#                        'redirect_url': f'/monotal/sell/edit/{product.product_id}/'
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'message': '商品を出品しました',
                        'redirect_url': '/monotal/'
                    })

            messages.success(request, '下書きを保存しました' if is_draft else '商品を出品しました')
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

        context = {
            'product': product,
            'product_images': product_images,
        }

        return render(request, self.template_name, context)


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
product_list = ProductListView.as_view()
product_detail = ProductDetailView.as_view()
interest_selection = InterestSelectionView.as_view()

# 本人確認関連
identity_verification = IdentityVerificationView.as_view()
admin_verification_list = AdminVerificationListView.as_view()
admin_verification_detail = AdminVerificationDetailView.as_view()
verification_image = VerificationImageView.as_view()
