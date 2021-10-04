from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='thoi-su')
    args = parser.parse_args()
    return args

URL = "http://cafef.vn"
URL_page = "https://cafef.vn/timeline/{}/trang-{}.chn"

def load_topics():
    topics = open('cafef_topics.txt').read().split('\n')
    topic2id = {}
    for topic in topics:
        topic, id = topic.split(',')
        topic2id[topic] = id
    return topic2id

def crawl_topic(topic, max_page=100):
    
    old_page_urls = set()

    for page in tqdm(range(1, max_page), desc="Crawling"):
        request_url = URL_page.format(topic2id[topic], page)
        driver.get(request_url)

        # crawl article urls
        item_news = driver.find_elements_by_css_selector('.tlitem')
        new_page_urls = set()

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
            new_page_urls.add(url)

            # if n_found urls == len(item_news) -> no new items -> last page -> break
            record = db.find_one({'url': url})
            if record is not None:
                continue

            title = title_elm.get_attribute('title')

            try:
                time_elm = item_new.find_element_by_css_selector('.knswli-right .time')
                post_time = time_elm.get_attribute('title')
            except:
                post_time = ''

            data = {
                'topic': topic,
                'title': title,
                'url': url,
                'post_time': post_time
            }
            db.insert_one(data)
        
        # if len(old_page_urls) > 0 and len(new_page_urls.intersection(old_page_urls)) == len(new_page_urls):
        #     print('All items in pages have been crawler => last page => break')
        #     break
        # else:
        #     old_page_urls = new_page_urls


if __name__ == '__main__':
    args = parse_args()
    print(args)

    mongodb = MongoClient()
    articles_db = mongodb['articles']
    db = articles_db['cafef']

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(
        executable_path='./chromedriver.exe',
        chrome_options=chrome_options
    )

    topic2id = load_topics()
    topics = topic2id.keys()

    for topic in topics:
        print(f'Crawl topic {topic}')
        crawl_topic(topic, max_page=1000)
