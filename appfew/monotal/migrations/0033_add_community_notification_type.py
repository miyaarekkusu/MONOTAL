from django.db import migrations


def add_community_notification_type(apps, schema_editor):
    NotificationType = apps.get_model('monotal', 'NotificationType')
    NotificationType.objects.get_or_create(
        notification_type_id=4,
        defaults={'notification_type_name': 'コミュニティ通知'},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0032_qa_models'),
    ]

    operations = [
        migrations.RunPython(add_community_notification_type, migrations.RunPython.noop),
    ]
