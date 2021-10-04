from pymongo import MongoClient
from tqdm import tqdm
import argparse
from urllib.request import urlopen
from bs4 import BeautifulSoup

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='articles')
    # parser.add_argument('--topic', default='kinh-doanh')
    args = parser.parse_args()
    return args


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

def convert_all_articles_to_text():
    articles = db.find({'content_html': {'$exists': True}})
    for article in tqdm(articles, total=articles.count()):
        # url = article['url']
        content_html = article['content_html']
        if content_html is not None:
            content = html2text(content_html)

            db.update_one({'_id': article['_id']},
                {'$set': {'content': content}})

if __name__ == '__main__':
    args = parse_args()
    print(args)
    DATABASE_USERNAME = "admin"
    DATABASE_PASSWORD = "admin"
    mongodb = MongoClient()
    mongodb.admin.authenticate( DATABASE_USERNAME , DATABASE_PASSWORD )

    articles_db = mongodb['article_db']
    db = articles_db[args.db]

    convert_all_articles_to_text()
