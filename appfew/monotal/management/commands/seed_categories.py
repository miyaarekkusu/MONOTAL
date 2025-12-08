from django.core.management.base import BaseCommand
from monotal.models import ProductCategory


class Command(BaseCommand):
    help = '商品カテゴリのシードデータを登録（レンタルサービス向け）'

    def handle(self, *args, **options):
        # 既存データをクリア
        ProductCategory.objects.all().delete()
        self.stdout.write('既存カテゴリをクリアしました')

        # レンタルサービス向けカテゴリ（消耗品・飲食物を除外）
        categories = [
            # 1. レディースファッション
            {'id': 1, 'name': 'レディースファッション', 'parent': None},
            {'id': 2, 'name': 'ドレス/フォーマル', 'parent': 1},
            {'id': 3, 'name': '着物/浴衣', 'parent': 1},
            {'id': 4, 'name': 'ジャケット/アウター', 'parent': 1},
            {'id': 5, 'name': 'スーツ', 'parent': 1},
            {'id': 6, 'name': 'バッグ', 'parent': 1},
            {'id': 7, 'name': 'アクセサリー', 'parent': 1},
            {'id': 8, 'name': '靴/パンプス', 'parent': 1},
            {'id': 9, 'name': '帽子', 'parent': 1},
            {'id': 10, 'name': 'ウィッグ', 'parent': 1},
            {'id': 11, 'name': 'その他', 'parent': 1},

            # 2. メンズファッション
            {'id': 20, 'name': 'メンズファッション', 'parent': None},
            {'id': 21, 'name': 'スーツ/フォーマル', 'parent': 20},
            {'id': 22, 'name': 'ジャケット/アウター', 'parent': 20},
            {'id': 23, 'name': 'バッグ', 'parent': 20},
            {'id': 24, 'name': '靴/革靴', 'parent': 20},
            {'id': 25, 'name': 'アクセサリー/時計', 'parent': 20},
            {'id': 26, 'name': '帽子', 'parent': 20},
            {'id': 27, 'name': 'その他', 'parent': 20},

            # 3. ベビー・キッズ
            {'id': 30, 'name': 'ベビー・キッズ', 'parent': None},
            {'id': 31, 'name': 'ベビーカー', 'parent': 30},
            {'id': 32, 'name': 'チャイルドシート', 'parent': 30},
            {'id': 33, 'name': 'ベビーベッド/寝具', 'parent': 30},
            {'id': 34, 'name': 'フォーマル服', 'parent': 30},
            {'id': 35, 'name': 'おもちゃ', 'parent': 30},
            {'id': 36, 'name': '知育玩具', 'parent': 30},
            {'id': 37, 'name': '抱っこひも/スリング', 'parent': 30},
            {'id': 38, 'name': 'その他', 'parent': 30},

            # 4. 家具・インテリア
            {'id': 40, 'name': '家具・インテリア', 'parent': None},
            {'id': 41, 'name': 'ソファ', 'parent': 40},
            {'id': 42, 'name': 'ベッド/マットレス', 'parent': 40},
            {'id': 43, 'name': '机/デスク', 'parent': 40},
            {'id': 44, 'name': '椅子/チェア', 'parent': 40},
            {'id': 45, 'name': '収納家具', 'parent': 40},
            {'id': 46, 'name': 'テーブル', 'parent': 40},
            {'id': 47, 'name': '照明', 'parent': 40},
            {'id': 48, 'name': 'ラグ/カーペット', 'parent': 40},
            {'id': 49, 'name': 'カーテン', 'parent': 40},
            {'id': 50, 'name': 'インテリア雑貨', 'parent': 40},
            {'id': 51, 'name': 'その他', 'parent': 40},

            # 5. 家電
            {'id': 60, 'name': '家電', 'parent': None},
            {'id': 61, 'name': 'テレビ/モニター', 'parent': 60},
            {'id': 62, 'name': '冷蔵庫', 'parent': 60},
            {'id': 63, 'name': '洗濯機/乾燥機', 'parent': 60},
            {'id': 64, 'name': 'エアコン', 'parent': 60},
            {'id': 65, 'name': '掃除機', 'parent': 60},
            {'id': 66, 'name': '電子レンジ/オーブン', 'parent': 60},
            {'id': 67, 'name': '空気清浄機', 'parent': 60},
            {'id': 68, 'name': '加湿器/除湿機', 'parent': 60},
            {'id': 69, 'name': 'ヒーター/ストーブ', 'parent': 60},
            {'id': 70, 'name': '扇風機/サーキュレーター', 'parent': 60},
            {'id': 71, 'name': 'その他', 'parent': 60},

            # 6. カメラ・映像機器
            {'id': 80, 'name': 'カメラ・映像機器', 'parent': None},
            {'id': 81, 'name': '一眼レフカメラ', 'parent': 80},
            {'id': 82, 'name': 'ミラーレスカメラ', 'parent': 80},
            {'id': 83, 'name': 'ビデオカメラ', 'parent': 80},
            {'id': 84, 'name': 'アクションカメラ', 'parent': 80},
            {'id': 85, 'name': 'ドローン', 'parent': 80},
            {'id': 86, 'name': 'レンズ', 'parent': 80},
            {'id': 87, 'name': '三脚/スタビライザー', 'parent': 80},
            {'id': 88, 'name': '照明機材', 'parent': 80},
            {'id': 89, 'name': 'プロジェクター', 'parent': 80},
            {'id': 90, 'name': 'その他', 'parent': 80},

            # 7. PC・タブレット
            {'id': 100, 'name': 'PC・タブレット', 'parent': None},
            {'id': 101, 'name': 'ノートPC', 'parent': 100},
            {'id': 102, 'name': 'デスクトップPC', 'parent': 100},
            {'id': 103, 'name': 'タブレット', 'parent': 100},
            {'id': 104, 'name': 'モニター/ディスプレイ', 'parent': 100},
            {'id': 105, 'name': 'キーボード/マウス', 'parent': 100},
            {'id': 106, 'name': 'PC周辺機器', 'parent': 100},
            {'id': 107, 'name': 'その他', 'parent': 100},

            # 8. スマートフォン・通信機器
            {'id': 110, 'name': 'スマートフォン・通信機器', 'parent': None},
            {'id': 111, 'name': 'スマートフォン', 'parent': 110},
            {'id': 112, 'name': 'Wi-Fiルーター', 'parent': 110},
            {'id': 113, 'name': 'モバイルバッテリー', 'parent': 110},
            {'id': 114, 'name': 'スマートウォッチ', 'parent': 110},
            {'id': 115, 'name': 'その他', 'parent': 110},

            # 9. オーディオ機器
            {'id': 120, 'name': 'オーディオ機器', 'parent': None},
            {'id': 121, 'name': 'スピーカー', 'parent': 120},
            {'id': 122, 'name': 'ヘッドフォン/イヤフォン', 'parent': 120},
            {'id': 123, 'name': 'アンプ', 'parent': 120},
            {'id': 124, 'name': 'レコードプレーヤー', 'parent': 120},
            {'id': 125, 'name': 'マイク', 'parent': 120},
            {'id': 126, 'name': 'その他', 'parent': 120},

            # 10. 楽器・音楽機材
            {'id': 130, 'name': '楽器・音楽機材', 'parent': None},
            {'id': 131, 'name': 'ギター/ベース', 'parent': 130},
            {'id': 132, 'name': 'ピアノ/キーボード', 'parent': 130},
            {'id': 133, 'name': 'ドラム/パーカッション', 'parent': 130},
            {'id': 134, 'name': '管楽器', 'parent': 130},
            {'id': 135, 'name': '弦楽器', 'parent': 130},
            {'id': 136, 'name': '和楽器', 'parent': 130},
            {'id': 137, 'name': 'DJ機器', 'parent': 130},
            {'id': 138, 'name': 'PA/レコーディング機器', 'parent': 130},
            {'id': 139, 'name': 'その他', 'parent': 130},

            # 11. スポーツ用品
            {'id': 140, 'name': 'スポーツ用品', 'parent': None},
            {'id': 141, 'name': 'ゴルフ', 'parent': 140},
            {'id': 142, 'name': 'テニス/バドミントン', 'parent': 140},
            {'id': 143, 'name': '野球', 'parent': 140},
            {'id': 144, 'name': 'サッカー/フットサル', 'parent': 140},
            {'id': 145, 'name': 'スキー/スノーボード', 'parent': 140},
            {'id': 146, 'name': 'サーフィン/マリンスポーツ', 'parent': 140},
            {'id': 147, 'name': 'フィットネス/トレーニング', 'parent': 140},
            {'id': 148, 'name': '自転車', 'parent': 140},
            {'id': 149, 'name': 'その他', 'parent': 140},

            # 12. アウトドア・キャンプ
            {'id': 150, 'name': 'アウトドア・キャンプ', 'parent': None},
            {'id': 151, 'name': 'テント', 'parent': 150},
            {'id': 152, 'name': 'タープ/シェルター', 'parent': 150},
            {'id': 153, 'name': 'シュラフ/寝袋', 'parent': 150},
            {'id': 154, 'name': 'テーブル/チェア', 'parent': 150},
            {'id': 155, 'name': 'バーベキュー用品', 'parent': 150},
            {'id': 156, 'name': 'クーラーボックス', 'parent': 150},
            {'id': 157, 'name': 'ランタン/ライト', 'parent': 150},
            {'id': 158, 'name': '登山用品', 'parent': 150},
            {'id': 159, 'name': '釣り具', 'parent': 150},
            {'id': 160, 'name': 'その他', 'parent': 150},

            # 13. 旅行用品
            {'id': 170, 'name': '旅行用品', 'parent': None},
            {'id': 171, 'name': 'スーツケース', 'parent': 170},
            {'id': 172, 'name': 'キャリーバッグ', 'parent': 170},
            {'id': 173, 'name': 'バックパック', 'parent': 170},
            {'id': 174, 'name': 'トラベルグッズ', 'parent': 170},
            {'id': 175, 'name': 'その他', 'parent': 170},

            # 14. 自動車・バイク用品
            {'id': 180, 'name': '自動車・バイク用品', 'parent': None},
            {'id': 181, 'name': 'カーナビ', 'parent': 180},
            {'id': 182, 'name': 'ドライブレコーダー', 'parent': 180},
            {'id': 183, 'name': 'ETC車載器', 'parent': 180},
            {'id': 184, 'name': 'タイヤ/ホイール', 'parent': 180},
            {'id': 185, 'name': 'ルーフキャリア/ルーフボックス', 'parent': 180},
            {'id': 186, 'name': 'バイク用品', 'parent': 180},
            {'id': 187, 'name': 'その他', 'parent': 180},

            # 15. ゲーム
            {'id': 190, 'name': 'ゲーム', 'parent': None},
            {'id': 191, 'name': '家庭用ゲーム機', 'parent': 190},
            {'id': 192, 'name': '携帯ゲーム機', 'parent': 190},
            {'id': 193, 'name': 'ゲームソフト', 'parent': 190},
            {'id': 194, 'name': 'VR機器', 'parent': 190},
            {'id': 195, 'name': 'ゲーミングPC/デバイス', 'parent': 190},
            {'id': 196, 'name': 'その他', 'parent': 190},

            # 16. おもちゃ・ホビー
            {'id': 200, 'name': 'おもちゃ・ホビー', 'parent': None},
            {'id': 201, 'name': 'フィギュア', 'parent': 200},
            {'id': 202, 'name': 'プラモデル/模型', 'parent': 200},
            {'id': 203, 'name': 'ラジコン', 'parent': 200},
            {'id': 204, 'name': 'ボードゲーム', 'parent': 200},
            {'id': 205, 'name': 'パズル', 'parent': 200},
            {'id': 206, 'name': 'ぬいぐるみ', 'parent': 200},
            {'id': 207, 'name': 'コスプレ衣装', 'parent': 200},
            {'id': 208, 'name': 'その他', 'parent': 200},

            # 17. 本・メディア
            {'id': 210, 'name': '本・メディア', 'parent': None},
            {'id': 211, 'name': '本/書籍', 'parent': 210},
            {'id': 212, 'name': '漫画/コミック', 'parent': 210},
            {'id': 213, 'name': 'CD/レコード', 'parent': 210},
            {'id': 214, 'name': 'DVD/ブルーレイ', 'parent': 210},
            {'id': 215, 'name': '楽譜', 'parent': 210},
            {'id': 216, 'name': 'その他', 'parent': 210},

            # 18. 美容機器
            {'id': 220, 'name': '美容機器', 'parent': None},
            {'id': 221, 'name': '美顔器', 'parent': 220},
            {'id': 222, 'name': '脱毛器', 'parent': 220},
            {'id': 223, 'name': 'ドライヤー/ヘアアイロン', 'parent': 220},
            {'id': 224, 'name': 'マッサージ機器', 'parent': 220},
            {'id': 225, 'name': 'その他', 'parent': 220},

            # 19. イベント・パーティー用品
            {'id': 230, 'name': 'イベント・パーティー用品', 'parent': None},
            {'id': 231, 'name': 'パーティーグッズ', 'parent': 230},
            {'id': 232, 'name': '季節イベント用品', 'parent': 230},
            {'id': 233, 'name': 'ウェディング用品', 'parent': 230},
            {'id': 234, 'name': '撮影用背景/小道具', 'parent': 230},
            {'id': 235, 'name': 'その他', 'parent': 230},

            # 20. 工具・DIY
            {'id': 240, 'name': '工具・DIY', 'parent': None},
            {'id': 241, 'name': '電動工具', 'parent': 240},
            {'id': 242, 'name': '手工具', 'parent': 240},
            {'id': 243, 'name': '計測機器', 'parent': 240},
            {'id': 244, 'name': '高圧洗浄機', 'parent': 240},
            {'id': 245, 'name': '発電機', 'parent': 240},
            {'id': 246, 'name': 'その他', 'parent': 240},

            # 21. その他
            {'id': 250, 'name': 'その他', 'parent': None},
            {'id': 251, 'name': 'オフィス用品', 'parent': 250},
            {'id': 252, 'name': 'アンティーク/コレクション', 'parent': 250},
            {'id': 253, 'name': 'その他', 'parent': 250},
        ]

        # 親カテゴリを先に作成
        parent_categories = [c for c in categories if c['parent'] is None]
        child_categories = [c for c in categories if c['parent'] is not None]

        created_count = 0

        # 親カテゴリ作成
        for cat in parent_categories:
            ProductCategory.objects.create(
                product_category_id=cat['id'],
                category_name=cat['name'],
                parent_product_category=None
            )
            created_count += 1

        # 子カテゴリ作成
        for cat in child_categories:
            parent = ProductCategory.objects.get(product_category_id=cat['parent'])
            ProductCategory.objects.create(
                product_category_id=cat['id'],
                category_name=cat['name'],
                parent_product_category=parent
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'{created_count}件のカテゴリを登録しました'))
