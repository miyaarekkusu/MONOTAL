# CHANGELOG v1.5.0

## 概要
v1.3.0の残り実装 + 発送方法マスターの削除 + マイページ改善

---

## 1. モデル変更

### 1.1 ShippingBurdenモデルの追加（v1.3.0）
**ファイル**: `appfew/monotal/models.py`

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

### 1.2 Productモデルの変更

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

**追加プロパティ**:
```python
@property
def min_rental_plan(self):
    """最短日数のレンタルプランを取得"""
    return self.rental_plans.order_by('rental_days').first()
```

**削除フィールド**:
- `shipping_method` - 発送方法フィールドを削除

### 1.3 ShippingMethodモデルの削除
発送方法マスター（M_ShippingMethod）を完全に削除

---

## 2. ビュー変更

### 2.1 ProductEditViewの追加（v1.3.0）
**ファイル**: `appfew/monotal/views.py`

商品編集ページを新規追加:
- 出品者本人のみアクセス可能
- 商品情報、画像、レンタルプラン、住所の編集が可能
- 画像の追加・削除対応

### 2.2 CreateSellViewの改善
- `shipping_burdens`をコンテキストに追加
- `shipping_burden_id`の取得と保存処理を追加
- `shipping_method`関連のコードを削除

### 2.3 ProductListViewの改善
- 非公開・削除商品（status_id=3,4）を除外
```python
.exclude(product_status_id__in=[3, 4])
```

### 2.4 ProductDetailViewの改善
- 削除商品（status_id=4）へのアクセスを拒否
- 非公開商品（status_id=3）は出品者のみアクセス可能
- `shipping_burden`のselect_relatedを追加
- `shipping_method`のselect_relatedを削除

---

## 3. URL追加

**ファイル**: `appfew/monotal/urls.py`

```python
path('product/<int:product_id>/edit/', views.product_edit, name='product_edit'),
```

---

## 4. テンプレート変更

### 4.1 base.html
- セカンダリナビゲーションをブロック化
- トップページ以外ではセカンダリナビを非表示に
```html
{% block secondary_nav %}{% endblock %}
```

### 4.2 home.html
- `{% block secondary_nav %}`でセカンダリナビを定義
- トップページのみカテゴリーナビが表示される

### 4.3 create_sell.html
- 発送料負担セレクトボックスを追加
- プレースホルダーを改善（「日数を入力」「金額を入力」）

### 4.4 product_detail.html
- 出品者の場合は「商品を編集する」ボタンを表示
- 配送料負担の動的表示を追加
- ステータスバッジの動的表示（status-1, status-2, status-3）
- 配送の方法（shipping_method）表示を削除

### 4.5 profile.html
- 価格表示を`min_rental_plan`を使用するように変更
- 表示形式: `¥X,XXX/Y日〜`

### 4.6 product_list.html
- 価格表示を`min_rental_plan`を使用するように変更
- `rental-duration`を削除（価格に統合）

### 4.7 マイページテンプレート（4ファイル）
- `mypage/bookmark_list.html`
- `mypage/browsing_history.html`
- `mypage/follow_list.html`
- `mypage/listing.html`

**変更内容**:
- 価格表示を`min_rental_plan`を使用するように変更
- 本人確認未完了バナーを追加（user_status_id != 2の場合）

```html
{% if request.user.user_status_id != 2 %}
<div class="mb-6 rounded-lg bg-amber-50 border border-amber-200 p-4">
    <div class="flex items-center gap-3">
        <span class="iconify text-amber-600 flex-shrink-0" data-icon="lucide:alert-triangle" data-width="20"></span>
        <div class="flex-1">
            <p class="text-sm font-medium text-amber-800">本人確認が完了していません</p>
            <p class="text-xs text-amber-600 mt-0.5">出品機能を利用するには本人確認が必要です。</p>
        </div>
        <a href="{% url 'identity_verification' %}" class="flex-shrink-0 rounded-full bg-amber-600 px-4 py-2 text-xs font-bold text-white hover:bg-amber-700 transition-colors">
            本人確認する
        </a>
    </div>
</div>
{% endif %}
```

---

## 5. CSS変更

### 5.1 product_detail.css
- ステータスバッジの色分け追加
  - `.status-1`: 貸出可能（緑）
  - `.status-2`: レンタル中（オレンジ）
  - `.status-3`: 非公開（グレー）
- 編集ボタンスタイル（`.edit-product-btn`）追加

### 5.2 create-sell.css
- `.field-hint`: フィールドヒントスタイル
- `.existing-image-item`: 既存画像アイテムスタイル（編集ページ用）
- `.cancel-link`: キャンセルリンクスタイル

---

## 6. JavaScript変更

### 6.1 create-sell.js
- `shipping_burden`の収集と送信を追加
- プレースホルダーを「日数を入力」「金額を入力」に変更

---

## 7. マイグレーション

### 0003_add_shipping_burden.py
- ShippingBurdenモデルの作成
- Productにshipping_burdenフィールドを追加
- 初期データ投入（出品者負担、レンタル者負担）

### 0004_remove_shipping_method.py
- Productからshipping_methodフィールドを削除
- ShippingMethodモデルを削除

---

## 8. admin.py変更
- ShippingMethodのインポートと登録を削除

---

## 実行コマンド

```bash
python manage.py migrate
```

---

## 削除されたもの

| 項目 | 説明 |
|------|------|
| ShippingMethodモデル | 発送方法マスター |
| Product.shipping_method | 商品の発送方法フィールド |
| M_ShippingMethodテーブル | データベーステーブル |
