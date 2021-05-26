from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Article

class ArticleViewSetTestCase(APITestCase):

    # list_url = reverse('news:article-list')

    # need to also create nlp and topics
    # def setUp(self):
    #     self.article = Article.objects.create(
    #         post_id = "1",
    #         post_title = "test title",
    #         url = "www.article.com",
    #         score = 5,
    #         publisher = "test publisher",
    #         headline = "some very important news",
    #         date_published = "2021-01-01",
    #         content = "sf asf asfl;kjasf; aslkjf owjnef opwnfoenqwf iowbnfwiofbn wfnqwe fn wfn asdf"
    #     )

    # get a page of articles
    def test_list_articles(self):
        # query params
        data = {
            "page": 1
        }

        response = self.client.get('/api/article', data=data)
        print(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_page_num_too_big(self):
        # query params
        data = {
            "page": 999999
        }

        response = self.client.get('/api/article', data=data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
