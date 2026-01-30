# CHANGELOG v1.7.0

## 概要
銀行口座管理機能の追加、出品時の受取口座バリデーション

---

## 1. モデル変更

### 1.1 BankAccountモデルの追加
**ファイル**: `appfew/monotal/models.py`

```python
class BankAccount(models.Model):
    """
    銀行口座テーブル
    ユーザーの振込・受取用銀行口座を管理

    【口座種別】
    - 1: 普通
    - 2: 当座
    """
    ACCOUNT_TYPE_CHOICES = [
        (1, '普通'),
        (2, '当座'),
    ]

    bank_account_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_accounts')
    bank_name = models.CharField(max_length=100)  # 銀行名
    branch_name = models.CharField(max_length=100)  # 支店名
    account_type = models.IntegerField(choices=ACCOUNT_TYPE_CHOICES, default=1)  # 口座種別
    account_number = models.CharField(max_length=20)  # 口座番号
    account_holder = models.CharField(max_length=100)  # 口座名義（カナ）
    is_default = models.BooleanField(default=False)  # デフォルト口座フラグ
    register_datetime = models.DateTimeField(auto_now_add=True)
    update_datetime = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'T_BankAccount'
```

**プロパティ**:
- `masked_account_number`: 口座番号をマスク表示（下4桁のみ表示）
- `account_type_display`: 口座種別の表示名

---

## 2. ビュー変更

### 2.1 MyPageBankAccountListViewの追加
**ファイル**: `appfew/monotal/views.py`

銀行口座管理ページ:
- 口座一覧表示
- 新規登録（POST、最大3件制限）
- Ajax対応

### 2.2 BankAccountEditViewの追加
銀行口座編集API:
- 口座情報の更新
- バリデーション付き

### 2.3 BankAccountDeleteViewの追加
銀行口座削除API:
- 口座の削除
- デフォルト口座削除時は残りの最初の口座をデフォルトに設定

### 2.4 CreateSellViewの改善
- `has_bank_account`をコンテキストに追加
- 受取口座未登録時のバリデーションエラー追加

### 2.5 ProductEditViewの改善
- `has_bank_account`をコンテキストに追加
- 受取口座未登録時のバリデーションエラー追加

---

## 3. URL追加

**ファイル**: `appfew/monotal/urls.py`

```python
path('mypage/bank-accounts/', views.mypage_bank_account_list, name='mypage_bank_account_list'),
path('mypage/bank-accounts/<int:bank_account_id>/edit/', views.bank_account_edit, name='bank_account_edit'),
path('mypage/bank-accounts/<int:bank_account_id>/delete/', views.bank_account_delete, name='bank_account_delete'),
```

---

## 4. テンプレート変更

### 4.1 mypage/bank_account_list.html（新規）
銀行口座管理ページ:
- 口座一覧表示（カード形式）
- 新規登録モーダル
- 編集モーダル
- 削除確認モーダル
- 最大3件の制限表示

### 4.2 mypage/_sidebar.html
- 「支払い方法」を「口座管理」に変更
- アイコンを`lucide:building-2`に変更
- アクティブ状態の判定追加

### 4.3 create_sell.html
- 受取口座セクションを追加
- 口座登録済み/未登録の状態表示
- 口座管理ページへのリンク

### 4.4 product_edit.html
- 受取口座セクションを追加（create_sell.htmlと同様）

---

## 5. CSS変更

### 5.1 create-sell.css
- `.bank-account-status`: 口座登録済み状態のスタイル

---

## 6. JavaScript追加

### 6.1 bank-account-manage.js（新規）
銀行口座管理ページ用JavaScript:
- 新規登録モーダル制御
- 編集モーダル制御
- 削除確認モーダル制御
- Ajax通信処理

---

## 7. マイグレーション

### 0010_bankaccount.py（新規）
- BankAccountモデルの作成

---

## 定数

```python
MAX_BANK_ACCOUNTS = 3  # 銀行口座の最大登録数
```

---

## 実行コマンド

```bash
python manage.py migrate
```
