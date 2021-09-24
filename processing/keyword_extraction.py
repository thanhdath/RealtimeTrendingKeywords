import yake
from pymongo import MongoClient
from process_html import html2text
import time

STOPWORDS = open('data/Stopwords/stopwords_vi_without.txt', encoding='utf8').read().splitlines()
 
KW_EXTRACTOR = yake.KeywordExtractor(
    lan='vi', 
    n=3,
    dedupLim=0.9,
    dedupFunc='jaro',
    windowsSize=1,
    top=20,
    stopwords=STOPWORDS
)

BATCH_SIZE = 32

ARTICLE_LIST = ['vnexpress']
 
def extract_keywords(text):
    keywords = KW_EXTRACTOR.extract_keywords(text)
    # ranked keywords, lower the score better the keyword.
    return keywords

def auto_extract_keywords():
    mongodb = MongoClient()
    articles_db = mongodb['article_db']

    while True:
        stime = time.time()

        # find articles that hasn't extract keywords
        articles = articles_db['articles'].find({
            'keywords_extracted': False
        }).limit(BATCH_SIZE)

        for article in articles:
            html = article['content_html']
            text = html2text(html)
            keywords_with_scores = extract_keywords(text)
            keywords, scores = list(zip(*keywords_with_scores))

            articles_db['articles'].update({
                '_id': article['_id']
            }, {
                '$set': {
                    'keywords': keywords,
                    'keyword_scores': scores,
                    'keywords_extracted': True
                }
            })

        etime = time.time()
        avg_time = (etime-stime)/BATCH_SIZE
        print(f'Average processing time: {avg_time:.3f}s/article')

        time.sleep(20)


if __name__ == '__main__':
    auto_extract_keywords()
