from django.db import models

class Article(models.Model):
    post_id = models.CharField(max_length=10, null=True)
    post_title = models.CharField(max_length=250)
    url = models.CharField(max_length=200)
    score = models.IntegerField(null=True)
    publisher = models.CharField(max_length=50, null=True)
    headline = models.CharField(max_length=250)
    date_published = models.DateTimeField(null=True)
    content = models.CharField(max_length=65000)
