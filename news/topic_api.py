from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import TopicSerializer
from .models import Article, TopicLkp
from .utils import filter_articles_by_timeframe


class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    queryset = TopicLkp.objects.all()
    http_method_names = ['get']

    # GET /api/topics
    # list all topics
    def list(self, request):
        topics = self.queryset
        serializer = self.get_serializer(topics, many=True)
        return Response(serializer.data)

    # GET /api/topics/counts
    # 
    # Optional query params:
    #   timeFrame - can having the following values [day, week, month, year]
    #              this specifies whether the count should be for articles from the past day, week, etc.
    #
    # If not query param specified, it will count all the articles.
    # 
    # retrieve the count of articles for each topic
    @action(methods=['GET'], detail=False)
    def counts(self, request):
        articles = Article.objects.all()
        query_params = request.query_params

        # check if a time frame was given, if it doesn't match day, week, month or year it won't filter anything
        if query_params.get('timeFrame'):
            articles = filter_articles_by_timeframe(articles, query_params.get('timeFrame'))

        response = {}
        topics = self.queryset

        for topic in topics:
            article_count = articles.filter(articlenlp__topic=topic.topic_id).count()
            response.update({
                topic.topic_name: article_count
            })

        return Response(response)