from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from textblob import TextBlob


class AnalysisView(viewsets.ViewSet):

    # POST /api/analysis/get_sentiment
    # body of request must be:
    #   {"text": "<text data>"}
    @action(methods=['POST'], detail=False)
    def get_sentiment(self, request):
        # request body must contain "text"
        if 'text' not in request.data:
            return Response({'error': 'must supply text'}, status=status.HTTP_400_BAD_REQUEST)
        
        # "text" must be a string
        if type(request.data['text']) != str:
            return Response({'error': 'text must be a string'}, status=status.HTTP_400_BAD_REQUEST)
        
        blob = TextBlob(request.data['text'])

        return Response({
            'sentiment': blob.sentiment.polarity,
            'subjectivity': blob.sentiment.subjectivity
        })
