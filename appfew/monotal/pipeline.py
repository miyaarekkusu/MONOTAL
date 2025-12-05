from django.shortcuts import redirect
from social_core.pipeline.partial import partial
from .models import User, UserStatus


@partial
def create_user_with_status(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        return {'is_new': False, 'user': user}

    email = details.get('email')
    if not email:
        return None

    # 既存ユーザーがいればそのままログイン
    try:
        existing_user = User.objects.get(email=email)
        return {'is_new': False, 'user': existing_user}
    except User.DoesNotExist:
        pass

    # セッションにGoogle情報を保存して追加情報入力画面へリダイレクト
    strategy.session_set('google_user_data', {
        'email': email,
        'name': details.get('fullname') or details.get('first_name', ''),
    })

    # 追加情報入力画面へリダイレクト（ユーザーは作成しない）
    return redirect('register_complete')
