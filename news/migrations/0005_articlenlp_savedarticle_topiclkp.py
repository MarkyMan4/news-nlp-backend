# Generated by Django 3.1.5 on 2021-03-30 03:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('news', '0004_auto_20210322_0218'),
    ]

    operations = [
        migrations.CreateModel(
            name='TopicLkp',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic_name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='SavedArticle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='news.article')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ArticleNlp',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sentiment', models.DecimalField(decimal_places=3, max_digits=4)),
                ('subjectivity', models.DecimalField(decimal_places=3, max_digits=4)),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='news.article')),
                ('topic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='news.topiclkp')),
            ],
        ),
    ]
