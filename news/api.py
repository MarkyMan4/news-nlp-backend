from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import ArticleSerializer, ArticleNlpSerializer
from .models import Article, ArticleNlp


class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer

    def get_queryset(self):
        article_id = self.request.query_params.get('id')
        return Article.objects.filter(pk=article_id)

class ArticleNlpViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleNlpSerializer

    def get_queryset(self):
        article_id = self.request.query_params.get('id')
        return ArticleNlp.objects.filter(article_id=article_id)
