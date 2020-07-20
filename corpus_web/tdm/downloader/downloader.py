import os
import sys
import time
import json
import requests
import csv
from datetime import date

from pmc_downloader import PMCDownloader
from elsevier_downloader import ElsevierDownloader
from springer_downloader import SpringerDownloader
from rsc_downloader import RSCDownloader
from aaas_downloader import AAASDownloader
from aps_downloader import APSDownloader
from crossref_downloader import CrossrefDownloader
from osti_downloader import OSTIDownloader

'''
import chemdataextractor.scrape.pub.rsc as RSC
from chemdataextractor.scrape import Selector
from chemdataextractor.scrape.pub.rsc import RscHtmlDocument
from chemdataextractor.doc import Document
from chemdataextractor.reader.rsc import RscHtmlReader
'''


def set_query(project):
	terms = []
	
	if project == 'COVID-19':
		"""
		<Keywords>
		"COVID-19" OR Coronavirus OR "Corona virus" OR "2019-nCoV" OR "SARS-CoV" OR "MERS-CoV" OR “Severe Acute Respiratory Syndrome” OR “Middle East Respiratory Syndrome” 
		"""
		terms = ['COVID-19', 'Coronavirus', 'Corona virus', '2019-nCoV', 'SARS-CoV', 'MERS-CoV', 'Severe Acute Respiratory Syndrome', 'Middle East Respiratory Syndrome']
	elif project == 'XAS':
		"""
		<Keywords>
		X-ray absorption fine structure (XAFS)
		Extended X-Ray Absorption Fine Structure (EXAFS)
		X-ray absorption near edge structure or spectroscopy (XANES), also known as 
		near edge X-ray absorption fine structure (NEXAFS)
		Pair distribution function (PDF)
		"""
		#terms = ['XAFS', 'XANES']
		terms = ['XAFS', 'EXAFS', 'XANES', 'NEXAFS']	# use this list. don't use ['XAFS', 'XANES'] since it doesn't cover all articles.
		#terms = ['EXAFS', 'XANES', 'NEXAFS', 'pair distribution function']
		#terms = ['EXAFS', 'XANES', 'NEXAFS']	# phrase and exact searching is not working in Crossref.
	elif project == 'GENESIS':
		"""
		<Keywords>
		flux growth
		molten flux
		self-flux
		halide flux
		oxide flux
		crystal habit
		hydrothermal reaction

		synthesis
		solid state synthesis
		solution phase synthesis
		melt synthesis

		Pourbaix diagram
		alloy diagram
		ternary "phase diagram"
		quaternary phase diagram
		single crystals of ____ were grown from ____ flux
		"""
		#terms = ['metathesis', 'nucleation', 'diffusion', 'preparation', 'precursor', 'eutectic', 'solubility', 'boule']
		'''
		terms = [
				'solid state synthesis',
				'solution phase synthesis',
				'melt synthesis',
				'hydrothermal reaction'
				#'Pourbaix diagram'	# too many results
				]
		'''
		terms = [
				'metathesis reaction',
				'metathetic reaction',
				'metathetical reaction',	# metathetical exchange reaction 
				'exchange reaction',
				'double decomposition',		# double decomposition reaction
				'double displacement',		# double displacement reaction
				'double replacement',		# double replacement reaction
				#'double ion exchange',
				'metathesis route',
				'metathesis pathway',
				'metathesis method',
				'solid state synthesis'		# -> redundant to the term above 
				]
			
	""" create a request query
	- add double quotation marks to search terms appear together. 
	  Note that it ignores punctuation marks. E.g., the search results between "solid state synthesis" and "solid-state synthesis" are the same.

	- wrap a query with parenthesis () that is used for multiple search terms/contraints, but it works for single terms as well. 
	 
	Ref: https://dev.elsevier.com/tips/ScienceDirectSearchTips.htm
	"""
	query = ''
	for i in range(0, len(terms)): 
		#if ' ' in terms[i]:
		if any(t in terms[i] for t in [' ', '-']):
			query += f'"{terms[i]}"'	
		else:
			query += terms[i]
			
		if i != (len(terms)-1):
			query += ' OR '	# space works the same as +

	query = query.strip()
	query = '(' + query + ')'

	print('query:', query)

	'''
	params = {'query.title': '%22pair distribution function%22', 'rows': 1000, 'cursor': "*", 'sort': 'score',
			  'filter': 'has-full-text:true,member:16',
			  'mailto': 'gpark@bnl.gov'}
					  
	response = requests.get('https://api.crossref.org/works', params=params)

	print(response.status_code)
	print(response.url)
	print(response.text)

	with open("crossref_test.json", 'wb') as file:
		for chunk in response.iter_content(2048):
			file.write(chunk)

	sys.exit()
	'''

	''' the Requests library neatly wraps up all that urllib.parse functionality for us. So, the following is not needed. '''
	#import urllib.parse
	#query = urllib.parse.quote_plus(query)	# URL encoding - quote() uses UTF-8 by default
	
	return terms, query


def download_Crossref(query):
	cd = CrossrefDownloader()
	cd.retrieve_articles(query)


def download_OSTI(query):
	od = OSTIDownloader()
	od.retrieve_articles(query)	


def download_APS(query):
	ad = APSDownloader()
	#for q in qs:
	#	ad.retrieve_articles(q)
	#ad.retrieve_all_open_access_articles()

	# debug - the following request hangs and causes an 502 Bad Gateway error!!
	response = requests.get('http://harvest.aps.org/v2/journals/articles?page=20&per_page=100&set=openaccess')
	print(response.headers)


def update_download_result(download_history_file, doi_title, publisher=None):
	if publisher is None:
		return

	if not os.path.exists(download_history_file):
		with open(download_history_file, 'w', newline='') as fp:
			writer = csv.writer(fp)
			writer.writerow(["Publisher", "Title", "URL"])
			for doi, title in doi_title.items():
				writer.writerow([publisher, title, "https://doi.org/" + doi])
	else:
		with open(download_history_file, 'a', newline='') as fp:
			writer = csv.writer(fp)
			for doi, title in doi_title.items():
				writer.writerow([publisher, title, "https://doi.org/" + doi])


def update_lit_stat(lit_stat, publisher):
	path = '/home/gpark/corpus_web/tdm/archive/' + publisher
	num_of_papers = 0
	for root, dirs, files in os.walk(path):
		num_of_papers += len(dirs)
	lit_stat[publisher] = num_of_papers
		

def main():
	start_time = time.time()
	
	# set queries based on project: 'XAS', 'GENESIS', 'COVID-19'
	project = 'XAS'
	keywords, query = set_query(project)
	year = 2020
	#year = None
	
	# instantiate downloaders
	ed = ElsevierDownloader()
	sd = SpringerDownloader()
	rd = RSCDownloader()
	pd = PMCDownloader()
	aaasd = AAASDownloader()

	fdate = date.today().strftime('%m-%d-%Y')
	download_history_file = '/home/gpark/corpus_web/tdm/archive/download_history/' + project + '/' + fdate + '.csv'

	with open('/home/gpark/corpus_web/tdm/archive/lit_stat.json', "r") as fp:	# load literature statistics.
		lit_stat = json.load(fp)

	# TODO: change it to sending the whole query once. query above syntax doesn't work, and OR doesn't work in search. 
	doi_title = aaasd.retrieve_articles(keywords, year, enable_sleep=False)
	update_download_result(download_history_file, doi_title, publisher='AAAS/Science')
	update_lit_stat(lit_stat, 'AAAS')
	
	doi_title = ed.retrieve_articles(query, year)
	update_download_result(download_history_file, doi_title, publisher='Elsevier')
	update_lit_stat(lit_stat, 'Elsevier')
	
	doi_title = sd.retrieve_articles(query, year)
	update_download_result(download_history_file, doi_title, publisher='Springer Nature')
	update_lit_stat(lit_stat, 'Springer')

	doi_title = rd.retrieve_articles(query)	# TODO: handle year!!
	update_download_result(download_history_file, doi_title, publisher='RSC')	# TODO: test more!!!
	update_lit_stat(lit_stat, 'RSC')
	
	# download PMC articles last since it contains other publishers' articles.
	doi_title = pd.retrieve_articles(query, year)
	update_download_result(download_history_file, doi_title, publisher='PMC')
	update_lit_stat(lit_stat, 'PMC')
	
	sorted_lit_stat = {k: v for k, v in sorted(lit_stat.items(), key=lambda x: x[1], reverse=True)}
	
	with open('/home/gpark/corpus_web/tdm/archive/lit_stat.json', "w") as fp:	# save updated literature statistics.
		json.dump(sorted_lit_stat, fp)
	
	'''
	download_APS(query)
	download_Crossref(query)
	download_OSTI(query)
	'''
	print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
	main()