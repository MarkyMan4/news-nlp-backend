from django.urls import path, include
from rest_framework import routers
from .api import ArticleViewSet, ArticleNlpViewSet
# from knox import views as knox_views

router = routers.DefaultRouter()
router.register('api/article', ArticleViewSet, 'article-list')
router.register('api/articlenlp', ArticleNlpViewSet, 'articlenlp-list')

urlpatterns = [
    path('', include(router.urls))
]