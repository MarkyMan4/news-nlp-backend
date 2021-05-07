from rest_framework import serializers
from .models import Article

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('post_title', 'url', 'publisher', 'headline', 'date_published', 'content')
