
# Can process in local machine (laptop)
mongorestore -u admin -p admin --host localhost:27018 --authenticationDatabase admin --gzip --archive=articles.gz --db articles

# process old data and import to mongo docker
conda activate .env-crawler-ubuntu/
python crawler/process_old_data.py

# delete temporal data in mongo docker
docker exec -it mongodb mongo -u admin -p admin
use articles
db.dropDatabase()

mongodump -u admin -p admin --host localhost:27018 --authenticationDatabase admin --gzip --archive=article_db.gz --db article_db
# send article_db.gz to server -> mongorestore to mongodocker


# server
docker exec -it mongodb mongorestore -u admin -p admin --host localhost:27017 --authenticationDatabase admin --gzip --archive=/article_db_with_keywords.gz --nsInclude article_db

