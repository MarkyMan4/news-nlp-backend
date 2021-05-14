from django.db.models import query
from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .serializers import ArticleSerializer, ArticleNlpSerializer, SavedArticleSerializer
from .models import Article, ArticleNlp, SavedArticle


class ArticleViewSet(viewsets.ViewSet):

    # /api/article<optional query params>
    # gets multiple articles along with some filtering
    # optional query params:
    #   1. publisher - specify publisher of articles
    #   2. startDate - only returns articles that were published on or after this date
    #   3. endDate - only returns articles that were published on or before this date
    #       - note dates should be given in the format yyyy-mm-dd
    #   4. topic - only return articles with specified topic
    #   5. minSentiment - only return articles with sentiment greater than or equal to this value
    #   6. maxSentiment - only return articles with sentiment less than or equal to this value
    #   7. minSubjectivity - only return articles with subjectivity greater than or equal to this value
    #   8. maxSubjectivity - only return articles with subjectivity less than or equal to this value
    def list(self, request):
        article_queryset = Article.objects.all()

        query_params = request.query_params

        # any filtering will be provided as query parameters
        article_queryset = self.filter_articles(article_queryset, query_params)

        article_serializer = ArticleSerializer(article_queryset, many=True)
        response_data = article_serializer.data

        # this seems ineffecient - has to do N queries where N is the number of articles 
        # in the database. Need to find a better way to do this. Ideally have one query
        # for articles and one for NLP, then find a way to combine them. Or one query that 
        # joins article with article_nlp and construct the response myself without serializers
        for article in response_data:
            nlp_queryset = ArticleNlp.objects.filter(article_id=article['id'])
            nlp_serializer = ArticleNlpSerializer(nlp_queryset.first())
            article['nlp'] = nlp_serializer.data

        return Response(response_data)

    # applies filtering to articles based on query params provided
    def filter_articles(self, article_queryset, query_params):
        if query_params.get('publisher'):
            article_queryset = article_queryset.filter(publisher=query_params.get('publisher'))

        # getting a warning here that these are naive datetimes, look into django.utils.datetime
        if query_params.get('startDate'):
            article_queryset = article_queryset.filter(date_published__gte=query_params.get('startDate'))

        if query_params.get('endDate'):
            article_queryset = article_queryset.filter(date_published__lte=query_params.get('endDate'))

        if query_params.get('topic'):
            article_queryset = article_queryset.filter(articlenlp__topic=query_params.get('topic'))

        if query_params.get('minSentiment'):
            article_queryset = article_queryset.filter(articlenlp__sentiment__gte=query_params.get('minSentiment'))

        if query_params.get('maxSentiment'):
            article_queryset = article_queryset.filter(articlenlp__sentiment__lte=query_params.get('maxSentiment'))

        if query_params.get('minSubjectivity'):
            article_queryset = article_queryset.filter(articlenlp__subjectivity__gte=query_params.get('minSubjectivity'))

        if query_params.get('maxSubjectivity'):
            article_queryset = article_queryset.filter(articlenlp__subjectivity__lte=query_params.get('maxSubjectivity'))

        return article_queryset

    # /api/article/<article id>
    # gets a specific news article
    def retrieve(self, request, pk=None):
        # queries for article and NLP
        article_queryset = Article.objects.filter(pk=pk)
        nlp_queryset = ArticleNlp.objects.filter(article_id=pk)

        # get objects for 404 from each queryset
        article = get_object_or_404(article_queryset)
        nlp = get_object_or_404(nlp_queryset)

        # create the serializers for each object
        article_serializer = ArticleSerializer(article)
        nlp_serializer = ArticleNlpSerializer(nlp)

        # construct the response with the NLP as a nested object
        response_data = article_serializer.data
        response_data['nlp'] = nlp_serializer.data
        
        return Response(response_data)

# ModelViewSet includes methods to get objects, create, edit and delete by default.
# Need to refine this so users can only delete their own saved articles. Also need
# to only allow get, post and delete. For get, users should only be able to retrieve 
# their own saved articles.
class SavedArticleViewset(viewsets.ModelViewSet):
    serializer_class = SavedArticleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SavedArticle.objects.all()

