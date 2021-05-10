from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import ArticleSerializer, ArticleNlpSerializer
from .models import Article, ArticleNlp


# class ArticleViewSet(viewsets.ModelViewSet):
#     serializer_class = ArticleSerializer

#     def get_queryset(self):
#         article_id = self.request.query_params.get('id')
#         return Article.objects.filter(pk=article_id)

class ArticleViewSet(viewsets.ViewSet):
    def list(self, request):
        article_queryset = Article.objects.all()
        # nlp_queryset = ArticleNlp.objects.all()

        article_serializer = ArticleSerializer(article_queryset, many=True)
        # nlp_serializer = ArticleNlpSerializer(nlp_queryset, many=True)

        response_data = article_serializer.data

        # this seems ineffecient - has to do N queries where N is the number of articles 
        # in the database. Need to find a better way to do this
        for article in response_data:
            nlp_queryset = ArticleNlp.objects.filter(article_id=article['id'])
            nlp_serializer = ArticleNlpSerializer(nlp_queryset.first())
            article['nlp'] = nlp_serializer.data

        return Response(response_data)

    def retrieve(self, request, pk=None):
        # queries for article and NLP
        article_queryset = Article.objects.filter(pk=pk)
        nlp_queryset = ArticleNlp.objects.filter(article_id=pk)

        # create the serializers for each object
        article_serializer = ArticleSerializer(article_queryset.first())
        nlp_serializer = ArticleNlpSerializer(nlp_queryset.first())

        # construct the response with the NLP as a nested object
        response_data = article_serializer.data
        response_data['nlp'] = nlp_serializer.data
        
        return Response(response_data)


