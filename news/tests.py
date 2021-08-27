from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Article, ArticleNlp, TopicLkp
from random import random
from datetime import datetime, timedelta
import json

NUM_ARTICLES = 500
NUM_TOPICS = 4

class ArticleViewSetTestCase(APITestCase):

    # list_url = reverse('news:article-list')

    # add dummy data to the test database
    def setUp(self):
        self.articles = []

        date = datetime(2021, 4, 30)

        # create 500 articles
        for i in range(NUM_ARTICLES):
            article = Article.objects.create(
                post_id = f'{i}',
                post_title = f'test title {i}',
                url = 'www.article.com',
                score = i,
                publisher = 'test publisher',
                headline = 'some very important news',
                date_published = date.strftime('%Y-%m-%d'),
                content = 'sf asf asfl;kjasf; aslkjf owjnef opwnfoenqwf iowbnfwiofbn wfnqwe fn wfn asdf'
            )

            self.articles.append(article)
            date -= timedelta(days=1)

        # create 4 topics
        self.topics = []

        for i in range(NUM_TOPICS):
            topic = TopicLkp.objects.create(
                topic_id=i,
                topic_name=f'topic {i}'
            )

            self.topics.append(topic)

        # create an nlp entry for each article
        for article in self.articles:
            ArticleNlp.objects.create(
                article=article,
                topic=self.topics[int(random() * len(self.topics))], # random topic
                sentiment=random() * (-1 if random() > 0.5 else 1), # between -1 and 1
                subjectivity=random(), # between 0 and 1
                keywords='asdf;asdf;asdf;asdf;asdf;asdf;asdf;asdf;asdf;asdf'
            )

    # get a page of articles
    def test_list_articles(self):
        data = {
            'page': 1
        }

        response = self.client.get('/api/article', data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_page_size(self):
        data = {
            'page': 1
        }

        response = self.client.get('/api/article', data=data)
        response_data = json.loads(response.content)

        self.assertEqual(len(response_data['articles']), 20)

    # make sure we get 404 when a page is too big or small
    def test_page_out_of_bounds(self):
        big_page = {
            'page': 10000
        }

        small_page = {
            'page': -10
        }

        big_page_response = self.client.get('/api/article', data=big_page)
        small_page_response = self.client.get('/api/article', data=small_page)

        self.assertEqual(big_page_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(small_page_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_article_query_params_with_sentiment(self):
        # no page specified so this is not paginated
        # haven't included tests for publisher yet
        sentiment_constraints = {
            'startDate': '2021-01-01T00:00:00Z',
            'endDate': '2021-04-01T00:00:00Z',
            'topic': 1,
            'minSentiment': -0.5,
            'maxSentiment': 0.5
        }

        response = self.client.get('/api/article', data=sentiment_constraints)

        def str_to_dt(date_str):
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')

        # ignore warnings about naive datetimes for now
        for article in json.loads(response.content):
            self.assertGreaterEqual(str_to_dt(article['date_published']), str_to_dt(sentiment_constraints['startDate']))
            self.assertLessEqual(str_to_dt(article['date_published']), str_to_dt(sentiment_constraints['endDate']))
            self.assertEqual(article['nlp']['topic'], sentiment_constraints['topic'])
            self.assertGreaterEqual(float(article['nlp']['sentiment']), sentiment_constraints['minSentiment'])
            self.assertLessEqual(float(article['nlp']['sentiment']), sentiment_constraints['maxSentiment'])

    def test_article_query_params_with_subjectivity(self):
        # no page specified so this is not paginated
        # haven't included tests for publisher yet
        subjectivity_constraints = {
            'startDate': '2021-01-01T00:00:00Z',
            'endDate': '2021-04-01T00:00:00Z',
            'topic': 2,
            'minSubjectivity': 0.1,
            'maxSubjectivity': 0.5
        }

        response = self.client.get('/api/article', data=subjectivity_constraints)

        def str_to_dt(date_str):
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')

        # ignore warnings about naive datetimes for now
        for article in json.loads(response.content):
            self.assertGreaterEqual(str_to_dt(article['date_published']), str_to_dt(subjectivity_constraints['startDate']))
            self.assertLessEqual(str_to_dt(article['date_published']), str_to_dt(subjectivity_constraints['endDate']))
            self.assertEqual(article['nlp']['topic'], subjectivity_constraints['topic'])
            self.assertGreaterEqual(float(article['nlp']['subjectivity']), subjectivity_constraints['minSubjectivity'])
            self.assertLessEqual(float(article['nlp']['subjectivity']), subjectivity_constraints['maxSubjectivity'])

    def test_article_sorting(self):
        newest_first_params = {
            'order': 'new'
        }

        oldest_first_params = {
            'order': 'old'
        }

        # get response using order new, old, and no params (no params should default to newest first)
        newest_first_resp = self.client.get('/api/article', data=newest_first_params)
        newest_first_no_params_resp = self.client.get('/api/article')
        oldest_first_resp = self.client.get('/api/article', data=oldest_first_params)

        def str_to_dt(date_str):
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')

        # check that each date is either greater than or less than the previous date
        # articles - list of Article objects
        # newestFirst - boolean value, this determines whether it checks if the current article's
        #          date should be less than or greater than the previous article's date
        def check_dates(articles, newestFirst):
            previous = None

            for i, article in enumerate(articles):
                if i == 0:
                    previous = article['date_published']
                else:
                    if(newestFirst):
                        self.assertLessEqual(str_to_dt(article['date_published']), str_to_dt(previous))
                    else:
                        self.assertGreaterEqual(str_to_dt(article['date_published']), str_to_dt(previous))

                    previous = article['date_published']

        # newest first - check that each date is LESS THAN OR EQUAL TO the previous date
        check_dates(json.loads(newest_first_resp.content), True)

        # newest first no params - same thing
        check_dates(json.loads(newest_first_no_params_resp.content), True)

        # oldest first - check that each date is GREATER THAN OR EQUAL TO the previous date
        check_dates(json.loads(oldest_first_resp.content), False)

    # ensure using topic ID or topic name give the same result when describing the same topic
    def test_topic_and_topic_name(self):
        topic_id_params = {
            'topic': 0
        }

        topic_name_params = {
            'topicName': 'topic 0'
        }

        # get the response 
        resp1 = self.client.get('/api/article', data=topic_id_params)
        resp2 = self.client.get('/api/article', data=topic_name_params)

        data1 = json.loads(resp1.content)
        data2 = json.loads(resp2.content)

        # get a list of IDs from each response and ensure they are the same
        ids1 = [item['id'] for item in data1]
        ids2 = [item['id'] for item in data2]

        self.assertEqual(ids1, ids2)

    def test_list_topics(self):
        response = self.client.get('/api/topics')
        data = json.loads(response.content)

        for i in range(len(data)):
            self.assertEqual(data[i]['topic_id'], i)
            self.assertEqual(data[i]['topic_name'], f'topic {i}')

    # test that the count of articles is accurate
    def test_get_article_counts(self):
        resp = self.client.get('/api/article/get_article_count')
        data = json.loads(resp.content)

        count = data['count']
        self.assertEqual(count, NUM_ARTICLES)

    # test that the sum of counts for each topic is equal to the total number of articles
    def test_get_article_count_by_topic(self):
        total_count = 0

        for i in range(NUM_TOPICS):
            # index is same as topic ID
            resp = self.client.get(f'/api/article/get_article_count?topic={i}')
            data = json.loads(resp.content)
            total_count += data['count']

        self.assertEqual(total_count, NUM_ARTICLES)

    def test_get_article_count_by_sentiment_no_query_params(self):
        resp = self.client.get('/api/article/count_by_sentiment')
        data = json.loads(resp.content)

        # ensure the response contains each type of sentiment
        self.assertIn('negative', list(data.keys()))
        self.assertIn('neutral', list(data.keys()))
        self.assertIn('positive', list(data.keys()))

        # ensure the total number of articles is correct
        total_articles = 0
        for key in data.keys():
            total_articles += data[key]

        self.assertEqual(total_articles, len(self.articles))


    def test_get_article_count_by_sentiment_with_query_params(self):
        time_frames = ['day', 'week', 'month', 'year']

        for tf in time_frames:
            resp = self.client.get(f'/api/article/count_by_sentiment?timeFrame={tf}')
            data = json.loads(resp.content)

            # ensure the response contains each type of sentiment
            self.assertIn('negative', list(data.keys()))
            self.assertIn('neutral', list(data.keys()))
            self.assertIn('positive', list(data.keys()))

    # this should behave the same as getting article counts with no query params
    def test_get_article_count_by_sentiment_bad_query_params(self):
        resp = self.client.get('/api/article/count_by_sentiment')
        data = json.loads(resp.content)

        # ensure the response contains each type of sentiment
        self.assertIn('negative', list(data.keys()))
        self.assertIn('neutral', list(data.keys()))
        self.assertIn('positive', list(data.keys()))

        # ensure the total number of articles is correct
        total_articles = 0
        for key in data.keys():
            total_articles += data[key]

        self.assertEqual(total_articles, len(self.articles))


