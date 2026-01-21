# MONOTAL 変更履歴 v1.3.0

**更新日**: 2026-01-21
**概要**: 商品編集機能の追加、プロフィールページの機能強化、発送料負担マスターの追加

---

## 目次

1. [新機能](#1-新機能)
2. [モデル変更](#2-モデル変更)
3. [ビュー変更](#3-ビュー変更)
4. [テンプレート変更](#4-テンプレート変更)
5. [CSS変更](#5-css変更)
6. [JavaScript変更](#6-javascript変更)
7. [マイグレーション変更](#7-マイグレーション変更)
8. [URL変更](#8-url変更)
9. [ファイル一覧](#9-ファイル一覧)

---

## 1. 新機能

### 1.1 商品編集機能

出品者が自分の商品を編集できる機能を追加。

**機能詳細**:
- 商品名、説明、カテゴリー、商品状態の編集
- 公開ステータスの変更（貸出可能 / 非公開 / 削除）
- 商品画像の追加・削除
- レンタルプランの編集（複数プラン対応）
- 発送元住所の編集
- 発送料負担の設定

**アクセス制御**:
- 出品者本人のみアクセス可能
- 商品詳細ページから「商品を編集する」ボタンで遷移

### 1.2 プロフィールページのタブ機能

**出品リストタブ**:
- 従来通りユーザーの出品商品を表示
- 自分のプロフィール: 非公開商品も表示（非公開バッジ付き）
- 他人のプロフィール: 公開商品のみ表示

**お気に入りタブ**（自分のプロフィールのみ）:
- ブックマークした商品一覧を表示
- 非公開・削除商品は自動除外

### 1.3 本人確認状態の条件付き表示

- 本人確認済み（user_status_id == 2）の場合のみバッジを表示
- 未確認の場合、自分のプロフィールには「本人確認する」リンクを表示

### 1.4 発送料負担マスター

配送料の負担者を選択できるマスターデータを追加。

**選択肢例**:
- 出品者負担
- レンタル者負担

---

## 2. モデル変更

### 2.1 ShippingBurden（新規モデル）

**ファイル**: `appfew/monotal/models.py:578-592`

```python
class ShippingBurden(models.Model):
    """
    発送料負担マスター
    例: 出品者負担、レンタル者負担
    """
    shipping_burden_id = models.AutoField(primary_key=True)
    burden_name = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'M_ShippingBurden'
        verbose_name = '発送料負担'
        verbose_name_plural = '発送料負担'
```

### 2.2 Productモデルへのフィールド追加

**追加フィールド**:
```python
shipping_burden = models.ForeignKey(
    ShippingBurden,
    on_delete=models.PROTECT,
    db_column='shipping_burden_id',
    null=True,
    blank=True
)
```

### 2.3 min_rental_plan プロパティ追加

最短日数のレンタルプランを取得するプロパティを追加。

```python
@property
def min_rental_plan(self):
    """最短日数のレンタルプランを取得"""
    return self.rental_plans.order_by('rental_days').first()
```

**用途**: 商品一覧やプロフィールで「¥1,500/3日〜」のような表示に使用。

---

## 3. ビュー変更

### 3.1 ProductEditView（新規ビュー）

**ファイル**: `appfew/monotal/views.py:1295-1576`

**GET処理**:
- 商品情報の取得（select_related, prefetch_related で最適化）
- 出品者以外はアクセス拒否
- マスターデータ（カテゴリー、状態、都道府県、発送日数、発送料負担）の取得
- レンタルプランの取得

**POST処理**:
- フォームバリデーション
  - 商品名: 必須、40文字以内
  - カテゴリー: 必須
  - 商品の説明: 必須、1000文字以内
  - 商品の状態: 必須
  - 発送までの日数: 必須
  - レンタルプラン: 1つ以上必須、金額100円以上
  - 住所: 郵便番号7桁、都道府県、市区町村、番地 必須
- 画像の追加・削除処理
- レンタルプランの更新（全削除→再作成）
- ユーザー住所の更新

**レスポンス**:
- AJAX: JSON形式でsuccess/errorsを返却
- 通常: リダイレクト + messages

### 3.2 ProfileView の改善

**ファイル**: `appfew/monotal/views.py:353-404`

**変更点**:
1. `is_own_profile` フラグの追加
2. 商品フィルタリングの改善
   - 削除商品（status_id=4）は常に除外
   - 他人のプロフィール: 非公開商品（status_id=3）も除外
3. ブックマーク商品の取得（自分のプロフィールのみ）

### 3.3 ProductListView の改善

**ファイル**: `appfew/monotal/views.py:821-830`

**変更点**:
- 非公開・削除商品を商品一覧から除外
```python
.exclude(product_status_id__in=[3, 4])
```

### 3.4 ProductDetailView の改善

**ファイル**: `appfew/monotal/views.py:969-984`

**変更点**:
1. 削除商品（status_id=4）へのアクセスを拒否
2. 非公開商品（status_id=3）は出品者のみアクセス可能

### 3.5 CreateSellView の改善

**ファイル**: `appfew/monotal/views.py:525-747`

**変更点**:
1. `shipping_burdens` をコンテキストに追加
2. `shipping_burden_id` の取得・バリデーション
3. 商品作成時に `shipping_burden` を保存

---

## 4. テンプレート変更

### 4.1 product_edit.html（新規）

**ファイル**: `appfew/templates/product_edit.html`

**構成**:
- 商品画像セクション（既存画像表示、削除、新規追加）
- 基本情報セクション（商品名、カテゴリー、状態、公開ステータス、説明）
- レンタルプランセクション（動的追加・削除）
- 配送・発送元情報セクション（発送日数、発送料負担、住所）

**特徴**:
- create_sell.html と同じCSS（create-sell.css）を使用
- 既存データのプリフィル
- 公開ステータス選択（貸出可能 / 非公開 / 削除）

### 4.2 profile.html の改善

**変更点**:

1. **本人確認バッジの条件付き表示**
```html
{% if profile_user.user_status_id == 2 %}
<!-- 本人確認済みバッジ -->
{% elif request.user == profile_user %}
<!-- 本人確認するリンク -->
{% endif %}
```

2. **タブUI追加**
```html
<button class="profile-tab active" data-tab="products">出品リスト</button>
<button class="profile-tab" data-tab="bookmarks">お気に入り</button>
```

3. **商品ステータスバッジの改善**
- status_id=1（貸出可能）: 緑色
- status_id=2（レンタル中）: オレンジ色
- status_id=3（非公開）: グレー

4. **価格表示の改善**
```html
{% if product.min_rental_plan %}
<span>¥{{ product.min_rental_plan.rental_fee|floatformat:0 }}</span>
<span>/{{ product.min_rental_plan.rental_days }}日〜</span>
{% endif %}
```

5. **お気に入りタブコンテンツ追加**
```html
<div id="tab-bookmarks" class="tab-content hidden">
    {% for product in bookmarked_products %}
    ...
    {% empty %}
    <!-- 空の状態表示 -->
    {% endfor %}
</div>
```

### 4.3 product_detail.html の改善

**変更点**:

1. **パンくずリストの位置変更**
   - detail-container の外から detail-left の中に移動
   - レイアウトの改善

2. **商品ステータスバッジの動的表示**
```html
{% if product.product_status %}
<div class="rental-badge status-{{ product.product_status.product_status_id }}">
    {{ product.product_status.status_name }}
</div>
{% endif %}
```

3. **配送料負担の表示**
```html
<span class="spec-value">
    {% if product.shipping_burden %}{{ product.shipping_burden.burden_name }}{% else %}-{% endif %}
</span>
```

4. **編集ボタンの追加（出品者のみ）**
```html
{% if is_seller %}
<a href="{% url 'product_edit' product_id=product.product_id %}" class="edit-product-btn">
    <span class="iconify" data-icon="lucide:edit" data-width="16"></span>
    商品を編集する
</a>
{% else %}
<button class="rental-cta-btn">レンタル手続きへ</button>
{% endif %}
```

### 4.4 create_sell.html の改善

**変更点**:

1. **発送料負担セレクトボックス追加**
```html
<div class="form-group">
    <label class="input-label">配送料の負担</label>
    <div class="select-wrapper">
        <select id="shippingBurden" class="form-select">
            <option value="" disabled selected>選択してください</option>
            {% for sb in shipping_burdens %}
            <option value="{{ sb.shipping_burden_id }}">{{ sb.burden_name }}</option>
            {% endfor %}
        </select>
    </div>
</div>
```

2. **プレースホルダーの改善**
   - 「3」→「日付を入力」
   - 「1,500」→「金額を入力」

### 4.5 base.html の改善

**変更点**:
- セカンダリナビゲーションをブロック化
- トップページ以外ではセカンダリナビを非表示に

```html
<!-- 変更前: 直接ハードコード -->
<div class="border-t border-zinc-100 bg-white">...</div>

<!-- 変更後: ブロック化 -->
{% block secondary_nav %}{% endblock %}
```

### 4.6 home.html の改善

- `{% block secondary_nav %}` でセカンダリナビを定義
- トップページのみカテゴリーナビが表示される

### 4.7 product_list.html の改善

**変更点**:

1. **価格表示の改善**
```html
{% if product.min_rental_plan %}
<div class="price-pill">
    <span>¥{{ product.min_rental_plan.rental_fee|floatformat:0 }}/{{ product.min_rental_plan.rental_days }}日〜</span>
</div>
{% endif %}
```

2. **不要な表示の削除**
   - レンタル日数表示（`.rental-duration`）を削除（価格に統合）

---

## 5. CSS変更

### 5.1 product_detail.css

**追加スタイル**:

1. **ステータスバッジの色分け**
```css
.rental-badge.status-1 {  /* 貸出可能 */
    color: #059669;
    border-color: rgba(5, 150, 105, 0.2);
}

.rental-badge.status-2 {  /* レンタル中 */
    color: #d97706;
    border-color: rgba(217, 119, 6, 0.2);
}

.rental-badge.status-3 {  /* 非公開 */
    color: #71717a;
    border-color: rgba(113, 113, 122, 0.2);
}
```

2. **編集ボタン**
```css
.edit-product-btn {
    width: 100%;
    border-radius: 8px;
    background: #18181b;
    padding: 14px;
    font-size: 16px;
    font-weight: 700;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}
```

### 5.2 create-sell.css

**追加スタイル**:

1. **フィールドヒント**
```css
.field-hint {
    font-size: 11px;
    color: #a1a1aa;
    margin: 6px 0 0 0;
}
```

2. **既存画像アイテム（編集ページ用）**
```css
.existing-image-item {
    aspect-ratio: 1;
    border-radius: 8px;
    border: 1px solid #e4e4e7;
    position: relative;
    overflow: hidden;
}

.existing-image-item .delete-image-btn {
    position: absolute;
    top: 4px;
    right: 4px;
    background: rgba(0, 0, 0, 0.5);
    opacity: 0;
    transition: opacity 0.2s;
}

.existing-image-item:hover .delete-image-btn {
    opacity: 1;
}
```

3. **キャンセルリンク**
```css
.cancel-link {
    display: block;
    text-align: center;
    margin-top: 16px;
    color: #71717a;
}
```

---

## 6. JavaScript変更

### 6.1 product-edit.js（新規）

**ファイル**: `appfew/statics/js/product-edit.js`

**機能**:

1. **画像管理**
   - 既存画像の削除（deleteImageIds配列で管理）
   - 新規画像のアップロード・プレビュー
   - 最大10枚制限
   - ファイルサイズ制限（10MB）

2. **レンタルプラン管理**
   - 動的な行追加・削除
   - 最低1行は維持

3. **郵便番号から住所自動入力**
   - zipcloud API を使用
   - 都道府県・市区町村を自動入力

4. **フォーム送信**
   - クライアントサイドバリデーション
   - FormData でマルチパート送信
   - AJAX送信（X-Requested-With: XMLHttpRequest）

5. **文字数カウント**
   - 商品名（40文字）
   - 説明（1000文字）

### 6.2 profile.js の改善

**追加機能**:
- タブ切り替え機能（`initTabs`関数）

```javascript
function initTabs() {
    const tabs = document.querySelectorAll('.profile-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            // タブスタイルの切り替え
            // コンテンツの表示/非表示切り替え
        });
    });
}
```

### 6.3 create-sell.js の改善

**変更点**:
1. プレースホルダーを「日付を入力」「金額を入力」に変更
2. `shipping_burden` フィールドの送信対応

### 6.4 login.js の改善

**変更点**:
- エラーメッセージを「電話番号またはメールアドレスを入力してください」から「電話番号を入力してください」に変更

---

## 7. マイグレーション変更

### 7.1 削除されたマイグレーション

以下のマイグレーションファイルを削除し、統合:

- `0002_user_bio.py`
- `0003_userhobby.py`
- `0004_productimage.py`
- `0005_prefecture_remove_useraddress_building_name_and_more.py`
- `0006_populate_prefectures.py`
- `0007_shippingdays_product_shipping_days.py`
- `0008_populate_shipping_days.py`

### 7.2 新規マイグレーション

#### 0002_populate_master_data.py

全マスターテーブルに初期データを一括投入。

**対象テーブル**（20種類）:
1. UserStatus（ユーザーステータス）
2. IdentityVerificationStatus（本人確認ステータス）
3. Prefecture（都道府県）
4. ProductCondition（商品状態）
5. ProductStatus（商品ステータス）
6. ShippingMethod（配送方法）
7. ShippingDays（発送日数）
8. RentalStatus（レンタルステータス）
9. RentalRequestStatus（レンタルリクエストステータス）
10. ReturnReason（返却理由）
11. ReportReason（通報理由）
12. ViolationReason（違反理由）
13. ViolationStatus（違反ステータス）
14. PaymentType（支払い方法）
15. InsuranceEnrollmentStatus（保険加入ステータス）
16. ChatRoomType（チャットルームタイプ）
17. MessageReadStatus（メッセージ既読ステータス）
18. NotificationType（通知タイプ）
19. NotificationReadStatus（通知既読ステータス）
20. TargetUserType（ターゲットユーザータイプ）

#### 0003_add_shipping_burden.py

**操作**:
1. `ShippingBurden` モデルの作成
2. `Product` モデルに `shipping_burden` フィールドを追加

---

## 8. URL変更

### 8.1 追加されたURL

**ファイル**: `appfew/monotal/urls.py:19`

```python
path('product/<int:product_id>/edit/', views.product_edit, name='product_edit'),
```

**URL**: `/monotal/product/{product_id}/edit/`
**ビュー**: `ProductEditView`
**名前**: `product_edit`

---

## 9. ファイル一覧

### 変更されたファイル（23ファイル）

| ファイル | 変更行数 | 概要 |
|---------|---------|------|
| `appfew/monotal/models.py` | +31 | ShippingBurden追加、Product改善 |
| `appfew/monotal/views.py` | +340 | ProductEditView追加、各View改善 |
| `appfew/monotal/urls.py` | +1 | product_edit URL追加 |
| `appfew/templates/profile.html` | +119 | タブUI、お気に入り、ステータス表示改善 |
| `appfew/templates/product_detail.html` | +51 | 編集ボタン、ステータスバッジ、パンくず移動 |
| `appfew/templates/create_sell.html` | +40 | 発送料負担選択追加 |
| `appfew/templates/home.html` | +18 | セカンダリナビをブロック化 |
| `appfew/templates/base.html` | -16 | セカンダリナビをブロック化 |
| `appfew/templates/product_list.html` | +8 | 価格表示改善 |
| `appfew/statics/css/product_detail.css` | +41 | ステータスバッジ色、編集ボタン |
| `appfew/statics/css/create-sell.css` | +65 | 既存画像アイテム、キャンセルリンク |
| `appfew/statics/js/profile.js` | +47 | タブ切り替え機能 |
| `appfew/statics/js/create-sell.js` | +8 | 発送料負担対応 |
| `appfew/statics/js/login.js` | +4 | エラーメッセージ修正 |
| `appfew/statics/css/admin_verification.css` | +6 | 軽微な修正 |

### 新規追加ファイル（4ファイル）

| ファイル | 行数 | 概要 |
|---------|-----|------|
| `appfew/templates/product_edit.html` | 255行 | 商品編集ページテンプレート |
| `appfew/statics/js/product-edit.js` | 573行 | 商品編集ページJavaScript |
| `appfew/monotal/migrations/0002_populate_master_data.py` | 273行 | マスターデータ投入 |
| `appfew/monotal/migrations/0003_add_shipping_burden.py` | 32行 | ShippingBurden追加 |

### 削除されたファイル（7ファイル）

- `appfew/monotal/migrations/0002_user_bio.py`
- `appfew/monotal/migrations/0003_userhobby.py`
- `appfew/monotal/migrations/0004_productimage.py`
- `appfew/monotal/migrations/0005_prefecture_remove_useraddress_building_name_and_more.py`
- `appfew/monotal/migrations/0006_populate_prefectures.py`
- `appfew/monotal/migrations/0007_shippingdays_product_shipping_days.py`
- `appfew/monotal/migrations/0008_populate_shipping_days.py`

---

## 今後の課題・TODO

1. **発送料負担マスターデータの投入**
   - ShippingBurden テーブルに「出品者負担」「レンタル者負担」等のデータを投入する必要あり

2. **商品編集のテスト**
   - 画像追加・削除の動作確認
   - レンタルプラン更新の動作確認
   - 公開ステータス変更時の挙動確認

3. **レンタル中商品の編集制御**
   - 現在、貸出中（status_id=2）の商品も編集可能
   - 必要に応じて編集制限を追加

---

## 実行が必要なコマンド

```bash
# マイグレーション適用
python manage.py migrate

# 発送料負担マスターデータの投入（管理画面またはシェルで）
# ShippingBurden.objects.create(burden_name='出品者負担')
# ShippingBurden.objects.create(burden_name='レンタル者負担')
```
