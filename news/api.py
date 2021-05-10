from rest_framework import generics, permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .serializers import ArticleSerializer, ArticleNlpSerializer
from .models import Article, ArticleNlp


class ArticleViewSet(viewsets.ViewSet):
    def list(self, request):
        article_queryset = Article.objects.all()

        query_params = request.query_params

        # any filtering will be provided as query parameters
        # TODO: figure out how to filter by topic, sentiment and subjectivity since this comes form article_nlp
        if query_params.get('publisher'):
            article_queryset = article_queryset.filter(publisher=query_params.get('publisher'))

        # getting a warning here that these are naive datetimes, look into django.utils.datetime
        if query_params.get('startDate'):
            article_queryset = article_queryset.filter(date_published__gte=query_params.get('startDate'))

        if query_params.get('endDate'):
            article_queryset = article_queryset.filter(date_published__lte=query_params.get('endDate'))


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

    def retrieve(self, request, pk=None):
        if request.query_params:
            print(request.query_params)
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


