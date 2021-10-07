from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse
import time
import datetime
from multiprocessing import Pool
import selenium
import pika
import json
from bs4 import BeautifulSoup
import logging

logging.basicConfig(filename='log.log',
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO)

CHROME_DRIVER_PATH = './chromedriver'
URL = "http://vnexpress.vn"
INTERVAL_CHECK_NEW_ARTICLES = 60

# MONGODB_HOST = "mongodb"
# RABBIT_MQ_HOST = "rabbitmq"
# SELENIUM_HOST = "http://selenium:4444/wd/hub"

MONGODB_HOST = "localhost:27018"
RABBIT_MQ_HOST = "localhost"
SELENIUM_HOST = "http://localhost:4444/wd/hub"

def parse_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--topic', default='kinh-doanh')
    parser.add_argument('--workers', default=2, type=int)
    args = parser.parse_args()
    return args

def convert_string_to_local_timestamp(str_datetime):
    """
    str_datetime Thứ sáu, 1/10/2021, 16:45 (GMT+7)
    """
    elms = str_datetime.split(',')
    date = elms[1].strip()
    time_with_gmt = elms[2].strip()
    time_str = time_with_gmt.split()[0]
    datetime_str = f"{date} {time_str}"
    return time.mktime(datetime.datetime.strptime(datetime_str, "%d/%m/%Y %H:%M").timetuple())

def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text()
    text = re.sub("\s+", " ", text)
    return text.strip()

def crawl_article(db, driver: webdriver.Chrome, url: str):
    try:
        driver.get(url)
    except selenium.common.exceptions.TimeoutException as err:
        print(err)
        time.sleep(5)
    time.sleep(.5)

    try:
        title_elm = driver.find_element_by_css_selector('.title-detail')
        title = title_elm.get_attribute('innerHTML')
    except Exception as err:
        print(f'err title {url}\n{err}')
        title = ''

    try:
        desc_elm = driver.find_element_by_css_selector('.description')
        desc = desc_elm.get_attribute('innerHTML')
    except Exception as err:
        print(f'err desc {url}\n{err}')
        desc = ''

    try:
        content_elm = driver.find_element_by_css_selector('.fck_detail')
        content_html = content_elm.get_attribute('innerHTML')
    except Exception as err:
        print(f'err content {url}\n{err}')
        content_html = ''

    # get timestamp
    # get published datetime
    published_timestamp = None
    published_time = None
    try:
        published_time = driver.find_element_by_css_selector('.header-content > .date')
        # published_time = text_from_html(published_time)
        published_time = published_time.get_attribute('innerHTML')
        published_timestamp = convert_string_to_local_timestamp(published_time)
    except Exception as err:
        print(f'Error get pusblished time {url}\n{err}')
        # return

    # get topics
    try:
        topic_elms = driver.find_elements_by_css_selector('.breadcrumb > li > a')
        topics = [x.get_attribute('innerHTML') for x in topic_elms]
        # topics = [text_from_html(x) for x in topic_elms]
    except Exception as err:
        topics = []
        print(f'err topic {url}')
    if len(topics) > 0:
        first_topic = topics[0]
    else:
        first_topic = None
    
    data = {
        'crawled': True,
        'source': 'vnexpress',
        'title': title,
        'description': desc,
        'content_html': content_html, 
        # 'tags': tags,
        'url': url,
        'topics': topics,
        'first_topic': first_topic,
        'published_timestamp': published_timestamp,
        'published_time': published_time,

        'keywords_extracted': False # temporal added
    }

    article_record = db.find_one({'url': url})
    # print(article_record)
    data_id = None
    if article_record is None:
        _id = db.insert_one(data)
        data_id = _id.inserted_id
    else:
        db.update({'url': url}, {'$set': data})
        data_id = str(article_record['_id'])
    data['_id'] = data_id
    return data

def crawl_newest_urls(db, driver, topic, max_page=4, threshold_exists_url=8):
    n_exists_url = 0
    all_newest_urls = set()

    for page in tqdm(range(1, max_page), desc="Crawling"):
        request_url = f"{URL}/{topic}-p{page}"
        driver.get(request_url)
        time.sleep(0.5) # sleep because title elements need time to load

        # crawl article urls
        item_news = driver.find_elements_by_css_selector('.item-news')

        for item_new in item_news:
            try:
                title_elm = item_new.find_element_by_css_selector('.title-news > a')
            except Exception as err:
                print(f'Error title - request url {request_url}', err)
                continue
        
            url = title_elm.get_attribute('href')
            if not re.match(r"https://vnexpress\.net/.+", url):
                continue

            record = db.find_one({'url': url})
            if record is not None:
                n_exists_url += 1
                if n_exists_url > threshold_exists_url:
                    break
                continue
            else:
                all_newest_urls.add(url)

            # title = title_elm.get_attribute('title')

            # data = {
            #     'topic': topic,
            #     'title': title,
            #     'url': url,
            #     # 'n_comments': n_comments,
            #     # 'published_time': published_time,
            #     # 'published_timestamp': published_timestamp
            # }
        
        if n_exists_url > threshold_exists_url:
            break
    return all_newest_urls

def load_topics():
    topics = open('url/vnexpress_topics.txt').read().split('\n')
    topics = [x.strip() for x in topics]
    return topics

def crawl_multiple_topics(urls):
    # print(topic_list)
    # logging.info(topic_list)
    # mongodb = MongoClient()
    mongodb = MongoClient(host=MONGODB_HOST)
    DATABASE_USERNAME = "admin"
    DATABASE_PASSWORD = "admin"
    mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

    articles_db = mongodb['article_db']
    db = articles_db['articles']
    # db.create_index([('crawled', 1)])
    # db.create_index([('url', 1)])
    # db.create_index([('topic', 1)])

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    
    driver = webdriver.Chrome(
        executable_path=CHROME_DRIVER_PATH,
        chrome_options=chrome_options
    )
    # instance_name = '_'.join(topic_list).replace(' ', '-')
    # driver = webdriver.Remote(
    #     SELENIUM_HOST,
    #     options=chrome_options
    # )

    for url in urls:
        try:
            data = crawl_article(db, driver, url)
        except Exception as err:
            print('Unknown error: ', err)
            print('Sleep for 10 seconds')
            logging.info('Unknown error: ', err)
            logging.info('Sleep for 10 seconds')
            time.sleep(10)

    driver.close()

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def realtime_crawl_articles(args):
    # topics = load_topics()
    # divided_topics = chunks(topics, len(topics)//args.workers)
    urls = open('process_old_data/urls.txt').read().split('\n')
    divided_urls = chunks(urls, len(urls)//args.workers)

    pool = Pool(args.workers)
    pool.map(crawl_multiple_topics, divided_urls)
    pool.close()


if __name__ == '__main__':
    args = parse_args()
    print(args)

    realtime_crawl_articles(args)
    

