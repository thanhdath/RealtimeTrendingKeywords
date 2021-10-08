
# import time
# from datetime import date, datetime, timedelta, timezone
# from elasticsearch import Elasticsearch
# import json
# from datetime import timezone
# import calendar

# es = Elasticsearch()

# KEYWORDS = ["covid-19", "việt nam", "messi", "mỹ", "facebook", "phi nhung", "taliban", 'vaccine']

# to_date = datetime(2021, 10, 9).date()
# from_date = datetime(2021, 9, 1).date()


# res = es.search(
#     index='trending_24h',
#     query={
#         "bool": {
#             "must": [
#                 {
#                     "range": {
#                         "time": {
#                             "gte": from_date.strftime('%Y/%m/%d'),
#                             "lte": to_date.strftime('%Y/%m/%d')
#                         }
#                     }
#                 }
#             ]
#         }
#     },
#     size=10000,
#     sort={
#         "time": {
#             "order": "desc"
#         }
#     }
# )

# res = res['hits']['hits']

# data = []
# for row in res:
#     data.append(row['_source'])

# import json
# with open('export.json', 'w+') as fp:
#     fp.write(json.dumps(data))




import json
data = json.loads(open('export.json').read())

KEYWORDS = ["covid-19", "việt nam", "messi", "mỹ", "facebook", "phi nhung", "taliban", 'vaccine']


