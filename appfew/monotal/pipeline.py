from django.shortcuts import redirect
from social_core.pipeline.partial import partial
from social_django.models import UserSocialAuth
from .models import User, UserStatus


def social_user_custom(backend, uid, user=None, *args, **kwargs):
    """
    既存のソーシャル認証を確認し、関連付けられたユーザーを返す
    AuthAlreadyAssociatedエラーを回避するためのカスタム処理

    UserStatus:
    1: 未認証ユーザー（メール認証済み、本人確認未完了）
    2: 承認済みユーザー（本人確認完了）
    3: 制限付きユーザー（違反等で制限中）
    4: 削除済みユーザー（退会済み）
    """
    provider = backend.name
    social = UserSocialAuth.objects.filter(provider=provider, uid=uid).first()

    if social:
        existing_user = social.user
        # ステータス1,2,3のユーザーはログイン可能
        if existing_user.user_status_id in [1, 2, 3]:
            return {
                'social': social,
                'user': existing_user,
                'is_new': False,
                'new_association': False
            }
        # ステータス4（削除済み）は新規扱い
        social.delete()
        return {
            'social': None,
            'user': None,
            'is_new': True,
            'new_association': True
        }

    # ソーシャル認証はないが、同じメールアドレスのユーザーがいるか確認
    # （後続のパイプラインで処理）
    return {
        'social': None,
        'user': user,
        'is_new': user is None,
        'new_association': True
    }


@partial
def create_user_with_status(strategy, details, backend, user=None, social=None, *args, **kwargs):
    """
    ユーザー作成またはログインを処理するパイプライン
    - ソーシャル認証済みユーザー → そのままログイン
    - 同じメールで登録済みユーザー → ソーシャル認証を紐づけてログイン
    - 新規ユーザー → 追加情報入力画面へリダイレクト（メール認証後にユーザー作成）

    UserStatus:
    1: 未認証ユーザー（メール認証済み、本人確認未完了）
    2: 承認済みユーザー（本人確認完了）
    3: 制限付きユーザー（違反等で制限中）
    4: 削除済みユーザー（退会済み）
    """
    # 既にユーザーが存在する場合（ソーシャル認証済み）
    if user:
        return {'is_new': False, 'user': user}

    email = details.get('email')
    if not email:
        return None

    # 既存ユーザーがいればチェック（複数存在する可能性があるのでfilterを使用）
    existing_users = User.objects.filter(email=email)

    # ステータス1,2,3のユーザーがいればログイン
    active_user = existing_users.filter(user_status_id__in=[1, 2, 3]).first()
    if active_user:
        # 既存ユーザーにソーシャル認証を紐づけ、ログインさせる
        return {
            'is_new': False,
            'user': active_user,
            'new_association': True,  # ソーシャル認証を紐づけるために必要
        }

    # セッションにGoogle情報を保存して追加情報入力画面へリダイレクト
    strategy.session_set('google_user_data', {
        'email': email,
        'name': details.get('fullname') or details.get('first_name', ''),
    })

    # 追加情報入力画面へリダイレクト（ユーザーはメール認証後に作成）
    return redirect('register_complete')
