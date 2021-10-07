import pymongo 
from tqdm import tqdm
from bs4 import BeautifulSoup
import re

def html2text(html, remove_elms=[]):
    soup = BeautifulSoup(html, features="html.parser")

    for elm in remove_elms:
        soup.select(elm).decompose()

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract()    # rip it out

    # get text
    text = soup.get_text(separator="\n")
    return text


mongodb = pymongo.MongoClient(host='localhost:27018')
DATABASE_USERNAME = "admin"
DATABASE_PASSWORD = "admin"
mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

db = mongodb['article_db']['articles']
outfp = open('process_old_data/urls.txt', 'w+')

for article in tqdm(
    db.find({
        'source': 'vnexpress', 
        'keywords_extracted': False
    }, no_cursor_timeout=True),
    total=db.find({'source': 'vnexpress'}).count()
    ):

    content_html = article['content_html']
    text = html2text(content_html).strip()

    if len(text) == 0:
        outfp.write(article['url'] + '\n')
           