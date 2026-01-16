from django.db import migrations


def populate_shipping_days(apps, schema_editor):
    """発送日数の初期データを登録"""
    ShippingDays = apps.get_model('monotal', 'ShippingDays')

    shipping_days_data = [
        {'days_label': '1〜2日で発送', 'days_min': 1, 'days_max': 2, 'display_order': 1},
        {'days_label': '2〜3日で発送', 'days_min': 2, 'days_max': 3, 'display_order': 2},
        {'days_label': '4〜7日で発送', 'days_min': 4, 'days_max': 7, 'display_order': 3},
    ]

    for data in shipping_days_data:
        ShippingDays.objects.get_or_create(
            days_label=data['days_label'],
            defaults={
                'days_min': data['days_min'],
                'days_max': data['days_max'],
                'display_order': data['display_order'],
            }
        )


def reverse_populate_shipping_days(apps, schema_editor):
    """発送日数データを削除（ロールバック用）"""
    ShippingDays = apps.get_model('monotal', 'ShippingDays')
    ShippingDays.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0007_shippingdays_product_shipping_days'),
    ]

    operations = [
        migrations.RunPython(populate_shipping_days, reverse_populate_shipping_days),
    ]
