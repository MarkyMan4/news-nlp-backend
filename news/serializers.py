from rest_framework import serializers
from .models import Article, ArticleNlp, SavedArticle

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('id', 'post_title', 'url', 'publisher', 'headline', 'date_published', 'content')

class ArticleNlpSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleNlp
        fields = ('sentiment', 'subjectivity', 'topic')

class SavedArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedArticle
        fields = ('user', 'article')
