from django.db import migrations


def update_rental_status(apps, schema_editor):
    """
    RentalStatusを6段階の往復発送フローに対応させる

    【変更前】
    1: 予約中
    2: 貸出中
    3: 返却済み
    4: キャンセル

    【変更後】
    1: 発送準備中
    2: 配送中
    3: レンタル中
    4: 返送中
    5: 返却済み
    6: キャンセル

    【データ移行】
    既存データの互換性を保つため:
    - 既存の rental_status_id=2（貸出中）→ 3（レンタル中）に移行
    - 既存の rental_status_id=3（返却済み）→ 5（返却済み）に移行
    - 既存の rental_status_id=4（キャンセル）→ 6（キャンセル）に移行
    """
    RentalStatus = apps.get_model('monotal', 'RentalStatus')
    RentalHistory = apps.get_model('monotal', 'RentalHistory')

    # Step 1: 新しいステータスを追加（5, 6）
    RentalStatus.objects.get_or_create(
        rental_status_id=5,
        defaults={'status_name': '返却済み_temp'}
    )
    RentalStatus.objects.get_or_create(
        rental_status_id=6,
        defaults={'status_name': 'キャンセル_temp'}
    )

    # Step 2: 既存のRentalHistoryデータを移行
    # 4（キャンセル）→ 6
    RentalHistory.objects.filter(rental_status_id=4).update(rental_status_id=6)
    # 3（返却済み）→ 5
    RentalHistory.objects.filter(rental_status_id=3).update(rental_status_id=5)
    # 2（貸出中）→ 3（レンタル中）
    RentalHistory.objects.filter(rental_status_id=2).update(rental_status_id=3)

    # Step 3: ステータス名を更新
    RentalStatus.objects.filter(rental_status_id=1).update(status_name='発送準備中')
    RentalStatus.objects.filter(rental_status_id=2).update(status_name='配送中')
    RentalStatus.objects.filter(rental_status_id=3).update(status_name='レンタル中')
    RentalStatus.objects.filter(rental_status_id=4).update(status_name='返送中')
    RentalStatus.objects.filter(rental_status_id=5).update(status_name='返却済み')
    RentalStatus.objects.filter(rental_status_id=6).update(status_name='キャンセル')


def reverse_rental_status(apps, schema_editor):
    """
    ロールバック: 元の4段階に戻す
    """
    RentalStatus = apps.get_model('monotal', 'RentalStatus')
    RentalHistory = apps.get_model('monotal', 'RentalHistory')

    # データを元に戻す
    RentalHistory.objects.filter(rental_status_id=3).update(rental_status_id=2)
    RentalHistory.objects.filter(rental_status_id=5).update(rental_status_id=3)
    RentalHistory.objects.filter(rental_status_id=6).update(rental_status_id=4)

    # ステータス名を元に戻す
    RentalStatus.objects.filter(rental_status_id=1).update(status_name='予約中')
    RentalStatus.objects.filter(rental_status_id=2).update(status_name='貸出中')
    RentalStatus.objects.filter(rental_status_id=3).update(status_name='返却済み')
    RentalStatus.objects.filter(rental_status_id=4).update(status_name='キャンセル')

    # 追加したステータスを削除
    RentalStatus.objects.filter(rental_status_id__in=[5, 6]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0020_add_shipping_prefecture_to_product'),
    ]

    operations = [
        migrations.RunPython(update_rental_status, reverse_rental_status),
    ]
