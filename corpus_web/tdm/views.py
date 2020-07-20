import os, glob, json
from django.shortcuts import get_object_or_404, render
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from django.http import JsonResponse, HttpResponse
#from .models import Article
#from .scraper import downloader, parser
#from .scraper.downloader import Downloader
#from .scraper.parser import Parser


es = Elasticsearch([{'host':'localhost', 'port':9200}]) # connect to cluster

with open("/home/gpark/corpus_web/tdm/analyzer/data/xas_classifier_data/xas_tree_updated_07-10-20.json", "r") as fp:
	xas_cls_data = json.load(fp)
	for item in xas_cls_data:
		if 'data' in item:
			for data in item['data']:
				data['fig_caption'] = ' '.join(data['fig_caption'])
				if 'fig_relevant_text' in data:
					data['fig_relevant_text'] = ' '.join(data['fig_relevant_text'])
					
'''
def append_fields(doc, field, result, elem):
	if field in doc['highlight']:
		for line in doc['highlight'][field]:
			elem.append(line)
	else:
		elem.append(doc['_source'][field])

	return elem
'''

def es_search(search_str, search_fields, show_only_xas_articles, search_type, operator, index_name='tdm_index'):
	"""
	searches for word in database with specified index 
	highlights terms and returns a 2D array 
	format ) results = [[title, abstract, relevant field 1, relevant field 2, ...]]
	
	Note:
		[GP] - added figure captions. - 07/13/2020
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
													#"fields": ["title", "abstract", "body_text", "figures"],
													"fields": search_fields,
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
													},
													"figures": {
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
	
	total_articles_with_xas_figure = 0
	
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

		elem = []
		for field in doc['highlight']:
			#if field != 'title':	# query must appear in abstract or body text. -> include title in the result. - 07-13-2020
			for line in doc['highlight'][field]:
				elem.append(line)

		if len(elem) > 0:
			elem.insert(0, doc['_source']['title'])
			elem.insert(1, doc['_source']['uid'])
			
			xas_cls = []
			for item in xas_cls_data:
				if elem[1] in item['id']:	# check if article is in XAS classification tree.
					xas_cls.append(item)
			
			elem.insert(2, xas_cls)
		
		if show_only_xas_articles == True:
			if len(elem[2]) > 0:
				results.append(elem)
				total_articles_with_xas_figure += 1
		else:
			results.append(elem)
	
	if show_only_xas_articles == True:
		total_articles = total_articles_with_xas_figure
	
	return results, total_articles


def search(request):
	results = []
	
	if 'q' in request.GET:
		query = request.GET['q']

		search_fields = []
		search_fields_txt = []	# for message

		title_checkbox = request.GET.get('title_checkbox', '')
		abstract_checkbox = request.GET.get('abstract_checkbox', '') 
		body_text_checkbox = request.GET.get('body_text_checkbox', '')
		figure_caption_checkbox = request.GET.get('figure_caption_checkbox', '')

		if title_checkbox == 'on':
			search_fields.append("title")
			search_fields_txt.append("title")
		if abstract_checkbox == 'on':
			search_fields.append("abstract")
			search_fields_txt.append("abstract")
		if body_text_checkbox == 'on':
			search_fields.append("body_text")
			search_fields_txt.append("body text")
		if figure_caption_checkbox == 'on':
			search_fields.append("figures")
			search_fields_txt.append("figure caption")
		
		show_only_xas_articles = False
		show_only_xas_checkbox = request.GET.get('show_only_xas_checkbox', '')
		if show_only_xas_checkbox == 'on':
			show_only_xas_articles = True

		query_tokens = query.split()
		
		search_type = 'best_fields'	# ES default search_type 
		operator = 'or'	# ES default operator 

		#if 'and' in (tok.lower() for tok in query_tokens):	# the old way to find phrases using 'and'
		if query.startswith('"') and query.endswith('"'):
			search_type = 'phrase'
		
		if 'and' in (tok.lower() for tok in query_tokens):	# the old way to find phrases using 'and'
			operator = 'and'
			
		query_tokens = list(filter(lambda a: a.lower() not in ['and', 'or'], query_tokens))	# remove 'and' 'or'

		results, total_num = es_search(' '.join(query_tokens), search_fields, show_only_xas_articles, search_type, operator)
		
		formatted_total_num = '{0:,d}'.format(total_num)
		
		if total_num == 10000:
			formatted_total_num = 'More than ' + formatted_total_num

		search_fields_txt = ', '.join(search_fields_txt)
		if show_only_xas_articles == True:
			message = f'\'You have searched for <strong>{query}</strong> in {search_fields_txt}. It only shows articles with XAS figures. <br> <strong>{formatted_total_num}</strong> results\'' 
		else:
			message = f'\'You have searched for <strong>{query}</strong> in {search_fields_txt}. <br> <strong>{formatted_total_num}</strong> results\'' 
	else:
		message = ''

	context = {
		'message': json.dumps(message),
		'results': json.dumps(results)
	}
	return render(request, 'tdm/search.html', context)


def scrape(request):
	"""
	TODO: this function is not used. remove it if not needed.
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
	context = {
		'data': xas_cls_data
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
			elif k == 'fig_relevant_text':
				print(type(v))
				print(v)
			
			'''
			elif k.startswith('fig_caption'):
				v = v.
				var fig_caption = 'fig_caption_' + i;
				var fig_file = 'fig_file_' + i;
				var fig_relevant_text = 'fig_relevant_text_' + i;
			'''
			
			tmp[k] = v
			if len(tmp) == 4:
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


def user_feedback(request):
	if request.method == 'POST' and request.is_ajax():
		feedback = {}
		feedback['rating'] = request.POST['rating']
		feedback['user_name'] = request.POST['user_name']
		feedback['comment'] = request.POST['comment']
		feedback['fig_relevant_text'] = request.POST['fig_relevant_text']

		with open("/home/gpark/corpus_web/tdm/analyzer/data/xas_classifier_data/user_feedback.json", 'a+') as fp:
			json.dump(feedback, fp)
			fp.write('\n')
		
		response = {
			'msg':'Thank you!!' # response message
		}
		return JsonResponse(response) # return response as JSON
		

def __unicode__(self):
    return u'%s' % (self)


def index(request):
	with open("/home/gpark/corpus_web/tdm/archive/lit_stat.json", "r") as read_file:
		data = json.load(read_file)
	
	context = {
		'data': data
	}
	return render(request, 'tdm/index.html', context)

