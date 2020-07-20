import os
import sys
import json
import requests
import time
from time import sleep
from base_downloader import BaseDownloader
import logging

from lxml import etree

logger = logging.getLogger(__name__)


class SpringerDownloader(BaseDownloader):
	"""
	Note:
	- It searches the entire text. However, it is impossible to search only body text such as q=(abstract:"exafs" OR body:"exafs")
	- When a doi contains parentheses, quotes should be placed around the expression:
	  http://api.springernature.com/metadata/pam?q=doi:"10.1016/S1071-3581(97)90014-3"&api_key=...
	- For multiple contraints, use brackets to group constraints
	  e.g., http://api.springernature.com/meta/v1/pam?q=(title:"game theory" OR title:"perfect information")&api_key=..
	- api.springer.com == api.springernature.com
	"""

	def __init__(self):
		super().__init__('Springer')
	
	
	def retrieve_articles(self, query, year):
		'''
		Parameters
		- s: Return results starting at the number specified.
		- p: The maximum number of results returned in a single query is 20 in the case of Openaccess requests
		'''
		max_rows = 20

		params = {'q': query, 's': 1, 'p': max_rows, 'api_key': self.api_key}
		
		if year is not None:
			params['q'] += 'year:' + str(year)

		search_url = "https://spdi.public.springernature.app/xmldata/jats"
		
		doi_title = {}	# this is to save the history of downloads.
		
		num_queries = 0
		while True:
			num_queries += 1

			response = requests.get(search_url, params=params)

			'''
			print(response.headers)
			print(response.text)
			
			with open('temp.txt', 'wb') as file:
				for chunk in response.iter_content(2048):
					file.write(chunk)
			
			input()
			'''
			
			if response.status_code == 200:
				root = etree.fromstring(response.text)
				result = root.find('.//result')
				records = root.find('.//records')
				
				if len(records) == 0:
					break
				
				# debug
				#for child in result:
				#	print(child.tag + ': ' + child.text)

				for record in records:
					doi = ''
					title = ''
					if record.tag == 'book-part-wrapper':
						chapter = record.find('.//book-part[@book-part-type="chapter"]')
						chapter_meta = chapter.find('.//book-part-meta')
						doi = chapter_meta.findtext('.//book-part-id[@book-part-id-type="doi"]')
						title = chapter_meta.findtext('.//title-group/title')
					elif record.tag == 'article':
						article_meta = record.find('.//article-meta')
						doi = article_meta.findtext('.//article-id[@pub-id-type="doi"]')
						title = article_meta.findtext('.//article-title')

					if doi != '' and doi not in self.existing_uids:	# skip already downloaded articles.
						
						#print("--- New article: %s ---" % doi)
						
						file = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
						file = file.lower()	# lowercase 
						file_dir = self.path + file + '/'
						if not os.path.exists(file_dir):
							os.mkdir(file_dir)	# create a directory for each article.

						str_val = etree.tostring(record, pretty_print=True)
						with open(file_dir + file + '.xml', 'wb') as file:
							file.write(str_val)
						self.update_uid(doi)	# add a new uid - 02-12-2020
						
						doi_title[doi] = title
						
				params['s'] += max_rows
			elif response.status_code == 504:
				print('>> 504 Gateway Time-out:', doi)
			else:
				self.display_error_msg(response)
				sys.exit()
		
		return doi_title
		
		'''
		# https://spdi.public.springernature.app/xmldata/jats?q=doi:10.1007/s10948-017-4174-6&api_key=85c22905a0f193750f8ade233e68a632
		# https://media.springernature.com/lw685/springer-static/image/art%3A10.1007%2Fs10853-007-2173-x/MediaObjects/10853_2007_2173_Figa_HTML.gif
		
		doi = '10.1007/s10853-007-2173-x'
		fig_link = "MediaObjects/10853_2007_2173_Fig1_HTML.gif"
		
		retrieval_url = "https://media.springernature.com/lw685/springer-static/image/art:" + doi + '/' + fig_link
			
		response = requests.get(retrieval_url)
		
		if response.status_code == 200:
			with open('springer_test/test_img.gif', 'wb') as file:
				for chunk in response.iter_content(2048):
					file.write(chunk)
		else:
			error_msg = f'>> ERROR Code: {response.status_code}\n' + \
						f'>> URL: {response.url}\n' + \
						f'>> Resp txt: {response.text}'
			print(error_msg)
		

		sys.exit()
		
	
		
		dois = ['10.1007/s10853-007-2173-x']
		
		for doi in dois:
			retrieval_url = "https://spdi.public.springernature.app/xmldata/jats" + \
							"?q=doi:" + doi + \
							"&api_key=" + self.api_key
			
			#sleep(1)
			r_response = requests.get(retrieval_url)
			
			#print(r_response.headers)

			if r_response.status_code == 200:
				file = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
				file = file.lower()	# lowercase 
				#file_dir = self.path + file + '/'
				file_dir = 'springer_test/'
				#os.mkdir(file_dir)	# create a directory for each article.
				
				self.write_to_file(r_response, file_dir, file, ".xml")
				self.update_uid(doi)	# add a new uid - 02-12-2020
			elif r_response.status_code == 504:
				print('>> 504 Gateway Time-out:', doi)
			else:
				self.display_error_msg(r_response)
				sys.exit()
		
		#self.save_uids()    # save new uids in the uid file. -> changed to save uids right after write_to_file() since errors frequently occur between articles. - 02-12-2020
		'''



	def retrieve_articles_old(self, query):
		'''
		Parameters
		- s: Return results starting at the number specified.
		- p: The maximum number of results returned in a single query is 20 in the case of Openaccess requests
		'''
		max_rows = 20

		params = {'q': query, 's': 1, 'p': max_rows, 'api_key': self.api_key}

		search_url = "http://api.springernature.com/openaccess/json"
		
		dois = set()
		
		num_queries = 0
		while True:
			num_queries += 1

			s_response = requests.get(search_url, params=params)

			if s_response.status_code == 200:
				s_response = s_response.json()

				logger.debug(json.dumps(s_response, indent=4, sort_keys=True))

				if len(s_response['records']) == 0:
					break

				for item in s_response["records"]:
					dois.add(item["doi"].lower())
					
				params['s'] += max_rows
			else:
				self.display_error_msg(s_response)
				sys.exit()
		
		
		print(len(dois))
		
		dois = self.remove_duplicates(dois)   # skip already downloaded articles.
		
		print(len(dois))
		
		input()
		
		for doi in dois:
			retrieval_url = "http://api.springernature.com/openaccess/jats" + \
							"?q=doi:" + doi + \
							"&api_key=" + self.api_key
			
			sleep(1)
			r_response = requests.get(retrieval_url)
			
			#print(r_response.headers)

			if r_response.status_code == 200:
				file = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
				file = file.lower()	# lowercase 
				file_dir = self.path + file + '/'
				os.mkdir(file_dir)	# create a directory for each article.
				
				self.write_to_file(r_response, file_dir, file, ".xml")
				self.update_uid(doi)	# add a new uid - 02-12-2020
			elif r_response.status_code == 504:
				print('>> 504 Gateway Time-out:', doi)
			else:
				self.display_error_msg(r_response)
				sys.exit()
		
		#self.save_uids()    # save new uids in the uid file. -> changed to save uids right after write_to_file() since errors frequently occur between articles. - 02-12-2020
