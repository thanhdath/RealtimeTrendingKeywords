from collections import Counter
from utils import *
from pymongo import MongoClient
from process_html import html2text
import time
import json
from elasticsearch import Elasticsearch

THRESHOLD_TFIDF_SCORE = 0.5
IDF = json.load(open("data/idf.json"))
MAX_IDF = max(IDF.values())

def extract_keywords(text, n=10):
    tfs = compute_tf(text)
    tfidfs = {}
    for word, tf in tfs.items():
        if word in stopwords or is_number(word): 
            continue 
        tfidf = tf*IDF.get(word, MAX_IDF)
        tfidfs[word] = tfidf
    sorted_keywords = sorted(tfidfs.items(), key=lambda x: x[1], reverse=True)
    sorted_keywords = sorted_keywords[:n]
    sorted_keywords = [(x[0].replace("_", " "), x[1]) for x in sorted_keywords]
    return sorted_keywords


BATCH_SIZE = 32

ARTICLE_LIST = ['vnexpress', 'cafef']

def auto_extract_keywords():
    # mongodb = MongoClient()
    while True:
        try:
            mongodb = MongoClient(host="mongodb")
            DATABASE_USERNAME = "admin"
            DATABASE_PASSWORD = "admin"
            mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

            articles_db = mongodb['article_db']

            # store data in elasticsearch
            es = Elasticsearch([{'host': 'elasticsearch'}])
            break
        except Exception as err:
            print(f'Error connect db', err)
            print('Try again in 5 seconds')
            time.sleep(5)


    # TODO: get data from rabitmq
    while True:
        try:
            stime = time.time()

            # find articles that hasn't extract keywords
            articles = articles_db['articles'].find({
                # 'keywords_extracted': False
            }).sort('published_timestamp', -1).limit(BATCH_SIZE)  # TODO: sort by timestamp

            for article in articles:
                if 'content_html' not in article: continue
                html = article['content_html']
                text = html2text(html)
                keywords_with_scores = extract_keywords(text)
                keywords, scores = list(zip(*keywords_with_scores))

                # get source, url, first_topic, keywords, keyword_scores and insert to elasticsearch
                es.index(
                    index='article_keywords',
                    doc_type='article_keywords',
                    id=str(article['_id']),
                    body={
                        'source': article['source'],
                        'url': article['url'],
                        'first_topic': article['first_topic'],
                        'keywords': keywords,
                        'keyword_scores': scores,
                        'published_timestamp': article['published_timestamp']
                    }
                )

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
        except Exception as err:
            print(f'Error execute keyword extraction', err)
            print('Try again in 10 seconds')
            time.sleep(10)


if __name__ == '__main__':
    auto_extract_keywords()
