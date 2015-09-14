# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('navigator', '0002_auto_20150911_1619'),
    ]

    operations = [
        migrations.AlterField(
            model_name='object',
            name='Mv',
            field=models.CharField(max_length=10),
        ),
    ]
