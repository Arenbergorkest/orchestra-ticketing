# Generated by Django 4.0.4 on 2022-12-05 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orchestra_ticketing', '0010_production_description_en_production_description_nl_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pricecategory',
            name='name_en',
        ),
        migrations.RemoveField(
            model_name='pricecategory',
            name='name_nl',
        ),
        migrations.RemoveField(
            model_name='production',
            name='description_en',
        ),
        migrations.RemoveField(
            model_name='production',
            name='description_nl',
        ),
        migrations.RemoveField(
            model_name='production',
            name='name_en',
        ),
        migrations.RemoveField(
            model_name='production',
            name='name_nl',
        ),
        migrations.AddField(
            model_name='order',
            name='allow_newsletter',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='location',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='onlineorder',
            name='payment_method',
            field=models.CharField(choices=[('transfer', 'By bank transfer'), ('cash', 'At the register (using cash or payconic app)')], default='transfer', max_length=8),
        ),
        migrations.AlterField(
            model_name='order',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='performance',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='poster',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='pricecategory',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='production',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
