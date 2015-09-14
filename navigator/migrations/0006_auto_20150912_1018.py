# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('navigator', '0005_auto_20150912_0953'),
    ]

    operations = [
        migrations.AlterField(
            model_name='object',
            name='objtype',
            field=models.CharField(max_length=10),
        ),
        migrations.DeleteModel(
            name='ObjType',
        ),
    ]
