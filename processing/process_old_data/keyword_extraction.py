from collections import Counter
from utils import *
from pymongo import MongoClient
from process_html import html2text
import time
import json
from elasticsearch import Elasticsearch
import pika
from tqdm import tqdm

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
N_KEYWORDS = 40

ARTICLE_LIST = ['vnexpress', 'cafef']
    
def auto_extract_keywords():
    
    while True:
        try:
            mongodb = MongoClient(host='0.0.0.0:27018')
            DATABASE_USERNAME = "admin"
            DATABASE_PASSWORD = "admin"
            mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

            articles_db = mongodb['article_db']

            # connection = pika.BlockingConnection(
            #     pika.ConnectionParameters('rabbitmq', heartbeat=3600) # 0 means keep connecting even not see any messages
            # )
            # channel = connection.channel()
            # channel.queue_declare(queue='articles')

            # store data in elasticsearch
            # es = Elasticsearch(["elasticsearch"])
            es = Elasticsearch()
            break
        except Exception as err:
            print(f'Error connect db', err)
            print('Try again in 5 seconds')
            time.sleep(5)

    # res = articles_db['articles'].update({}, 
    #     {'$set': {'keywords_extracted': False}},
    #     multi=True
    # )
    # print('update ', res)
    articles_db['articles'].create_index([('keywords_extracted', 1)])
    articles_db['articles'].create_index([('published_timestamp', 1)])

    for article in tqdm(
        articles_db['articles'].find({'keywords_extracted': False}, no_cursor_timeout=True).sort('published_timestamp', -1), 
        total=articles_db['articles'].count(),
        desc="processing keywords"
        ):
        # print(article['url'])
        if 'content_html' not in article: continue
        html = article['content_html']
        text = html2text(html)
        text = text.strip()

        if len(text) == 0:
            continue
                
        keywords_with_scores = extract_keywords(text)

        if len(keywords_with_scores) == 0:
            continue

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

if __name__ == '__main__':
    auto_extract_keywords()
