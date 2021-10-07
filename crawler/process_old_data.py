import pymongo
from tqdm import tqdm
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--old-host', default='localhost:27018')
parser.add_argument('--new-host', default='localhost:27018')
args = parser.parse_args()
print(args)

client_old = pymongo.MongoClient(host=args.old_host)
client_new = pymongo.MongoClient(host=args.new_host)
client_old.admin.authenticate( 'admin' , 'admin' )
client_new.admin.authenticate( 'admin' , 'admin' )

old_db = client_old['articles']
new_db = client_new['article_db']

batch_data = []
for article in tqdm(old_db['cafef'].find()):
    if 'published_timestamp' not in article: continue
    data = {
        'source': 'cafef',
        'title': article['title'],
        'description': article['description'],
        'content_html': article['content_html'],
        'url': article['url'],
        'first_topic': article['topic'],
        'published_time': article.get('published_time', None),
        'published_timestamp': article['published_timestamp']
    }
    batch_data.append(data)
    if len(batch_data) == 50:
        new_db['articles'].insert_many(batch_data)
        batch_data = []

if len(batch_data) > 0:    
    new_db['articles'].insert_many(batch_data)


batch_data = []
for article in tqdm(old_db['vnexpress'].find()):
    if 'published_timestamp' not in article: continue
    data = {
        'source': 'vnexpress',
        'title': article['title'],
        'description': article['description'],
        'content_html': article['content_html'],
        'url': article['url'],
        'topics': article['topics'],
        'first_topic': article['first_topic'],
        'published_time': article.get('published_time', None),
        'published_timestamp': article['published_timestamp']
    }
    batch_data.append(data)

    if len(batch_data) == 50:
        new_db['articles'].insert_many(batch_data)
        batch_data = []

if len(batch_data) > 0:    
    new_db['articles'].insert_many(batch_data)

new_db['articles'].create_index([('crawled', 1)])
new_db['articles'].create_index([('url', 1)])
new_db['articles'].create_index([('first_topic', 1)])

