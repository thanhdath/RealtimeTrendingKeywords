from collections import Counter
from utils import *
# from pymongo import MongoClient
from process_html import html2text
import time
import json
from elasticsearch import Elasticsearch
import pika
from datetime import datetime

THRESHOLD_TFIDF_SCORE = 0.5
IDF = json.load(open("data/idf.json"))
MAX_IDF = max(IDF.values())

def extract_keywords(text, n=10):
    # text = clean_str(text)
    tfs = compute_tf(text)
    tfidfs = {}
    for word, tf in tfs.items():
        if word in stopwords or is_number(word) or len(word.strip()) == 0: 
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

def callback(es, body):
    try:
        article = json.loads(body)

        if 'content_html' not in article: return
        
        # print(f"Processing article {article['url']}")
        description_html = article['description']
        content_html = article['content_html']

        content = html2text(content_html)
        content = content.strip()

        description = html2text(description_html)
        description = description.strip()

        title = article['title']

        text = '. '.join([title, description, content])

        if len(text) == 0:
            return 

        keywords_with_scores = extract_keywords(text, n=N_KEYWORDS)
        
        if len(keywords_with_scores) == 0:
            return

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
                'published_time': article['published_time'],
                'published_time_dt': datetime.fromtimestamp(article['published_timestamp']),
                'published_timestamp': article['published_timestamp']
            }
        )
    except Exception as err:
        print('callback function error', err)
    

def auto_extract_keywords():
    # mongodb = MongoClient()
    while True:
        try:
            # mongodb = MongoClient(host="mongodb")
            # DATABASE_USERNAME = "admin"
            # DATABASE_PASSWORD = "admin"
            # mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

            # articles_db = mongodb['article_db']

            connection = pika.BlockingConnection(
                pika.ConnectionParameters('rabbitmq', heartbeat=3600) # 0 means keep connecting even not see any messages
            )
            channel = connection.channel()
            # channel.queue_declare(queue='articles')

            # store data in elasticsearch
            es = Elasticsearch([{'host': 'elasticsearch'}])
            break
        except Exception as err:
            print(f'Error connect db', err)
            print('Try again in 5 seconds')
            time.sleep(5)

    channel.basic_consume(
        queue='articles',
        auto_ack=True,
        on_message_callback=lambda ch, method, properties, body: callback(es, body))
    
    print(' [*] Waiting for messages.')

    channel.start_consuming()

    # TODO: get data from rabitmq
    # while True:
    #     try:
    #         stime = time.time()

            # find articles that hasn't extract keywords
            # articles = articles_db['articles'].find({
            #     # 'keywords_extracted': False
            # }).sort('published_timestamp', -1).limit(BATCH_SIZE)  # TODO: sort by timestamp

            # for article in articles:
            #     if 'content_html' not in article: continue
            #     html = article['content_html']
            #     text = html2text(html)
            #     keywords_with_scores = extract_keywords(text)
            #     keywords, scores = list(zip(*keywords_with_scores))

            #     # get source, url, first_topic, keywords, keyword_scores and insert to elasticsearch
            #     es.index(
            #         index='article_keywords',
            #         doc_type='article_keywords',
            #         id=str(article['_id']),
            #         body={
            #             'source': article['source'],
            #             'url': article['url'],
            #             'first_topic': article['first_topic'],
            #             'keywords': keywords,
            #             'keyword_scores': scores,
            #             'published_timestamp': article['published_timestamp']
            #         }
            #     )

            #     articles_db['articles'].update({
            #         '_id': article['_id']
            #     }, {
            #         '$set': {
            #             'keywords': keywords,
            #             'keyword_scores': scores,
            #             'keywords_extracted': True
            #         }
            #     })

        #     etime = time.time()
        #     avg_time = (etime-stime)/BATCH_SIZE
        #     print(f'Average processing time: {avg_time:.3f}s/article')

        #     time.sleep(20)
        # except Exception as err:
        #     print(f'Error execute keyword extraction', err)
        #     print('Try again in 10 seconds')
        #     time.sleep(10)


if __name__ == '__main__':
    auto_extract_keywords()
