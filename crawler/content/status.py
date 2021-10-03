# check crawling status

import pymongo 

ARTICLE_LIST = ['cafef', 'vnexpress']

mongodb = pymongo.MongoClient()
articles_db = mongodb['articles']

for article in ARTICLE_LIST:
    db = articles_db[article]

    n_urls = db.count()
    n_crawled = db.find({'crawled': True}).count()
    n_found_content = db.find({'content_html': {'$exists': True}}).count()

    print(f"article {article}\n"
    f"number of urls: {n_urls}\n"
    f"number crawled: {n_crawled}\n"
    f"number has content: {n_found_content}\n")
