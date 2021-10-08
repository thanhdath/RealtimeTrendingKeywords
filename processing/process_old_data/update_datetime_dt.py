from collections import Counter
from utils import *
from pymongo import MongoClient
from process_html import html2text
import time
import json
from elasticsearch import Elasticsearch
from tqdm import tqdm
from multiprocessing import Pool
from datetime import datetime

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

def update():
    
    while True:
        try:
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

    res = es.search(
        index='article_keywords',
        doc_type='article_keywords',
        body={
            "query": {
                "bool": {
                    "must_not": [
                        {
                        "exists": {
                            "field": "published_time_dt"
                        }
                        }
                    ]
                }
            }
        },
        size=10000)

    res = res['hits']['hits']
    print(len(res))
    
    for article in tqdm(res, desc="updating", total=len(res)):
        id = article['_id']
        article = article['_source']

        if article['published_timestamp'] is not None:
            try:
                es.delete(
                    index="article_keywords",
                    doc_type="article_keywords",
                    id=id)
            except Exception as err:
                print(err)

            # print(article)
            es.index(
                index='article_keywords',
                doc_type='article_keywords',
                id=id,
                body={
                    'source': article['source'],
                    'url': article['url'],
                    'first_topic': article['first_topic'],
                    'keywords': article['keywords'],
                    'keyword_scores': article['keyword_scores'],
                    'published_time': article['published_time'],
                    'published_timestamp': article['published_timestamp'],
                    'published_time_dt': datetime.fromtimestamp(article['published_timestamp'])
                }
            )


if __name__ == '__main__':
    update()



