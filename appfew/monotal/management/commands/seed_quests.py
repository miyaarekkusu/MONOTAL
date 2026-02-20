from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from monotal.models import (
    ProductCategory, Coupon, CouponTargetCategory,
    Quest, QuestMission,
)


class Command(BaseCommand):
    help = 'クエストの初期データを登録（チュートリアル＋カテゴリ別）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', action='store_true',
            help='既存クエストデータを削除してから登録',
        )

    def handle(self, *args, **options):
        if options['clear']:
            QuestMission.objects.all().delete()
            Quest.objects.all().delete()
            self.stdout.write('既存クエストデータをクリアしました')

        self._create_tutorial_quests()
        self._create_category_quests()
        self.stdout.write(self.style.SUCCESS('クエストの初期データ登録が完了しました'))

    def _create_coupon(self, name, discount, category=None):
        """報酬用クーポンを作成して返す。categoryが指定された場合は対象カテゴリも設定"""
        coupon = Coupon.objects.create(
            coupon_name=name,
            discount_amount=discount,
            expires_at=timezone.now() + timedelta(days=365 * 10),  # クエスト用は長期有効
            is_active=True,
        )
        if category:
            # 対象カテゴリ（そのカテゴリ＋子孫全て）
            self._add_category_targets(coupon, category)
        else:
            # 全カテゴリ対象：ルートカテゴリを全て追加
            for root_cat in ProductCategory.objects.filter(parent_product_category__isnull=True):
                self._add_category_targets(coupon, root_cat)
        return coupon

    def _add_category_targets(self, coupon, category):
        """クーポン対象カテゴリを再帰的に追加"""
        CouponTargetCategory.objects.get_or_create(
            coupon=coupon, product_category=category
        )
        for child in ProductCategory.objects.filter(parent_product_category=category):
            self._add_category_targets(coupon, child)

    def _create_tutorial_quests(self):
        """チュートリアルクエスト3つを作成"""
        self.stdout.write('チュートリアルクエストを作成中...')

        # Q1: はじめてのMONOTAL
        coupon1 = self._create_coupon('クエスト報酬: はじめてのMONOTAL（200円OFF）', 200)
        q1 = Quest.objects.create(
            product_category=None,
            quest_name='はじめてのMONOTAL',
            quest_description='MONOTALの基本的な使い方を学びましょう。プロフィールを設定して、商品を探してみよう！',
            difficulty=0,
            reward_coupon=coupon1,
            display_order=1,
        )
        for i, (name, ctype, params) in enumerate([
            ('プロフィール画像を設定しよう', 'profile_image_set', {}),
            ('自己紹介を書こう', 'bio_set', {}),
            ('趣味を登録しよう', 'hobby_registered', {}),
            ('商品を3つ閲覧しよう', 'browsing_history_count', {'count': 3}),
            ('商品を1つブックマークしよう', 'bookmark_count', {'count': 1}),
        ], 1):
            QuestMission.objects.create(
                quest=q1, mission_name=name,
                condition_type=ctype, condition_params=params,
                display_order=i,
            )

        # Q2: 本人確認を完了しよう
        coupon2 = self._create_coupon('クエスト報酬: 本人確認完了（500円OFF）', 500)
        q2 = Quest.objects.create(
            product_category=None,
            quest_name='本人確認を完了しよう',
            quest_description='安全にレンタルを利用するために、本人確認と決済情報を登録しましょう。',
            difficulty=0,
            reward_coupon=coupon2,
            display_order=2,
        )
        for i, (name, ctype, params) in enumerate([
            ('本人確認を完了する', 'identity_verified', {}),
            ('住所を登録する', 'address_registered', {}),
            ('銀行口座を登録する', 'bank_account_registered', {}),
            ('クレジットカードを登録する', 'credit_card_registered', {}),
        ], 1):
            QuestMission.objects.create(
                quest=q2, mission_name=name,
                condition_type=ctype, condition_params=params,
                display_order=i,
            )

        # Q3: コミュニティに参加しよう
        coupon3 = self._create_coupon('クエスト報酬: コミュニティ参加（300円OFF）', 300)
        q3 = Quest.objects.create(
            product_category=None,
            quest_name='コミュニティに参加しよう',
            quest_description='MONOTALのコミュニティに参加して、他のユーザーと交流しよう！',
            difficulty=0,
            reward_coupon=coupon3,
            display_order=3,
        )
        for i, (name, ctype, params) in enumerate([
            ('ユーザーを1人フォローしよう', 'follow_count', {'count': 1}),
            ('Q&Aで質問を投稿しよう', 'qa_question_posted', {'count': 1}),
            ('掲示板で発言しよう', 'board_post_count', {'count': 1}),
        ], 1):
            QuestMission.objects.create(
                quest=q3, mission_name=name,
                condition_type=ctype, condition_params=params,
                display_order=i,
            )

        self.stdout.write(f'  チュートリアルクエスト 3件作成完了')

    def _create_category_quests(self):
        """ルートカテゴリごとに初級・中級・上級クエストを作成"""
        root_categories = ProductCategory.objects.filter(
            parent_product_category__isnull=True
        ).order_by('product_category_id')

        self.stdout.write(f'カテゴリ別クエストを作成中... ({root_categories.count()}カテゴリ)')

        display_order = 100  # チュートリアルの後

        for cat in root_categories:
            cat_name = cat.category_name

            # 初級
            coupon_b = self._create_coupon(f'クエスト報酬: {cat_name} 初級（300円OFF）', 300, cat)
            qb = Quest.objects.create(
                product_category=cat,
                quest_name=f'{cat_name} 初級',
                quest_description=f'{cat_name}カテゴリの商品を探して、出品やレンタルに挑戦してみよう！',
                difficulty=1,
                reward_coupon=coupon_b,
                display_order=display_order,
            )
            for i, (name, ctype, params) in enumerate([
                (f'{cat_name}の商品を5つ閲覧しよう', 'browsing_history_count', {'count': 5}),
                (f'{cat_name}の商品を1つブックマークしよう', 'bookmark_count', {'count': 1}),
                (f'{cat_name}の商品を1つ出品しよう', 'product_listed', {'count': 1}),
                (f'{cat_name}の商品を1回レンタルしよう', 'rental_completed_renter', {'count': 1}),
            ], 1):
                QuestMission.objects.create(
                    quest=qb, mission_name=name,
                    condition_type=ctype, condition_params=params,
                    display_order=i,
                )

            # 中級
            coupon_m = self._create_coupon(f'クエスト報酬: {cat_name} 中級（500円OFF）', 500, cat)
            qm = Quest.objects.create(
                product_category=cat,
                quest_name=f'{cat_name} 中級',
                quest_description=f'{cat_name}カテゴリでの出品・レンタル・レビューを積み重ねよう！',
                difficulty=2,
                reward_coupon=coupon_m,
                display_order=display_order + 1,
            )
            for i, (name, ctype, params) in enumerate([
                (f'{cat_name}の商品を3つ出品しよう', 'product_listed', {'count': 3}),
                (f'{cat_name}の商品を3回レンタルしよう', 'rental_completed_renter', {'count': 3}),
                (f'{cat_name}のレンタルを3回完了しよう（貸し手）', 'rental_completed_lender', {'count': 3}),
                (f'{cat_name}のレンタルに対してレビューを3件書こう', 'review_written', {'count': 3}),
            ], 1):
                QuestMission.objects.create(
                    quest=qm, mission_name=name,
                    condition_type=ctype, condition_params=params,
                    display_order=i,
                )

            # 上級
            coupon_a = self._create_coupon(f'クエスト報酬: {cat_name} 上級（1000円OFF）', 1000, cat)
            qa = Quest.objects.create(
                product_category=cat,
                quest_name=f'{cat_name} 上級',
                quest_description=f'{cat_name}カテゴリのエキスパートを目指そう！',
                difficulty=3,
                reward_coupon=coupon_a,
                display_order=display_order + 2,
            )
            for i, (name, ctype, params) in enumerate([
                (f'{cat_name}の商品を5つ出品しよう', 'product_listed', {'count': 5}),
                (f'{cat_name}の商品を5回レンタルしよう', 'rental_completed_renter', {'count': 5}),
                (f'{cat_name}のレンタルを5回完了しよう（貸し手）', 'rental_completed_lender', {'count': 5}),
                (f'{cat_name}のレンタルに対してレビューを5件書こう', 'review_written', {'count': 5}),
            ], 1):
                QuestMission.objects.create(
                    quest=qa, mission_name=name,
                    condition_type=ctype, condition_params=params,
                    display_order=i,
                )

            display_order += 10
            self.stdout.write(f'  {cat_name}: 初級・中級・上級 作成完了')
