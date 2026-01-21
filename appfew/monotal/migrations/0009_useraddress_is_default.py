# Generated manually
from django.db import migrations, models


def set_first_address_as_default(apps, schema_editor):
    """既存データの最初の住所をデフォルトに設定"""
    UserAddress = apps.get_model('monotal', 'UserAddress')

    # ユーザーごとにグループ化して最初の住所をデフォルトに設定
    processed_users = set()
    for address in UserAddress.objects.all().order_by('user_id', 'register_datetime'):
        if address.user_id not in processed_users:
            address.is_default = True
            address.save()
            processed_users.add(address.user_id)


def reverse_set_default(apps, schema_editor):
    """逆マイグレーション: デフォルトを解除"""
    UserAddress = apps.get_model('monotal', 'UserAddress')
    UserAddress.objects.all().update(is_default=False)


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0008_populate_shipping_days'),
        ('monotal', '0003_add_shipping_burden'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraddress',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_first_address_as_default, reverse_set_default),
    ]
