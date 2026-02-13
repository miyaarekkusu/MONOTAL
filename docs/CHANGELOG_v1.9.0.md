# CHANGELOG v1.9.0

## リリース日
2026-02-09

## 概要
保険加入機能・補償申請（請求）機能の実装。ユーザーが月額料金で保険に加入し、レンタル商品の破損時に修理費用の補償を受けられる機能を追加。管理者向けの補償申請審査画面も実装。

---

## 新機能

### 1. 保険加入機能

#### 1.1 保険プラン
| 項目 | 内容 |
|-----|------|
| プラン名 | MONOTALあんしん補償 |
| 月額料金 | ¥2,000 |
| 補償上限 | ¥50,000 |
| 対象 | レンタル中の商品破損・故障 |

**補償内容**: 商品の修理費用、部品交換費用、修理不可の場合は上限額まで補償

#### 1.2 加入フロー
1. マイページサイドバーの「保険」からアクセス
2. プラン内容を確認
3. 「月額¥2,000で加入する」ボタンをクリック
4. Ajax処理で即座に加入完了（自動承認）
5. トースト通知で結果表示

#### 1.3 解約
- 確認モーダル表示後に解約処理
- `insurance_end_datetime` を設定（レコード削除はしない）
- いつでも再加入可能

---

### 2. 補償申請（請求）機能

#### 2.1 補償申請フロー
1. 保険加入済みユーザーがマイページから「補償を申請する」
2. レンタル履歴を選択（キャンセル済み・補償申請済みは除外）
3. 破損内容と修理費用（1〜50,000円）を入力
4. 3種類の画像をアップロード:
   - **破損した商品の画像** (image_type=1)
   - **修理費用の領収書** (image_type=2)
   - **修理後の商品の画像** (image_type=3)
5. 補償申請完了（status=1: 審査中）

#### 2.2 リアルタイムバリデーション
- 各フィールドごとにインラインエラーメッセージ表示（赤文字 + 赤枠）
- レンタル履歴: `change` 時に未選択チェック
- 破損内容: `blur` 時に空チェック、入力中はエラークリア
- 修理費用: `type="text" inputmode="numeric"` で数字のみ許可、`input`/`blur` 時に範囲チェック
- 画像: `change` 時に未選択・サイズ(5MB)・形式チェック
- サーバー側も `field` キー付きJSONでフィールド特定エラーを返却

#### 2.3 管理者審査フロー
1. `/admin/insurance/claims/` で補償申請一覧を確認
2. ステータスフィルタータブで絞り込み（すべて/審査中/承認済み/却下）
3. 詳細ページで申請者情報・レンタル情報・破損内容・画像を確認
4. Ajax承認/却下処理（ページ遷移なし）
5. 却下時は却下理由モーダルで理由入力
6. トースト通知で結果表示後、自動で一覧に遷移

#### 2.4 審査結果通知
- 承認/却下時に補償申請者へシステム通知を送信
- 承認: 「補償申請が承認されました」+ 商品名・補償金額
- 却下: 「補償申請が却下されました」+ 却下理由（ある場合）
- 通知リンク先: 保険ページ（`/mypage/insurance/`）

---

## データベース変更

### マイグレーション: `0022_insuranceclaimstatus_insurance_coverage_limit_and_more.py`

#### 既存モデルの拡張
**Insurance（保険マスター）**:
- `coverage_limit` (DecimalField): 補償上限金額を追加

#### 新規モデル

| モデル | テーブル名 | 説明 |
|-------|-----------|------|
| InsuranceClaimStatus | M_InsuranceClaimStatus | 補償申請ステータスマスター |
| InsuranceClaim | T_InsuranceClaim | 補償申請本体 |
| InsuranceClaimImage | T_InsuranceClaimImage | 補償申請添付画像 |

#### マスターデータ

**M_InsuranceClaimStatus**:
| ID | status_name |
|----|------------|
| 1 | 審査中 |
| 2 | 承認 |
| 3 | 却下 |

**M_RentalRequestStatus（追加）**:
| ID | status_name |
|----|------------|
| 5 | 取引完了 |

---

## ファイル構成

### ビュー
| ファイル | 内容 |
|---------|------|
| `monotal/views_insurance.py` | 保険関連ビュー（ユーザー側5つ + 管理者側4つ + 通知ヘルパー1つ） |

**ユーザー側ビュー**:
- `insurance_page` - 保険加入ページ表示
- `insurance_enroll` - 保険加入処理（POST/Ajax）
- `insurance_cancel` - 保険解約処理（POST/Ajax）
- `insurance_claim_page` - 補償申請ページ表示
- `insurance_claim_submit` - 補償申請処理（POST/Ajax + fieldバリデーション）

**管理者側ビュー**:
- `admin_insurance_claims` - 補償申請一覧（フィルター機能付き）
- `admin_insurance_claim_detail` - 補償申請詳細（GET/POST Ajax承認・却下）
- `insurance_claim_approve` - 承認処理（フォールバック）
- `insurance_claim_reject` - 却下処理（フォールバック）
- `_send_claim_notification` - 審査結果通知ヘルパー

### テンプレート
| ファイル | 内容 |
|---------|------|
| `templates/mypage/insurance.html` | 保険加入/解約ページ（トースト通知、解約確認モーダル） |
| `templates/mypage/insurance_claim.html` | 補償申請フォーム（リアルタイムバリデーション） |
| `templates/admin/insurance_claims.html` | 補償申請一覧（ステータスフィルタータブ） |
| `templates/admin/insurance_claim_detail.html` | 補償申請詳細（Ajax承認/却下、画像モーダル、却下理由モーダル） |

### 静的ファイル
| ファイル | 内容 |
|---------|------|
| `statics/css/admin_insurance.css` | 管理者画面CSS（フィルタータブ、却下モーダル、結果カード等） |
| `statics/js/admin_insurance.js` | 管理者画面JS（Ajax処理、モーダル、トースト通知） |

### URL設計
```
# ユーザー側
mypage/insurance/                    → insurance_page
mypage/insurance/enroll/             → insurance_enroll
mypage/insurance/cancel/             → insurance_cancel
mypage/insurance/claim/              → insurance_claim_page
mypage/insurance/claim/submit/       → insurance_claim_submit

# 管理者側
admin/insurance/claims/              → admin_insurance_claims
admin/insurance/claims/<id>/         → admin_insurance_claim_detail
admin/insurance/claims/<id>/approve/ → insurance_claim_approve
admin/insurance/claims/<id>/reject/  → insurance_claim_reject
```

---

## UI/UXデザイン

### ユーザー側
- Tailwind CSSベースのマイページ統一デザイン
- 保険加入: ボタンローディング状態 + トースト通知
- 保険解約: 確認モーダル（注意アイコン + 説明文）→ トースト通知
- 補償申請: リアルタイムフィールドバリデーション + サーバーエラー表示

### 管理者側
- 本人確認審査ページと統一されたUI（`admin_verification.css` ベース）
- `info-card` / `info-row` レイアウト
- ステータスバッジ（pending/approved/rejected）
- 画像クリック拡大モーダル
- Ajax承認/却下（ページ遷移なし）+ トースト通知
- 却下理由入力モーダル
- ステータスフィルタータブ（すべて/審査中/承認済み/却下）+ 件数バッジ

---

## 統合箇所

### マイページサイドバー
- `templates/mypage/_sidebar.html` に保険リンクを追加
- アイコン: `lucide:shield-check`
- アクティブ状態のハイライト対応

---

## セキュリティ

1. **認証**: 全ビューに `@login_required` 適用
2. **権限**: 管理者ビューで `is_staff` チェック（GET/POST両方）
3. **CSRF**: Ajax通信時に `X-CSRFToken` ヘッダー送信
4. **バリデーション**: クライアント側 + サーバー側の二重チェック
5. **重複防止**: 同一レンタル履歴への二重補償申請防止
6. **通知失敗**: 通知送信失敗は例外を握りつぶし、本体処理に影響させない
