from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Article, ArticleNlp, TopicLkp
from random import random
import json

class ArticleViewSetTestCase(APITestCase):

    # list_url = reverse('news:article-list')

    # add dummy data to the test database
    def setUp(self):
        self.articles = []

        # create 100 articles
        for i in range(100):
            article = Article.objects.create(
                post_id = f"{i}",
                post_title = f"test title {i}",
                url = "www.article.com",
                score = i,
                publisher = "test publisher",
                headline = "some very important news",
                date_published = "2021-01-01",
                content = "sf asf asfl;kjasf; aslkjf owjnef opwnfoenqwf iowbnfwiofbn wfnqwe fn wfn asdf"
            )

            self.articles.append(article)

        # create 4 topics
        self.topics = []

        for i in range(4):
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
                subjectivity=random() # between 0 and 1
            )

    # get a page of articles
    def test_list_articles(self):
        data = {
            "page": 1
        }

        response = self.client.get('/api/article', data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_page_size(self):
        data = {
            "page": 1
        }

        response = self.client.get('/api/article', data=data)
        response_data = json.loads(response.content)

        self.assertEqual(len(response_data['articles']), 20)

    # make sure we get 404 when a page is too big or small
    def test_page_out_of_bounds(self):
        big_page = {
            "page": 10000
        }

        small_page = {
            "page": -10
        }

        big_page_response = self.client.get('/api/article', data=big_page)
        small_page_response = self.client.get('/api/article', data=small_page)

        self.assertEqual(big_page_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(small_page_response.status_code, status.HTTP_404_NOT_FOUND)

