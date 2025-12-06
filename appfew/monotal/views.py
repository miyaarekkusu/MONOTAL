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
from .models import User, UserStatus, EmailVerificationToken


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
        return render(request, 'common.html')


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
            # ユーザー名・電話番号: ステータス1,2,3で重複不可（4:削除済みのみ再利用可）
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

            messages.success(request, '会員登録が完了しました。')
            return redirect('index')

        except EmailVerificationToken.DoesNotExist:
            return render(request, 'verify_failed.html', {
                'message': '無効な認証リンクです。'
            })


class ProfileView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'profile.html')


class CreateSellView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'create_sell.html')


index = IndexView.as_view()
login_view = LoginView.as_view()
logout_view = LogoutView.as_view()
register = RegisterView.as_view()
register_form = RegisterFormView.as_view()
register_complete = RegisterCompleteView.as_view()
register_sent = RegisterSentView.as_view()
email_verify = EmailVerifyView.as_view()
profile = ProfileView.as_view()
create_sell = CreateSellView.as_view()
