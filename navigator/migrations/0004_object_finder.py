# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('navigator', '0003_auto_20150911_2122'),
    ]

    operations = [
        migrations.AddField(
            model_name='object',
            name='finder',
            field=models.ImageField(default=b'default.gif', upload_to=b'finders'),
        ),
    ]
