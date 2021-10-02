from elasticsearch import Elasticsearch
from datetime import datetime
import time

es = Elasticsearch("http://localhost:9200")


resp = es.info()
print(resp)
for i in range(100):
    doc = {
        'author': 'kimchy',
        'text': 'Elasticsearch: cool. bonsai cool.',
        'timestamp': datetime.now(),
        "x" : i,
        "y" : i
    }
    res = es.index(index="test-index", id=i, body=doc)
    print(res['result'])
    time.sleep(10)

res = es.get(index="test-index", id=1)
print(res['_source'])

es.indices.refresh(index="test-index")

res = es.search(index="test-index", query={"match_all": {}})
# print("Got %d Hits:" % res['hits']['total']['value'])
for hit in res['hits']['hits']:
    print(hit["_source"])
    # print("%(timestamp)s %(author)s: %(text)s" % hit["_source"])