from django.db import migrations


def add_return_statuses(apps, schema_editor):
    """
    RentalStatusに返品フロー用ステータスを追加

    7: 返品申請中
    8: 返品承認済み
    9: 返品返送中
    """
    RentalStatus = apps.get_model('monotal', 'RentalStatus')

    RentalStatus.objects.get_or_create(
        rental_status_id=7,
        defaults={'status_name': '返品申請中'}
    )
    RentalStatus.objects.get_or_create(
        rental_status_id=8,
        defaults={'status_name': '返品承認済み'}
    )
    RentalStatus.objects.get_or_create(
        rental_status_id=9,
        defaults={'status_name': '返品返送中'}
    )


def reverse_return_statuses(apps, schema_editor):
    """ロールバック: 返品ステータスを削除"""
    RentalStatus = apps.get_model('monotal', 'RentalStatus')
    RentalStatus.objects.filter(rental_status_id__in=[7, 8, 9]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0026_rentalhistory_overdue_notified_datetime_and_more'),
    ]

    operations = [
        migrations.RunPython(add_return_statuses, reverse_return_statuses),
    ]
