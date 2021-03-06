from rest_framework import serializers
from .models import Article, ArticleNlp, SavedArticle, TopicLkp

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('id', 'post_title', 'url', 'publisher', 'headline', 'date_published', 'content')

class ArticleNlpSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleNlp
        fields = ('sentiment', 'subjectivity', 'topic', 'keywords')

class SavedArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedArticle
        fields = ('id', 'user', 'article')

class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicLkp
        fields = ('topic_id', 'topic_name')
