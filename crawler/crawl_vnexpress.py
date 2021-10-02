from selenium import webdriver
from pymongo import MongoClient
from tqdm import tqdm
import re
import argparse
import selenium
import time
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import datetime

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='tin-tuc-24h')
    args = parser.parse_args()
    return args

SOURCE = 'vnexpress'
URL = "http://vnexpress.net"
TIME_TO_REFRESH = 60

def convert_string_to_local_timestamp(str_datetime):
    return time.mktime(datetime.datetime.strptime(str_datetime, "%Y-%m-%d %H:%M:%S").timetuple())

def crawl_newest_article_urls(driver, max_look_back=3):
    old_page_urls = set()
    all_newest_urls = set()

    for page in tqdm(range(1, max_look_back), desc="Crawling"):
        request_url = f"{URL}/tin-tuc-24h-p{page}"
        driver.get(request_url)

        # crawl article urls
        item_news = driver.find_elements_by_css_selector('.item-news')
        new_page_urls = set()

        for item_new in item_news:
            try:
                title_elm = item_new.find_element_by_css_selector('.title-news > a')
            except Exception as err:
                print(err)
                continue
        
            url = title_elm.get_attribute('href')
            if not re.match(r"https://vnexpress\.net/.+", url):
                continue

            record = db.find_one({'url': url})
            if record is not None:
                continue
            new_page_urls.add(url)

            title = title_elm.get_attribute('title')

            # get published datetime
            published_timestamp = None
            published_time = None
            try:
                published_time = item_new.find_element_by_css_selector('.time-count > span')
                published_time = published_time.get_attribute('datetime')
                published_timestamp = convert_string_to_local_timestamp(published_time)
            except Exception as err:
                print('Error get pusblished time', err)
                continue

            data = {
                'topic': topic,
                'title': title,
                'url': url,
                'n_comments': 0,
                'published_time': published_time,
                'published_timestamp': published_timestamp
            }
            db.insert_one(data)
            # print(data)
        # if n_found urls == len(item_news) -> no new items -> last page -> break
        if len(old_page_urls) > 0 and len(new_page_urls.intersection(old_page_urls)) == len(new_page_urls):
            print('All items in pages have been crawler => last page => break')
            break
        else:
            old_page_urls = new_page_urls

        all_newest_urls = all_newest_urls.union(new_page_urls)
    
    return all_newest_urls

def crawl_article(driver: webdriver.Chrome, url: str):
    try:
        driver.get(url)
    except selenium.common.exceptions.TimeoutException as err:
        print(err)
        time.sleep(10)
    # time.sleep(2)

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

    for i in range(5):
        tag_elms = driver.find_elements_by_css_selector('.tags .item-tag a')
        # print(len(tag_elms))
        if len(tag_elms) > 0:
            break
        else:
            time.sleep(1)
    try:
        tags = [x.get_attribute('innerHTML') for x in tag_elms]
    except selenium.common.exceptions.StaleElementReferenceException as err:
        time.sleep(0.5)
        try:
            tags = [x.get_attribute('innerHTML') for x in tag_elms]
        except:
            tags = []
            print('error tags')

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
        'source': SOURCE,
        'title': title,
        'description': desc,
        'content_html': content_html, 
        'tags': tags,
        'url': url,
        'topics': topics,
        'first_topic': first_topic,

        'keywords_extracted': False # temporal added
    }

    article_record = db.find_one({'url': url})
    print(article_record)
    if article_record is None:
        db.insert_one(data)
    else:
        db.update({'url': url}, {'$set': data})

def crawl_newest_articles(driver, max_look_back=3):

    while True:
        try:
            all_newest_urls = crawl_newest_article_urls(driver, max_look_back)

            for url in all_newest_urls:
                crawl_article(driver, url)
        except:
            continue
        time.sleep(TIME_TO_REFRESH)


if __name__ == '__main__':
    args = parse_args()
    print(args)
    DATABASE_USERNAME = "admin"
    DATABASE_PASSWORD = "admin"

    # mongodb = MongoClient()
    mongodb = MongoClient(host="mongodb")
    mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

    articles_db = mongodb['article_db']
    db = articles_db['articles']


    ########################################################
    ###### Selenium in machine
    ########################################################
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = r"C:\Program Files (x86)\Google\Chrome Beta\Application\chrome.exe"

    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(
        executable_path='../chromedriver.exe',
        chrome_options=chrome_options
    )
    """
    ########################################################
    ###### Selenium in docker
    ########################################################
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')

    # driver = webdriver.Remote("http://localhost:4444/wd/hub",options=chrome_options)
    driver = webdriver.Remote("http://selenium:4444/wd/hub",options=chrome_options)

    topic = args.topic

    # create index for fast query
    db.create_index([('published_timestamp', 1)])
    db.create_index([('keywords_extracted', 1)])

    print(f"Crawl topic {topic}")
    crawl_newest_articles(driver, max_look_back=3)
