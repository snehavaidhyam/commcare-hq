# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-23 21:12
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0037_merge_20180807_0915'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='billingaccount',
            name='restrict_signup_email',
        ),
    ]
