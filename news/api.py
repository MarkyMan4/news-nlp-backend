from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework import pagination
from rest_framework import response
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .serializers import ArticleSerializer, ArticleNlpSerializer, SavedArticleSerializer, TopicSerializer
from .models import Article, ArticleNlp, SavedArticle, TopicLkp

from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import nltk
from nltk.corpus import stopwords
import pickle
import string
from datetime import datetime, timedelta

# TODO: move this to a separate file with other utility functions
def get_article_nlp(article_nlp):
    nlp_serializer = ArticleNlpSerializer(article_nlp)
    nlp = nlp_serializer.data
    nlp['topic_name'] = article_nlp.topic.topic_name

    return nlp

# given a time frame of day, week, month or year, return the date that corresponds with that time frame
def get_filter_date(timeframe):
    filter_date = datetime(1970, 1, 1) # default to this so if a valid value wasn't given for timeFrame, it won't filter anything

    if timeframe == 'day':
        filter_date = datetime.now() - timedelta(days = 1)
    elif timeframe == 'week':
        filter_date = datetime.now() - timedelta(days = 7)
    elif timeframe == 'month':
        filter_date = datetime.now() - timedelta(days = 30)
    elif timeframe == 'year':
        filter_date = datetime.now() - timedelta(days = 365)

    return filter_date

# Applies date filtering to an ArticleNlp queryset.
# Timeframe should be day, week, month or year. If it is any other value,
# no filtering will be applied
def filter_article_nlp_by_timeframe(article_nlp, timeframe):
    filter_date = get_filter_date(timeframe)
    
    return article_nlp.filter(article__date_published__gte=filter_date)

# same thing as filter_article_nlp_by_timeframe, but for an Article queryset
def filter_articles_by_timeframe(articles, timeframe):
    filter_date = get_filter_date(timeframe)
    
    return articles.filter(date_published__gte=filter_date)

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
    #   9. topicName - only return articles with this topic
    #  10. order - Must be 'new' or 'old'. This determines if the results will be ordered from
    #              newest to oldest or oldest to newest. Default from newest to oldest.
    def list(self, request):
        article_queryset = Article.objects.all().order_by('-date_published')

        query_params = request.query_params

        # any filtering will be provided as query parameters
        article_queryset = self.filter_articles(article_queryset, query_params)

        # apply pagination
        data_for_serializer = article_queryset
        total_pages = 1
        page_no = 1

        if 'page' in query_params:
            paginator = PageNumberPagination()
            data_for_serializer = paginator.paginate_queryset(article_queryset, request)
            total_pages = paginator.page.paginator.num_pages
            page_no = paginator.page.number
            
        
        article_serializer = ArticleSerializer(data_for_serializer, many=True)
        
        response_data = article_serializer.data

        # this seems ineffecient - has to do N queries where N is the number of articles 
        # in the database. Need to find a better way to do this. Ideally have one query
        # for articles and one for NLP, then find a way to combine them. Or one query that 
        # joins article with article_nlp and construct the response myself without serializers
        for article in response_data:
            nlp_queryset = ArticleNlp.objects.filter(article_id=article['id'])
            article_nlp = nlp_queryset.first()
            article['nlp'] = get_article_nlp(article_nlp)

        # need to do this check again so the final repsonse can be formatted
        if 'page' in query_params:
            response_data = {
                'page': page_no,
                'total_pages': total_pages,
                'articles': response_data
            }

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

        # will only filter on topic or topic_name, not both. If both are supplied, it will only filter on topic
        if query_params.get('topicName') and not query_params.get('topic'):
            topic = TopicLkp.objects.filter(topic_name=query_params.get('topicName')).first()
            
            # if an invalid topic name was given, don't do any filtering
            if topic:
                article_queryset = article_queryset.filter(articlenlp__topic=topic.topic_id)

        if query_params.get('minSentiment'):
            article_queryset = article_queryset.filter(articlenlp__sentiment__gte=query_params.get('minSentiment'))

        if query_params.get('maxSentiment'):
            article_queryset = article_queryset.filter(articlenlp__sentiment__lte=query_params.get('maxSentiment'))

        if query_params.get('minSubjectivity'):
            article_queryset = article_queryset.filter(articlenlp__subjectivity__gte=query_params.get('minSubjectivity'))

        if query_params.get('maxSubjectivity'):
            article_queryset = article_queryset.filter(articlenlp__subjectivity__lte=query_params.get('maxSubjectivity'))

        if query_params.get('order'):
            # only need to handle case for sorting oldest to newest since it sorts by newest by default
            if query_params.get('order') == 'old':
                article_queryset = article_queryset.order_by('date_published')

        return article_queryset

    # /api/article/<article id>
    # gets a specific news article
    def retrieve(self, request, pk=None):
        response_data = {}

        # queries for article and NLP
        article_queryset = Article.objects.filter(pk=pk)
        nlp_queryset = ArticleNlp.objects.filter(article_id=pk)

        if article_queryset:
            # get objects for 404 from each queryset
            article = get_object_or_404(article_queryset)
            article_nlp = get_object_or_404(nlp_queryset)

            # create the serializer for article
            article_serializer = ArticleSerializer(article)

            # construct the response with the NLP as a nested object
            response_data = article_serializer.data
            response_data['nlp'] = get_article_nlp(article_nlp)
        else:
            response_data = {
                'error': 'article does not exist'
            }
        
        return Response(response_data)

    # cleans headline text by tokenizing it and removing stopwords and punctuation
    def clean_headline(self, headline: str):
        stop_words = set(stopwords.words('english'))
        return [word for word in nltk.word_tokenize(headline) if word not in stop_words and word not in string.punctuation]

    # given a list of tags, lookup the headline in the tag_lookup object
    def get_headlines_by_tags(self, tags):
        # load the tag lookup
        with open('news/models/tag_lookup.pickle', 'rb') as f:
            tag_lookup = pickle.load(f)

        headlines = []

        for tag in tags:
            headlines.append(tag_lookup[tag])

        return headlines

    # given a list of headlines, find the articles in the database and return a list of Article objects
    def get_articles_by_headlines(self, headlines: list):
        articles = []

        for h in headlines:
            article = Article.objects.filter(headline=h).first()

            # serialize the article and get the NLP for it
            article_data = ArticleSerializer(article).data
            article_nlp = ArticleNlp.objects.filter(article_id=article.id).first()
            article_data['nlp'] = get_article_nlp(article_nlp)

            articles.append(article_data)

        return articles

    # /api/article/<article ID>/get_similar
    # optional query param: numResults - number of articles to return
    @action(methods=['GET'], detail=True)
    def get_similar(self, request, pk):
        # check for query params, number of results defaults to 10
        # have to put 11 here since the first result is the same article, using 11 will give 10 similar articles
        num_results = 11

        if request.query_params.get('numResults') and request.query_params.get('numResults').isnumeric():
            num_results = int(request.query_params.get('numResults')) + 1 # need to add one since the first result is always the same article

        # load the doc2vec model
        model = Doc2Vec.load('news/models/headline_model')

        # retrieve the headline from the database, return error if the pk doesn't exist
        article = Article.objects.filter(pk=pk).first()

        if not article:
            return Response({'error': 'article does not exist'})

        headline = article.headline

        # find the top n most similar articles
        clean_headline = self.clean_headline(headline)
        similar = model.docvecs.most_similar(positive=[model.infer_vector(clean_headline)],topn=num_results)

        # remove the first item since it is the same headline
        similar.pop(0)

        # similar is a list of tuples of the form (tag, % similarity), we only need the tag
        tags = [tag[0] for tag in similar]
        headlines = self.get_headlines_by_tags(tags)

        # get the article objects for response
        similar_articles = self.get_articles_by_headlines(headlines)

        return Response(similar_articles)

    # /api/article/get_article_count
    # optional query param: topic - the ID of the topic to find the count for, defaults to counting all articles
    @action(methods=['GET'], detail=False)
    def get_article_count(self, request):
        articles = Article.objects.all()

        if request.query_params.get('topic'):
            topic_id = request.query_params.get('topic')
            articles = articles.filter(articlenlp__topic=topic_id)

        num_articles = articles.count()

        response = {
            'count': num_articles
        }

        return Response(response)

    # /api/article/count_by_sentiment
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
        article_nlp = ArticleNlp.objects.all()
        query_params = request.query_params

        # check if a time frame was given, if it doesn't match day, week, month or year it won't filter anything
        if query_params.get('timeFrame'):
            article_nlp = filter_article_nlp_by_timeframe(article_nlp, query_params.get('timeFrame'))

        negative_count = article_nlp.filter(sentiment__lt=-0.05).count()
        neutral_count = article_nlp.filter(sentiment__gte=-0.05, sentiment__lte=0.05).count()
        positive_count = article_nlp.filter(sentiment__gt=0.05).count()

        response = {
            'negative': negative_count,
            'neutral': neutral_count,
            'positive': positive_count
        }

        return Response(response)

    # /api/article/subjectivity_by_sentiment
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
        article_nlp = ArticleNlp.objects.all()
        res = []
        query_params = request.query_params

        print(len(article_nlp))

        # check if a time frame was given, if it doesn't match day, week, month or year it won't filter anything
        if query_params.get('timeFrame'):
            article_nlp = filter_article_nlp_by_timeframe(article_nlp, query_params.get('timeFrame'))

        print(len(article_nlp))

        for art in article_nlp:
            res.append(
                {
                    'x': float(art.sentiment),
                    'y': float(art.subjectivity)
                }
            )

        return Response(res)


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
