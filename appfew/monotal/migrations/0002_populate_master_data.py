"""
マスターテーブル初期データ投入マイグレーション
"""
from django.db import migrations


def populate_master_data(apps, schema_editor):
    """全マスターテーブルに初期データを投入"""

    # 1. UserStatus（ユーザーステータス）
    UserStatus = apps.get_model('monotal', 'UserStatus')
    user_statuses = [
        {'user_status_id': 1, 'status_name': '未認証ユーザー'},
        {'user_status_id': 2, 'status_name': '承認済みユーザー'},
        {'user_status_id': 3, 'status_name': '制限付きユーザー'},
        {'user_status_id': 4, 'status_name': '削除済みユーザー'},
    ]
    for data in user_statuses:
        UserStatus.objects.get_or_create(user_status_id=data['user_status_id'], defaults=data)

    # 2. IdentityVerificationStatus（本人確認ステータス）
    IdentityVerificationStatus = apps.get_model('monotal', 'IdentityVerificationStatus')
    verification_statuses = [
        {'identity_verification_status_id': 0, 'status_name': '審査待ち'},
        {'identity_verification_status_id': 1, 'status_name': '承認済み'},
        {'identity_verification_status_id': 2, 'status_name': '却下'},
    ]
    for data in verification_statuses:
        IdentityVerificationStatus.objects.get_or_create(
            identity_verification_status_id=data['identity_verification_status_id'],
            defaults=data
        )

    # 3. Prefecture（都道府県）
    Prefecture = apps.get_model('monotal', 'Prefecture')
    prefectures = [
        ('01', '北海道'), ('02', '青森県'), ('03', '岩手県'), ('04', '宮城県'),
        ('05', '秋田県'), ('06', '山形県'), ('07', '福島県'), ('08', '茨城県'),
        ('09', '栃木県'), ('10', '群馬県'), ('11', '埼玉県'), ('12', '千葉県'),
        ('13', '東京都'), ('14', '神奈川県'), ('15', '新潟県'), ('16', '富山県'),
        ('17', '石川県'), ('18', '福井県'), ('19', '山梨県'), ('20', '長野県'),
        ('21', '岐阜県'), ('22', '静岡県'), ('23', '愛知県'), ('24', '三重県'),
        ('25', '滋賀県'), ('26', '京都府'), ('27', '大阪府'), ('28', '兵庫県'),
        ('29', '奈良県'), ('30', '和歌山県'), ('31', '鳥取県'), ('32', '島根県'),
        ('33', '岡山県'), ('34', '広島県'), ('35', '山口県'), ('36', '徳島県'),
        ('37', '香川県'), ('38', '愛媛県'), ('39', '高知県'), ('40', '福岡県'),
        ('41', '佐賀県'), ('42', '長崎県'), ('43', '熊本県'), ('44', '大分県'),
        ('45', '宮崎県'), ('46', '鹿児島県'), ('47', '沖縄県'),
    ]
    for code, name in prefectures:
        Prefecture.objects.get_or_create(prefecture_code=code, defaults={'prefecture_name': name})

    # 4. ProductCondition（商品状態）
    ProductCondition = apps.get_model('monotal', 'ProductCondition')
    conditions = [
        {'product_condition_id': 1, 'condition_name': '新品・未使用'},
        {'product_condition_id': 2, 'condition_name': '未使用に近い'},
        {'product_condition_id': 3, 'condition_name': '目立った傷や汚れなし'},
        {'product_condition_id': 4, 'condition_name': 'やや傷や汚れあり'},
        {'product_condition_id': 5, 'condition_name': '傷や汚れあり'},
        {'product_condition_id': 6, 'condition_name': '全体的に状態が悪い'},
    ]
    for data in conditions:
        ProductCondition.objects.get_or_create(product_condition_id=data['product_condition_id'], defaults=data)

    # 5. ProductStatus（商品ステータス）
    ProductStatus = apps.get_model('monotal', 'ProductStatus')
    product_statuses = [
        {'product_status_id': 1, 'status_name': '貸出可能'},
        {'product_status_id': 2, 'status_name': '貸出中'},
        {'product_status_id': 3, 'status_name': 'メンテナンス中'},
        {'product_status_id': 4, 'status_name': '非公開'},
    ]
    for data in product_statuses:
        ProductStatus.objects.get_or_create(product_status_id=data['product_status_id'], defaults=data)

    # 6. ShippingMethod（配送方法）
    ShippingMethod = apps.get_model('monotal', 'ShippingMethod')
    shipping_methods = [
        {'shipping_method_id': 1, 'shipping_method_name': '未定'},
        {'shipping_method_id': 2, 'shipping_method_name': 'らくらくメルカリ便'},
        {'shipping_method_id': 3, 'shipping_method_name': 'ゆうゆうメルカリ便'},
        {'shipping_method_id': 4, 'shipping_method_name': 'ゆうメール'},
        {'shipping_method_id': 5, 'shipping_method_name': 'レターパック'},
        {'shipping_method_id': 6, 'shipping_method_name': '普通郵便'},
        {'shipping_method_id': 7, 'shipping_method_name': 'クロネコヤマト'},
        {'shipping_method_id': 8, 'shipping_method_name': 'ゆうパック'},
        {'shipping_method_id': 9, 'shipping_method_name': 'クリックポスト'},
        {'shipping_method_id': 10, 'shipping_method_name': 'ゆうパケット'},
    ]
    for data in shipping_methods:
        ShippingMethod.objects.get_or_create(shipping_method_id=data['shipping_method_id'], defaults=data)

    # 7. ShippingDays（発送日数）
    ShippingDays = apps.get_model('monotal', 'ShippingDays')
    shipping_days = [
        {'shipping_days_id': 1, 'days_label': '1〜2日で発送', 'days_min': 1, 'days_max': 2, 'display_order': 1},
        {'shipping_days_id': 2, 'days_label': '2〜3日で発送', 'days_min': 2, 'days_max': 3, 'display_order': 2},
        {'shipping_days_id': 3, 'days_label': '4〜7日で発送', 'days_min': 4, 'days_max': 7, 'display_order': 3},
    ]
    for data in shipping_days:
        ShippingDays.objects.get_or_create(shipping_days_id=data['shipping_days_id'], defaults=data)

    # 8. RentalStatus（レンタルステータス）
    RentalStatus = apps.get_model('monotal', 'RentalStatus')
    rental_statuses = [
        {'rental_status_id': 1, 'status_name': '予約中'},
        {'rental_status_id': 2, 'status_name': '貸出中'},
        {'rental_status_id': 3, 'status_name': '返却済み'},
        {'rental_status_id': 4, 'status_name': 'キャンセル'},
    ]
    for data in rental_statuses:
        RentalStatus.objects.get_or_create(rental_status_id=data['rental_status_id'], defaults=data)

    # 9. RentalRequestStatus（レンタルリクエストステータス）
    RentalRequestStatus = apps.get_model('monotal', 'RentalRequestStatus')
    request_statuses = [
        {'rental_request_status_id': 1, 'status_name': '申請中'},
        {'rental_request_status_id': 2, 'status_name': '承認済み'},
        {'rental_request_status_id': 3, 'status_name': '却下'},
        {'rental_request_status_id': 4, 'status_name': 'キャンセル'},
    ]
    for data in request_statuses:
        RentalRequestStatus.objects.get_or_create(
            rental_request_status_id=data['rental_request_status_id'],
            defaults=data
        )

    # 10. ReturnReason（返却理由）
    ReturnReason = apps.get_model('monotal', 'ReturnReason')
    return_reasons = [
        {'return_reason_id': 1, 'return_reason_name': '通常返却'},
        {'return_reason_id': 2, 'return_reason_name': '破損'},
        {'return_reason_id': 3, 'return_reason_name': '紛失'},
        {'return_reason_id': 4, 'return_reason_name': '期間延長希望'},
    ]
    for data in return_reasons:
        ReturnReason.objects.get_or_create(return_reason_id=data['return_reason_id'], defaults=data)

    # 11. ReportReason（通報理由）
    ReportReason = apps.get_model('monotal', 'ReportReason')
    report_reasons = [
        {'report_reason_id': 1, 'report_reason_name': '不適切なコンテンツ'},
        {'report_reason_id': 2, 'report_reason_name': '詐欺'},
        {'report_reason_id': 3, 'report_reason_name': '規約違反'},
        {'report_reason_id': 4, 'report_reason_name': 'スパム'},
        {'report_reason_id': 5, 'report_reason_name': 'その他'},
    ]
    for data in report_reasons:
        ReportReason.objects.get_or_create(report_reason_id=data['report_reason_id'], defaults=data)

    # 12. ViolationReason（違反理由）
    ViolationReason = apps.get_model('monotal', 'ViolationReason')
    violation_reasons = [
        {'violation_reason_id': 1, 'violation_reason_name': 'スパム行為'},
        {'violation_reason_id': 2, 'violation_reason_name': '支払い遅延'},
        {'violation_reason_id': 3, 'violation_reason_name': '商品破損'},
        {'violation_reason_id': 4, 'violation_reason_name': '規約違反'},
    ]
    for data in violation_reasons:
        ViolationReason.objects.get_or_create(violation_reason_id=data['violation_reason_id'], defaults=data)

    # 13. ViolationStatus（違反ステータス）
    ViolationStatus = apps.get_model('monotal', 'ViolationStatus')
    violation_statuses = [
        {'violation_status_id': 1, 'status_name': '警告中'},
        {'violation_status_id': 2, 'status_name': '停止中'},
        {'violation_status_id': 3, 'status_name': '解除済み'},
    ]
    for data in violation_statuses:
        ViolationStatus.objects.get_or_create(violation_status_id=data['violation_status_id'], defaults=data)

    # 14. PaymentType（支払い方法）
    PaymentType = apps.get_model('monotal', 'PaymentType')
    payment_types = [
        {'payment_type_id': 1, 'payment_type_name': 'クレジットカード'},
        {'payment_type_id': 2, 'payment_type_name': 'デビットカード'},
        {'payment_type_id': 3, 'payment_type_name': '銀行振込'},
        {'payment_type_id': 4, 'payment_type_name': '電子マネー'},
    ]
    for data in payment_types:
        PaymentType.objects.get_or_create(payment_type_id=data['payment_type_id'], defaults=data)

    # 15. InsuranceEnrollmentStatus（保険加入ステータス）
    InsuranceEnrollmentStatus = apps.get_model('monotal', 'InsuranceEnrollmentStatus')
    insurance_statuses = [
        {'insurance_enrollment_status_id': 1, 'status_name': '未加入'},
        {'insurance_enrollment_status_id': 2, 'status_name': '加入中'},
        {'insurance_enrollment_status_id': 3, 'status_name': '解約済み'},
    ]
    for data in insurance_statuses:
        InsuranceEnrollmentStatus.objects.get_or_create(
            insurance_enrollment_status_id=data['insurance_enrollment_status_id'],
            defaults=data
        )

    # 16. ChatRoomType（チャットルームタイプ）
    ChatRoomType = apps.get_model('monotal', 'ChatRoomType')
    chat_room_types = [
        {'chat_room_type_id': 1, 'type_name': '1対1'},
        {'chat_room_type_id': 2, 'type_name': 'グループ'},
        {'chat_room_type_id': 3, 'type_name': '商品チャット'},
        {'chat_room_type_id': 4, 'type_name': 'コミュニティチャット'},
    ]
    for data in chat_room_types:
        ChatRoomType.objects.get_or_create(chat_room_type_id=data['chat_room_type_id'], defaults=data)

    # 17. MessageReadStatus（メッセージ既読ステータス）
    MessageReadStatus = apps.get_model('monotal', 'MessageReadStatus')
    message_read_statuses = [
        {'message_read_status_id': 1, 'status_name': '未読'},
        {'message_read_status_id': 2, 'status_name': '既読'},
    ]
    for data in message_read_statuses:
        MessageReadStatus.objects.get_or_create(
            message_read_status_id=data['message_read_status_id'],
            defaults=data
        )

    # 18. NotificationType（通知タイプ）
    NotificationType = apps.get_model('monotal', 'NotificationType')
    notification_types = [
        {'notification_type_id': 1, 'notification_type_name': 'システム通知'},
        {'notification_type_id': 2, 'notification_type_name': 'メッセージ通知'},
        {'notification_type_id': 3, 'notification_type_name': 'レンタル通知'},
    ]
    for data in notification_types:
        NotificationType.objects.get_or_create(
            notification_type_id=data['notification_type_id'],
            defaults=data
        )

    # 19. NotificationReadStatus（通知既読ステータス）
    NotificationReadStatus = apps.get_model('monotal', 'NotificationReadStatus')
    notification_read_statuses = [
        {'notification_read_status_id': 1, 'status_name': '未読'},
        {'notification_read_status_id': 2, 'status_name': '既読'},
    ]
    for data in notification_read_statuses:
        NotificationReadStatus.objects.get_or_create(
            notification_read_status_id=data['notification_read_status_id'],
            defaults=data
        )

    # 20. TargetUserType（ターゲットユーザータイプ）
    TargetUserType = apps.get_model('monotal', 'TargetUserType')
    target_user_types = [
        {'target_user_type_id': 1, 'type_name': '全ユーザー'},
        {'target_user_type_id': 2, 'type_name': '特定ユーザー'},
    ]
    for data in target_user_types:
        TargetUserType.objects.get_or_create(
            target_user_type_id=data['target_user_type_id'],
            defaults=data
        )


def reverse_master_data(apps, schema_editor):
    """マスターデータを削除（ロールバック用）"""
    # 依存関係があるため、通常はロールバックしない
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_master_data, reverse_master_data),
    ]
