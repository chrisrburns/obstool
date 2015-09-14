# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Object',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('descr', models.CharField(max_length=200)),
                ('RA', models.FloatField()),
                ('DEC', models.FloatField()),
                ('size', models.FloatField()),
                ('Mv', models.FloatField()),
                ('distance', models.FloatField()),
                ('rating', models.IntegerField()),
                ('dark', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='Type',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=10)),
                ('descr', models.CharField(max_length=200)),
            ],
        ),
        migrations.AddField(
            model_name='object',
            name='type',
            field=models.ForeignKey(to='navigator.Type'),
        ),
    ]
