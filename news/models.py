from django.db import models

class Article(models.Model):
    post_id = models.CharField(max_length=10, null=True)
    post_title = models.CharField(max_length=400)
    url = models.CharField(max_length=350)
    score = models.IntegerField(null=True)
    publisher = models.CharField(max_length=50, null=True)
    headline = models.CharField(max_length=400)
    date_published = models.DateTimeField(null=True)
    content = models.CharField(max_length=65000)
