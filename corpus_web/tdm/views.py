import os, glob, json
from django.shortcuts import get_object_or_404, render
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
#from .models import Article
#from .scraper import downloader, parser
#from .scraper.downloader import Downloader
#from .scraper.parser import Parser


es = Elasticsearch([{'host':'localhost', 'port':9200}]) # connect to cluster

'''
def append_fields(doc, field, result, elem):
	if field in doc['highlight']:
		for line in doc['highlight'][field]:
			elem.append(line)
	else:
		elem.append(doc['_source'][field])

	return elem
'''

def es_search(search_str, search_type, operator, index_name='tdm_index_2'):
	"""
	searches for word in database with specified index 
	highlights terms and returns a 2D array 
	format ) results = [[title, abstract, relevant field 1, relevant field 2, ...]]
	
	Note: 
		[GP] - "number_of_fragments" set to zero so that complete sentences are displayed. - 08/09/2019
		[GP] - changed tags to "<mark>". - 08/09/2019
	
	Ref: 
		https://www.elastic.co/guide/en/elasticsearch/reference/current//search-request-body.html#request-body-search-highlighting
		If the number_of_fragments value is set to 0 then no fragments are produced, instead the whole content of the field is returned, and of course it is highlighted. 
	"""
	
	res = es.search(index=index_name, body={"query": {
												"multi_match": {
													"query": search_str, 
													"type": search_type, 
													#"fields": ["uid", "publisher", "type", "title", "year", "author", "keywords", "abstract", "body_text"]
													"fields": ["title", "abstract", "body_text"],
													"operator": operator
												}
											},
											"highlight":{
												#"order": "score",
												#"fields":{"*":{}}
												"pre_tags" : ["<mark>"],
												"post_tags" : ["</mark>"],
												"fields": {
														"title": {
															"number_of_fragments" : 0
														  },
														"abstract": {
															"number_of_fragments" : 0,
															#"fragment_size": 150,
															#"boundary_max_size": 100,
															#"boundary_chars": "\n",
															#"boundary_scanner": 
															"type": "unified"
														  },
														  "body_text": {
															"number_of_fragments" : 0
														  }
														}	
											},										
											"size": 1000})
							
	results = []
	total_articles = res['hits']['total']['value']

	print("%d documents found: " % res['hits']['total']['value'])
	'''
	for doc in res['hits']['hits']:
		elem = []
		for field in doc['highlight']:
			temp_elem = append_fields(doc, 'title', results, elem)
			#temp_elem.append(doc['_source']['uid'])
			#temp_elem2 = append_fields(doc, 'abstract', results, temp_elem)
			temp_elem2 = append_fields(doc, 'uid', results, temp_elem)
			
			if field != 'title' or field != 'abstract': # add other lines
				for line in doc['highlight'][field]:
					temp_elem2.append(line)
		results.append(temp_elem2)
	'''
	
	for doc in res['hits']['hits']:
		'''
		{
		  "_index": "bookdb_index",
		  "_type": "book",
		  "_id": "3",
		  "_score": 1.6323128,
		  "_source": {
			"summary": "build scalable search applications using Elasticsearch without having to do complex low-level programming or understand advanced data science algorithms",
			"title": "Elasticsearch in Action",
			"publish_date": "2015-12-03"
		  },
		  "highlight": {
			"title": [
			  "Elasticsearch <em>in</em> <em>Action</em>"
			]
		  }
		},
		'''
		#print(doc)
		#input('enter')
	
		elem = []
		for field in doc['highlight']:
			if field != 'title':	# query must appear in abstract or body text. 
				for line in doc['highlight'][field]:
					elem.append(line)

		if len(elem) > 0:
			elem.insert(0, doc['_source']['title'])
			elem.insert(1, doc['_source']['uid'])
		
		results.append(elem)
		
	return results, total_articles



''' deprecated (used before ES)
def find_sent(text, query_tokens, search_operation):
	"""
	Find sentences containing keywords and highlight the keywords.
	"""
	
	ret_sents = []

	for sent in text:
		lowercased_tokens = [x[0].lower() for x in sent['token_pos']]	# lowercase
		
		if search_operation == 'AND':
			result = all(elem in lowercased_tokens for elem in query_tokens)
		elif search_operation == 'OR':
			result = any(elem in lowercased_tokens for elem in query_tokens)
				
		if result == True:
			highlighted_sent = sent['sent']
			tokens = sent['token_pos']
			
			match_tokens = []	# save token's offsets
			for qt in query_tokens:
				for tok in tokens:
					if tok[0].lower() == qt:
						start_offset = tok[1]
						end_offset = tok[2]
						match_tokens.append([start_offset, end_offset])
			
			# sort offsets by descending order and add tags into the string. 
			# String manipulation backwards can preserve the offsets.
			sorted_match_tokens = sorted(match_tokens, key=lambda l:l[1], reverse=True)

			for item in sorted_match_tokens:
				start_offset = item[0]
				end_offset = item[1]
				highlighted_sent = highlighted_sent[:end_offset] + '</mark>' + highlighted_sent[end_offset:]
				highlighted_sent = highlighted_sent[:start_offset] + '<mark>' + highlighted_sent[start_offset:]
			
			ret_sents.append(highlighted_sent)
			
	return ret_sents
'''

def search(request):
	results = []
	
	if 'q' in request.GET:
		query = request.GET['q']
		
		query_tokens = query.split()
		
		search_type = 'best_fields'	# ES default search_type 
		operator = 'or'	# ES default operator 

		#if 'and' in (tok.lower() for tok in query_tokens):	# the old way to find phrases using 'and'
		if query.startswith('"') and query.endswith('"'):
			search_type = 'phrase'
		
		if 'and' in (tok.lower() for tok in query_tokens):	# the old way to find phrases using 'and'
			operator = 'and'
			
		query_tokens = list(filter(lambda a: a.lower() not in ['and', 'or'], query_tokens))	# remove 'and' 'or'

		results, total_num = es_search(' '.join(query_tokens), search_type, operator)
		
		formatted_total_num = '{0:,d}'.format(total_num)
		
		if total_num == 10000:
			formatted_total_num = 'more than ' + formatted_total_num
		
		message = f'You have searched for: {query} | Results of {formatted_total_num}' 
	else:
		message = ''

	context = {
		'message': message,
		'results': json.dumps(results)
	}
	return render(request, 'tdm/search.html', context)

	'''
	#first_article = Article.objects.get(pk=1)
	first_article = get_object_or_404(Article, pk=1)
	context = {
		'first_article': first_article,
	}
	return render(request, 'tdm/search.html', context)
	'''


def scrape(request):
	"""
	!! If it scrapes articles here, then it can't print debugs.
	"""
	if 'input' in request.GET:
		input_txt = request.GET['input']

		#d = Downloader()
		#d.retrieve_article_from_Elsevier('EXAFS')
		#d.retrieve_article_from_PMC('EXAFS')
		#d.retrieve_article_from_Wiley('EXAFS')
		#d.retrieve_article_from_APS('EXAFS')
		#d.retrieve_article_from_Springer('EXAFS')

		#e = Parser()
		#e.parse_XML_Elsevier("../archive/Elsevier/articles/S0022328X0101453X.xml")
		#e.parse_XML_Springer("../archive/Springer/101007s007750181608y.xml")
		#e.parse_XML_PMC("../archive/PMC/PMC6281269/pone.0208355.nxml")

		return render(request, 'tdm/scrape.html')
	else:
		return render(request, 'tdm/scrape.html')

	'''
	retVal = parser.parseJATS('tdm/archive/springer_nature.xml')
	context = {
		'title': retVal["title"],
		'abstract': retVal["abstract"],
		'body': retVal["body"],
	}
	return render(request, 'tdm/scrape.html', context)
	'''			
	

def xas_classification(request):
	"""
	
	"""
	'''
	results = []

	dirs = []
	#dirs.append("/home/gpark/corpus_web/tdm/archive/PMC/")
	dirs.append("/home/gpark/corpus_web/tdm/archive/Springer/articles")
	#dirs.append("/home/gpark/corpus_web/tdm/archive/Elsevier/articles")
	
	total_articles = 0
	
	for dir in dirs:
		for root, dirs, files in os.walk(dir):
		#	results.extend([os.path.join(root, file) for file in files if file.endswith(".json")])
			for file in files:
				if file.endswith(".json"):
					with open(os.path.join(root, file), "r") as read_file:
						data = json.load(read_file)
						year = data['year']
						title = data['title']

						xas_info = data['xas_info']
						
						for xi in xas_info:
							print(xi['region'])
							print(xi['element'])
							print(xi['edge'])
						

						if len(xas_info) > 0:
							title_year = '[' + str(year) + '] ' + title
							xas_info.insert(0, title_year)
							
							xas_info.insert(1, data['uid'])

							results.append(xas_info)
							total_articles += 1
	
	total_articles = '{0:,d}'.format(total_articles)
	'''
				
	with open("/home/gpark/corpus_web/tdm/analyzer/data/xas_classifier_data/xas_tree.json", "r") as read_file:
		data = json.load(read_file)
	
	context = {
		'data': data
	}
	return render(request, 'tdm/xas_classification.html', context)


def xas_page(request):
	if request.method == 'POST':
		data = request.POST.copy()
		article_link = data.get('article_link')
		del data['csrfmiddlewaretoken']
		del data['article_link']

		fig_data = []
		
		tmp = {}
		for k, v in data.items():
			k = k.rsplit('_', 1)[0]

			if k == 'fig_file':
				v = v.replace("/home/gpark/corpus_web/tdm/archive", "")
			tmp[k] = v
			if len(tmp) == 3:
				fig_data.append(tmp)
				tmp = {}

		'''
		Note that don't write any comments inside of context. it causes errors!! - 11/08/2019
		e.g., when there's comments above 'fig_data' or 'article_link' variable, it is not passed to html.
		'''
		context = {
			'fig_data': fig_data,
			'article_link': article_link
		}

		return render(request, 'tdm/xas_page.html', context)
	

def __unicode__(self):
    return u'%s' % (self)


def index(request):
	return render(request, 'tdm/index.html')

