from django.contrib.auth.backends import ModelBackend
from .models import User


class PhonePasswordBackend(ModelBackend):
    """
    電話番号とパスワードでログインするカスタム認証バックエンド

    UserStatus:
    1: 未認証ユーザー（メール認証済み、本人確認未完了）
    2: 承認済みユーザー（本人確認完了）
    3: 制限付きユーザー（違反等で制限中）
    4: 削除済みユーザー（退会済み）
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            # 電話番号でユーザーを検索
            # ステータス1,2,3のユーザーはログイン可能（4:削除済みは不可）
            user = User.objects.get(
                phone_number=username,
                user_status_id__in=[1, 2, 3]
            )
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
