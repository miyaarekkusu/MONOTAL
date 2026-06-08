"""
取引中止機能用モデル追加マイグレーション
- M_CancellationReason (中止理由マスター)
- M_CancellationStatus (中止ステータスマスター)
- T_CancellationRequest (取引中止申請)
- M_RentalStatus に 10=中止申請中 / 11=中止済み を追加
"""

from django.db import migrations, models
import django.db.models.deletion


def insert_initial_data(apps, schema_editor):
    """初期データ投入"""
    CancellationReason = apps.get_model('monotal', 'CancellationReason')
    CancellationStatus = apps.get_model('monotal', 'CancellationStatus')
    RentalStatus = apps.get_model('monotal', 'RentalStatus')

    # 中止理由マスター
    reasons = [
        '商品説明と実物が異なる',
        '商品が届かない',
        '商品が破損していた',
        '相手と連絡が取れない',
        'その他',
    ]
    for name in reasons:
        CancellationReason.objects.get_or_create(reason_name=name)

    # 中止ステータスマスター
    statuses = ['申請中', '承認', '却下']
    for name in statuses:
        CancellationStatus.objects.get_or_create(status_name=name)

    # レンタルステータスに追加
    RentalStatus.objects.get_or_create(rental_status_id=10, defaults={'status_name': '中止申請中'})
    RentalStatus.objects.get_or_create(rental_status_id=11, defaults={'status_name': '中止済み'})


def reverse_initial_data(apps, schema_editor):
    """ロールバック用"""
    CancellationReason = apps.get_model('monotal', 'CancellationReason')
    CancellationStatus = apps.get_model('monotal', 'CancellationStatus')
    RentalStatus = apps.get_model('monotal', 'RentalStatus')

    CancellationReason.objects.all().delete()
    CancellationStatus.objects.all().delete()
    RentalStatus.objects.filter(rental_status_id__in=[10, 11]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0034_useraddress_is_deleted'),
    ]

    operations = [
        # M_CancellationReason
        migrations.CreateModel(
            name='CancellationReason',
            fields=[
                ('cancellation_reason_id', models.AutoField(primary_key=True, serialize=False)),
                ('reason_name', models.CharField(max_length=100, unique=True)),
            ],
            options={
                'verbose_name': '中止理由',
                'verbose_name_plural': '中止理由',
                'db_table': 'M_CancellationReason',
            },
        ),
        # M_CancellationStatus
        migrations.CreateModel(
            name='CancellationStatus',
            fields=[
                ('cancellation_status_id', models.AutoField(primary_key=True, serialize=False)),
                ('status_name', models.CharField(max_length=50, unique=True)),
            ],
            options={
                'verbose_name': '中止ステータス',
                'verbose_name_plural': '中止ステータス',
                'db_table': 'M_CancellationStatus',
            },
        ),
        # T_CancellationRequest
        migrations.CreateModel(
            name='CancellationRequest',
            fields=[
                ('cancellation_request_id', models.AutoField(primary_key=True, serialize=False)),
                ('detail', models.CharField(blank=True, max_length=1000, null=True)),
                ('admin_note', models.CharField(blank=True, max_length=1000, null=True)),
                ('previous_rental_status_id', models.IntegerField()),
                ('request_datetime', models.DateTimeField(auto_now_add=True)),
                ('approval_datetime', models.DateTimeField(blank=True, null=True)),
                ('rejection_datetime', models.DateTimeField(blank=True, null=True)),
                ('register_datetime', models.DateTimeField(auto_now_add=True)),
                ('update_datetime', models.DateTimeField(auto_now=True)),
                ('cancellation_reason', models.ForeignKey(
                    db_column='cancellation_reason_id',
                    on_delete=django.db.models.deletion.PROTECT,
                    to='monotal.cancellationreason',
                )),
                ('cancellation_status', models.ForeignKey(
                    db_column='cancellation_status_id',
                    on_delete=django.db.models.deletion.PROTECT,
                    to='monotal.cancellationstatus',
                )),
                ('rental_history', models.ForeignKey(
                    db_column='rental_history_id',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='cancellation_requests',
                    to='monotal.rentalhistory',
                )),
                ('requester_user', models.ForeignKey(
                    db_column='requester_user_id',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='cancellation_requests',
                    to='monotal.user',
                )),
            ],
            options={
                'verbose_name': '取引中止申請',
                'verbose_name_plural': '取引中止申請',
                'db_table': 'T_CancellationRequest',
            },
        ),
        # 初期データ投入
        migrations.RunPython(insert_initial_data, reverse_initial_data),
    ]
