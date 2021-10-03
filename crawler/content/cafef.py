from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse
import time
from multiprocessing import Pool

def parse_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--topic', default='kinh-doanh')
    parser.add_argument('--workers', default=4, type=int)
    args = parser.parse_args()
    return args

def crawl_article(db, driver: webdriver.Chrome, url: str):
    if "https://cafef.vn/" not in url:
        url = f"https://cafef.vn/{url}"

    print(url)
    driver.get(url)
    time.sleep(0.5)

    try:
        title_elm = driver.find_element_by_css_selector('h1.title')
        title = title_elm.get_attribute('innerHTML')
    except Exception as err:
        print('err title', err)
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
        print('err desc')
        desc = ''
    
    # try:
    #     share_elm = driver.find_element_by_css_selector('.kbwcs-number')
    #     share_count = share_elm.get_attribute('innerHTML')
    # except Exception as err:
    #     print('err share', err)
    #     share_count = 0

    # try:
    #     like_frame_elm = None
    #     for i in range(5):
    #         try:
    #             like_frame_elm = driver.find_element_by_tag_name(".fb-like > span > iframe")
    #             break
    #         except Exception as err:
    #             time.sleep(1)

    #     if like_frame_elm is not None:  
    #         driver.switch_to.frame(like_frame_elm)
    #         like_elm = driver.find_element_by_css_selector('#u_0_3')
    #         like_count = like_elm.get_attribute('innerHTML')
    #         driver.switch_to.default_content()
    #     else:
    #         like_count = None
    # except Exception as err:
    #     print('err like', err)
    #     like_count = 0

    try:
        content_elm = driver.find_element_by_css_selector('#mainContent')
        content_html = content_elm.get_attribute('innerHTML')
    except Exception as err:
        print('err content', err)
        content_html = ''

    try:
        tag_elms = driver.find_elements_by_css_selector('.tagdetail > .row2 > a')
        tags = [x.get_attribute('innerHTML') for x in tag_elms]
    except selenium.common.exceptions.StaleElementReferenceException as err:
        time.sleep(0.5)
        try:
            tag_elms = driver.find_elements_by_css_selector('.tagdetail > .row2 > a')
            tags = [x.get_attribute('innerHTML') for x in tag_elms]
        except:
            tags = []
            print('error tags')
    
    data = {
        'title': title,
        'description': desc,
        'content_html': content_html, 
        'tags': tags,
        'url': url,
        # 'share_count': share_count,
        # 'like_count': like_count
    }

    article_record = db.find_one({'url': url})
    if article_record is None:
        db.insert_one(data)
    else:
        db.update({'url': url}, {'$set': data})

def crawl_urls(db, driver, topic):
    # import pdb; pdb.set_trace()
    articles = db.find({'topic': topic, 'content_html': {'$exists': False}})
    for article in tqdm(articles, desc="Crawling articles"):
        url = article['url']
        crawl_article(db, driver, url)

def load_topics():
    topics = open('url/cafef_topics.txt').read().split('\n')
    topic2id = {}
    for topic in topics:
        topic, id = topic.split(',')
        topic2id[topic] = id
    return topic2id

def crawl_multiple_topics(topic_list):
    print(topic_list)
    mongodb = MongoClient()
    articles_db = mongodb['articles']
    db = articles_db['cafef']

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(
        executable_path='./chromedriver',
        chrome_options=chrome_options
    )

    for topic in topic_list:
        crawl_urls(db, driver, topic)

    driver.close()

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

if __name__ == '__main__':
    args = parse_args()
    print(args)

    topic2id = load_topics()
    topics = list(topic2id.keys())

    divided_topics = chunks(topics, len(topics)//args.workers)
    pool = Pool(args.workers)
    pool.map(crawl_multiple_topics, divided_topics)
    pool.close()

