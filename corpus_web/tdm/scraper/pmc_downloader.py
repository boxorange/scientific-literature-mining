import os
import sys
import json
import csv
import tarfile
import requests
from requests.utils import quote
from lxml import etree
from ftplib import FTP
from base_downloader import BaseDownloader
import logging

logger = logging.getLogger(__name__)


class PMCDownloader(BaseDownloader):
	"""
	Note:
	- It searches the entire text.
	- PubMed Central (PMC) is the U.S. National Institutes of Health (NIH) free digital archive of biomedical and life sciences journal literature.
	
	TODO:
	- Think more about ND (no derivatives) licenses: CC BY-ND CC BY-NC-ND
	
	References:
	- https://www.ncbi.nlm.nih.gov/home/develop/api/
	- https://www.ncbi.nlm.nih.gov/pmc/tools/get-full-text/
	- https://dataguide.nlm.nih.gov/eutilities/utilities.html
	- https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/180101/index.html
	- https://www.ncbi.nlm.nih.gov/books/NBK25498/#chapter3.Application_3_Retrieving_large
	- https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/
	- https://www.ncbi.nlm.nih.gov/pmc/tools/oai/#examples
	- https://www.ncbi.nlm.nih.gov/pmc/tools/articles-by-license/
	- https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
	"""


	def __init__(self):
		self.ncbi_api_key = 'YOUR_API_KEY'
		self.destination = BaseDownloader.archive_path + "PMC/"


	def download_files(self, uids):
		"""
		params
		- uids: dict of key: PMCID - value: either DOI or PMCID
		
		Comments:
		- Use of OA service https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/ to get file paths instead of reading oa_file_list.
		"""
		ftp = FTP('ftp.ncbi.nlm.nih.gov')
		ftp.login(user='anonymous', passwd='anonymous@anonymous.com')
		ftp.cwd('/pub/pmc')

		for pmc_id in uids.keys():
			found = False

			response = requests.get('https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=' + pmc_id)
			
			if response.status_code == 200:
				root = etree.fromstring(response.content)
				
				link = root.find('.//record/link[@format="tgz"]')
				
				if link is not None:	# e.g., PMC4486727 -> <error code="idIsNotOpenAccess">
					found = True
					
					link = link.get("href")	# e.g., ftp://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_package/8e/71/PMC5334499.tar.gz

					source = link.split('/pmc/', 1)[-1]
					filename = link.rsplit('/', 1)[-1]

					f = open(self.destination + filename, 'wb')
					ftp.retrbinary('RETR ' + source, f.write, 1024)
					f.close()

					tar = tarfile.open(self.destination + filename)
					tar.extractall(self.destination)
					tar.close()
					
					os.remove(self.destination + filename)
					
			if found is False:
				logger.error(f'>>> This PMCID - {pmc_id} is not in the server!!!')
				
				BaseDownloader.existing_uids.remove(uids.get(pmc_id))
				BaseDownloader.to_be_saved_uids.remove(uids.get(pmc_id))
			
		ftp.quit()


	def retrieve_articles(self, query):
		#search_url = 'https://www.ncbi.nlm.nih.gov/pmc'
		#params = {'term': query + ' AND cc license[filter]', 'retmax': 500}
		#response = requests.get(search_url, params=params)

		search_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
		id_converter_url = 'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/'

		'''
		Parameters
		- api_key: 10 requests per second (w/o 3 requests per second)
		- db: to narrow the search down to the pubmed DB only (e.g., db=pubmed)
		- retmode: to have a JSON string in response and not an XML (e.g., retmode=json)
		- retstart: Sequential index of the first UID in the retrieved set to be shown in the XML output (default=0, corresponding to the first record of the entire set).
		- retmax: to obtain 20 results (e.g., retmax=20)
		- sort: the results are sorted by relevance and not by added date which is the default ranking option on pubmed (e.g., sort=relevance)
		- term=[your query], the URL-encoded query
		'''
		search_params = {'api_key': self.ncbi_api_key, 'db': 'pmc', 'term': query + ' AND cc license[filter]', 'retmax': 200}
		id_converter_params = {'tool': 'tdm_project', 'email': 'gpark@bnl.gov', 'format': 'json'}

		# retrieve data in batches of 200
		# ID converter service allows for conversion of up to 200 IDs in a single request.
		uids = {}	# key: PMCID, value: either DOI or PMCID (if DOI doesn't exist)
		retstart = 0
		while True:
			s_response = requests.get(search_url, params=search_params)

			if s_response.status_code == 200:
				root = etree.fromstring(s_response.content)
				
				id_list = [child.text for child in root.find('IdList')]
				
				pmc_ids = ','.join(['PMC' + x for x in id_list])
				
				id_converter_params['ids'] = pmc_ids
				
				c_response = requests.get(id_converter_url, params=id_converter_params)

				if c_response.status_code == 200:
					c_response = c_response.json()
					
					for item in c_response['records']:
						#logger.debug(f">>> pmcid: {item['pmcid']} | doi: {item['doi']}")
						uids[item["pmcid"]] = item["doi"] if 'doi' in item else item["pmcid"]
					
					# if the number of results is less than retmax, RetMax returns the number or remaining counts.
					retstart += int(root.find('RetMax').text)

					#print('retstart:', retstart)

					if retstart == int(root.find('Count').text):
						break

					search_params['retstart'] = retstart
				else:
					self.display_error_msg(c_response)
					sys.exit()
			else:
				self.display_error_msg(s_response)
				sys.exit()
		
		duplicate_removed_uids = self.check_uids(set(uids.values()))   # check if it's already downloaded.

		uids.update({k: v for k, v in uids.items() if v in duplicate_removed_uids})

		self.download_files(uids)
		
		self.save_uids()    # save new uids in the uid file.


	# deprecated
	def update_oa_file_list(self):
		ftp = FTP('ftp.ncbi.nlm.nih.gov')
		ftp.login(user='anonymous', passwd='anonymous@anonymous.com')
		ftp.cwd('/pub/pmc/')

		source = 'oa_file_list.csv'

		f = open("oa_file_list.csv", 'wb')
		ftp.retrbinary('RETR ' + source, f.write, 1024)
		f.close()

		ftp.quit()


	# deprecated
	def download_files_using_csv_list(self, pmc_ids):
		"""
		params
		- pmc_ids: list of PMCIDs
		
		Comments
		- Use oa_file_list.csv downloaded from FTP server.
		"""
		ftp = FTP('ftp.ncbi.nlm.nih.gov')
		ftp.login(user='anonymous', passwd='anonymous@anonymous.com')
		ftp.cwd('/pub/pmc')

		csv_file = csv.reader(open('oa_file_list.csv', "rt"))
		csv_list = list(csv_file)	# to iterate multiple times w/o index reset, store it into a list.

		for pmc_id in pmc_ids:
			found = False
			for row in csv_list:
				# row: File | Article Citation | Accession ID (PMCID) | Last Updated (YYYY-MM-DD HH:MM:SS) | PMID | License
				if pmc_id == row[2]:
					found = True
					source = row[0]
					filename = row[0].split('/')[-1]

					f = open(self.destination + filename, 'wb')
					ftp.retrbinary('RETR ' + source, f.write, 1024)
					f.close()

					tar = tarfile.open(self.destination + filename)
					tar.extractall(self.destination)
					tar.close()
					break
					
			if found is False:
				logger.error(f'>>> This PMCID - {pmc_id} is not in the server!!!')
				
				BaseDownloader.existing_uids.remove(pmc_ids.get(pmc_id))
				BaseDownloader.to_be_saved_uids.remove(pmc_ids.get(pmc_id))
			
		ftp.quit()
