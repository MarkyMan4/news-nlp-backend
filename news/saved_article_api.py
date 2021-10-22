from rest_framework import permissions
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import ArticleSerializer, SavedArticleSerializer
from .models import Article, ArticleNlp, SavedArticle
from .utils import get_article_nlp


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
