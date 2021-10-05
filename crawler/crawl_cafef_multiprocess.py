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

#logging.basicConfig(filename='log.log',
    # filemode='a',
    # format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    # datefmt='%H:%M:%S',
    # level=#logging.DEBUG)

CHROME_DRIVER_PATH = './chromedriver.exe'
INTERVAL_CHECK_NEW_ARTICLES = 120
URL = "http://cafef.vn"
URL_page = "https://cafef.vn/timeline/{}/trang-{}.chn"


def parse_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--topic', default='kinh-doanh')
    parser.add_argument('--workers', default=2, type=int)
    parser.add_argument('--n-page-lookback', default=20, type=int)
    args = parser.parse_args()
    return args

def convert_string_to_local_timestamp(str_datetime):
    """
    str_datetime 03-10-2021 - 22:46 PM
    """
    return time.mktime(datetime.datetime.strptime(str_datetime, "%d-%m-%Y - %H:%M %p").timetuple())

def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text()
    text = re.sub("\s+", " ", text)
    return text.strip()

def crawl_article(db, driver: webdriver.Chrome, url: str):
    if "https://cafef.vn/" not in url:
        url = f"https://cafef.vn/{url}"

    try:
        driver.get(url)
    except Exception as err:
        print(f'error get url {url}\n{err}')
        time.sleep(5)

    try:
        title_elm = driver.find_element_by_css_selector('h1.title')
        title = title_elm.get_attribute('innerHTML')
    except Exception as err:
        print(f'err title {url}\n{err}')
        title = ''

    desc = None
    for i in range(5):
        try:
            desc_elm = driver.find_element_by_css_selector('h2.sapo')
            desc = desc_elm.get_attribute('innerHTML')
            break
        except Exception as err:
            time.sleep(1)
    if desc is None:
        print(f'err desc {url}\n{err}')
        desc = ''

    try:
        content_elm = driver.find_element_by_css_selector('#mainContent')
        content_html = content_elm.get_attribute('innerHTML')
    except Exception as err:
        print(f'err content {url}\n{err}')
        content_html = ''

    published_timestamp = None
    published_time = None
    try:
        published_time = driver.find_element_by_css_selector('.pdate')
        published_time = published_time.get_attribute('innerHTML').strip()
        published_timestamp = convert_string_to_local_timestamp(published_time)
    except Exception as err:
        print(f'err datetime {url}\n{err}')

    try:
        topic_elm = driver.find_element_by_css_selector('.cat')
        topic = topic_elm.get_attribute('innerHTML')
    except Exception as err:
        print(f'err content {url}\n{err}')
        topic = ''

    data = {
        'crawled': True,
        'source': 'cafef',
        'title': title,
        'description': desc,
        'content_html': content_html, 
        'first_topic': topic,
        # 'tags': [],
        'url': url,
        'published_time': published_time,
        'published_timestamp': published_timestamp,

        'keywords_extracted': False # temporal added
    }

    article_record = db.find_one({'url': url})
    if article_record is None:
        db.insert_one(data)
    else:
        db.update({'url': url}, {'$set': data})
    return data

def crawl_newest_urls(db, driver, topic, topic2id, max_page=4, threshold_exists_url=8):
    n_exists_url = 0
    all_newest_urls = set()

    for page in tqdm(range(1, max_page), desc="Crawling"):
        request_url = URL_page.format(topic2id[topic], page)
        driver.get(request_url)

        # crawl article urls
        item_news = driver.find_elements_by_css_selector('.tlitem')

        if len(item_news) == 0:
            print('No more item news => break')
            break

        for item_new in item_news:
            try:
                title_elm = item_new.find_element_by_css_selector('h3 > a')
            except Exception as err:
                print(err)
                continue
        
            url = title_elm.get_attribute('href')

            record = db.find_one({'url': url})
            if record is not None:
                n_exists_url += 1
                if n_exists_url > threshold_exists_url:
                    break
                continue
            else:
                all_newest_urls.add(url)

            # title = title_elm.get_attribute('title')

            # try:
            #     time_elm = item_new.find_element_by_css_selector('.knswli-right .time')
            #     post_time = time_elm.get_attribute('title')
            # except:
            #     post_time = ''

            # data = {
            #     'topic': topic,
            #     'title': title,
            #     'url': url,
            #     'post_time': post_time
            # }

        if n_exists_url > threshold_exists_url:
            break
    return all_newest_urls

def crawl_newest_articles(db, rabitmq_channel, driver, topic, topic2id, max_page=4, threshold_exists_url=8):
    new_urls = crawl_newest_urls(db, driver, topic, topic2id, max_page=max_page, threshold_exists_url=threshold_exists_url)

    for url in new_urls:
        data = crawl_article(db, driver, url)
        if data is not None:
            send_data = {
                '_id': str(data['_id']),
                'source': data['source'],
                'title': data['title'],
                'description': data['description'],
                'content_html': data['content_html'], 
                'first_topic': data['first_topic'],
                'url': data['url'],
                'published_time': data['published_time'],
                'published_timestamp': data['published_timestamp'],
            }

            rabitmq_channel.basic_publish(
                exchange='',
                routing_key='articles',
                body=json.dumps(send_data)
            )

def load_topics():
    topics = open('url/cafef_topics.txt').read().split('\n')
    topic2id = {}
    for topic in topics:
        topic, id = topic.split(',')
        topic2id[topic] = id
    return topic2id

def crawl_multiple_topics(params):
    log_fp = open('log.log', 'w+')
    topic_list, n_page_lookback = params

    print(topic_list)
    #logging.info(topic_list)
    # log_fp.write(topic_list)

    topic2id = load_topics()
    # mongodb = MongoClient()
    mongodb = MongoClient(host="mongodb")
    DATABASE_USERNAME = "admin"
    DATABASE_PASSWORD = "admin"
    mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

    articles_db = mongodb['article_db']
    db = articles_db['articles']
    db.create_index([('crawled', 1)])
    db.create_index([('url', 1)])
    db.create_index([('topic', 1)])

    # connect to rabitmq to send data to processing machine
    print('connecting to rabbitmq')
    #logging.info('trying to connect to rabbitmq')
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
            break
        except Exception as err:
            print('connect error. try again in 5 seconds.')
            time.sleep(5)
    channel = connection.channel()
    channel.queue_declare(queue='articles')
    
    print('done connection')
    #logging.info('done connection')

    # init chrome
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    # driver = webdriver.Chrome(
    #     executable_path=CHROME_DRIVER_PATH,
    #     chrome_options=chrome_options
    # )
    instance_name = '_'.join(topic_list).replace(' ', '-')
    driver = webdriver.Remote(
        "http://selenium:4444/wd/hub",
        # desired_capabilities={
        #     "browserName": "chrome",
        #     'name': instance_name,
        #     'video': False
        # },
        options=chrome_options
    )

    while True:
        for topic in topic_list:
            crawl_newest_articles(db, channel, driver, topic, topic2id, max_page=n_page_lookback)

        print(f'sleeping for {INTERVAL_CHECK_NEW_ARTICLES}s')
        #logging.info(f'sleeping for {INTERVAL_CHECK_NEW_ARTICLES}s')
        time.sleep(INTERVAL_CHECK_NEW_ARTICLES)

    driver.close()
    connection.close()

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def realtime_crawl_articles(args):
    topic2id = load_topics()
    topics = list(topic2id.keys())
    divided_topics = chunks(topics, len(topics)//args.workers)

    print(f'Init pool with {args.workers} workers.')
    #logging.info(f'Init pool with {args.workers} workers.')
    pool = Pool(args.workers)
    pool.map(crawl_multiple_topics, [(topics, args.n_page_lookback) for topics in divided_topics])
    pool.close()


if __name__ == '__main__':
    args = parse_args()
    print(args)

    realtime_crawl_articles(args)
    

