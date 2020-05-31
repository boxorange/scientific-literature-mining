import sys
from time import sleep
import json
import requests
from base_downloader import BaseDownloader
import logging

logger = logging.getLogger(__name__)


class APSDownloader(BaseDownloader):
	"""
	Note:
	- APS doesn't provide a search API yet, so searching has to be done via Crossref.
	- It's ideal to get BagIt format (.zip) that contains full text in xml format and image files.
	But, not all articles are stored in that format.
	First try to get BagIt format, and if an error (401 or 404) occurs, then get an article using links by Crossref.
	E.g., 10.1103/PhysRevSTAB.4.072801
		link from Crossref: http://link.aps.org/article/10.1103/PhysRevSTAB.4.072801
			-> json format which contains meta data.
		link from Crossref: http://harvest.aps.org/v2/journals/articles/10.1103/PhysRevSTAB.4.072801/fulltext
			-> pdf format
		url from Harvest api: http://harvest.aps.org/v2/journals/articles/10.1103/PhysRevSTAB.4.072801
			-> BagIt format
	E.g., 10.1103/PhysRevB.50.11121
		link from Crossref: http://link.aps.org/article/10.1103/PhysRevB.50.11121
		-> the link is redirected to http://harvest.aps.org/v2/journals/articles/10.1103/PhysRevB.50.11121, and 401 error occurs.
	
	TODO:
	- 
	
	References:
	- http://harvest.aps.org/
	- https://journals.aps.org/licenses
	"""

	def __init__(self):
		super().__init__('APS')
	
	
	def retrieve_all_open_access_articles(self):
		"""
		!! the request hangs in around 10-13 times, and the server returns an error msg - 502 Bad Gateway error!!
		"""
		search_url = 'http://harvest.aps.org/v2/journals/articles?set=openaccess'
		
		num_of_requests = 0
		
		dois = set()
		while True:
			#sleep(1)
			# http://docs.python-requests.org/en/master/user/advanced/#timeouts
			response = requests.get(search_url, timeout=None)
			
			num_of_requests += 1
			print(f'>>> Number of requests: {num_of_requests}')
			
			if response.status_code == 200:
				next_page = response.links["next"].get('url') if response.headers.get('link') is not None else None
				
				response = response.json()
				for item in response["data"]:
					doi = item["identifiers"]["doi"]
					dois.add(doi)

				# http://docs.python-requests.org/en/master/user/advanced/
				# if response.links["next"] is not None:
				if next_page is not None:
					#print(response.links["next"].get('url'))
					#print(response.links["last"])
					#search_url = response.links["next"].get('url')
					search_url = next_page
				else:
					break
			else:
				self.display_error_msg(response)
				sys.exit()

		duplicate_removed_uids = self.check_uids(dois)   # check if it's already downloaded.
		
		for doi in duplicate_removed_uids:
			search_url = "http://harvest.aps.org/v2/journals/articles/" + doi

			#headers = {'Accept': 'application/zip'}
			headers = {'Accept': 'text/xml'}

			response = requests.get(search_url, headers=headers)
			
			if response.status_code == 200:
				#print(response.headers)

				filename = "APS_" + ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.

				self.write_to_file(response, self.path, filename, ".xml")
			else:
				self.display_error_msg(response)
				sys.exit()
						
		self.save_uids()    # save new uids in the uid file.
		

	def retrieve_articles(self, query):
		max_rows = 1000

		params = {'query': query, 'rows': max_rows, 'cursor': "*", 'sort': 'score',
				  'filter': 'has-full-text:true,member:16', # APS member id is 16.
				  'mailto': 'gpark@bnl.gov'}

		num_queries = 0
		while True:
			num_queries += 1

			response = requests.get('https://api.crossref.org/works', params=params)
			
			if response.status_code == 200:
				#print(response.headers)
				#print('>> status_code:',response.status_code)
				#print(response.url)

				response = response.json()

				total_results = response["message"]["total-results"]

				#print(json.dumps(response, indent=4, sort_keys=True))
				#print('>> total_results:',total_results)
				#print('>> num_queries:',num_queries)

				doi_link = {}
				for item in response["message"]["items"]:
					doi = item["DOI"].lower()
					link = item['link']
					
					doi_link[doi] = link
					
				duplicate_removed_uids = self.check_uids(set(doi_link.keys()))   # check if it's already downloaded.

				doi_link = {k: v for k, v in doi_link.items() if k in duplicate_removed_uids}

				if total_results < (num_queries*max_rows):
					break

				params['cursor'] = response['message']['next-cursor']
			else:
				self.display_error_msg(response)
				sys.exit()

		for doi, link in doi_link.items():
			search_url = "http://harvest.aps.org/v2/journals/articles/" + doi

			headers = {'Accept': 'application/zip'}
			response = requests.get(search_url, headers=headers)

			#print(response.headers)

			filename = "APS_" + ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.

			if response.status_code == 200:
				self.write_to_file(response, self.path, filename, ".zip")
			else:
				for l in link:
					url = l.get('URL')
					
					response = requests.get(url)

					if response.status_code == 200:
						type = response.headers['content-type']
						ext = ''
						if type == 'application/vnd.tesseract.article+json':
							ext = '.json'
						elif type == 'application/pdf':
							ext = '.pdf'
						else:
							logger.error(f'>> undefined type: {type} | URL: {url}')
							sys.exit()

						self.write_to_file(response, self.path, filename, ext)
					else:
						self.display_error_msg(response)
						sys.exit()
						
		self.save_uids()    # save new uids in the uid file.
