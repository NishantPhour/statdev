# Generated by Django 3.2.16 on 2025-02-13 09:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('action', models.CharField(max_length=512)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user', models.IntegerField(blank=True, null=True)),
                ('category', models.IntegerField(blank=True, choices=[(1, 'Communicate'), (2, 'Assign'), (3, 'Refer'), (4, 'Issue'), (5, 'Decline'), (6, 'Publish'), (7, 'Lodge'), (8, 'Next Step'), (9, 'Change'), (10, 'Create'), (11, 'Cancelled')], null=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
    ]
