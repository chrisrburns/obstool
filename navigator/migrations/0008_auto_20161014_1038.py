# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-10-14 17:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('navigator', '0007_object_comments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='object',
            name='comments',
            field=models.TextField(max_length=1000),
        ),
    ]
