from elasticsearch import Elasticsearch

es = Elasticsearch()

res = es.search(
    index="article_keywords", 
    doc_type='article_keywords', 
    body={
        "query": {
            "bool": {
                "must_not": {
                    "exists": {
                        "field": "keywords"
                    }
                }
            }
        }
    },size=10000
    )

res = res['hits']['hits']
print(len(res))

if len(res) > 0:
    for old_record in res:
        try:
            r = es.delete(
                index="article_keywords",
                doc_type="article_keywords",
                id=old_record['_id'])
            # print(r)
        except Exception as err:
            print(err)



# res = es.search()
# {
#     "query": {
#         "bool": {
#             "must_not": {
#                 "exists": {
#                     "field": "scholarship"
#                 }
#             }
#         }
#     }
# }