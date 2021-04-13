from django.db import models
from django.contrib.auth.models import User

class Article(models.Model):
    post_id = models.CharField(max_length=10, null=True)
    post_title = models.CharField(max_length=400)
    url = models.CharField(max_length=500)
    score = models.IntegerField(null=True)
    publisher = models.CharField(max_length=50, null=True)
    headline = models.CharField(max_length=400)
    date_published = models.DateTimeField(null=True)
    content = models.CharField(max_length=65000)

class SavedArticle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)

class TopicLkp(models.Model):
    topic_id = models.IntegerField(unique=True)
    topic_name = models.CharField(max_length=50)

class ArticleNlp(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    topic = models.ForeignKey(TopicLkp, to_field='topic_id', db_column='topic', on_delete=models.CASCADE)
    sentiment = models.DecimalField(max_digits=4, decimal_places=3)
    subjectivity = models.DecimalField(max_digits=4, decimal_places=3)
