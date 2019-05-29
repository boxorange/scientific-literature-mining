import sys
import json
import requests
from base_downloader import BaseDownloader
import logging

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
		self.springer_api_key = 'YOUR_API_KEY'
		self.destination = BaseDownloader.archive_path + "Springer/articles/"
	

	def retrieve_articles(self, query):
		'''
		Parameters
		- s: Return results starting at the number specified.
		- p: The maximum number of results returned in a single query is 20 in the case of Openaccess requests
		'''
		max_rows = 20

		params = {'q': query, 's': 1, 'p': max_rows, 'api_key': self.springer_api_key}

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
					dois.add(item["doi"])
					
				params['s'] += max_rows
			else:
				self.display_error_msg(s_response)
				sys.exit()
		
		dois = self.check_uids(dois)   # check if it's already downloaded.

		for doi in dois:
			retrieval_url = "http://api.springernature.com/openaccess/jats" + \
							"?q=doi:" + doi + \
							"&api_key=" + self.springer_api_key

			r_response = requests.get(retrieval_url)

			if r_response.status_code == 200:
				filename = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
				self.write_to_file(r_response, self.destination, filename, ".xml")
			else:
				self.display_error_msg(r_response)
				sys.exit()
		
		self.save_uids()    # save new uids in the uid file.
