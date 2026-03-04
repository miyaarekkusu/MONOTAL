from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = '全マスターテーブルの初期データを投入（get_or_createで冪等）'

    @transaction.atomic
    def handle(self, *args, **options):
        from monotal.models import (
            UserStatus, IdentityVerificationStatus, Prefecture,
            ProductCondition, ProductStatus, ShippingBurden,
            ShippingDays, RentalStatus, RentalRequestStatus,
            RentalRequestReadType, ReturnReason, ReportReason,
            ViolationReason, ViolationStatus, PaymentType,
            InsuranceEnrollmentStatus, InsuranceClaimStatus,
            ChatRoomType, MessageReadStatus, NotificationType,
            NotificationReadStatus, TargetUserType,
            BoardCategory, QACategory, Insurance,
            CancellationReason, CancellationStatus,
        )

        # 1. UserStatus
        for sid, name in [(1, '未認証ユーザー'), (2, '承認済みユーザー'), (3, '制限付きユーザー'), (4, '削除済みユーザー')]:
            UserStatus.objects.get_or_create(user_status_id=sid, defaults={'status_name': name})
        self.stdout.write('UserStatus: OK')

        # 2. IdentityVerificationStatus
        for sid, name in [(0, '審査待ち'), (1, '承認済み'), (2, '却下')]:
            IdentityVerificationStatus.objects.get_or_create(identity_verification_status_id=sid, defaults={'status_name': name})
        self.stdout.write('IdentityVerificationStatus: OK')

        # 3. Prefecture
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
        self.stdout.write('Prefecture: OK')

        # 4. ProductCondition
        for cid, name in [(1, '新品・未使用'), (2, '未使用に近い'), (3, '目立った傷や汚れなし'),
                          (4, 'やや傷や汚れあり'), (5, '傷や汚れあり'), (6, '全体的に状態が悪い')]:
            ProductCondition.objects.get_or_create(product_condition_id=cid, defaults={'condition_name': name})
        self.stdout.write('ProductCondition: OK')

        # 5. ProductStatus
        for sid, name in [(1, '貸出可能'), (2, '貸出中'), (3, 'メンテナンス中'), (4, '非公開')]:
            ProductStatus.objects.get_or_create(product_status_id=sid, defaults={'status_name': name})
        self.stdout.write('ProductStatus: OK')

        # 6. ShippingBurden
        for sid, name in [(1, '出品者負担'), (2, 'レンタル者負担'), (3, '両者負担')]:
            ShippingBurden.objects.get_or_create(shipping_burden_id=sid, defaults={'burden_name': name})
        self.stdout.write('ShippingBurden: OK')

        # 7. ShippingDays
        for sid, label, dmin, dmax, order in [
            (1, '1〜2日で発送', 1, 2, 1), (2, '2〜3日で発送', 2, 3, 2), (3, '4〜7日で発送', 4, 7, 3)]:
            ShippingDays.objects.get_or_create(shipping_days_id=sid, defaults={
                'days_label': label, 'days_min': dmin, 'days_max': dmax, 'display_order': order})
        self.stdout.write('ShippingDays: OK')

        # 8. RentalStatus (updated 9-status flow)
        for sid, name in [
            (1, '発送準備中'), (2, '配送中'), (3, 'レンタル中'),
            (4, '返送中'), (5, '返却済み'), (6, 'キャンセル'),
            (7, '返品申請中'), (8, '返品承認済み'), (9, '返品返送中')]:
            RentalStatus.objects.get_or_create(rental_status_id=sid, defaults={'status_name': name})
        self.stdout.write('RentalStatus: OK')

        # 9. RentalRequestStatus
        for sid, name in [(1, '申請中'), (2, '承認済み'), (3, '却下'), (4, 'キャンセル')]:
            RentalRequestStatus.objects.get_or_create(rental_request_status_id=sid, defaults={'status_name': name})
        self.stdout.write('RentalRequestStatus: OK')

        # 10. RentalRequestReadType
        for sid, name in [(1, '受け取った申請/承認待ち'), (2, '受け取った申請/承認済み'),
                          (3, '送った申請/承認待ち'), (4, '送った申請/承認済み')]:
            RentalRequestReadType.objects.get_or_create(rental_request_read_type_id=sid, defaults={'type_name': name})
        self.stdout.write('RentalRequestReadType: OK')

        # 11. ReturnReason
        for rid, name in [(1, '通常返却'), (2, '破損'), (3, '紛失'), (4, '期間延長希望')]:
            ReturnReason.objects.get_or_create(return_reason_id=rid, defaults={'return_reason_name': name})
        self.stdout.write('ReturnReason: OK')

        # 12. ReportReason
        for rid, name in [(1, '不適切なコンテンツ'), (2, '詐欺'), (3, '規約違反'), (4, 'スパム'), (5, 'その他')]:
            ReportReason.objects.get_or_create(report_reason_id=rid, defaults={'report_reason_name': name})
        self.stdout.write('ReportReason: OK')

        # 13. ViolationReason
        for vid, name in [(1, 'スパム行為'), (2, '支払い遅延'), (3, '商品破損'), (4, '規約違反')]:
            ViolationReason.objects.get_or_create(violation_reason_id=vid, defaults={'violation_reason_name': name})
        self.stdout.write('ViolationReason: OK')

        # 14. ViolationStatus
        for sid, name in [(1, '警告中'), (2, '停止中'), (3, '解除済み')]:
            ViolationStatus.objects.get_or_create(violation_status_id=sid, defaults={'status_name': name})
        self.stdout.write('ViolationStatus: OK')

        # 15. PaymentType
        for pid, name in [(1, 'クレジットカード'), (2, 'デビットカード'), (3, '銀行振込'), (4, '電子マネー')]:
            PaymentType.objects.get_or_create(payment_type_id=pid, defaults={'payment_type_name': name})
        self.stdout.write('PaymentType: OK')

        # 16. InsuranceEnrollmentStatus
        for sid, name in [(1, '未加入'), (2, '加入中'), (3, '解約済み')]:
            InsuranceEnrollmentStatus.objects.get_or_create(insurance_enrollment_status_id=sid, defaults={'status_name': name})
        self.stdout.write('InsuranceEnrollmentStatus: OK')

        # 17. InsuranceClaimStatus
        for sid, name in [(1, '審査中'), (2, '承認'), (3, '却下')]:
            InsuranceClaimStatus.objects.get_or_create(insurance_claim_status_id=sid, defaults={'status_name': name})
        self.stdout.write('InsuranceClaimStatus: OK')

        # 18. ChatRoomType
        for tid, name in [(1, '1対1'), (2, 'グループ'), (3, '商品チャット'), (4, 'コミュニティチャット')]:
            ChatRoomType.objects.get_or_create(chat_room_type_id=tid, defaults={'type_name': name})
        self.stdout.write('ChatRoomType: OK')

        # 19. MessageReadStatus
        for sid, name in [(1, '未読'), (2, '既読')]:
            MessageReadStatus.objects.get_or_create(message_read_status_id=sid, defaults={'status_name': name})
        self.stdout.write('MessageReadStatus: OK')

        # 20. NotificationType
        for tid, name in [(1, 'システム通知'), (2, 'メッセージ通知'), (3, 'レンタル通知'), (4, 'コミュニティ通知')]:
            NotificationType.objects.get_or_create(notification_type_id=tid, defaults={'notification_type_name': name})
        self.stdout.write('NotificationType: OK')

        # 21. NotificationReadStatus
        for sid, name in [(1, '未読'), (2, '既読')]:
            NotificationReadStatus.objects.get_or_create(notification_read_status_id=sid, defaults={'status_name': name})
        self.stdout.write('NotificationReadStatus: OK')

        # 22. TargetUserType
        for tid, name in [(1, '全ユーザー'), (2, '特定ユーザー')]:
            TargetUserType.objects.get_or_create(target_user_type_id=tid, defaults={'type_name': name})
        self.stdout.write('TargetUserType: OK')

        # 23. BoardCategory（掲示板カテゴリ）
        for bid, name in [(1, 'ファッション'), (2, '家電・ガジェット'), (3, 'アウトドア・スポーツ'),
                          (4, '趣味・エンタメ'), (5, '暮らし・インテリア'), (7, '雑談・交流')]:
            BoardCategory.objects.get_or_create(id=bid, defaults={'name': name})
        self.stdout.write('BoardCategory: OK')

        # 24. QACategory（Q&Aカテゴリ）
        for qid, name in [(1, 'レンタルについて'), (2, '商品について'), (3, '配送・返却について'),
                          (4, 'お支払いについて'), (5, 'トラブル・問題'), (6, 'アカウント・設定'), (7, 'その他')]:
            QACategory.objects.get_or_create(id=qid, defaults={'name': name})
        self.stdout.write('QACategory: OK')

        # 25. Insurance（保険プラン）
        Insurance.objects.get_or_create(insurance_id=1, defaults={
            'insurance_name': 'MONOTAL補償保険制度',
            'insurance_description': 'レンタル中の商品破損・故障を補償する保険プランです。',
            'insurance_fee': 2000,
            'coverage_limit': 50000,
        })
        self.stdout.write('Insurance: OK')

        # 26. CancellationReason（キャンセル理由）
        for cid, name in [(1, '商品説明と実物が異なる'), (2, '商品が届かない'), (3, '商品が破損していた'),
                          (4, '相手と連絡が取れない'), (5, 'その他')]:
            CancellationReason.objects.get_or_create(cancellation_reason_id=cid, defaults={'reason_name': name})
        self.stdout.write('CancellationReason: OK')

        # 27. CancellationStatus（キャンセルステータス）
        for cid, name in [(1, '申請中'), (2, '承認'), (3, '却下')]:
            CancellationStatus.objects.get_or_create(cancellation_status_id=cid, defaults={'status_name': name})
        self.stdout.write('CancellationStatus: OK')

        self.stdout.write(self.style.SUCCESS('全マスターデータの投入完了'))
