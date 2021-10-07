import pymongo 
from tqdm import tqdm
from bs4 import BeautifulSoup
import re

def text_from_html(body):
    soup = BeautifulSoup(body, 'html.parser')
    text = soup.get_text()
    text = re.sub("\s+", " ", text)
    return text.strip()

mongodb = pymongo.MongoClient(host='localhost:27018')
DATABASE_USERNAME = "admin"
DATABASE_PASSWORD = "admin"
mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

db = mongodb['article_db']['articles']

for article in tqdm(
    db.find({'source': 'vnexpress'}, no_cursor_timeout=True),
    total=db.find({'source': 'vnexpress'}).count()
    ):
    topics = article['topics']
    first_topic = article['first_topic']

    if first_topic is None:
        print(article['url'])
        continue
        
    #     break

    if '<a' in first_topic:
        first_topic = text_from_html(first_topic)

    topics = [text_from_html(html) for html in topics]

    db.update({
        '_id': article['_id']
    }, {
        '$set': {
            'topics': topics,
            'first_topic': first_topic
        }
    })
