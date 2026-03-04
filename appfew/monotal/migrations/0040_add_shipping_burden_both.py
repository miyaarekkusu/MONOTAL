from django.db import migrations


def add_both_burden(apps, schema_editor):
    ShippingBurden = apps.get_model('monotal', 'ShippingBurden')
    ShippingBurden.objects.get_or_create(
        shipping_burden_id=3,
        defaults={'burden_name': '両者負担'}
    )


def reverse_add_both_burden(apps, schema_editor):
    ShippingBurden = apps.get_model('monotal', 'ShippingBurden')
    ShippingBurden.objects.filter(shipping_burden_id=3).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0039_merge_0034_message_reply_to_0038_quest_expires_at'),
    ]

    operations = [
        migrations.RunPython(add_both_burden, reverse_add_both_burden),
    ]
