# from pymongo import MongoClient
from process_html import html2text
import time
from datetime import date, datetime, timedelta, timezone
from elasticsearch import Elasticsearch
import numpy as np
from scipy.signal import savgol_filter
from collections import Counter

STOPWORDS = open('data/Stopwords/stopwords_vi_without.txt', encoding='utf8').read().splitlines()
 
ARTICLE_LIST = ['vnexpress', 'cafef']

INTERVAL_EXTRACTION_TIME = 3600
N_KEYWORDS = 100

FILTERED_KEYWORDS = ['descriptions', 'selected', 'audio track', 'cancel',
    'escape', 'beginning', 'transparent', 'cyan', 'opaque', 'window', 'dialog', 'magenta', 'blue',
    'green', 'color', 'white', 'transparency', 'yellow', 'player', 'thời lượng']

def get_keywords_stream_24h(es, current_datetime, article_source, look_back=14):
    # db_keywords = mongodb['article_db']['articles']

    keywords_stream = []
    keyword_scores_stream = []

    for i in range(look_back):
        start_day = current_datetime - timedelta(days=i+1)
        end_day = current_datetime - timedelta(days=i)

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
            query=query,
            size=10000
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

def extract_trending_score_24h(es, current_datetime, article_source, n=100):
    keywords_stream, keyword_scores_stream = get_keywords_stream_24h(
        es, current_datetime, article_source, look_back=7)
    keywords_stream = keywords_stream[::-1]
    keyword_scores_stream = keyword_scores_stream[::-1]

    n_articles = len(keywords_stream[-1])

    noun_freq_score = Counter()
    for post_nouns, kw_scores in zip(keywords_stream[-1], keyword_scores_stream[-1]):
        noun2score = {n: s for n, s in zip(post_nouns, kw_scores)}
        noun_freq_score.update(noun2score)
    n_total = len(keywords_stream[-1])
    noun_freq_score = {k: np.log(1+v/n_total) for k, v in noun_freq_score.items()}
    candidate_nouns = list(noun_freq_score.keys())
    candidate_nouns = [x for x in candidate_nouns if len(x) > 1]
    candidate_nouns = list(set(candidate_nouns) - set(FILTERED_KEYWORDS))

    noun_freqs_stream = []
    for nouns_list, scores_list in zip(keywords_stream, keyword_scores_stream):
        counter = Counter()
        for nouns, scores in zip(nouns_list, scores_list):
            noun2score = {n: s for n, s in zip(nouns, scores)}
            counter.update(noun2score)
        n_total = len(nouns_list)
        counter = {k: np.log(1+v/n_total) for k, v in counter.items()}
        noun_freqs_stream.append(counter)

    noun_time_score = compute_trending_score(candidate_nouns, noun_freqs_stream)
    # noun_time_score = sorted(noun_time_score.items(), key=lambda x: x[1], reverse=True)

    # import pdb; pdb.set_trace()
    noun_trending_score = {}
    for noun in candidate_nouns:
        noun_trending_score[noun] = noun_time_score[noun]  * noun_freq_score[noun] 

    noun_trending_score = sorted(noun_trending_score.items(), key=lambda x: x[1], reverse=True)
    noun_trending_score = noun_trending_score[:n]
    return noun_trending_score, n_articles

def get_trending_score(x_last, prev_xs, w1=3., w2=2., w3=1., w4=1.):
    if len(prev_xs) > 7: prev_xs = prev_xs[-7:]
    extended_prev_xs = np.zeros(7)
    if len(prev_xs) > 0:
        extended_prev_xs[-len(prev_xs):] = prev_xs
    score = w1*max((x_last - extended_prev_xs[-1]), 0)
    score += w2*max((x_last - extended_prev_xs[-3:].mean()), 0)
    score += w3*max((x_last-extended_prev_xs.mean()), 0)
    # score += w4*max((x_last-extended_prev_xs.mean()),0)
    return score

def compute_trending_score(candidate_nouns, noun_freqs_stream):
    noun_trending_score = {}
    for noun in candidate_nouns:
        xs = [N.get(noun, 0) for N in noun_freqs_stream]
        # xs = savgol_filter(xs, 7, 3)

        if noun_freqs_stream[-1].get(noun, 0) == 0:
            xs[-1] = 0

        ys = []

        cur_xs = xs[-1]
        prev_xs = xs[:-1]
        y = get_trending_score(cur_xs, prev_xs)
        noun_trending_score[noun] = y
    return noun_trending_score

def compute_trending_score(candidate_nouns, noun_freqs_stream):
    noun_trending_score = {}
    for noun in candidate_nouns:
        xs = [N.get(noun, 0) for N in noun_freqs_stream]
        # xs = savgol_filter(xs, 7, 3)

        if noun_freqs_stream[-1].get(noun, 0) == 0:
            xs[-1] = 0

        ys = []

        cur_xs = xs[-1]
        prev_xs = xs[:-1]
        y = get_trending_score(cur_xs, prev_xs)
        noun_trending_score[noun] = y
    return noun_trending_score

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
        es = Elasticsearch([{'host': 'elasticsearch'}])
        # es = Elasticsearch()
    except Exception as err:
        print(f'Error connect db', err)
        print('Try again in 5 seconds')
        time.sleep(5)

    while True:
        # try:
        stime = time.time()

        current_datetime = datetime.now()
        for article_source in ['all']:
            trending_keywords = extract_trending_score_24h(
                es,
                current_datetime,
                # today.year, 
                # today.month, 
                # today.day, 
                article_source=article_source,
                n=N_KEYWORDS)
            
            dt_now = datetime.now()

            # trending_col.insert_one({
            #     'trending_keywords': trending_keywords,
            #     'time': today.strftime("%Y/%m/%d"),
            #     'article_source': article_source,
            #     'extracted_timestamp': dt_now.timestamp(),
            #     'extracted_time': dt_now.strftime("%Y/%m/%d %H:%M:%S")
            # })
            keywords, keywords_rank_scores = zip(*trending_keywords)

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

        time.sleep(INTERVAL_EXTRACTION_TIME)
        # except Exception as err:
        #     print(f'Error execute trending detection', err)
        #     print('Try again in 10 seconds')
        #     time.sleep(INTERVAL_EXTRACTION_TIME/2)


if __name__ == '__main__':
    auto_extract_trending()
