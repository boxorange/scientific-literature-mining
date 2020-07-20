"""
@author: ahass

INSTRUCTIONS:

before running -- make sure elasticsearch is running on command line

index_folder relies on two functions (extract_data, index_file) to properly index 
every json file found inside a given folder into the elasticsearch database

simply run the index_folder function with your index name and folder path
ex: index_folder('test1', path/to/data)
"""

import sys
import glob, os, json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from time import time

es = Elasticsearch([{'host':'localhost', 'port':9200}]) # connect to cluster


def append_fields(doc, field, result, elem):
	if field in doc['highlight']:
		for line in doc['highlight'][field]:
			elem.append(line)
	else:
		elem.append(doc['_source'][field])

	return elem


def es_search(searchstr, index_name='springer_idx'):
	"""
	searches for word in database with specified index 
	highlights terms and returns a 2D array 
	format ) results = [[title, abstract, relevant field 1, relevant field 2, ...]]
	"""
	res = es.search(index=index_name, body={"query": {
													"multi_match": {
																	"query": searchstr, 
																	"fields": ["title", "abstract"]
																}
													#"multi_match": {
													#				"query": searchstr, 
													#				"fields": ["uid", "publisher", "type", "title", "year", "author", "keywords", "abstract", "body_text"]
													#			}
													}, 
											"highlight":{
												#"order": "score",
												#"fields":{"*":{}}
												"fields": {
														"abstract": {
															"number_of_fragments" : 0,
															#"fragment_size": 150,
															#"boundary_max_size": 100,
															#"boundary_chars": "\n",
															#"boundary_scanner": 
															"type": "unified"
														  }
														#"content": {
														#	"matched_fields": ["content", "content.plain"],
														#	"type" : "fvh"
														}#		
												},										
											"size": 1000})
	results = []
	total_articles = res['hits']['total']['value']

	print("%d documents found: " % res['hits']['total']['value'])

	for doc in res['hits']['hits']:
		elem = []
		for field in doc['highlight']:
			temp_elem = append_fields(doc, 'title', results, elem)
			temp_elem.append(doc['_source']['uid'])
			#temp_elem2 = append_fields(doc, 'abstract', results, temp_elem)
			temp_elem2 = append_fields(doc, 'uid', results, temp_elem)
			
			print(doc['_source']['uid'])
			
			if field != 'title' or field != 'abstract': # add other lines
				for line in doc['highlight'][field]:
				
					print(line)
					input('enter')
					
					temp_elem2.append(line)
					
		results.append(temp_elem2)

	return results, total_articles


def extract_data(file, *args):
	"""
	reformats json file to "uid", "publisher", "type", "title", "year", "author", "abstract", and "body_text"
	
	Note: 
		[GP] changed type of 'aggregated' from string to list to display only sentences having a query - 08/09/2019
		[GP] added figure captions. - 07/12/2020
	"""
	with open(file) as json_file:   
		json_file = json.load(json_file) # load json as a dictionary obj
	
	# change string to list since ES splits string to chars. e.g., "Advances..." -> "A", "d", "v",... 07/12/2020
	json_file['title'] = [json_file['title']]
	
	for arg in args:
		aggregated = []
		for feature in json_file[arg]:
			if arg == 'title':
				aggregated.append(feature)
			if arg == 'abstract' or arg == 'body_text':
				aggregated.append(feature["sent"])
			elif arg == 'figures':
				for ele in feature["caption"]:
					aggregated.append(ele["sent"])
			del feature

		json_file[arg] = aggregated
	
	#if "figures" in json_file:
	#	del json_file["figures"]
	if "xas_info" in json_file:
		del json_file["xas_info"]

	return json_file
	
	
def index_folder(index, paths):
	"""
	loads entire folder with given index name 
	
	Note: 
		[GP] added 'title' to change it to a list because ES highlight causes an error when it deals with a string type. - 08/09/2019
		[GP] added figure captions. - 07/12/2020
	"""
	for path in paths:
		#for f in glob.glob(os.path.join(path, '*.json')):
		for root, dirs, files in os.walk(path):
			for file in files:
				if file.endswith(".json"):
					# Ignore downloaded json files, and only use a generated json which has the same name of an original article.
					if 'IOP_JSON' not in path:
						if (os.path.exists(os.path.join(root, file.replace(".json", ".xml"))) or \
							os.path.exists(os.path.join(root, file.replace(".json", ".nxml"))) or \
							os.path.exists(os.path.join(root, file.replace(".json", ".html")))):
							pass
						else:
							print('downloaded json:', os.path.join(root, file))
							continue

					print(file)
					
					if 'IOP_JSON' in path:
						data = extract_data(os.path.join(root, file), 'title', 'abstract', 'body_text')
					else:
						data = extract_data(os.path.join(root, file), 'title', 'abstract', 'body_text', 'figures')

					yield {
						'_index': index,
						'_source': data
					}


def create_index(index_name, paths):
	"""
	Ref: https://github.com/elastic/elasticsearch-py/issues/451
	"""
	t = time()
	
	'''
	Disable date detection to avoid the following error. - 7/12/2020 
	'status': 400, 'error': {'type': 'illegal_argument_exception', 'reason': 'mapper [body_text] of different type, current_type [date], merged_type [text]'}
	'''
	request_body = {
			"mappings" : {
				"date_detection" : False
			}
		}
			
	if es.indices.exists(index_name):
		sys.exit(index_name + ' already exists!!')
	else:
		es.indices.create(index=index_name, body=request_body, request_timeout=30)

	bulk(es, index_folder(index_name, paths), max_chunk_bytes=1024)
	
	print('sec it took: ' + str(time()-t))

	
def main():
	paths = []
	'''
	paths.append("/home/gpark/corpus_web/tdm/archive/IOP_JSON")
	paths.append("/home/gpark/corpus_web/tdm/archive/AAAS")
	paths.append("/home/gpark/corpus_web/tdm/archive/Elsevier")
	paths.append("/home/gpark/corpus_web/tdm/archive/Springer")
	paths.append("/home/gpark/corpus_web/tdm/archive/RSC")
	paths.append("/home/gpark/corpus_web/tdm/archive/PMC")
	'''
	paths.append("/home/gpark/corpus_web/tdm/archive/tmp")

	index_name = 'test_index'
	
	create_index(index_name, paths)

	#es_search('gold')
	# extract_data('C:\\Users\\ahass\\sample-data\\S0022024897008221.json', 'body_text')

	
if __name__ == "__main__":
	main()
	


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


''' deprecated
# search('index1', 'The K-edge photoabsorption spectra of')
def search(index_name, searchstr):
	"""
	searches for word in database with specified index 
	"""
	res = es.search(index=index_name, 
					body={"query": 
								{"multi_match": 
									{"query": searchstr, 
									"fields": ["uid", "publisher", "type", "title", "year", "author", "keywords", "abstract"]}}, 
									"highlight":
										{"fields":
											{"content":{}}
										}
						})
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
'''