# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('navigator', '0006_auto_20150912_1018'),
    ]

    operations = [
        migrations.AddField(
            model_name='object',
            name='comments',
            field=models.TextField(default='None', max_length=100),
            preserve_default=False,
        ),
    ]
