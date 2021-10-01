from pymongo import MongoClient

DATABASE_USERNAME = "admin"
DATABASE_PASSWORD = "admin"

mongodb = MongoClient()
print(mongodb)

# mongodb.admin.authenticate(DATABASE_USERNAME, DATABASE_PASSWORD)

articles_db = mongodb.article_db

coll = articles_db.dataset
