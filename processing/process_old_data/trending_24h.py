# from pymongo import MongoClient
from process_html import html2text
import time
from datetime import date, datetime, timedelta, timezone
from elasticsearch import Elasticsearch

STOPWORDS = open('data/Stopwords/stopwords_vi_without.txt', encoding='utf8').read().splitlines()
 
ARTICLE_LIST = ['vnexpress', 'cafef']

INTERVAL_EXTRACTION_TIME = 3600
N_KEYWORDS = 100

def get_keywords_stream_day(es, year, month, day, article_source, look_back=14):
    # db_keywords = mongodb['article_db']['articles']

    
    next_day = datetime(year=year, month=month, day=day) + timedelta(days=1)
    keywords_stream = []
    keyword_scores_stream = []

    for i in range(look_back):
        start_day = next_day - timedelta(days=i+1)
        end_day = next_day - timedelta(days=i)

        start_timestamp = start_day.timestamp()
        end_timestamp = end_day.timestamp()

        if article_source == 'all':
            query={
                'range': {
                    'published_timestamp': {
                        'gte': start_timestamp,
                        'lt': end_timestamp
                    }
                }
            }
        else:
            query = {
                'bool': {
                    'must': [
                        {
                            'range': {
                                'published_timestamp': {
                                    'gte': start_timestamp,
                                    'lt': end_timestamp
                                }
                            }
                        },
                        {
                            'match': {
                                'source': article_source
                            }
                        }
                    ]
                }
            }   
            

        cursor = es.search(
            index='article_keywords',
            query=query
        )
        cursor = cursor['hits']['hits']

        # query = {
        #     'published_timestamp': {
        #         '$gte': start_timestamp,
        #         '$lt': end_timestamp
        #     },
        #     'keywords_extracted': True
        # }
        # if article_source is not None:
        #     query['source'] = article_source

        # cursor = db_keywords.find(
        #     query,
        #     {
        #         'keywords': True, 
        #         'keyword_scores': True
        #     }
        # )

        day_keywords = []
        day_keyword_scores = []

        for row in cursor:
            day_keywords.append(row['_source']['keywords'])
            day_keyword_scores.append(row['_source']['keyword_scores'])

        keywords_stream.append(day_keywords)
        keyword_scores_stream.append(day_keyword_scores)
    
    return keywords_stream, keyword_scores_stream

def extract_trending_score_day(es, year, month, day, article_source, n=100):
    keywords_stream, keyword_scores_stream = get_keywords_stream_day(es, year, month, day, article_source, look_back=1)
    day_keywords = keywords_stream[0]
    day_kscores = keyword_scores_stream[0]

    from collections import Counter
    keyword_counter = Counter()
    
    for doc_keywords in day_keywords:
        keyword_counter.update(doc_keywords)

    keyword_counter = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)
    keyword_counter = keyword_counter[:n]
    return keyword_counter


def auto_extract_trending():
    # mongodb = MongoClient()
    # mongodb = MongoClient(host="mongodb")
    # DATABASE_USERNAME = "admin"
    # DATABASE_PASSWORD = "admin"
    # mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

    # articles_db = mongodb['article_db']
    # trending_col = articles_db['trending']

    # store data in elasticsearch
    try:
        # es = Elasticsearch([{'host': 'elasticsearch'}])
        es = Elasticsearch()
    except Exception as err:
        print(f'Error connect db', err)
        print('Try again in 5 seconds')
        time.sleep(5)

    stime = time.time()

    # current_datetime = datetime.now()
    for i in range(24*5):
        current_datetime = datetime.now()
        current_datetime = current_datetime - timedelta(hours=i)
        print(f'process 24h - current {current_datetime}')

        for article_source in ['all']:
            trending_keywords = extract_trending_score_24h(
                es,
                current_datetime,
                article_source=article_source,
                n=N_KEYWORDS)

            if len(trending_keywords) == 0:
                continue
            
            keywords, keywords_rank_scores = zip(*trending_keywords)

            dt_now = datetime.now()

            es.index(
                index='trending_24h',
                doc_type='trending_24h',
                id=dt_now.timestamp(),
                body={
                    'trending_keywords': keywords,
                    'keywords_rank_scores': keywords_rank_scores,
                    'time': current_datetime.strftime("%Y/%m/%d"),
                    'article_source': article_source,
                    'extracted_timestamp': dt_now.timestamp(),
                    'extracted_time': dt_now.strftime("%Y/%m/%d %H:%M:%S")
                }
            )

        etime = time.time()
        execution_time = etime - stime
        print(f'Average processing time: {execution_time:.3f}s/article')

            #     time.sleep(INTERVAL_EXTRACTION_TIME)
            # except Exception as err:
            #     print(f'Error execute keyword extraction', err)
            #     print('Try again in 10 seconds')
            #     time.sleep(10)


if __name__ == '__main__':
    auto_extract_trending()
