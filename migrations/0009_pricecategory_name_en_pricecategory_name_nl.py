# Generated by Django 4.0.3 on 2022-04-12 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra_ticketing', '0008_paperorder_onlineorder_newsletter_signup_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricecategory',
            name='name_en',
            field=models.CharField(max_length=200, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='pricecategory',
            name='name_nl',
            field=models.CharField(max_length=200, null=True, unique=True),
        ),
    ]