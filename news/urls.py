from django.urls import path, include
from rest_framework import routers
from .article_api import ArticleViewSet
from .saved_article_api import SavedArticleViewset
from .topic_api import TopicViewSet
from .analysis_api import AnalysisView
# from knox import views as knox_views

router = routers.DefaultRouter(trailing_slash=False)
router.register('api/article', ArticleViewSet, 'article-list')
router.register('api/savearticle', SavedArticleViewset, 'save-article')
router.register('api/topics', TopicViewSet, 'topic-list')
router.register('api/analysis', AnalysisView, 'analysis')
# router.register('api/articlenlp', ArticleNlpViewSet, 'articlenlp-retrieve')

urlpatterns = [
    path('', include(router.urls))
]