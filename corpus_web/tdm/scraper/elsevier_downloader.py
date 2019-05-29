import sys
import datetime
import json
import requests
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
	- https://dev.elsevier.com/tecdoc_text_mining.html
	- https://dev.elsevier.com/tips/ScienceDirectSearchTips.htm
	"""

	
	def __init__(self):
		self.elsevier_api_key = 'YOUR_API_KEY'
		self.destination = BaseDownloader.archive_path + "Elsevier/articles/"


	def retrieve_articles(self, query):
		search_headers = {'X-ELS-APIKEY': self.elsevier_api_key,
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

		search_url = "https://api.elsevier.com/content/search/sciencedirect"

		# check the number of results of the given query.
		# offset max value is 6000. If the total results exceed the number, split results by year.
		Is_date_field_needed = False
		s_response = requests.put(search_url, headers=search_headers, data=json.dumps(params))
		
		if s_response.status_code == 200:
			s_response = s_response.json()
			
			total_results = s_response["resultsFound"]
			accumulated_results = 0
			if total_results > 6000:    # offset max value is 6000
				Is_date_field_needed = True
				current_year = datetime.datetime.now()
				params['date'] = str(current_year.year)
			
			uids = {}	# key: PII, value: either DOI or PII (if DOI doesn't exist)
			
			while True:
				num_queries = 0
				while True:
					num_queries += 1

					# data must be json formatted.
					s_response = requests.put(search_url, headers=search_headers, data=json.dumps(params))

					if s_response.status_code == 200:
						s_response = s_response.json()

						logger.debug(json.dumps(s_response, indent=4, sort_keys=True))

						if s_response["resultsFound"] == 0:
							break

						for item in s_response["results"]:
							# DOIs are used to check if articles have been already downloaded.
							# if an article doesn't have a DOI, then just use a PII.
							# Here, PII is unformatted (e.g., formatted: S0022-2860(06)00707-1 <-> unformatted: S0022286006007071)
							uids[item["pii"]] = item["doi"] if 'doi' in item else item["pii"]
						
						if s_response["resultsFound"] < (num_queries*max_rows):
							break

						params['display']['offset'] += max_rows
					else:
						self.display_error_msg(s_response)
						sys.exit()
				
				accumulated_results += s_response["resultsFound"]
				
				# TODO: total_results must be the same as accumulated_results, but for some reason, they are different.
				# A possible reason is that the same paper appears in different years. 
				# print('total_results:', total_results, ' / accumulated_results:', accumulated_results, ' / date:', params['date'])
				if Is_date_field_needed == False or total_results <= accumulated_results:
					break

				params['date'] = str(int(params['date']) - 1)   # decrease date until it finds all articles.
				params['display']['offset'] = 0                 # reset offset
			
			
			duplicate_removed_uids = self.check_uids(set(uids.values()))   # check if it's already downloaded.

			piis = [k for k, v in uids.items() if v in duplicate_removed_uids]

			for pii in piis:
				retrieval_uri = "https://api.elsevier.com/content/article/pii/" + pii

				retrieval_headers = {'X-ELS-APIKEY': self.elsevier_api_key}

				r_response = requests.get(retrieval_uri, headers=retrieval_headers)

				if r_response.status_code == 200:
					self.write_to_file(r_response, self.destination, pii, ".xml")
				else:
					self.display_error_msg(r_response)
					sys.exit()

			self.save_uids()    # save new uids in the uid file.
		else:
			self.display_error_msg(s_response)
			sys.exit()
