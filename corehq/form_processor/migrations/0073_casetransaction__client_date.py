# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-07-25 16:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('form_processor', '0072_case_attachment_drops'),
    ]

    operations = [
        migrations.AddField(
            model_name='casetransaction',
            name='_client_date',
            field=models.DateTimeField(db_column='client_date', null=True),
        ),
    ]
