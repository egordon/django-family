# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-15 22:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('family', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='person',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='family.Person'),
        ),
    ]
