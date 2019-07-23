
import os, glob, json
from django.shortcuts import get_object_or_404, render
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
#from .models import Article
#from .scraper import downloader, parser
#from .scraper.downloader import Downloader
#from .scraper.parser import Parser

# ------------------------------------------------------------------------------

es = Elasticsearch([{'host':'localhost', 'port':9200}]) # connect to cluster

# aiko's funciton
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

def index_folder(path, index='index1'):
    """
    loads entire folder with given index name
    """
    for f in glob.glob(os.path.join(path, '*.json')):
        data = extract_data(f, 'abstract', 'body_text')

        yield{
                '_index': index,
                '_source': data
                }

def es_search(searchstr, index_name='index1'):
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

# ------------------------------------------------------------------------------

def __unicode__(self):
    return u'%s' % (self)

def index(request):
	return render(request, 'tdm/index.html')

# can be reused
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


def search(request):
	results = []

	if 'q' in request.GET:
		query = request.GET['q']

		query_tokens = query.split()
		query_tokens = [x.lower() for x in query_tokens]	# lowercase

		search_operation = 'AND'	# default value is AND.

		if 'or' in query_tokens:
			search_operation = 'OR'

		query_tokens = list(filter(lambda a: a not in ['and', 'or'], query_tokens))	# remove 'and' 'or'

		#results = es_search(' '.join(query_tokens))
		results = es_search(query)

		'''
		dirs = []
		#dirs.append("/home/gpark/corpus_web/tdm/archive/PMC/")
		#dirs.append("/home/gpark/corpus_web/tdm/archive/Springer/articles")
		#dirs.append("/home/gpark/corpus_web/tdm/archive/Elsevier/articles")
		dirs.append("C://Users//ahass//mysite//tdm/archive//")


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

							sents = find_sent(data['abstract'], query_tokens, search_operation)
							sents.extend(find_sent(data['body_text'], query_tokens, search_operation))

							#print(sents)

							if len(sents) > 0:
								title_year = '[' + str(year) + '] ' + title
								sents.insert(0, title_year)

								sents.insert(1, data['uid'])

								results.append(sents)
								total_articles += 1


		total_articles = '{0:,d}'.format(total_articles)
		'''

		message = f'You have searched for: {query}'
	else:
		message = ''

	print(results)

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

	with open("C://Users//ahass//mysite//tdm/analyzer//xas_tree.json", "r") as read_file:
		data = json.load(read_file)

	context = {
		'data': data
	}
	return render(request, 'tdm/xas_classification.html', context)
