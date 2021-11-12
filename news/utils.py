# Helper functions used by various API endpoints
from .serializers import ArticleNlpSerializer
from datetime import datetime, timedelta
from news.models import Article, ArticleNlp, TopicLkp


def get_article_nlp(article_nlp: ArticleNlp):
    nlp_serializer = ArticleNlpSerializer(article_nlp)
    nlp = nlp_serializer.data
    nlp['topic_name'] = article_nlp.topic.topic_name

    return nlp

# given a time frame of day, week, month or year, return the date that corresponds with that time frame
def get_filter_date(timeframe: str):
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
def filter_article_nlp_by_timeframe(article_nlp: ArticleNlp, timeframe: str):
    filter_date = get_filter_date(timeframe)
    
    return article_nlp.filter(article__date_published__gte=filter_date)

# same thing as filter_article_nlp_by_timeframe, but for an Article queryset
def filter_articles_by_timeframe(articles: Article, timeframe: str):
    filter_date = get_filter_date(timeframe)
    
    return articles.filter(date_published__gte=filter_date)

def get_counts_by_topic(articles: Article, timeframe: str = None):
    """
    Get a count of articles for each topic.

    Args:
        articles (Article): Filtered or unfiltered queryset of articles to find the counts for
        timeframe (str): Timeframe to filter articles by.
                         Can having the following values [day, week, month, year]
                         This specifies whether the count should be for articles from the past day, week, etc.

    Returns:
        dict: counts for each topic
    """
    # check if a time frame was given, if it doesn't match day, week, month or year it won't filter anything
    if timeframe:
        articles = filter_articles_by_timeframe(articles, timeframe)

    counts = {}
    topics = TopicLkp.objects.all()

    for topic in topics:
        article_count = articles.filter(articlenlp__topic=topic.topic_id).count()
        counts.update({
            topic.topic_name: article_count
        })

    return counts

def get_counts_by_sentiment(articles: Article, timeframe: str = None):
    """
    Get a count of articles for each sentiment (positive, neutral, negative)

    Args:
        articles (Article): Filtered or unfiltered queryset of articles to find the counts for
        timeframe (str): Timeframe to filter articles by.
                         Can having the following values [day, week, month, year]
                         This specifies whether the count should be for articles from the past day, week, etc.

    Returns:
        dict: counts for each sentiment
    """
    # check if a time frame was given, if it doesn't match day, week, month or year it won't filter anything
    if timeframe:
        articles = filter_articles_by_timeframe(articles, timeframe)

    # get list of IDs from the filtered set of articles
    article_ids = articles.values_list('id')

    # get NLP info for all the articles provided
    article_nlp = ArticleNlp.objects.filter(article_id__in=article_ids)

    negative_count = article_nlp.filter(sentiment__lt=-0.05).count()
    neutral_count = article_nlp.filter(sentiment__gte=-0.05, sentiment__lte=0.05).count()
    positive_count = article_nlp.filter(sentiment__gt=0.05).count()

    counts = {
        'negative': negative_count,
        'neutral': neutral_count,
        'positive': positive_count
    }

    return counts

def get_subjectivity_by_sentiment(articles: Article, timeframe: str = None):
    """
    Gets subjectivity and sentiment for all articles

    Args:
        articles (Article): Filtered or unfiltered queryset of articles to find the counts for
        timeframe (str): Timeframe to filter articles by.
                         Can having the following values [day, week, month, year]
                         This specifies whether the count should be for articles from the past day, week, etc.

    Returns:
        list: list of dictionaries where the keys in each dictionary and x and y. The keys are left generic on
              purpose since this data is meant to be used on a graph. x is sentiment and y is subjectivity

            [
                {x: <sentiment1>, y: <subjectivity>},
                ...
            ]
    """
    # check if a time frame was given, if it doesn't match day, week, month or year it won't filter anything
    if timeframe:
        articles = filter_articles_by_timeframe(articles, timeframe)

    # get list of IDs from the filtered set of articles
    article_ids = articles.values_list('id')

    # get NLP info for all the articles provided
    article_nlp = ArticleNlp.objects.filter(article_id__in=article_ids)

    values = []

    for art in article_nlp:
        values.append(
            {
                'x': float(art.sentiment),
                'y': float(art.subjectivity)
            }
        )

    return values
