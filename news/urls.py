from django.urls import path, include
from rest_framework import routers
from .api import ArticleViewSet, SavedArticleViewset, TopicViewSet
# from knox import views as knox_views

router = routers.DefaultRouter(trailing_slash=False)
router.register('api/article', ArticleViewSet, 'article-list')
router.register('api/savearticle', SavedArticleViewset, 'save-article')
router.register('api/topics', TopicViewSet, 'topic-list')
# router.register('api/articlenlp', ArticleNlpViewSet, 'articlenlp-retrieve')

urlpatterns = [
    path('', include(router.urls))
]