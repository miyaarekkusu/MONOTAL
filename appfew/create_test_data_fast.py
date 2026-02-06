#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高速テストデータ作成スクリプト（画像なし版）
1万件の商品データを数分で作成
"""
import os
import sys
import io

# UTF-8エンコーディング設定（Windows対応）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import django
import random

# Django設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appfew.settings')
django.setup()

from monotal.models import (
    Product, ProductCategory, ProductCondition, ProductStatus,
    ShippingDays, ProductRentalPlan, User, UserAddress
)

# 商品名のテンプレート
PRODUCT_TEMPLATES = {
    1: [  # カメラ・撮影機材
        "Canon EOS {}", "Nikon Z{}", "Sony Alpha {}",
        "Fujifilm X-T{}", "Panasonic LUMIX {}",
        "Canon EF {}mm f/1.8 レンズ", "Nikon NIKKOR {}mm レンズ",
        "Sony FE {}mm レンズ", "Manfrotto 三脚", "Gitzo 三脚",
    ],
    2: [  # 家電・生活家電
        "Dyson 掃除機 V{}", "ルンバ {}",
        "バルミューダ トースター", "ヘルシオ ホットクック",
        "ダイソン ドライヤー", "パナソニック 美顔器 {}",
        "ブラウン シェーバー {}", "象印 炊飯器",
    ],
    3: [  # アウトドア・スポーツ用品
        "コールマン テント {}人用", "スノーピーク タープ",
        "モンベル 寝袋", "キャプテンスタッグ テーブル",
        "ロゴス チェア", "ユニフレーム 焚き火台",
    ],
    4: [  # 楽器・音楽機材
        "Fender Stratocaster", "Gibson Les Paul {}",
        "Yamaha アコギ FG{}", "Roland 電子ピアノ",
        "KORG シンセサイザー", "Shure マイク SM{}",
    ],
    5: [  # パソコン・周辺機器
        "MacBook Pro {}インチ", "ThinkPad X{}",
        "Dell XPS {}", "iPad Pro {}インチ",
        "LG モニター {}インチ", "Logicool マウス MX{}",
    ],
}

DESCRIPTIONS = [
    "美品です。動作確認済み。",
    "使用感少なめ。綺麗な状態です。",
    "数回使用のみ。ほぼ新品同様です。",
    "中古品ですが状態良好。",
    "レンタル専用に購入した商品です。",
]


def create_test_products_fast(count=10000):
    """高速テスト商品作成（画像なし）"""

    print("=" * 60)
    print(f"高速テストデータ作成開始: {count}件（画像なし）")
    print("=" * 60)

    # マスターデータ取得
    categories = list(ProductCategory.objects.all())
    conditions = list(ProductCondition.objects.all())
    shipping_days_list = list(ShippingDays.objects.all())
    users = list(User.objects.filter(user_status_id=2))

    if not categories:
        print("❌ エラー: カテゴリーが存在しません")
        return

    # 商品状態マスター作成
    if not conditions:
        print("商品状態マスターを作成中...")
        conditions = [
            ProductCondition.objects.create(condition_name="新品・未使用"),
            ProductCondition.objects.create(condition_name="未使用に近い"),
            ProductCondition.objects.create(condition_name="目立った傷や汚れなし"),
            ProductCondition.objects.create(condition_name="やや傷や汚れあり"),
        ]

    # 発送日数マスター作成
    if not shipping_days_list:
        print("発送日数マスターを作成中...")
        shipping_days_list = [
            ShippingDays.objects.create(days_name="1〜2日で発送"),
            ShippingDays.objects.create(days_name="2〜3日で発送"),
            ShippingDays.objects.create(days_name="4〜7日で発送"),
        ]

    # テストユーザー作成
    if not users:
        print("テストユーザーを作成中...")
        from django.contrib.auth.hashers import make_password
        test_user = User.objects.create(
            user_name=f"test_user_{random.randint(1000, 9999)}",
            display_name="テストユーザー",
            email=f"test{random.randint(1000, 9999)}@example.com",
            phone_number=f"090{random.randint(10000000, 99999999)}",
            password=make_password("testpass123"),
            user_status_id=2
        )
        users = [test_user]

        # テストユーザーの住所も作成
        UserAddress.objects.create(
            user=test_user,
            postal_code="1000001",
            prefecture="東京都",
            city="千代田区",
            address_line="千代田1-1-1",
            is_default=True
        )

    product_status_listed = ProductStatus.objects.get_or_create(
        product_status_id=1,
        defaults={'status_name': '貸出可能'}
    )[0]

    print("\n商品作成中...")

    products_to_create = []
    plans_to_create = []

    for i in range(count):
        category = random.choice(categories)

        # 商品名生成
        template = random.choice(PRODUCT_TEMPLATES.get(category.product_category_id, ["商品 {}"]))
        try:
            product_name = template.format(random.randint(1, 99))
        except:
            product_name = template

        description = random.choice(DESCRIPTIONS)
        base_price = random.randint(500, 20000)
        base_days = random.choice([1, 3, 7])

        # 商品作成
        product = Product(
            product_name=product_name,
            product_description=description,
            user=random.choice(users),
            product_category=category,
            product_condition=random.choice(conditions),
            product_status=product_status_listed,
            shipping_days=random.choice(shipping_days_list),
            rental_days=base_days,
            rental_fee=base_price,
            shipping_address=users[0].addresses.first() if users[0].addresses.exists() else None
        )
        products_to_create.append(product)

        # 1000件ごとにバルクインサート
        if len(products_to_create) >= 1000:
            print(f"  {i+1}/{count} 件作成中...")
            Product.objects.bulk_create(products_to_create)

            # レンタルプラン作成
            for prod in products_to_create:
                num_plans = random.randint(1, 3)
                for plan_idx in range(num_plans):
                    days = [1, 3, 7, 14, 30][plan_idx] if plan_idx < 5 else 7
                    fee = random.randint(500, 20000)
                    plans_to_create.append(ProductRentalPlan(
                        product=prod,
                        rental_days=days,
                        rental_fee=fee
                    ))

            ProductRentalPlan.objects.bulk_create(plans_to_create)
            products_to_create = []
            plans_to_create = []

    # 残りを追加
    if products_to_create:
        print(f"  {count}/{count} 件作成中...")
        Product.objects.bulk_create(products_to_create)

        for prod in products_to_create:
            num_plans = random.randint(1, 3)
            for plan_idx in range(num_plans):
                days = [1, 3, 7, 14, 30][plan_idx] if plan_idx < 5 else 7
                fee = random.randint(500, 20000)
                plans_to_create.append(ProductRentalPlan(
                    product=prod,
                    rental_days=days,
                    rental_fee=fee
                ))

        ProductRentalPlan.objects.bulk_create(plans_to_create)

    print("=" * 60)
    print(f"✅ 完了！{count}件の商品を作成しました")
    print("=" * 60)

    # 統計表示
    total_products = Product.objects.count()
    total_plans = ProductRentalPlan.objects.count()
    print(f"\n統計:")
    print(f"  総商品数: {total_products:,} 件")
    print(f"  総レンタルプラン数: {total_plans:,} 件")


if __name__ == '__main__':
    import time
    start_time = time.time()

    create_test_products_fast(count=10000)

    elapsed_time = time.time() - start_time
    print(f"\n実行時間: {elapsed_time:.2f}秒")
