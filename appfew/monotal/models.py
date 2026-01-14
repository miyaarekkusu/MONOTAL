"""
Django Models - レンタルプラットフォーム（Rental Platform）
物理モデルERから自動生成 / Gerado automaticamente do modelo físico 
テーブル総数: 45 (マスター21 + トランザクション24)

【重要な概念 / Conceitos Importantes】

1. db_table = データベースのテーブル名を明示的に指定
   例: db_table = 'T_User' → DBに正確に「T_User」というテーブルが作成される
   
2. on_delete = 外部キーで参照されているレコードが削除された時の動作
   - CASCADE: 親を削除すると子も削除（ユーザー削除 → 住所も削除）
   - PROTECT: 子が存在する場合、親の削除を防止（ステータスを使用中の商品がある場合）
   - SET_NULL: 親削除時にNULLに設定
   
3. related_name = 逆参照時の名前（user.products.all() のように使用）

4. db_column = データベースのカラム名を明示的に指定

【テーブル構成 / Organização das Tabelas】

1. ユーザー関連 (User Domain)
   - UserStatus, User, UserManager, UserAddress
   - IdentityVerificationStatus, IdentityVerification, IdentityVerificationImage

2. ユーザー関係 (User Relationships)
   - Follow, Block, UserReview

3. 商品関連 (Product Domain)
   - ProductCategory, ProductCondition, ProductStatus, ShippingMethod
   - Product, Bookmark, BrowsingHistory

4. レンタル関連 (Rental Domain)
   - RentalStatus, RentalRequestStatus, ReturnReason
   - RentalRequest, RentalHistory, ReturnReasonHistory

5. 通報・違反関連 (Report & Violation Domain)
   - ReportReason, Report
   - ViolationReason, ViolationStatus, ViolationHistory

6. 決済・保険関連 (Payment & Insurance Domain)
   - PaymentType, PaymentInfo
   - Insurance, InsuranceEnrollmentStatus, InsuranceEnrollment

7. チャット・メッセージ関連 (Chat & Message Domain)
   - ChatRoomType, Community, ChatRoom, ChatRoomParticipant
   - Message, MessageImage, MessageReadStatus, MessageRead

8. 通知関連 (Notification Domain)
   - NotificationType, NotificationReadStatus, TargetUserType
   - Notification, NotificationRead, NotificationTargetUser
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  1. ユーザー関連 / USER DOMAIN                                                ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class UserStatus(models.Model):
    """
    ユーザーステータスマスター
    1: 未認証ユーザー（メール認証済み、本人確認未完了）
    2: 承認済みユーザー（本人確認完了）
    3: 制限付きユーザー（違反等で制限中）
    4: 削除済みユーザー（退会済み）
    """
    user_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_UserStatus'
        verbose_name = 'ユーザーステータス'
        verbose_name_plural = 'ユーザーステータス'
    
    def __str__(self):
        return self.status_name


class UserManager(BaseUserManager):
    """
    ユーザーマネージャー（カスタム）
    ユーザー作成のロジックを管理
    """
    
    def create_user(self, email, user_name, display_name, phone_number, password=None, **extra_fields):
        """通常ユーザーを作成"""
        if not phone_number:
            raise ValueError('電話番号は必須です')
        email = self.normalize_email(email) if email else ''
        user = self.model(
            email=email,
            user_name=user_name,
            display_name=display_name,
            phone_number=phone_number,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, user_name, display_name, phone_number, password=None, **extra_fields):
        """スーパーユーザー（管理者）を作成"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, user_name, display_name, phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    ユーザーテーブル（メイン）
    
    【重要ポイント】
    - AbstractBaseUserを継承 = 認証機能を持つカスタムユーザーモデル
    - USERNAME_FIELD = 'email' = ログインにメールアドレスを使用
    - user_status への参照は on_delete=PROTECT = ステータスの削除を防止
    """
    user_id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=20, default='')
    password_hash = models.CharField(max_length=255)
    login_attempt_count = models.IntegerField(default=0)
    last_login_datetime = models.DateTimeField(null=True, blank=True)
    
    user_status = models.ForeignKey(
        UserStatus,
        on_delete=models.PROTECT,
        db_column='user_status_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    delete_datetime = models.DateTimeField(null=True, blank=True)
    
    user_image = models.ImageField(upload_to='user_images/', null=True, blank=True)
    bio = models.CharField(max_length=160, blank=True, default='')  # 自己紹介文（Twitter仕様: 160文字）

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['user_name', 'display_name']

    @property
    def id(self):
        """social-auth-djangoとの互換性のため"""
        return self.user_id

    class Meta:
        db_table = 'T_User'
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
    
    def __str__(self):
        return f"{self.display_name} ({self.email})"


class EmailVerificationToken(models.Model):
    """
    メール認証トークンテーブル
    認証完了までユーザー登録情報を一時保存
    認証後にユーザーを作成する
    """
    token_id = models.AutoField(primary_key=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True)

    # 登録情報（認証後にユーザー作成に使用）
    email = models.EmailField(max_length=255)
    user_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    password_hash = models.CharField(max_length=255, blank=True, default='')  # Google認証の場合は空
    is_google_auth = models.BooleanField(default=False)  # Google認証フラグ

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'T_EmailVerificationToken'
        verbose_name = 'メール認証トークン'
        verbose_name_plural = 'メール認証トークン'

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.email} - {self.token}"


class UserAddress(models.Model):
    """
    ユーザー住所テーブル
    
    【on_deleteの説明】
    CASCADE = ユーザーが削除されたら、その住所も自動的に削除される
    """
    user_address_id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
        db_column='user_id'
    )
    
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    municipality = models.CharField(max_length=100, null=True, blank=True)
    street_address = models.CharField(max_length=200, null=True, blank=True)
    building_name = models.CharField(max_length=100, null=True, blank=True)
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'UserAddress'
        verbose_name = 'ユーザー住所'
        verbose_name_plural = 'ユーザー住所'
    
    def __str__(self):
        return f"{self.user.display_name} - {self.postal_code}"


class UserHobby(models.Model):
    """
    ユーザー趣味テーブル
    ユーザーの興味のあるカテゴリを管理
    """
    user_hobby_id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hobbies',
        db_column='user_id'
    )
    product_category = models.ForeignKey(
        'ProductCategory',
        on_delete=models.CASCADE,
        db_column='product_category_id'
    )

    register_datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'T_UserHobby'
        verbose_name = 'ユーザー趣味'
        verbose_name_plural = 'ユーザー趣味'
        unique_together = [['user', 'product_category']]

    def __str__(self):
        return f"{self.user.user_name} - {self.product_category.category_name}"


# ────────────────────────────────────────────────────────────────────────────────
# 本人確認 / Identity Verification
# ────────────────────────────────────────────────────────────────────────────────

class IdentityVerificationStatus(models.Model):
    """
    本人確認ステータスマスター
    例: 未確認、確認済み、却下
    """
    identity_verification_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_IdentityVerificationStatus'
        verbose_name = '本人確認ステータス'
        verbose_name_plural = '本人確認ステータス'
    
    def __str__(self):
        return self.status_name


class IdentityVerification(models.Model):
    """
    本人確認テーブル
    ユーザーの本人確認申請と結果を管理
    """
    identity_verification_id = models.AutoField(primary_key=True)
    
    identity_verification_status = models.ForeignKey(
        IdentityVerificationStatus,
        on_delete=models.PROTECT,
        db_column='identity_verification_status_id'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id'
    )
    
    rejection_datetime = models.DateTimeField(null=True, blank=True)
    approval_datetime = models.DateTimeField(null=True, blank=True)
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'T_IdentityVerification'
        verbose_name = '本人確認'
        verbose_name_plural = '本人確認'
    
    def __str__(self):
        return f"{self.user.display_name} - {self.identity_verification_status}"


class IdentityVerificationImage(models.Model):
    """
    本人確認画像テーブル
    身分証明書の画像データを保存
    """
    identity_verification_image_id = models.AutoField(primary_key=True)
    
    identity_verification = models.ForeignKey(
        IdentityVerification,
        on_delete=models.CASCADE,
        related_name='images',
        db_column='identity_verification_id'
    )
    
    image_data = models.BinaryField()
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_IdentityVerificationImage'
        verbose_name = '本人確認画像'
        verbose_name_plural = '本人確認画像'


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  2. ユーザー関係 / USER RELATIONSHIPS                                         ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class Follow(models.Model):
    """
    フォローテーブル
    ユーザー間のフォロー関係を管理
    
    【unique_together の説明】
    同じユーザーを2回フォローできないように、
    (follower_user, followed_user) の組み合わせを一意にする
    """
    follow_id = models.AutoField(primary_key=True)
    
    follower_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        db_column='follower_user_id'
    )
    followed_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        db_column='followed_user_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_Follow'
        verbose_name = 'フォロー'
        verbose_name_plural = 'フォロー'
        unique_together = [['follower_user', 'followed_user']]
    
    def __str__(self):
        return f"{self.follower_user.display_name}が{self.followed_user.display_name}をフォロー"


class Block(models.Model):
    """
    ブロックテーブル
    ユーザー間のブロック関係を管理
    """
    block_id = models.AutoField(primary_key=True)
    
    blocker_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocking',
        db_column='blocker_user_id'
    )
    blocked_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by',
        db_column='blocked_user_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_Block'
        verbose_name = 'ブロック'
        verbose_name_plural = 'ブロック'
        unique_together = [['blocker_user', 'blocked_user']]
    
    def __str__(self):
        return f"{self.blocker_user.display_name}が{self.blocked_user.display_name}をブロック"


class UserReview(models.Model):
    """
    ユーザー評価テーブル
    ユーザー間の評価とレビューを管理
    """
    user_review_id = models.AutoField(primary_key=True)
    
    reviewer_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_given',
        db_column='reviewer_user_id'
    )
    reviewed_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        db_column='reviewed_user_id'
    )
    
    review_content = models.CharField(max_length=1000, null=True, blank=True)
    review_score = models.DecimalField(max_digits=3, decimal_places=2)
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'T_UserReview'
        verbose_name = 'ユーザー評価'
        verbose_name_plural = 'ユーザー評価'
    
    def __str__(self):
        return f"{self.reviewer_user.display_name} → {self.reviewed_user.display_name}: {self.review_score}"


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  3. 商品関連 / PRODUCT DOMAIN                                                 ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class ProductCategory(models.Model):
    """
    商品カテゴリマスター（階層構造対応）
    例: 電化製品 > ノートパソコン
    
    【階層構造の説明】
    parent_product_category = Noneの場合、親カテゴリ（ルート）
    parent_product_category = 他のカテゴリの場合、子カテゴリ
    """
    product_category_id = models.AutoField(primary_key=True)
    
    parent_product_category = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        db_column='parent_product_category_id'
    )
    
    category_name = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'M_ProductCategory'
        verbose_name = '商品カテゴリ'
        verbose_name_plural = '商品カテゴリ'
    
    def __str__(self):
        return self.category_name


class ProductCondition(models.Model):
    """
    商品状態マスター
    例: 新品、中古良好、使用感あり
    """
    product_condition_id = models.AutoField(primary_key=True)
    condition_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_ProductCondition'
        verbose_name = '商品状態'
        verbose_name_plural = '商品状態'
    
    def __str__(self):
        return self.condition_name


class ProductStatus(models.Model):
    """
    商品ステータスマスター
    例: 貸出可能、貸出中、メンテナンス中、非公開
    """
    product_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_ProductStatus'
        verbose_name = '商品ステータス'
        verbose_name_plural = '商品ステータス'
    
    def __str__(self):
        return self.status_name


class ShippingMethod(models.Model):
    """
    配送方法マスター
    例: 宅配便、郵便、直接手渡し
    """
    shipping_method_id = models.AutoField(primary_key=True)
    shipping_method_name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'M_ShippingMethod'
        verbose_name = '配送方法'
        verbose_name_plural = '配送方法'
    
    def __str__(self):
        return self.shipping_method_name


class Product(models.Model):
    """
    商品テーブル
    レンタル可能な商品を管理
    
    【on_delete の使い分け】
    - マスターデータ（ステータス、カテゴリなど）: PROTECT
    - オーナー（ユーザー）: CASCADE
    """
    product_id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=200)
    product_description = models.CharField(max_length=2000, null=True, blank=True)
    
    # 外部キー: マスターデータ（全てPROTECT）
    shipping_method = models.ForeignKey(
        ShippingMethod,
        on_delete=models.PROTECT,
        db_column='shipping_method_id'
    )
    product_condition = models.ForeignKey(
        ProductCondition,
        on_delete=models.PROTECT,
        db_column='product_condition_id'
    )
    product_status = models.ForeignKey(
        ProductStatus,
        on_delete=models.PROTECT,
        db_column='product_status_id'
    )
    product_category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        db_column='product_category_id'
    )
    
    # レンタル情報
    rental_days = models.IntegerField()
    rental_fee = models.DecimalField(max_digits=10, decimal_places=2)
    contract_datetime = models.DateTimeField(null=True, blank=True)
    listing_stop_datetime = models.DateTimeField(null=True, blank=True)
    
    # 外部キー: オーナー（CASCADE）
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='products',
        db_column='user_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    delete_datetime = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'T_Product'
        verbose_name = '商品'
        verbose_name_plural = '商品'
    
    def __str__(self):
        return self.product_name


class ProductImage(models.Model):
    """
    商品画像テーブル
    商品の画像を管理（複数画像対応）

    【CASCADE の理由】
    商品が削除されたら、その画像も不要になるため
    """
    product_image_id = models.AutoField(primary_key=True)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        db_column='product_id'
    )

    image = models.ImageField(upload_to='product_images/')
    display_order = models.IntegerField(default=0)  # 表示順序（0が最初）
    register_datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'T_ProductImage'
        verbose_name = '商品画像'
        verbose_name_plural = '商品画像'
        ordering = ['display_order', 'product_image_id']

    def __str__(self):
        return f"{self.product.product_name} - 画像 {self.display_order + 1}"


class Bookmark(models.Model):
    """
    お気に入りテーブル
    ユーザーがお気に入り登録した商品を管理
    """
    bookmark_id = models.AutoField(primary_key=True)
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        db_column='product_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='bookmarks', 
        db_column='user_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_Bookmark'
        verbose_name = 'お気に入り'
        verbose_name_plural = 'お気に入り'
        unique_together = [['product', 'user']]
    
    def __str__(self):
        return f"{self.user.display_name} - {self.product.product_name}"


class BrowsingHistory(models.Model):
    """
    閲覧履歴テーブル
    ユーザーの商品閲覧履歴を記録
    """
    browsing_history_id = models.AutoField(primary_key=True)
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        db_column='product_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='browsing_history', 
        db_column='user_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_BrowsingHistory'
        verbose_name = '閲覧履歴'
        verbose_name_plural = '閲覧履歴'


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  4. レンタル関連 / RENTAL DOMAIN                                              ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class RentalStatus(models.Model):
    """
    レンタルステータスマスター
    例: 予約中、貸出中、返却済み、キャンセル
    """
    rental_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_RentalStatus'
        verbose_name = 'レンタルステータス'
        verbose_name_plural = 'レンタルステータス'
    
    def __str__(self):
        return self.status_name


class RentalRequestStatus(models.Model):
    """
    レンタルリクエストステータスマスター
    例: 申請中、承認済み、却下、キャンセル
    """
    rental_request_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_RentalRequestStatus'
        verbose_name = 'レンタルリクエストステータス'
        verbose_name_plural = 'レンタルリクエストステータス'
    
    def __str__(self):
        return self.status_name


class ReturnReason(models.Model):
    """
    返却理由マスター
    例: 破損、紛失、期間延長希望
    """
    return_reason_id = models.AutoField(primary_key=True)
    return_reason_name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'M_ReturnReason'
        verbose_name = '返却理由'
        verbose_name_plural = '返却理由'
    
    def __str__(self):
        return self.return_reason_name


class RentalRequest(models.Model):
    """
    レンタルリクエストテーブル
    レンタルの申請と承認プロセスを管理
    """
    rental_request_id = models.AutoField(primary_key=True)
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.PROTECT, 
        db_column='product_id'
    )
    requester_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rental_requests_made',
        db_column='requester_user_id'
    )
    requested_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rental_requests_received',
        db_column='requested_user_id'
    )
    rental_request_status = models.ForeignKey(
        RentalRequestStatus,
        on_delete=models.PROTECT,
        db_column='rental_request_status_id'
    )
    
    approval_datetime = models.DateTimeField(null=True, blank=True)
    rejection_datetime = models.DateTimeField(null=True, blank=True)
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'T_RentalRequest'
        verbose_name = 'レンタルリクエスト'
        verbose_name_plural = 'レンタルリクエスト'


class RentalHistory(models.Model):
    """
    レンタル履歴テーブル
    
    【重要: on_delete=PROTECT を使用】
    履歴データは監査、分析、トラブル対応に必要なため、
    関連するユーザーや商品が削除されても履歴は保持する必要がある
    → PROTECTを使用し、履歴がある場合は削除を防止
    """
    rental_history_id = models.AutoField(primary_key=True)
    
    # 外部キー: 全てPROTECT（履歴保護）
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        db_column='product_id'
    )
    lender_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='rentals_as_lender',
        db_column='lender_user_id'
    )
    renter_user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='rentals_as_renter',
        db_column='renter_user_id'
    )
    rental_status = models.ForeignKey(
        RentalStatus,
        on_delete=models.PROTECT,
        db_column='rental_status_id'
    )
    
    shipping_completed_datetime = models.DateTimeField(null=True, blank=True)
    rental_start_datetime = models.DateTimeField(null=True, blank=True)
    rental_end_datetime = models.DateTimeField(null=True, blank=True)
    receipt_completed_datetime = models.DateTimeField(null=True, blank=True)
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'T_RentalHistory'
        verbose_name = 'レンタル履歴'
        verbose_name_plural = 'レンタル履歴'
    
    def __str__(self):
        return f"{self.product.product_name} - {self.renter_user.display_name}"


class ReturnReasonHistory(models.Model):
    """
    返却理由履歴テーブル
    商品返却時の理由と詳細を記録
    """
    return_history_id = models.AutoField(primary_key=True)
    
    rental_history = models.ForeignKey(
        RentalHistory,
        on_delete=models.CASCADE,
        db_column='rental_history_id'
    )
    return_reason = models.ForeignKey(
        ReturnReason,
        on_delete=models.PROTECT,
        db_column='return_reason_id'
    )
    
    return_request_datetime = models.DateTimeField()
    return_completed_datetime = models.DateTimeField(null=True, blank=True)
    return_reason_detail = models.CharField(max_length=1000, null=True, blank=True)
    return_status_id = models.IntegerField(null=True, blank=True)
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'T_ReturnReason'
        verbose_name = '返却理由履歴'
        verbose_name_plural = '返却理由履歴'


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  5. 通報・違反関連 / REPORT & VIOLATION DOMAIN                                ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class ReportReason(models.Model):
    """
    通報理由マスター
    例: 不適切なコンテンツ、詐欺、規約違反
    """
    report_reason_id = models.AutoField(primary_key=True)
    report_reason_name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'M_ReportReason'
        verbose_name = '通報理由'
        verbose_name_plural = '通報理由'
    
    def __str__(self):
        return self.report_reason_name


class Report(models.Model):
    """
    通報テーブル
    不適切なユーザーや商品の通報を管理
    """
    report_id = models.AutoField(primary_key=True)
    
    reporter_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_made',
        db_column='reporter_user_id'
    )
    report_reason = models.ForeignKey(
        ReportReason,
        on_delete=models.PROTECT,
        db_column='report_reason_id'
    )
    
    report_detail = models.CharField(max_length=1000, null=True, blank=True)
    report_datetime = models.DateTimeField()
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_Report'
        verbose_name = '通報'
        verbose_name_plural = '通報'


# ────────────────────────────────────────────────────────────────────────────────
# 違反 / Violation
# ────────────────────────────────────────────────────────────────────────────────

class ViolationReason(models.Model):
    """
    違反理由マスター
    例: スパム行為、支払い遅延、商品破損
    """
    violation_reason_id = models.AutoField(primary_key=True)
    violation_reason_name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        db_table = 'M_ViolationReason'
        verbose_name = '違反理由'
        verbose_name_plural = '違反理由'
    
    def __str__(self):
        return self.violation_reason_name


class ViolationStatus(models.Model):
    """
    違反ステータスマスター
    例: 警告中、停止中、解除済み
    """
    violation_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_ViolationStatus'
        verbose_name = '違反ステータス'
        verbose_name_plural = '違反ステータス'
    
    def __str__(self):
        return self.status_name


class ViolationHistory(models.Model):
    """
    違反履歴テーブル
    ユーザーの規約違反履歴を管理
    """
    violation_history_id = models.AutoField(primary_key=True)
    
    violation_reason = models.ForeignKey(
        ViolationReason,
        on_delete=models.PROTECT,
        db_column='violation_reason_id'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='violations',
        db_column='user_id'
    )
    violation_status = models.ForeignKey(
        ViolationStatus,
        on_delete=models.PROTECT,
        db_column='violation_status_id'
    )
    
    violation_detail = models.CharField(max_length=1000, null=True, blank=True)
    violation_release_datetime = models.DateTimeField(null=True, blank=True)
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_ViolationHistory'
        verbose_name = '違反履歴'
        verbose_name_plural = '違反履歴'


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  6. 決済・保険関連 / PAYMENT & INSURANCE DOMAIN                               ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class PaymentType(models.Model):
    """
    支払い方法マスター
    例: クレジットカード、デビットカード、銀行振込、電子マネー
    """
    payment_type_id = models.AutoField(primary_key=True)
    payment_type_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_PaymentType'
        verbose_name = '支払い方法'
        verbose_name_plural = '支払い方法'
    
    def __str__(self):
        return self.payment_type_name


class PaymentInfo(models.Model):
    """
    支払い情報テーブル
    ユーザーの支払い方法を管理
    """
    payment_info_id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='payment_info', 
        db_column='user_id'
    )
    payment_type = models.ForeignKey(
        PaymentType, 
        on_delete=models.PROTECT, 
        db_column='payment_type_id'
    )
    
    transfer_name = models.CharField(max_length=100, null=True, blank=True)
    card_token = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        db_table = 'T_PaymentInfo'
        verbose_name = '支払い情報'
        verbose_name_plural = '支払い情報'


# ────────────────────────────────────────────────────────────────────────────────
# 保険 / Insurance
# ────────────────────────────────────────────────────────────────────────────────

class Insurance(models.Model):
    """
    保険マスター
    商品レンタル時の保険商品
    """
    insurance_id = models.AutoField(primary_key=True)
    insurance_name = models.CharField(max_length=100, null=True, blank=True)
    insurance_description = models.CharField(max_length=1000, null=True, blank=True)
    insurance_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        db_table = 'M_Insurance'
        verbose_name = '保険'
        verbose_name_plural = '保険'
    
    def __str__(self):
        return self.insurance_name or f'保険 {self.insurance_id}'


class InsuranceEnrollmentStatus(models.Model):
    """
    保険加入ステータスマスター
    例: 未加入、加入中、解約済み
    """
    insurance_enrollment_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_InsuranceEnrollmentStatus'
        verbose_name = '保険加入ステータス'
        verbose_name_plural = '保険加入ステータス'
    
    def __str__(self):
        return self.status_name


class InsuranceEnrollment(models.Model):
    """
    保険加入テーブル
    ユーザーの保険加入状況を管理
    """
    insurance_enrollment_id = models.AutoField(primary_key=True)
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='user_id'
    )
    insurance = models.ForeignKey(
        Insurance, 
        on_delete=models.PROTECT, 
        db_column='insurance_id'
    )
    
    insurance_start_datetime = models.DateTimeField()
    insurance_end_datetime = models.DateTimeField()
    
    class Meta:
        db_table = 'T_InsuranceEnrollment'
        verbose_name = '保険加入'
        verbose_name_plural = '保険加入'


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  7. チャット・メッセージ関連 / CHAT & MESSAGE DOMAIN                           ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class ChatRoomType(models.Model):
    """
    チャットルームタイプマスター
    例: 1対1、グループ、商品チャット、コミュニティチャット
    """
    chat_room_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        db_table = 'M_ChatRoomType'
        verbose_name = 'チャットルームタイプ'
        verbose_name_plural = 'チャットルームタイプ'
    
    def __str__(self):
        return self.type_name or f'タイプ {self.chat_room_type_id}'


class Community(models.Model):
    """
    コミュニティテーブル
    ユーザーコミュニティを管理
    """
    community_id = models.AutoField(primary_key=True)
    community_name = models.CharField(max_length=200, null=True, blank=True)
    
    class Meta:
        db_table = 'T_Community'
        verbose_name = 'コミュニティ'
        verbose_name_plural = 'コミュニティ'
    
    def __str__(self):
        return self.community_name or f'コミュニティ {self.community_id}'


class ChatRoom(models.Model):
    """
    チャットルームテーブル
    ユーザー間、商品、コミュニティのチャットルームを管理
    """
    chat_room_id = models.AutoField(primary_key=True)
    
    chat_room_type = models.ForeignKey(
        ChatRoomType, 
        on_delete=models.PROTECT, 
        db_column='chat_room_type_id'
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        db_column='product_id'
    )
    community = models.ForeignKey(
        Community, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        db_column='community_id'
    )
    
    class Meta:
        db_table = 'T_ChatRoom'
        verbose_name = 'チャットルーム'
        verbose_name_plural = 'チャットルーム'


class ChatRoomParticipant(models.Model):
    """
    チャットルーム参加者テーブル
    各チャットルームの参加ユーザーを管理
    """
    chat_room_participant_id = models.AutoField(primary_key=True)
    
    chat_room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        db_column='chat_room_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='user_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_ChatRoomParticipant'
        verbose_name = 'チャットルーム参加者'
        verbose_name_plural = 'チャットルーム参加者'
        unique_together = [['chat_room', 'user']]


class Message(models.Model):
    """
    メッセージテーブル
    チャット内のメッセージを管理
    """
    message_id = models.AutoField(primary_key=True)
    
    chat_room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name='messages', 
        db_column='chat_room_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='user_id'
    )
    
    message_content = models.CharField(max_length=2000, null=True, blank=True)
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_Message'
        verbose_name = 'メッセージ'
        verbose_name_plural = 'メッセージ'


class MessageImage(models.Model):
    """
    メッセージ画像テーブル
    メッセージに添付された画像を管理
    """
    message_image_id = models.AutoField(primary_key=True)
    
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='images', 
        db_column='message_id'
    )
    
    image_data = models.BinaryField()
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_MessageImage'
        verbose_name = 'メッセージ画像'
        verbose_name_plural = 'メッセージ画像'


class MessageReadStatus(models.Model):
    """
    メッセージ既読ステータスマスター
    例: 未読、既読
    """
    message_read_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_MessageReadStatus'
        verbose_name = 'メッセージ既読ステータス'
        verbose_name_plural = 'メッセージ既読ステータス'
    
    def __str__(self):
        return self.status_name


class MessageRead(models.Model):
    """
    メッセージ既読テーブル
    各ユーザーのメッセージ既読状態を管理
    """
    message_read_id = models.AutoField(primary_key=True)
    
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        db_column='message_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='user_id'
    )
    message_read_status = models.ForeignKey(
        MessageReadStatus, 
        on_delete=models.PROTECT, 
        db_column='message_read_status_id'
    )
    
    read_datetime = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'T_MessageRead'
        verbose_name = 'メッセージ既読'
        verbose_name_plural = 'メッセージ既読'
        unique_together = [['message', 'user']]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  8. 通知関連 / NOTIFICATION DOMAIN                                            ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

class NotificationType(models.Model):
    """
    通知タイプマスター
    例: システム通知、メッセージ通知、レンタル通知
    """
    notification_type_id = models.AutoField(primary_key=True)
    notification_type_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_NotificationType'
        verbose_name = '通知タイプ'
        verbose_name_plural = '通知タイプ'
    
    def __str__(self):
        return self.notification_type_name


class NotificationReadStatus(models.Model):
    """
    通知既読ステータスマスター
    例: 未読、既読
    """
    notification_read_status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'M_NotificationReadStatus'
        verbose_name = '通知既読ステータス'
        verbose_name_plural = '通知既読ステータス'
    
    def __str__(self):
        return self.status_name


class TargetUserType(models.Model):
    """
    ターゲットユーザータイプマスター
    通知の対象ユーザータイプを管理
    """
    target_user_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        db_table = 'M_TargetUserType'
        verbose_name = 'ターゲットユーザータイプ'
        verbose_name_plural = 'ターゲットユーザータイプ'
    
    def __str__(self):
        return self.type_name or f'タイプ {self.target_user_type_id}'


class Notification(models.Model):
    """
    通知テーブル
    システムからユーザーへの通知を管理
    """
    notification_id = models.AutoField(primary_key=True)
    
    notification_type = models.ForeignKey(
        NotificationType, 
        on_delete=models.PROTECT, 
        db_column='notification_type_id'
    )
    
    notification_title = models.CharField(max_length=200)
    notification_detail = models.CharField(max_length=1000, null=True, blank=True)
    link_url = models.CharField(max_length=500, null=True, blank=True)
    
    class Meta:
        db_table = 'T_Notification'
        verbose_name = '通知'
        verbose_name_plural = '通知'


class NotificationRead(models.Model):
    """
    通知既読テーブル
    各ユーザーの通知既読状態を管理
    """
    notification_read_id = models.AutoField(primary_key=True)
    
    notification = models.ForeignKey(
        Notification, 
        on_delete=models.CASCADE, 
        db_column='notification_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='user_id'
    )
    notification_read_status = models.ForeignKey(
        NotificationReadStatus,
        on_delete=models.PROTECT,
        db_column='notification_read_status_id'
    )
    
    read_datetime = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'T_NotificationRead'
        verbose_name = '通知既読'
        verbose_name_plural = '通知既読'
        unique_together = [['notification', 'user']]


class NotificationTargetUser(models.Model):
    """
    通知ターゲットユーザーテーブル
    通知の送信対象ユーザーを管理
    """
    notification_target_user_id = models.AutoField(primary_key=True)
    
    notification = models.ForeignKey(
        Notification, 
        on_delete=models.CASCADE, 
        db_column='notification_id'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='user_id'
    )
    
    register_datetime = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'T_NotificationTargetUser'
        verbose_name = '通知ターゲットユーザー'
        verbose_name_plural = '通知ターゲットユーザー'
        unique_together = [['notification', 'user']]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║  補足説明 / ADDITIONAL NOTES                                                  ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""
【on_delete の選択基準】

1. models.CASCADE
   使用場面: 親がなければ子も不要な場合
   例: 
   - User → UserAddress（ユーザー削除 → 住所も削除）
   - Product → ProductImage（商品削除 → 画像も削除）
   - ChatRoom → Message（ルーム削除 → メッセージも削除）

2. models.PROTECT
   使用場面: 重要なデータ、削除してはいけないデータ
   例:
   - マスターデータ全般（Status → Product など）
   - 履歴データ（User → RentalHistory など）
   - 監査が必要なデータ

3. models.SET_NULL
   使用場面: 参照は残すが親は削除したい
   注意: null=True が必要
   例:
   - User → Article（ユーザー削除後も記事は残す）

【db_table の必要性】

指定しない場合: 'appname_modelname' という名前になる
指定する場合: 正確に指定した名前になる

例:
class User(models.Model):
    class Meta:
        db_table = 'T_User'  # テーブル名は正確に「T_User」

【related_name の使い方】

user.products.all()  # ユーザーの全商品
user.addresses.all()  # ユーザーの全住所  
user.following.all()  # フォロー中のユーザー
user.followers.all()  # フォロワー一覧


【テーブル一覧 / TABLE INDEX】

┌─────────────────────────────────────────────────────────────────────────────┐
│ DOMAIN                    │ MASTER (M_)           │ TRANSACTION (T_)        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. User                   │ UserStatus            │ User                    │
│                           │ IdentityVerification- │ UserAddress             │
│                           │   Status              │ IdentityVerification    │
│                           │                       │ IdentityVerificationImg │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. User Relations         │ -                     │ Follow                  │
│                           │                       │ Block                   │
│                           │                       │ UserReview              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Product                │ ProductCategory       │ Product                 │
│                           │ ProductCondition      │ Bookmark                │
│                           │ ProductStatus         │ BrowsingHistory         │
│                           │ ShippingMethod        │                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Rental                 │ RentalStatus          │ RentalRequest           │
│                           │ RentalRequestStatus   │ RentalHistory           │
│                           │ ReturnReason          │ ReturnReasonHistory     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. Report & Violation     │ ReportReason          │ Report                  │
│                           │ ViolationReason       │ ViolationHistory        │
│                           │ ViolationStatus       │                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 6. Payment & Insurance    │ PaymentType           │ PaymentInfo             │
│                           │ Insurance             │ InsuranceEnrollment     │
│                           │ InsuranceEnrollment-  │                         │
│                           │   Status              │                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 7. Chat & Message         │ ChatRoomType          │ Community               │
│                           │ MessageReadStatus     │ ChatRoom                │
│                           │                       │ ChatRoomParticipant     │
│                           │                       │ Message                 │
│                           │                       │ MessageImage            │
│                           │                       │ MessageRead             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 8. Notification           │ NotificationType      │ Notification            │
│                           │ NotificationReadStatus│ NotificationRead        │
│                           │ TargetUserType        │ NotificationTargetUser  │
└─────────────────────────────────────────────────────────────────────────────┘

Total: 21 Master Tables + 24 Transaction Tables = 45 Tables
"""