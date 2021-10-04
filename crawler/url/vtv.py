from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse
from datetime import datetime, timedelta

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='chinh-tri')
    args = parser.parse_args()
    return args

URL = "http://vtv.vn"
# URL_page = "https://vtv.vn/timeline/{}/trang-{}.htm"
URL_page = "https://vtv.vn/{}/xem-theo-ngay/{}-{}-{}/trang-{}.htm"
START_DATE = datetime(2015, 1, 1)
END_DATE = datetime.today()

"""
the-thao,
suc-khoe,
different format, can not crawl
"""

def load_topics():
    topics = open('url/vtv_topics.txt').read().split('\n')
    topic2id = {}
    for topic in topics:
        topic, id = topic.split(',')
        topic2id[topic] = id
    return topic2id

def crawl_topic(topic, max_page=100):
    
    old_page_urls = set()
    
    for day_delta in tqdm(list(range((END_DATE-START_DATE).days)), desc="crawling"):
        cur_date = END_DATE - timedelta(days=day_delta)
        for page in range(1, 20):
            request_url = URL_page.format(topic, cur_date.day, 
                cur_date.month, cur_date.year, page)
            driver.get(request_url)

            # crawl article urls
            item_news = driver.find_elements_by_css_selector('.tlitem')
            new_page_urls = set()

            if len(item_news) == 0:
                # print('No more item news => break')
                break

            for item_new in item_news:
                try:
                    title_elm = item_new.find_element_by_css_selector('h4 > a')
                except Exception as err:
                    print(err)
                    continue
            
                url = title_elm.get_attribute('href')
                new_page_urls.add(url)

                # if n_found urls == len(item_news) -> no new items -> last page -> break
                record = db.find_one({'url': url})
                if record is not None:
                    continue

                title = title_elm.get_attribute('title')

                try:
                    time_elm = item_new.find_element_by_css_selector('.time > span')
                    post_time = time_elm.get_attribute('innerHTML')
                except Exception as err:
                    print('error time', err)
                    post_time = ''

                data = {
                    'topic': topic,
                    'title': title,
                    'url': url,
                    'post_time': post_time
                }
                db.insert_one(data)


if __name__ == '__main__':
    args = parse_args()
    print(args)

    mongodb = MongoClient()
    articles_db = mongodb['articles']
    db = articles_db['vtv']

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(
        executable_path='./chromedriver',
        chrome_options=chrome_options
    )

    topic2id = load_topics()
    crawl_topic(args.topic, max_page=10000)
