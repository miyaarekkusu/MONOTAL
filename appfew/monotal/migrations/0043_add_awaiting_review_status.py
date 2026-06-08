from django.db import migrations


def add_awaiting_review_status(apps, schema_editor):
    """
    RentalStatusに評価待ちステータスを追加

    12: 評価待ち（貸主が返却を受取完了後、相互評価が揃うまでの中間状態）
    """
    RentalStatus = apps.get_model('monotal', 'RentalStatus')
    RentalStatus.objects.get_or_create(
        rental_status_id=12,
        defaults={'status_name': '評価待ち'}
    )


def reverse_awaiting_review_status(apps, schema_editor):
    RentalStatus = apps.get_model('monotal', 'RentalStatus')
    RentalStatus.objects.filter(rental_status_id=12).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0042_make_product_condition_nullable'),
    ]

    operations = [
        migrations.RunPython(add_awaiting_review_status, reverse_awaiting_review_status),
    ]
