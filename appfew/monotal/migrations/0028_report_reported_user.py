from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0027_add_return_statuses'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='reported_user',
            field=models.ForeignKey(
                db_column='reported_user_id',
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='reports_received',
                to='monotal.user',
            ),
            preserve_default=False,
        ),
    ]
