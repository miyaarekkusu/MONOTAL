from django.db import migrations


def populate_insurance_claim_status(apps, schema_editor):
    InsuranceClaimStatus = apps.get_model('monotal', 'InsuranceClaimStatus')
    statuses = [
        {'insurance_claim_status_id': 1, 'status_name': '審査中'},
        {'insurance_claim_status_id': 2, 'status_name': '承認'},
        {'insurance_claim_status_id': 3, 'status_name': '却下'},
    ]
    for status in statuses:
        InsuranceClaimStatus.objects.get_or_create(
            insurance_claim_status_id=status['insurance_claim_status_id'],
            defaults={'status_name': status['status_name']}
        )


def reverse_populate(apps, schema_editor):
    InsuranceClaimStatus = apps.get_model('monotal', 'InsuranceClaimStatus')
    InsuranceClaimStatus.objects.filter(insurance_claim_status_id__in=[1, 2, 3]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('monotal', '0040_add_shipping_burden_both'),
    ]

    operations = [
        migrations.RunPython(populate_insurance_claim_status, reverse_populate),
    ]
