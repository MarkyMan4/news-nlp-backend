from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import TopicLkp
from textblob import TextBlob
import math
from textblob import TextBlob
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from gensim.models import LdaMulticore
from backend import settings
import os


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

    # POST /api/analysis/get_keywords
    # body of request must be:
    #   {"text": "<text data>"}
    @action(methods=['POST'], detail=False)
    def get_keywords(self, request):
        # request body must contain "text"
        if 'text' not in request.data:
            return Response({'error': 'must supply text'}, status=status.HTTP_400_BAD_REQUEST)
        
        # "text" must be a string
        if type(request.data['text']) != str:
            return Response({'error': 'text must be a string'}, status=status.HTTP_400_BAD_REQUEST)

        keywords = self.find_keywords(request.data['text'])

        return Response({
            'keywords': keywords
        })

    # Helper methods for getting keywords via TF-IDF
    def get_unique_terms(self, tokens: list) -> list:
        # find the unique terms, then count how many times each term appears
        unique_terms = []

        for token in tokens:
            if token not in unique_terms:
                unique_terms.append(token)

        return unique_terms

    def get_term_frequency(self, unique_terms: list, all_tokens: list) -> dict:
        # find how many times each term appears
        term_counts = {}
        for term in unique_terms:
            term_counts.update({term: 0})

        for token in all_tokens:
            term_counts[token] += 1

        # find term frequencies by diving # of times each term appears by the term counts
        term_freqs = {}
        num_terms = len(all_tokens)

        for term in unique_terms:
            term_freqs.update({term: term_counts[term] / num_terms})

        return term_freqs

    def get_inverse_document_frequency(self, content: str, unique_terms: list) -> dict:
        # split content into sentences
        sentences = sent_tokenize(content)
        num_sentences = len(sentences)

        # split each sentence into word tokens, no need to remove stop words here
        sentences = [word_tokenize(sent) for sent in sentences]

        # find number of sentences containing each term
        sentence_freqs = {}

        for term in unique_terms:
            sentence_freqs.update({term: 0})
            
        for term in unique_terms:
            for sent in sentences:
                if term in sent:
                    sentence_freqs[term] += 1

        # compute inverse document frequency for each term
        idf = {}

        for term in unique_terms:
            term_val = 0

            # avoid division by 0
            if sentence_freqs[term] != 0:
                term_val = math.log(num_sentences / sentence_freqs[term])

            idf.update({
                term: term_val
            })

        return idf

    def get_tf_idf(self, unique_terms: list, term_freqs: dict, idf: dict) -> dict:
        # find tfidf for each term
        tfidf = {}

        for term in unique_terms:
            tfidf.update({
                term: term_freqs[term] * idf[term]
            })

        return tfidf

    def find_keywords(self, content: str) -> str:
        """
        Find the top ten key words using the TF-IDF calculation.

        Term Frequency = (# of times term appears) / (total # of terms in article)
        Inverse Document Frequency = log(# of sentences / # of sentences with the term)
        TF-IDF - term frequency * inverse document frequency

        Higher TF-IDF score means the term is more important.

        Args:
            content (str): content from news article to find keywords for

        Returns:
            str: semi-colon separated list of keywords
        """
        # tokenize the content and remove stopwords and punctuation
        sentences = sent_tokenize(content)
        tokens = []
        # sent tokenize first so the way it creates tokens is consistent with how it's done when computing IDF
        for sent in sentences:
            tokens += word_tokenize(sent)
        
        tokens = [t for t in tokens if t.lower() not in stopwords.words('english') and len(t) >= 3 and t.lower() != 'said']

        unique_terms = self.get_unique_terms(tokens)

        # get TF and IDF then calculate TF-IDF
        term_freqs = self.get_term_frequency(unique_terms, tokens)
        idf = self.get_inverse_document_frequency(content, unique_terms)
        tfidf_scores = self.get_tf_idf(unique_terms, term_freqs, idf)

        # take the top 10 words with highest TF-IDF score
        # swap keys and values so the list can be sorted by TF-IDF score easily
        swapped_key_and_vals = []
        for item in tfidf_scores.items():
            swapped_key_and_vals.append((item[1], item[0]))

        # take the last ten items in reversed order so it's sorted in descending order
        top_ten = sorted(swapped_key_and_vals)[-1:-11:-1]
        top_ten_terms = [item[1] for item in top_ten]

        return top_ten_terms

    @action(methods=['POST'], detail=False)
    def get_topic_probability(self, request) -> int:
        """
        Use the trained LDA model to predict the topic of the given article.
        This doesn't round the probabilities. That can be handled by the client.

        Args:
            preprocessed_article (str): article to predict the topic for

        Returns:
            Response: probabililty of the text being in any one of the topics.
                      Format:
                      [
                        {
                            "topic_name": <name>,
                            "probability": <probability>
                        },
                        ...
                      ]
        """
        # request body must contain "text"
        if 'text' not in request.data:
            return Response({'error': 'must supply text'}, status=status.HTTP_400_BAD_REQUEST)
        
        # "text" must be a string
        if type(request.data['text']) != str:
            return Response({'error': 'text must be a string'}, status=status.HTTP_400_BAD_REQUEST)

        model = LdaMulticore.load(os.path.join(settings.STATIC_ROOT, 'news_lda_model'))

        preprocessed = self.preprocess(request.data['text'])

        # create bag of words with preprocessed article
        bow = model.id2word.doc2bow(preprocessed)

        # make prediction
        # pred is a list of tuples of the form (<topic id>, <topic probability>)
        probabilities = model[bow]

        # Look up the topic name for each result and format for response
        response = []

        for prob in probabilities:
            topic_name = TopicLkp.objects.filter(topic_id=prob[0]).first().topic_name
            probability = prob[1]

            response.append({
                'topic_name': topic_name,
                'probability': probability
            })

        return Response(response)

    def preprocess(self, text: str) -> list:
        """
        Preprocess text for topic modeling.
        This involves removing stop words and any words less than
        three characters. It also word tokenizes sentences and 
        lemmatizes each word.

        Args:
            text (str): Article to preprocess

        Returns:
            list: list of lowercase, lemmatized tokens from the article
        """
        stop_words = stopwords.words('english')
        lemmatizer = WordNetLemmatizer()

        tokens = word_tokenize(text.lower()) # make all text lower case
        words = [] # words resulting from applying the filters

        for token in tokens:
            if len(token) > 3 and token not in stop_words:
                words.append(lemmatizer.lemmatize(token))
        
        return words

