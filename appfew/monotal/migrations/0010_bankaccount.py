from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0009_useraddress_is_default'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankAccount',
            fields=[
                ('bank_account_id', models.AutoField(primary_key=True, serialize=False)),
                ('bank_name', models.CharField(max_length=100)),
                ('branch_name', models.CharField(max_length=100)),
                ('account_type', models.IntegerField(choices=[(1, '普通'), (2, '当座')], default=1)),
                ('account_number', models.CharField(max_length=20)),
                ('account_holder', models.CharField(max_length=100)),
                ('is_default', models.BooleanField(default=False)),
                ('register_datetime', models.DateTimeField(auto_now_add=True)),
                ('update_datetime', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(db_column='user_id', on_delete=django.db.models.deletion.CASCADE, related_name='bank_accounts', to='monotal.user')),
            ],
            options={
                'verbose_name': '銀行口座',
                'verbose_name_plural': '銀行口座',
                'db_table': 'T_BankAccount',
            },
        ),
    ]
