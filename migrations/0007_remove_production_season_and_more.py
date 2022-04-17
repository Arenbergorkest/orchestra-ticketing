# Generated by Django 4.0.2 on 2022-04-04 18:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra_ticketing', '0006_alter_onlineorder_payment_method'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='production',
            name='season',
        ),
        migrations.AlterField(
            model_name='onlineorder',
            name='first_concert',
            field=models.BooleanField(choices=[(None, '- Choose -'), (True, 'Yes'), (False, 'No')], null=True),
        ),
        migrations.DeleteModel(
            name='Season',
        ),
    ]