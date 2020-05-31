import sys
import json
import requests
from base_downloader import BaseDownloader
import logging

logger = logging.getLogger(__name__)


class OSTIDownloader(BaseDownloader):
	"""
	Note:
	- 
	
	References:
	- https://www.osti.gov/api/v1/docs
	
	Licenses:
	- 
	"""

	def __init__(self):
		self.destination = BaseDownloader.archive_path + "OSTI/"
	
	
	def update_dict(self, key, dict):
		if dict is None:
			return
			
		if key in dict:
			dict[key] += 1
		else:
			dict[key] = 1
			
		
		

	def retrieve_articles(self, query):
		'''
		Parameters:
		- fulltext: Searches the article full text (if available) for the provided terms
		'''
		
		""" Search articles """
		search_url = "https://www.osti.gov/api/v1/records"
		
		search_headers = {'Content-Type': 'application/json',
						  'Accept': 'application/json'}
						  
		params = {'fulltext': '(' + query + ')', 'page': 1}
		
		article_info = {}
		
		
		
		publisher = {}	# debug
		
		
		
		
		""" Search articles """
		num_queries = 0
		while True:
			num_queries += 1
			#print('num_queries:', num_queries)

			s_response = requests.get(search_url, headers=search_headers, params=params)
			
			'''
			print(s_response.url)
			print(s_response.headers)
			print(s_response.status_code)
			print(s_response.text)
			'''

			if s_response.status_code == 200:
				''' link example
				<https://www.osti.gov/api/v1/records?fulltext=%28%28%22solid+state+synthesis%22+OR+%22solution+phase+synthesis%22+OR+%22melt+synthesis%22+OR+%22hydrothermal+reaction%22%29%29&page=2>; rel="next", 
				<https://www.osti.gov/api/v1/records?fulltext=%28%28%22solid+state+synthesis%22+OR+%22solution+phase+synthesis%22+OR+%22melt+synthesis%22+OR+%22hydrothermal+reaction%22%29%29&page=85>; rel="last"
				'''
				next_page = ''
				for x in s_response.headers['Link'].split(','):
					if x.endswith('rel="next"'):
						next_page = x.split(';')[0].strip(' <>')
						next_page = next_page.split('page=')[1]
						break
				
				
				print(s_response.headers['Link'])
				
				
				s_response = s_response.json()

				print(json.dumps(s_response, indent=4, sort_keys=True))
				
				for item in s_response:
					#print('title:', item["title"], '/ doi: https://doi.org/' + item["doi"])
					
					if item["doi"] != "":
						#print(item["doi"])
						
						fulltext_link = ''
						for x in item["links"]:
							if x["rel"] == "fulltext":
								fulltext_link = x["href"]
								break
						
						if fulltext_link != '':
							doi = item["doi"].lower()
							
							metadata = {}
							metadata['uid'] = doi
							metadata['publisher'] = item['publisher'] if 'publisher' in item else None
							metadata['type'] = item['product_type']	if 'product_type' in item else None	# e.g., journal-article -> https://api.crossref.org/v1/types
							metadata['title'] = item['title'] if 'title' in item else None
							metadata['year'] = item['publication_date'] if 'publication_date' in item else None
							metadata['author'] = []
							if 'authors' in item:
								for author in item['authors']:
									metadata['author'].append(author)
							metadata['abstract'] = item['description'] if 'description' in item else None

							article_info[doi] = {'link': fulltext_link, 'metadata': metadata}



							# debug
							if metadata['publisher'] is not None:
								self.update_dict(metadata['publisher'], publisher)




				if next_page == '':
					break
				else:
					print('next_page:', next_page)
					#search_url = next_page
					
					params['page'] = next_page
			else:
				self.display_error_msg(s_response)
				sys.exit()
		
		
		# debug
		for elem in sorted(publisher.items(), reverse=True, key=lambda tup: tup[1])[:]:
			print(': '.join(map(str, elem)) +'\n')
		

		print('>>> BEFORE number of items:', len(article_info))
		
		duplicate_removed_uids = self.check_uids(set(article_info.keys()))   # check if it's already downloaded.

		article_info = {k: v for k, v in article_info.items() if k in duplicate_removed_uids}
		
		print('>>> AFTER number of items:', len(article_info))
		

		""" Download articles """
		for doi, info in article_info.items():
			link = info['link']
			metadata = info['metadata']
			
			filename = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
			
			params = {'directFulltextAccess': 'BNL'}

			response = requests.get(link, params=params)
			if response.status_code == 200:
				
				print(response.headers)
				
				self.write_to_file(response, self.destination, filename, ".pdf")

				# write metadata to file
				with open(self.destination + filename + '.json', 'w') as outfile:
					json.dump(metadata, outfile)
			else:
				self.display_error_msg(response, member)
				sys.exit()
				
			input()
			
		self.save_uids()    # save new uids in the uid file.
		
		
		
		'''
		#response = requests.get('https://www.osti.gov/servlets/purl/1485438' + '/fulltext')
		response = requests.get('https://www.osti.gov/servlets/purl/1485438' + '?directFulltextAccess=BNL')

		if response.status_code == 200:
			with open("osti_test.pdf", 'wb') as file:
			#with open("osti_test.html", 'wb') as file:	# the content is HTML type.
				for chunk in response.iter_content(2048):
					file.write(chunk)

		sys.exit()
		'''
		'''
		response = requests.get('https://www.osti.gov/api/v1/records?fulltext=%22exafs%22')

		print(response.headers)
		response = response.json()
		#print(json.dumps(response, indent=4, sort_keys=True))

		with open("osti_search.json", 'w') as file:	# the content is HTML type.
			file.write(json.dumps(response, indent=4, sort_keys=True))
		
		
		params = {'q': query, 's': 1, 'p': max_rows, 'api_key': self.springer_api_key}

		search_url = "http://api.springernature.com/openaccess/json"
		
		dois = set()
		'''
		



