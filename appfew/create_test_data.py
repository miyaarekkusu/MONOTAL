#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
テストデータ作成スクリプト
1万件の商品データを作成（画像付き）
"""
import os
import sys
import io

# UTF-8エンコーディング設定（Windows対応）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import django
import random
import requests
from io import BytesIO
from django.core.files import File
from django.core.files.uploadedfile import InMemoryUploadedFile

# Django設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appfew.settings')
django.setup()

from monotal.models import (
    Product, ProductCategory, ProductCondition, ProductStatus,
    ShippingDays, ProductImage, ProductRentalPlan, User
)

# 商品名のテンプレート
PRODUCT_TEMPLATES = {
    1: [  # カメラ・撮影機材
        "Canon EOS {model}", "Nikon Z {model}", "Sony Alpha {model}",
        "Fujifilm X-T{model}", "Panasonic LUMIX {model}",
        "Canon EF {focal}mm f/{aperture} レンズ",
        "Nikon NIKKOR {focal}mm f/{aperture} レンズ",
        "Sony FE {focal}mm f/{aperture} レンズ",
        "Manfrotto 三脚 {model}", "Gitzo 三脚 {model}",
        "Godox ストロボ {model}", "Profoto ライト {model}",
    ],
    2: [  # 家電・生活家電
        "Dyson 掃除機 V{model}", "ルンバ {model}",
        "バルミューダ トースター {model}", "ヘルシオ ホットクック {model}",
        "ダイソン ドライヤー {model}", "パナソニック 美顔器 {model}",
        "ブラウン シェーバー {model}", "象印 炊飯器 {model}",
        "デロンギ コーヒーメーカー {model}", "バーミックス {model}",
    ],
    3: [  # アウトドア・スポーツ用品
        "コールマン テント {model}人用", "スノーピーク タープ {model}",
        "モンベル 寝袋 {model}", "キャプテンスタッグ テーブル {model}",
        "ロゴス チェア {model}", "ユニフレーム 焚き火台 {model}",
        "YETI クーラーボックス {model}L", "ハイドロフラスク {model}ml",
        "パタゴニア ダウンジャケット {model}", "ノースフェイス リュック {model}L",
    ],
    4: [  # 楽器・音楽機材
        "Fender Stratocaster {model}", "Gibson Les Paul {model}",
        "Yamaha アコギ {model}", "Roland 電子ピアノ {model}",
        "KORG シンセサイザー {model}", "Moog {model}",
        "Pearl ドラムセット {model}", "Zildjian シンバル {model}",
        "Shure マイク SM{model}", "RODE マイク NT{model}",
        "Behringer ミキサー {model}ch", "Focusrite オーディオIF {model}",
    ],
    5: [  # パソコン・周辺機器
        "MacBook Pro {model}インチ", "ThinkPad X{model}",
        "Dell XPS {model}", "Surface Laptop {model}",
        "iPad Pro {model}インチ", "Surface Pro {model}",
        "LG モニター {model}インチ", "EIZO モニター {model}インチ",
        "Logicool マウス MX{model}", "HHKB Professional {model}",
        "Anker モバイルバッテリー {model}mAh", "RAVPower 充電器 {model}W",
    ],
}

# 商品説明のテンプレート
DESCRIPTIONS = [
    "美品です。動作確認済み。付属品完備。",
    "使用感少なめ。綺麗な状態です。箱あり。",
    "数回使用のみ。ほぼ新品同様です。",
    "中古品ですが状態良好。動作問題なし。",
    "キズや汚れがありますが使用には問題ありません。",
    "レンタル専用に購入した商品です。丁寧に扱っています。",
    "プロ仕様の高品質な製品です。初心者からプロまで使えます。",
    "人気商品！レビュー高評価の定番モデルです。",
]

# 画像検索キーワード（カテゴリー別）
IMAGE_KEYWORDS = {
    1: ["camera", "lens", "photography", "tripod"],
    2: ["appliance", "gadget", "electronics", "kitchen"],
    3: ["camping", "outdoor", "hiking", "sports"],
    4: ["guitar", "music", "instrument", "audio"],
    5: ["laptop", "computer", "keyboard", "monitor"],
}


def download_image_from_url(url, filename):
    """URLから画像をダウンロード"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img_temp = BytesIO(response.content)
            return InMemoryUploadedFile(
                img_temp,
                None,
                filename,
                'image/jpeg',
                img_temp.tell(),
                None
            )
    except Exception as e:
        print(f"画像ダウンロード失敗: {e}")
    return None


def create_test_products(count=10000, batch_size=100):
    """テスト商品を作成"""

    print("=" * 60)
    print(f"テストデータ作成開始: {count}件")
    print("=" * 60)

    # 必要なマスターデータを取得
    categories = list(ProductCategory.objects.all())
    conditions = list(ProductCondition.objects.all())
    shipping_days_list = list(ShippingDays.objects.all())
    users = list(User.objects.filter(user_status_id=2))  # 承認済みユーザー

    if not categories:
        print("❌ エラー: カテゴリーが存在しません")
        return

    if not conditions:
        print("⚠️  商品状態マスターを作成します...")
        conditions = [
            ProductCondition.objects.create(condition_name="新品・未使用"),
            ProductCondition.objects.create(condition_name="未使用に近い"),
            ProductCondition.objects.create(condition_name="目立った傷や汚れなし"),
            ProductCondition.objects.create(condition_name="やや傷や汚れあり"),
            ProductCondition.objects.create(condition_name="傷や汚れあり"),
        ]
        print(f"✓ {len(conditions)}件の商品状態を作成")

    if not shipping_days_list:
        print("⚠️  発送日数マスターを作成します...")
        shipping_days_list = [
            ShippingDays.objects.create(days_name="1〜2日で発送"),
            ShippingDays.objects.create(days_name="2〜3日で発送"),
            ShippingDays.objects.create(days_name="4〜7日で発送"),
        ]
        print(f"✓ {len(shipping_days_list)}件の発送日数を作成")

    if not users:
        print("⚠️  テストユーザーを作成します...")
        from django.contrib.auth.hashers import make_password
        test_user = User.objects.create(
            user_name=f"test_user_{random.randint(1000, 9999)}",
            display_name="テストユーザー",
            email=f"test{random.randint(1000, 9999)}@example.com",
            phone_number=f"090{random.randint(10000000, 99999999)}",
            password=make_password("testpass123"),
            user_status_id=2  # 承認済み
        )
        users = [test_user]
        print(f"✓ テストユーザー作成: {test_user.user_name}")

    product_status_listed = ProductStatus.objects.get_or_create(
        product_status_id=1,
        defaults={'status_name': '貸出可能'}
    )[0]

    created_count = 0

    for i in range(0, count, batch_size):
        batch_products = []
        batch_images = []
        batch_plans = []

        batch_end = min(i + batch_size, count)

        for j in range(i, batch_end):
            # ランダムにカテゴリー選択
            category = random.choice(categories)

            # 商品名生成
            template = random.choice(PRODUCT_TEMPLATES.get(category.product_category_id, ["商品 {model}"]))
            product_name = template.format(
                model=random.randint(100, 999),
                focal=random.choice([24, 35, 50, 85, 135, 200]),
                aperture=random.choice([1.4, 1.8, 2.8, 4]),
            )

            # 商品説明
            description = random.choice(DESCRIPTIONS)

            # レンタル基本価格（ProductRentalPlanで詳細設定）
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
                rental_days=base_days,  # 必須フィールド
                rental_fee=base_price,  # 必須フィールド
            )
            batch_products.append(product)

        # バルクインサート
        Product.objects.bulk_create(batch_products)

        # 画像とレンタルプランを追加
        for product in batch_products:
            # 画像ダウンロード（1〜3枚）
            num_images = random.randint(1, 3)
            keyword = random.choice(IMAGE_KEYWORDS.get(product.product_category_id, ["product"]))

            for img_idx in range(num_images):
                # Unsplash Source API（800x600、ランダム）
                image_url = f"https://source.unsplash.com/800x600/?{keyword}"

                # 画像をダウンロード
                img_file = download_image_from_url(
                    image_url,
                    f"product_{product.product_id}_{img_idx}.jpg"
                )

                if img_file:
                    product_image = ProductImage(
                        product=product,
                        display_order=img_idx
                    )
                    product_image.image.save(
                        f"product_{product.product_id}_{img_idx}.jpg",
                        img_file,
                        save=True
                    )

            # レンタルプラン作成（1〜3プラン）
            num_plans = random.randint(1, 3)
            rental_days_options = [1, 3, 7, 14, 30]
            plan_base_price = random.randint(500, 20000)

            for plan_idx in range(num_plans):
                days = rental_days_options[plan_idx] if plan_idx < len(rental_days_options) else random.choice(rental_days_options)
                fee = plan_base_price * days // 3  # 日数に応じた価格

                batch_plans.append(ProductRentalPlan(
                    product=product,
                    rental_days=days,
                    rental_fee=fee
                ))

        # レンタルプランをバルク作成
        if batch_plans:
            ProductRentalPlan.objects.bulk_create(batch_plans)

        created_count = batch_end
        progress = (created_count / count) * 100
        print(f"進捗: {created_count}/{count} 件 ({progress:.1f}%)")

    print("=" * 60)
    print(f"✅ 完了！{created_count}件の商品を作成しました")
    print("=" * 60)


if __name__ == '__main__':
    import time
    start_time = time.time()

    # 1万件作成
    create_test_products(count=10000, batch_size=100)

    elapsed_time = time.time() - start_time
    print(f"\n実行時間: {elapsed_time:.2f}秒")
