from pymongo import MongoClient
from process_html import html2text
import time
from datetime import date, datetime, timedelta, timezone

STOPWORDS = open('data/Stopwords/stopwords_vi_without.txt', encoding='utf8').read().splitlines()
 
ARTICLE_LIST = ['vnexpress']

INTERVAL_EXTRACTION_TIME = 60

def get_keywords_stream(mongodb, year, month, day, article_source, look_back=14):
    db_keywords = mongodb['article_db']['articles']
    
    next_day = datetime(year=year, month=month, day=day) + timedelta(days=1)
    keywords_stream = []
    keyword_scores_stream = []

    for i in range(look_back):
        start_day = next_day - timedelta(days=i+1)
        end_day = next_day - timedelta(days=i)

        start_timestamp = start_day.timestamp()
        end_timestamp = end_day.timestamp()

        query = {
            'source': article_source,
            'published_timestamp': {
                '$gte': start_timestamp,
                '$lt': end_timestamp
            },
            'keywords_extracted': True
        }

        cursor = db_keywords.find(
            query,
            {
                'keywords': True, 
                'keyword_scores': True
            }
        )

        day_keywords = []
        day_keyword_scores = []

        for row in cursor:
            day_keywords.append(row['keywords'])
            day_keyword_scores.append(row['keyword_scores'])

        keywords_stream.append(day_keywords)
        keyword_scores_stream.append(day_keyword_scores)
    
    return keywords_stream, keyword_scores_stream
    
def extract_trending_score(mongodb, year, month, day, article_source):
    keywords_stream, keyword_scores_stream = get_keywords_stream(mongodb, year, month, day, article_source, look_back=1)
    day_keywords = keywords_stream[0]
    day_kscores = keyword_scores_stream[0]

    from collections import Counter
    keyword_counter = Counter()
    
    for doc_keywords in day_keywords:
        keyword_counter.update(doc_keywords)

    keyword_counter = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)
    return keyword_counter

def auto_extract_trending():
    mongodb = MongoClient()
    articles_db = mongodb['article_db']
    trending_col = articles_db['trending']

    while True:
        stime = time.time()

        today = date.today() - timedelta(days=2)
        for article_source in ARTICLE_LIST:
            trending_keywords = extract_trending_score(
                mongodb,
                today.year, 
                today.month, 
                today.day, 
                article_source=article_source)
            
            dt_now = datetime.now()
            trending_col.insert_one({
                'trending_keywords': trending_keywords,
                'time': today.strftime("%Y/%m/%d"),
                'article_source': article_source,
                'extracted_timestamp': dt_now.timestamp(),
                'extracted_time': dt_now.strftime("%Y/%m/%d %H:%M:%S")
            })

        etime = time.time()
        execution_time = etime - stime
        print(f'Average processing time: {execution_time:.3f}s/article')

        time.sleep(INTERVAL_EXTRACTION_TIME)


if __name__ == '__main__':
    auto_extract_trending()
