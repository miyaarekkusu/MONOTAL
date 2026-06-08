# デプロイ手順（MONOTAL - Azure App Service）

## 基本情報

| 項目 | 値 |
|------|-----|
| サイト | `monotal-aaf4czf9dpczazey.japaneast-01.azurewebsites.net` |
| リソースグループ | `HAL` |
| ランタイム | Python 3.13 (Linux) |
| スタートアップコマンド | `bash /home/startup.sh` |
| DB | `/home/data/db.sqlite3`（永続ストレージ、デプロイに含めない） |

## zip構造（重要）

`appfew/` の **中身** をzipルート直下に配置する。`appfew/` をトップディレクトリにしない。

```
deploy.zip
├── manage.py
├── appfew/          ← Djangoアプリ
├── monotal/         ← Django設定
├── statics/
├── templates/
├── requirements.txt
└── ...
```

### 除外対象

- `db.sqlite3`
- `media/`
- `user_images/`
- `__pycache__/`
- `deploy.zip`（既存のzipファイル）

## デプロイコマンド

### 1. zip作成

```bash
cd /c/Users/kohta/source/repos/miyaarekkusu/HEWSakuhin

# 作業ディレクトリ作成
rm -rf /tmp/deploy_flat && mkdir -p /tmp/deploy_flat
cp -r appfew/* /tmp/deploy_flat/
rm -f /tmp/deploy_flat/deploy.zip /tmp/deploy_flat/db.sqlite3

# zip作成（除外対象を指定）
rm -f /tmp/deploy.zip
cd /tmp/deploy_flat
"/c/Program Files/7-Zip/7z.exe" a -tzip /tmp/deploy.zip . -xr!__pycache__ -xr!media -xr!user_images
```

### 2. Kudu Zip Deploy API

```bash
curl -X POST \
  -u '$monotal:SzfSZbyhtZyHWsKqHkxxyJWujshH2WLbijRoixegkfANEHpZDq4G86b2upjc' \
  --data-binary @/tmp/deploy.zip \
  -H "Content-Type: application/zip" \
  "https://monotal-aaf4czf9dpczazey.scm.japaneast-01.azurewebsites.net/api/zipdeploy"
```

### 3. App Service再起動

```bash
cmd.exe /c "az webapp restart --name monotal-aaf4czf9dpczazey --resource-group HAL"
```

## 注意事項

- Oryxビルド（`SCM_DO_BUILD_DURING_DEPLOYMENT=true`）はそのまま維持する（pip install等が必要）
- `/home/startup.sh` はデプロイとは別に管理する（変更はKudu VFS APIか直接編集）
- DB（`/home/data/db.sqlite3`）は永続ストレージに配置されており、デプロイで上書きされない
