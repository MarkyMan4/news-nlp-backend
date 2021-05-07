from rest_framework import serializers
from .models import Article

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('id', 'post_title', 'url', 'publisher', 'headline', 'date_published', 'content')
