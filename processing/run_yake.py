import yake
import pandas as pd
import re
import time
from collections import Counter

def multidocs_extraction(docs_phrase, threshold, records):
    res = Counter(docs_phrase)
    select = []
    for k,v in res.items():
        if k not in records and v >= threshold:
            print('Found Key Phrase:', k)
            select.append(k)
    return select

if __name__ =='__main__':
    time_start = time.time()
    # Get vocab
    vocab_add =['Methamphetamine',',', ';', ':']
    with open('./data/vocab_oov_full.txt', 'r') as f:
        vocab_oov = [word.strip() for word in f] #if word not in remove_vocab]
    with open('./data/Viet74K.txt', 'r') as f:
        vocab_vi = [word.strip() for word in f] #if word not in remove_vocab]
    vocab = vocab_oov + vocab_vi + vocab_add

    # Get Data
    df = pd.read_csv('./data/test.csv', nrows= 20,sep = ';')
    data = df['content']
    print(data)

    # Configuration
    language = "vi"
    max_ngram_size = 10
    deduplication_thresold = 0.5
    deduplication_algo = 'seqm'
    windowSize = 1
    numOfKeywords = 200
    threshold = 5
    doc_id = 0
    docs_phrase = []
    results=[]
    records= []
    for doc in data:
        try:
            doc_id += 1
            #print(doc)
            doc = doc.split("\n",4)[4]
            doc= re.sub(r"\n|\r", "", doc)
            doc = re.sub(' +','. ',doc)
            #print(doc)
            custom_kw_extractor = yake.KeywordExtractor(lan=language, n=max_ngram_size, dedupLim=deduplication_thresold, dedupFunc=deduplication_algo, windowsSize=windowSize, top=numOfKeywords, features=None)
            keyphrase = custom_kw_extractor.extract_keywords(doc, vocab)

            print("------Top %d phrases of doc_id %d are follows------:"%(numOfKeywords, doc_id))
            for k,v in keyphrase:
                if len(k.split()) > 2:
                    print(k)
                    docs_phrase.append(k)
            # Extract phrase across multi documents:
        except:
            pass
    if doc_id%50==0:
        print('----- Keyphrases on %d documents -----'%doc_id)
    result = []
    result = multidocs_extraction(docs_phrase, threshold, records)
    # using list comprehension to perform task

    #print('-'*50)
    with open('./results/keyphrases_extractions_test.txt', 'a+', encoding='utf8') as f:
        f.write('----- Calculate on %d documents -----\n'%doc_id)
        
    for k in result:
        f.write("{}\n".format(k))
        records.append(k)

    print('Time comletation (m):', (time.time() - time_start)/60)