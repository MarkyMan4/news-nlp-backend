from datetime import time
from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import ArticleSerializer, SavedArticleSerializer
from .models import Article, ArticleNlp, SavedArticle
from .utils import get_article_nlp, get_counts_by_topic, get_counts_by_sentiment, get_subjectivity_by_sentiment, get_counts_by_date_per_topic


# ModelViewSet includes methods to get objects, create, edit and delete by default.
# Need to refine this so users can only delete their own saved articles. Also need
# to only allow get, post and delete.
class SavedArticleViewset(viewsets.ModelViewSet):
    serializer_class = SavedArticleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SavedArticle.objects.all()
    http_method_names = ['get', 'post', 'delete'] # ModelViewSet includes many methods out of the box, so this limits them to only what is needed

    # list all articles saved by the current user
    def list(self, request):
        # query the saved articles for this user
        user_saved_articles = self.queryset.filter(user=request.user)
        article_ids = [saved_article.article_id for saved_article in user_saved_articles]
        articles = Article.objects.filter(id__in=article_ids)
        
        # serialize the result
        article_serializer = ArticleSerializer(articles, many=True)
        response_data = article_serializer.data

        # add the NLP data to the response object
        # this is duplicate code from ArticleViewSet, need to refactor this file to make this stuff more reusable
        for article in response_data:
            nlp_queryset = ArticleNlp.objects.filter(article_id=article['id'])
            article_nlp = nlp_queryset.first()
            article['nlp'] = get_article_nlp(article_nlp)
        
        return Response(response_data)

    # save an article
    # TODO: don't allow a user to save the same article more than once
    def create(self, request, *args, **kwargs):
        data = request.data
        data['user'] = request.user.id # add the user id to the data to be saved

        # don't save the article if it is already saved by this user
        saved_art = self.queryset.filter(user__id=request.data['user'], article__id=request.data['article'])

        if saved_art.count() > 0:
            return Response({'error': 'This article is already saved'})

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # can add custom functionality when saving here if needed
    def perform_create(self, serializer):
        serializer.save()

    # only allow users to delete their own saved articles
    # the pk should be an article ID, this method will then lookup the user ID
    # since the user should not be allowed to save the same article more than once,
    # this is guaranteed to be a unique combination
    def destroy(self, request, pk):
        article_to_delete = SavedArticle.objects.filter(user=request.user.id, article=pk)
        response = {'result': 'you do not have permission to delete this saved article'}

        if(article_to_delete.first().user_id == request.user.id):
            article_to_delete.delete()
            response = {'result': 'saved article deleted'}

        return Response(response)

    # GET /api/savearticle/<article id>/is_saved
    # check if a given article is saved by the user
    @action(methods=['GET'], detail=True)
    def is_saved(self, request, pk):
        res = {'result': False}
        user_id = request.user.id
        
        try:
            user_articles = SavedArticle.objects.filter(user_id=user_id, article_id=pk)

            if len(user_articles) > 0:
                res['result'] = True
        except Exception as e:
            print(e)

        return Response(res)

    def get_saved_articles(self, user):
        # get saved articles for the current user
        user_saved_articles = self.queryset.filter(user=user)
        article_ids = [saved_article.article_id for saved_article in user_saved_articles]
        articles = Article.objects.filter(id__in=article_ids)

        return articles

    # POST /api/savearticle/clear_saved_articles
    # deletes all saved articles for the user
    @action(methods=['POST'], detail=False)
    def clear_saved_articles(self, request):
        response = {'result': 'all saved articles deleted'}

        try:
            self.queryset.filter(user=request.user).delete()
        except:
            response = {'error': 'failed to clear saved articles'}

        return Response(response)

    # GET /api/savearticle/count_by_topic
    # 
    # Optional query params:
    #   timeFrame - can having the following values [day, week, month, year]
    #              this specifies whether the count should be for articles from the past day, week, etc.
    #
    # If not query param specified, it will count all the articles.
    # 
    # retrieve the count of articles for each topic
    @action(methods=['GET'], detail=False)
    def count_by_topic(self, request):
        articles = self.get_saved_articles(request.user)

        # Retrieve the query param. if nothing was provided, this will be None
        query_params = request.query_params
        timeframe = query_params.get('timeFrame')
        topic = query_params.get('topic')

        counts = get_counts_by_topic(articles, timeframe, topic)

        return Response(counts)

    # /api/savearticle/count_by_sentiment
    # gets the article count for each sentiment
    # breakdown as follows:
    #   -1.0 <= sentiment < -0.05   -- negative
    #   -0.05 <= sentiment <= 0.05   -- neutral
    #   0.05 < sentiment <= 1.0     -- positive
    # Optional query params:
    #   timeFrame - can having the following values [day, week, month, year]
    #              this specifies whether the count should be for articles from the past day, week, etc.
    #
    # If not query param specified, it will count all the articles.
    @action(methods=['GET'], detail=False)
    def count_by_sentiment(self, request):
        articles = self.get_saved_articles(request.user)

        # Retrieve the query param. if nothing was provided, this will be None
        query_params = request.query_params
        timeframe = query_params.get('timeFrame')
        topic = query_params.get('topic')

        counts = get_counts_by_sentiment(articles, timeframe, topic)

        return Response(counts)

    # /api/savearticle/subjectivity_by_sentiment
    # Retrieves the sentiment and subjectivity for all articles
    # The reponse of this method is useful for creating viualizations.
    # It returns a list in this format: 
    # [
    #   {x: <sentiment1>, y: <subjectivity>},
    #   ...
    # ]
    # Optional query params:
    #   timeFrame - can having the following values [day, week, month, year]
    #              this specifies whether the count should be for articles from the past day, week, etc.
    # TODO: allow this to be filtered by topic
    @action(methods=['GET'], detail=False)
    def subjectivity_by_sentiment(self, request):
        articles = self.get_saved_articles(request.user)

        # Retrieve the query param. if nothing was provided, this will be None
        query_params = request.query_params
        timeframe = query_params.get('timeFrame')
        topic = query_params.get('topic')

        values = get_subjectivity_by_sentiment(articles, timeframe, topic)

        return Response(values)

    # /api/savearticle/count_by_topic_date
    # gets article count by date for each topic
    # 
    # response looks like this:
    # {
    #   "<topic name 1>": {
    #       {"date": <date>, "count": <count>},
    #       ...
    #   }
    #   "<topic name 2>": {
    #       ...
    #   }
    #   ...
    # }
    @action(methods=['GET'], detail=False)
    def count_by_topic_date(self, request):
        user_id =  request.user.id
        query_params = request.query_params
        timeframe = query_params.get('timeFrame')
        topic = query_params.get('topic')

        counts_by_date = get_counts_by_date_per_topic(timeframe, topic, user_id)

        return Response(counts_by_date)
