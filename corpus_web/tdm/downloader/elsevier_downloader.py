import os
import sys
from datetime import datetime
import json
import requests
from time import sleep
from base_downloader import BaseDownloader
import logging

logger = logging.getLogger(__name__)


class ElsevierDownloader(BaseDownloader):
	"""
	Note:
	- For performance reasons, a search request returns up to 200 results in a single response.
	  Multiple requests can be used to collate more than 200 results -> the new version indicates that the max value is 100
	- The max offset value is 6000, so if total results exceeed the number, then work-around it by spliting the number of results using date.
	- PUT method (cf. GET) is highly recommended for ScienceDirect Search API.
	- Don't use title for filename since titles contain special characters. Instead, use PII for filenames.
	- Use PII (Elsevier's own internal document identifier) to collate articles instead of DOI because not all articles have a DOI.
	  But, use DOIs (unless it doensn't exist) for duplicate check to match uids with other publishers.
	  Eg., PII: S0151910701800544 -> No DOI!!
	  [2001] Étude de l'ordre local par mesure enthalpique différentielle et par exafs en transmission dans les matériaux du système GeTeSb (by ZinebBouchaour et al.)
	
	References:
	- https://dev.elsevier.com/tecdoc_sdsearch_migration.html
	- https://dev.elsevier.com/support.html
	- https://dev.elsevier.com/tecdoc_text_mining.html
	- https://dev.elsevier.com/tips/ScienceDirectSearchTips.htm
	"""

	
	def __init__(self):
		super().__init__('Elsevier')

	
	def get_uid(self, response, uid, doi_title):
		if "results" in response:
			for item in response["results"]:
				# DOIs are used to check if articles have been already downloaded.
				# if an article doesn't have a DOI, then just use a PII.
				# Here, PII is unformatted (e.g., formatted: S0022-2860(06)00707-1 <-> unformatted: S0022286006007071)
				uid[item["pii"]] = item["doi"].lower() if "doi" in item else item["pii"].lower()
				
				if "doi" in item:
					doi_title[item["doi"].lower()] = item["title"]


	def retrieve_articles(self, query, year):
		search_headers = {'X-ELS-APIKEY': self.api_key,
						  'Content-Type': 'application/json',
						  'Accept': 'application/json'}

		max_rows = 100
		
		'''
		Parameters
		- qs: The general search field for searching over all article / book chapter content (excluding references)
		- '&subscribed=true' parameter doesn't work in search request
		'''
		params = {'qs': query,
				  'display': {
					  'offset': 0,
					  'show': max_rows,
					  'sortBy': 'relevance'
					  }
				 }
		
		if year is not None:
			params['date'] = str(year)
		
		search_url = "https://api.elsevier.com/content/search/sciencedirect"

		is_date_field_needed = False
		s_response = requests.put(search_url, headers=search_headers, data=json.dumps(params))	# search response
		
		if s_response.status_code == 200:
			s_response = s_response.json()
			
			total_results = s_response["resultsFound"]	# check the number of results of the given query.
			accumulated_results = 0
			if total_results > 6000:    # offset max value is 6000. If the total results exceed the number, split results by year.
				is_date_field_needed = True
				current_date_time = datetime.now()
				current_year = current_date_time.year + 1	# start searching from the following year (e.g., current year 2019, then 2020) because some publications are released in the following year.
				params['date'] = str(current_year)
			
			uid = {}		# key: PII, value: either DOI or PII (if DOI doesn't exist)
			doi_title = {}	# this is to save the history of downloads.
			
			finish_search = False # used for COVID-19 project

			while True:
				num_queries = 0
				while True:
					num_queries += 1
					
					'''
					consecutive requests without delay causes 429 error even though rate limit doesn't exceeds (check the limit in headers - 'X-RateLimit-Remaining')
						<error-code>RATE_LIMIT_EXCEEEDED</error-code> 
						<error-message>Rate of requests exceeds specified limits. Recommend lowering request rate and/or concurrency of requests.</error-message>
					Adding a time delay can avoid this 429 error.
					'''
					sleep(1)

					# data must be json formatted.
					s_response = requests.put(search_url, headers=search_headers, data=json.dumps(params))

					if s_response.status_code == 200:
						s_response = s_response.json()

						logger.debug(json.dumps(s_response, indent=4, sort_keys=True))

						if s_response["resultsFound"] == 0:
							break
						
						""" START - Special case of COVID-19
						The number of COVID related articles exceeds 6000 in 2020. 
						So, retrieve the most recent articles up to 6000 by month.
						"""
						total_results_in_year = s_response["resultsFound"]	# debugging
						accumulated_results_in_year = 0		# debugging
						if total_results_in_year > 6000:    # offset max value is 6000
							params['date'] = None
							params['sortBy'] = 'date'
							params['loadedAfter'] = datetime(current_year, current_date_time.month, 1).isoformat() # year, month, day
							params['loadedAfter'] += 'Z'	# Z is utc timezone
							params['display']['offset'] = 0	# reset offset
							
							num_queries_in_month = 0
							
							while True:
								num_queries_in_month += 1
								
								sleep(1)
								s_r_by_month = requests.put(search_url, headers=search_headers, data=json.dumps(params)) # search response by month

								if s_r_by_month.status_code == 200:
									s_r_by_month = s_r_by_month.json()

									logger.debug(json.dumps(s_r_by_month, indent=4, sort_keys=True))

									if s_r_by_month["resultsFound"] == 0:
										break
									
									self.get_uid(s_r_by_month, uid, doi_title)

									if s_r_by_month["resultsFound"] <= (num_queries_in_month*max_rows):
										break
										
									params['display']['offset'] += max_rows
									
									if params['display']['offset'] > 6000:
										break
								else:
									self.display_error_msg(s_r_by_month)
									sys.exit()
							
							# debugging
							accumulated_results_in_year += s_r_by_month["resultsFound"]
							print('total_results_in_year:', total_results_in_year, ' / accumulated_results_in_year:', accumulated_results_in_year, ' / loadedAfter:', params['loadedAfter'])
							print('len(uid):', len(uid), ' / len(doi_title):', len(doi_title))
							
							finish_search = True
							break
							""" END - Special case of COVID-19 """
						else:
							self.get_uid(s_response, uid, doi_title)
						
						if s_response["resultsFound"] <= (num_queries*max_rows):
							break

						params['display']['offset'] += max_rows
					else:
						self.display_error_msg(s_response)
						sys.exit()
				
				if finish_search:	# used for COVID-19 project
					break
				
				accumulated_results += s_response["resultsFound"]
				
				'''
				TODO: total_results must be the same as accumulated_results, but for some reason, they are different.
				A possible reason is that the same paper appears in different years. 
				'''
				print('total_results:', total_results, ' / accumulated_results:', accumulated_results, ' / date:', params['date'])
				if is_date_field_needed == False or total_results <= accumulated_results:
					break
				
				current_year -= 1	# decrease date until it finds all articles.
				params['date'] = str(current_year)
				params['display']['offset'] = 0	# reset offset
			
			
			print("Before uid:", len(uid))

			duplicate_removed_uid = self.remove_duplicates(set(uid.values()))   # skip already downloaded articles.

			uid = {k: v for k, v in uid.items() if v in duplicate_removed_uid}
			doi_title = {k: v for k, v in doi_title.items() if k in duplicate_removed_uid}

			print("After uid:", len(uid))

			for pii, doi in uid.items():
				
				if pii in self.error_list:
					continue
				
				retrieval_uri = "https://api.elsevier.com/content/article/pii/" + pii

				retrieval_headers = {'X-ELS-APIKEY': self.api_key}

				sleep(1)
				r_response = requests.get(retrieval_uri, headers=retrieval_headers)	# retrieval response

				if r_response.status_code == 200:
					# doi for dir/file names
					'''
					file = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
					file = file.lower()	# lowercase 
					file_dir = self.path + file + '/'
					os.mkdir(file_dir)	# create a directory for each article.
					self.write_to_file(r_response, file_dir, file, ".xml")
					'''
					# pii for dir/file names
					file_dir = self.path + pii + '/'
					if not os.path.exists(file_dir):
						os.mkdir(file_dir)	# create a directory for each article.
					self.write_to_file(r_response, file_dir, pii, ".xml")
					
					self.update_uid(doi)	# add a new uid - 02-12-2020
				else:
					self.display_error_msg(r_response)
					sys.exit()

			#self.save_uids()    # save new uids in the uid file. -> changed to save uids right after write_to_file() since errors frequently occur between articles. - 02-12-2020
			
			return doi_title
		else:
			self.display_error_msg(s_response)
			sys.exit()
