from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse
import time
import datetime
from multiprocessing import Pool

def parse_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument('--topic', default='kinh-doanh')
    parser.add_argument('--workers', default=4, type=int)
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

def crawl_article(db, driver: webdriver.Chrome, url: str):
    try:
        driver.get(url)
    except Exception as err:
        print(err)
        time.sleep(10)
        return
    time.sleep(.5)

    try:
        title_elm = driver.find_element_by_css_selector('.title-detail')
        title = title_elm.get_attribute('innerHTML')
    except Exception as err:
        print('err title', err)
        title = ''

    try:
        desc_elm = driver.find_element_by_css_selector('.description')
        desc = desc_elm.get_attribute('innerHTML')
    except Exception as err:
        print('err desc', err)
        desc = ''

    try:
        content_elm = driver.find_element_by_css_selector('.fck_detail')
        content_html = content_elm.get_attribute('innerHTML')
        height = content_elm.size['height'] + content_elm.location['y']
        driver.execute_script(f"window.scrollTo(0, {height});")
    except Exception as err:
        print('err content', err)
        content_html = ''

    # get timestamp
    # get published datetime
    published_timestamp = None
    published_time = None
    try:
        published_time = driver.find_element_by_css_selector('.header-content > .date')
        published_time = published_time.get_attribute('innerHTML')
        published_timestamp = convert_string_to_local_timestamp(published_time)
    except Exception as err:
        print('Error get pusblished time', err)
        # return

    # for i in range(5):
    #     tag_elms = driver.find_elements_by_css_selector('.tags .item-tag a')
    #     # print(len(tag_elms))
    #     if len(tag_elms) > 0:
    #         break
    #     else:
    #         time.sleep(1)
    # try:
    #     tags = [x.get_attribute('innerHTML') for x in tag_elms]
    # except selenium.common.exceptions.StaleElementReferenceException as err:
    #     time.sleep(0.5)
    #     try:
    #         tags = [x.get_attribute('innerHTML') for x in tag_elms]
    #     except:
    #         tags = []
    #         print('error tags')

    # get topics
    try:
        topic_elms = driver.find_elements_by_css_selector('.breadcrumb > li')

        topics = [x.get_attribute('innerHTML') for x in topic_elms]
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
    print(article_record)
    if article_record is None:
        db.insert_one(data)
    else:
        db.update({'url': url}, {'$set': data})

def crawl_urls(db, driver, topic):
    # import pdb; pdb.set_trace()
    articles = db.find({'topic': topic, 'crawled': {'$ne': True}})
    for article in tqdm(articles, desc="Crawling articles"):
        url = article['url']
        if 'content_html' not in article:
            crawl_article(db, driver, url)

def load_topics():
    topics = open('url/vnexpress_topics.txt').read().split('\n')
    topics = [x.strip() for x in topics]
    return topics

def crawl_multiple_topics(topic_list):
    print(topic_list)
    mongodb = MongoClient()
    articles_db = mongodb['articles']
    db = articles_db['vnexpress']
    db.create_index([('crawled', 1)])

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument('--headless')
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

    topics = load_topics()

    divided_topics = chunks(topics, len(topics)//args.workers)
    pool = Pool(args.workers)
    pool.map(crawl_multiple_topics, divided_topics)
    pool.close()

