import sys
import json
import requests
from time import sleep
from base_downloader import BaseDownloader
import logging

logger = logging.getLogger(__name__)


class CrossrefDownloader(BaseDownloader):
	"""
	Note:
	- Requests to RSC servers need headers.
	- Requests to Wiley servers need clickthrough token.
	- When you search with query terms, on Crossref servers they are not searching full text, or even abstracts of articles,
	  but only what is available in the data that is returned to you. That is, they search article titles, authors, etc.
	  https://media.readthedocs.org/pdf/habanero/latest/habanero.pdf
	- case-insensitive search
	- /works: returns a list of all works (journal articles, conference proceedings, books, components, etc), 20 per page
	- Multiple filters can be specified in a single query. In such a case, different filters will be applied with AND semantics,
	  while specifying the same filter multiple times will result in OR semantics
	
	References:
	- https://github.com/CrossRef/rest-api-doc
	- https://github.com/CrossRef/rest-api-doc/blob/master/api_format.md
	- https://www.crossref.org/services/metadata-delivery/rest-api/#tdm
	- https://www.crossref.org/06members/50go-live.html
	- https://www.crossref.org/labs/
	- https://www.doi.org/registration_agencies.html
	- https://search.crossref.org/help/api
	
	Licenses:
	- Emerald: https://www.emeraldinsight.com/page/tdmfaqs
	- Wiley: http://olabout.wiley.com/WileyCDA/Section/id-826542.html
	- AAAS: http://www.sciencemag.org/subscribe/institutional-license-agreement
	- IOP Science: https://iopscience.iop.org/info/page/text-and-data-mining
	"""
		
	'''
	pubisher_preDOIs = {
		"Elsevier": ['10.1016', '10.1006'],
		"RSC": ['10.1039'],
		# Springer (Biomed Central Ltd.)	10.1186
		"Springer": ['10.1007', '10.1140', '10.1186', '10.1891'],
		# The Electrochemical Society (of Japan),
		"ECS": ['10.1149', '10.5796'],
		"Nature": ['10.1038'],
		# American Chemical Society
		"ACS": ['10.1021', '10.26434', '10.29200'],
		# American Physical Society (To be tested)
		"APS": ['10.1103', '10.29172'],
		"Wiley": ['10.1002', '10.1111'],
		# American Association for the Advancement of Science
		"AAAS": ['10.1126'],
		"Emerald": ['10.1108', '10.5042']
	}
	'''

	def __init__(self):
		super().__init__('Crossref')
		'''
		self.Crossref_Member_IDs = {
				#"Elsevier": '78',
				#"Springer": ['93', '297', '793'],
				'16': "APS",
				'292': "RSC",
				'77': "ECS",
				'316': "ACS",
				'311': "Wiley",
				'221': "AAAS",
				'140': "Emerald",
				#'266': "IOP",
				'329': "IUCr"
			}
		'''
		self.Crossref_Member_IDs = {
				#'16': "APS",
				#'316': "ACS"
				#'311': "Wiley"	# to be downloaded again
				#'329': "IUCr"
				#'292': "RSC"
				'140': "Emerald"
				}

	def retrieve_articles(self, query):
		'''
		Parameters:
		- row: the default number of results are returned 20 at a time. The maximum number rows you can ask for in one query is 1000.
		- cursor: used for deep paging
		- sort: sort the results by score (relevance), published, is-referenced-by-count, ...
		'''
		max_rows = 1000

		selected_members = ''
		for id in self.Crossref_Member_IDs.keys():
			selected_members += (',member:' + id)
		
		params = {'query.title': query, 'rows': max_rows, 'cursor': "*", 'sort': 'score',
				  'filter': 'has-full-text:true' + selected_members,
				  'mailto': 'gpark@bnl.gov'}

		article_info = {}
				
		""" Search articles """
		num_queries = 0
		while True:
			num_queries += 1

			response = requests.get('https://api.crossref.org/works', params=params)
			
			if response.status_code == 200:
				response = response.json()

				total_results = response["message"]["total-results"]
				
				''' debug
				print(json.dumps(response, indent=4, sort_keys=True))
				print('>> total_results:',total_results)
				print('>> num_queries:',num_queries)
				'''

				for item in response["message"]["items"]:
					doi = item["DOI"].lower()
					
					member_id = item['member']
					member = self.Crossref_Member_IDs.get(member_id)
						
					link = []
					# In case of Wiley, only use a link with 'text-mining' of intended-application element
					# because Wiley has links with 'unspecified' types, and one of them is just an webpage, so it replaces a pdf file with an webpage.
					if member == 'Wiley':
						for l in item['link']:
							if l.get('intended-application') == 'text-mining':
								link.append(l)
					else:
						link = item['link']
					
					if len(link) != 0:
						
						print(doi)
						
						metadata = {}
						metadata['uid'] = item['DOI'] if 'DOI' in item else None
						metadata['publisher'] = item['publisher'] if 'publisher' in item else None
						metadata['type'] = item['type']	if 'type' in item else None	# e.g., journal-article -> https://api.crossref.org/v1/types
						metadata['title'] = item['title'] if 'title' in item else None
						metadata['year'] = item['issued']['date-parts'][0][0] if 'issued' in item else None
						metadata['author'] = []
						if 'author' in item:
							for author in item['author']:
								if 'family' in author:
									name = author['given'] + ' ' if 'given' in author else ''
									name += author['family']
									metadata['author'].append(name)
						metadata['abstract'] = item['abstract'] if 'abstract' in item else None

						article_info[doi] = {'link': link, 'member': member, 'metadata': metadata}
					else:
						logger.error(f'>> No links - Member: {member} / DOI : {doi}')

				if total_results < (num_queries*max_rows):
					break

				params['cursor'] = response['message']['next-cursor']
			else:
				self.display_error_msg(response)
				sys.exit()
		
		duplicate_removed_uids = self.check_uids(set(article_info.keys()))   # check if it's already downloaded.

		article_info = {k: v for k, v in article_info.items() if k in duplicate_removed_uids}
		
		print('>>> number of items:', len(article_info))

		
		""" Download articles """
		for doi, info in article_info.items():
			link = info['link']
			member = info['member']
			metadata = info['metadata']
			
			filename = member + '_'   # filename prefix is a publisher.
			filename += ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
			destination = BaseDownloader.archive_path + member + "/"

			headers = {'User-Agent': 'Mozilla/5.0'}
			
			if member == 'Wiley':
				headers['CR-Clickthrough-Client-Token'] = self.api_key

			pdf_flag = False				# check if a pdf file is already donwnloaded. 
											# It's to avoid duplicate downloads for the same pdf file.
			is_article_downloaded = False	# this is to determine if doi needs to be removed.

			for l in link:
				url = l.get('URL')
				type = l.get('content-type')

				ext = ''
				if type in ['application/pdf', 'unspecified']:
					if pdf_flag is True:
						continue
					ext = '.pdf'
				elif type == 'text/xml':
					ext = '.xml'
				elif type == 'text/html':
					ext = '.html'
				elif type == 'text/plain':
					ext = '.txt'
				else:
					logger.error(f'>> undefined type: {type} | Member: {member} | URL: {url}')
					sys.exit()

				response = requests.get(url, headers=headers)
				if response.status_code == 200:
					self.write_to_file(response, destination, filename, ext)
					
					# write metadata to file
					with open(destination + filename + '.json', 'w') as outfile:
						json.dump(metadata, outfile)

					if ext == '.pdf':
						pdf_flag = True
					
					is_article_downloaded = True
					
					
					print(response.headers)
						
				#elif response.status_code in [401, 403, 404]:	# 401: Not Authorized | 403: Forbidden | 404: Not Found
				#	logger.error(f'>> ERROR code: {response.status_code} | Member: {member} | URL: {url}')
					
				#	BaseDownloader.existing_uids.remove(doi)
				#	BaseDownloader.to_be_saved_uids.remove(doi)
				else:
					self.display_error_msg(response, member)
					#sys.exit()
			
			# articles have multiple links where some link works, but other link doesn't work.
			# e.g., "http://link.aps.org/article/10.1103/PhysRevB.66.064209" -> 401 (unauthorized error)
			#       "http://harvest.aps.org/v2/journals/articles/10.1103/PhysRevB.66.064209/fulltext" -> works
			if is_article_downloaded is False:
				if doi in BaseDownloader.existing_uids:
					BaseDownloader.existing_uids.remove(doi)
				if doi in BaseDownloader.to_be_saved_uids:
					BaseDownloader.to_be_saved_uids.remove(doi)
					
					
		self.save_uids()    # save new uids in the uid file.
