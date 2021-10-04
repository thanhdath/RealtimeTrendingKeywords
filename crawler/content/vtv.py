from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse
import time

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='kinh-doanh')
    args = parser.parse_args()
    return args

def crawl_article(driver: webdriver.Chrome, url: str):
    driver.get(url)

    try:
        title_elm = driver.find_element_by_css_selector('.title_detail')
        title = title_elm.get_attribute('innerHTML')
    except Exception as err:
        print('err title', err)
        title = ''

    desc = None
    for i in range(5):
        try:
            desc_elm = driver.find_element_by_css_selector('h2.sapo')
            desc = desc_elm.get_attribute('innerHTML')
        except Exception as err:
            time.sleep(1)
    if desc is None:
        print('err desc')
        desc = ''

    try:
        content_elm = driver.find_element_by_css_selector('#entry-body')
        content_html = content_elm.get_attribute('innerHTML')
    except Exception as err:
        print('err content', err)
        content_html = ''

    try:
        tag_elms = driver.find_elements_by_css_selector('.news_keyword > a')
        tags = [x.get_attribute('innerHTML') for x in tag_elms]
    except selenium.common.exceptions.StaleElementReferenceException as err:
        time.sleep(0.5)
        try:
            tag_elms = driver.find_elements_by_css_selector('.news_keyword > a')
            tags = [x.get_attribute('innerHTML') for x in tag_elms]
        except:
            tags = []
            print('error tags')
    
    data = {
        'title': title,
        'description': desc,
        'content_html': content_html, 
        'tags': tags,
        'url': url
    }

    article_record = db.find_one({'url': url})
    if article_record is None:
        db.insert_one(data)
    else:
        db.update({'url': url}, {'$set': data})

def crawl_urls(topic):
    # import pdb; pdb.set_trace()
    articles = db.find({'topic': topic})
    for article in tqdm(articles, desc="Crawling articles"):
        url = article['url']
        crawl_article(driver, url)

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

    crawl_urls(args.topic)
