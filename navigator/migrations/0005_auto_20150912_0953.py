# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('navigator', '0004_object_finder'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Type',
            new_name='ObjType',
        ),
        migrations.RenameField(
            model_name='object',
            old_name='type',
            new_name='objtype',
        ),
    ]
