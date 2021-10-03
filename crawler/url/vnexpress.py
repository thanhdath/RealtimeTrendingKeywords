from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse
import datetime
import time

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='kinh-doanh')
    args = parser.parse_args()
    return args

URL = "http://vnexpress.net"

def load_topics():
    topics = open('vnexpress_topics.txt').read().split('\n')
    topics = [x.strip() for x in topics]
    return topics

def convert_string_to_local_timestamp(str_datetime):
    return time.mktime(datetime.datetime.strptime(str_datetime, "%Y-%m-%d %H:%M:%S").timetuple())

def crawl_topic(topic, max_page=100):
    
    old_page_urls = set()

    for page in tqdm(range(1, max_page), desc="Crawling"):
        request_url = f"{URL}/{topic}-p{page}"
        driver.get(request_url)
        time.sleep(0.5)

        # crawl article urls
        item_news = driver.find_elements_by_css_selector('.item-news')
        new_page_urls = set()

        for item_new in item_news:
            try:
                title_elm = item_new.find_element_by_css_selector('.title-news > a')
            except Exception as err:
                print('Error title', err)
                continue
        
            url = title_elm.get_attribute('href')
            if not re.match(r"https://vnexpress\.net/.+", url):
                continue
            new_page_urls.add(url)

            # if n_found urls == len(item_news) -> no new items -> last page -> break
            record = db.find_one({'url': url})
            if record is not None:
                continue

            title = title_elm.get_attribute('title')

            # try:
            #     comment = item_new.find_element_by_css_selector('.description .meta-news .count_cmt .font_icon')
            #     n_comments = comment.get_attribute('innerHTML').strip()
            #     if len(n_comments) == '':
            #         n_comments = 0
            #     else:
            #         n_comments = int(n_comments)
            # except Exception as err:
            #     print('Error comment', err)
            #     n_comments = 0

            # get published datetime
            # published_timestamp = None
            # published_time = None
            # try:
            #     published_time = item_new.find_element_by_css_selector('.time-count > span')
            #     published_time = published_time.get_attribute('datetime')
            #     published_timestamp = convert_string_to_local_timestamp(published_time)
            # except Exception as err:
            #     print('Error get pusblished time', err)
            #     continue

            data = {
                'topic': topic,
                'title': title,
                'url': url,
                # 'n_comments': n_comments,
                # 'published_time': published_time,
                # 'published_timestamp': published_timestamp
            }
            db.insert_one(data)
        
        if len(old_page_urls) > 0 and len(new_page_urls.intersection(old_page_urls)) == len(new_page_urls):
            print('All items in pages have been crawler => last page => break')
            break
        else:
            old_page_urls = new_page_urls


if __name__ == '__main__':
    args = parse_args()
    print(args)

    mongodb = MongoClient()
    articles_db = mongodb['articles']
    db = articles_db['vnexpress']

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(
        executable_path='./chromedriver.exe',
        chrome_options=chrome_options
    )

    # topic = args.topic

    topics = load_topics()

    for topic in topics:
        print(f"Crawl topic {topic}")
        crawl_topic(topic, max_page=300)
