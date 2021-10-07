from collections import Counter
from utils import *
from pymongo import MongoClient
from process_html import html2text
import time
import json
from elasticsearch import Elasticsearch
import pika
from tqdm import tqdm
from multiprocessing import Pool

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
    

def extract_keyword_and_insert(article):
    # print(article['url'])
    if 'content_html' not in article: return [], []
    html = article['content_html']
    text = html2text(html)
    text = text.strip()

    if len(text) == 0:
        return [], []
            
    keywords_with_scores = extract_keywords(text)

    if len(keywords_with_scores) == 0:
        return [], []

    keywords, scores = list(zip(*keywords_with_scores))

    # get source, url, first_topic, keywords, keyword_scores and insert to elasticsearch
    return keywords, scores

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

    batch_articles = []
    for article in tqdm(
        articles_db['articles'].find({'keywords_extracted': True}, no_cursor_timeout=True).sort('published_timestamp', -1), 
        total=articles_db['articles'].count(),
        desc="importing keywords to elasticsearch"
        ):

        keywords = article['keywords']
        scores = article['keyword_scores']

        if len(keywords) == 0:
            continue

        res = es.search(index="article_keywords", doc_type='article_keywords', body={
            "query": {
                "match_phrase": {
                    "url": article['url']
                }
            }
        })
        res = res['hits']['hits']

        if len(res) > 0:
            for old_record in res:
                try:
                    es.delete(
                        index="article_keywords",
                        doc_type="article_keywords",
                        id=old_record['_id'])
                except Exception as err:
                    print(err)

        idx_keep = [i for i, k in enumerate(keywords) if len(k.strip()) > 0]
        keywords = [keywords[i] for i in idx_keep]
        scores = [scores[i] for i in idx_keep]
            
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
                'published_time': article['published_time'],
                'published_timestamp': article['published_timestamp']
            }
        )


if __name__ == '__main__':
    auto_extract_keywords()
