from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.contrib.staticfiles.storage import staticfiles_storage
from django.shortcuts import get_object_or_404
from .serializers import ArticleSerializer
from .models import Article, ArticleNlp, TopicLkp
from .utils import get_article_nlp, get_counts_by_sentiment, get_subjectivity_by_sentiment, get_counts_by_date_per_topic
from backend import settings
import os

from gensim.models.doc2vec import Doc2Vec
import nltk
from nltk.corpus import stopwords
import pickle
import string


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
    #  11. headlineLike - return articles with a headline like this (case insensitive)
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

        if query_params.get('headlineLike'):
            article_queryset = article_queryset.filter(headline__icontains=query_params.get('headlineLike'))

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
        with open(os.path.join(settings.STATIC_ROOT, 'tag_lookup.pickle'), 'rb') as f:
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
        model = Doc2Vec.load(os.path.join(settings.STATIC_ROOT, 'headline_model'))

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
        articles = Article.objects.all()
        query_params = request.query_params
        timeframe = query_params.get('timeFrame')
        topic = query_params.get('topic')
        counts = get_counts_by_sentiment(articles, timeframe, topic)

        return Response(counts)

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
        articles = Article.objects.all()
        query_params = request.query_params
        timeframe = query_params.get('timeFrame')
        topic = query_params.get('topic')
        values = get_subjectivity_by_sentiment(articles, timeframe, topic)

        return Response(values)

    # /api/article/count_by_topic_date
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
        query_params = request.query_params
        timeframe = query_params.get('timeFrame')
        topic = query_params.get('topic')
        counts_by_date = get_counts_by_date_per_topic(timeframe, topic)

        return Response(counts_by_date)



