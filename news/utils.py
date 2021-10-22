# Helper functions used by various API endpoints
from .serializers import ArticleNlpSerializer
from datetime import datetime, timedelta


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
