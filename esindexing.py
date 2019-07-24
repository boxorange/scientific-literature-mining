
"""
@author: ahass

INSTRUCTIONS:

before running -- make sure elasticsearch is running on command line

index_folder relies on two functions (extract_data, index_file) to properly index 
every json file found inside a given folder into the elasticsearch database

simply run the index_folder function with your index name and folder path
(use double-slash '\\' when providing path)

ex: index_folder('test1', 'C:\\Users\\ahass\\sample-data')
"""

import glob, os, json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from time import time

es = Elasticsearch([{'host':'localhost', 'port':9200}]) # connect to cluster

def extract_data(file, *args):
    """
    reformats json file to "uid", "publisher", "type", "title", "year", "author", 
    "abstract", and "body_text"
    """
    with open(file) as json_file:   
        json_file = json.load(json_file) # load json as a dictionary obj
    
    for arg in args:
        aggregated = ''
        
        for feature in json_file[arg]:
            aggregated += feature["sent"] + ' '
            del feature
        
        json_file[arg] = aggregated
        
    del json_file["figure_caption"]
    del json_file["xas_info"]
    
    return json_file
    
def index_folder(index, path):
    """
    loads entire folder with given index name 
    """
    for f in glob.glob(os.path.join(path, '*.json')):
        data = extract_data(f, 'abstract', 'body_text')
                
        yield{
                '_index': index,
                '_source': data
                }
        
def search(index_name, searchstr):
    """
    searches for word in database with specified index 
    """
    res = es.search(index=index_name, body={"query": {"multi_match": {"query": searchstr, "fields": ["uid", "publisher", "type", "title", "year", "author", "keywords", "abstract"]}}, "highlight":{"fields":{"content":{}}}})
    results = []
    
    print("%d documents found: " % res['hits']['total']['value'])
    for doc in res['hits']['hits']:
        # print('%s) %s' % (doc['_id'], doc['_source']['title']))
        # print(doc)
        elem = []
        elem.append(doc['_source']['title'])
        elem.append(doc['_source']['abstract'])
        results.append(elem)
        
    return results

# search('index1', 'The K-edge photoabsorption spectra of')
# extract_data('C:\\Users\\ahass\\sample-data\\S0022024897008221.json', 'body_text')
t = time()
bulk(es, index_folder('index1', 'D:\\SULI\\Elsevier\\articles'), max_chunk_bytes=1024)
print('sec it took: ' + str(time()-t))
"""
def time_analysis(*intervals):
    initial = time()
    for i in range(intervals): # ex. append time when 10000 documents are indexed
        bulk(es, index_folder('index1', 'D:\\SULI\\Elsevier\\articles'), max_chunk_bytes=i)
        print('max_chunk_bytes=' + str(i) + ' index time: ' + str(time()-initial))
    #elapsed_time = time() - initial
    #1024
    # print('operation took ' + str(elapsed_time) + ' seconds (' + str(elapsed_time/60) + ' minutes)')

time_analysis(5000)
"""