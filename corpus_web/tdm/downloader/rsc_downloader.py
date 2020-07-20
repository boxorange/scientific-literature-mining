import os
import sys
import json
import re
import lxml
import requests
from time import sleep
from base_downloader import BaseDownloader

import chemdataextractor.scrape.pub.rsc as RSC
from chemdataextractor.scrape import Selector
from chemdataextractor.scrape.pub.rsc import RscHtmlDocument
from chemdataextractor.doc import Document
from chemdataextractor.reader.rsc import RscHtmlReader

import logging

logger = logging.getLogger(__name__)


class RSCDownloader(BaseDownloader):
	"""
	Note:
	- 
	
	References:
	- 
	
	Licenses:
	- 
	"""
	
	rsc_scraper = RSC.RscSearchScraper()

	def __init__(self):
		super().__init__('RSC')
		self.sleep_sec = 10	# Keep delays to 10-20 seconds between requests.


	def retrieve_articles(self, query):
		'''
		Parameters:
		- 
		'''
		params = {'Category': 'Journal', 
				  'searchtext': query,	# don't use 'ExactText'
				  'OpenAccess': 'false',
				  'SortBy': 'Relevance',
				  'PageSize': 100}
				  
		headers = {'User-Agent': 'TDMCrawler; mailto: gpark@bnl.gov; BNL CSI Literature mining project'}
		
		s_response = self.rsc_scraper.http.get('https://pubs.rsc.org/en/results', params=params, headers=headers)
		
		all_new_doi_title = {}	# this is to save the history of downloads.
		
		if s_response.status_code == 200:
			selector = Selector.from_html(s_response)
			sessionkey = selector.css('#SearchTerm::attr("value")').extract()[0]

			page_num = 1
			while True:
				searchdata = {'searchterm': sessionkey, 'resultcount': 100, 'category': 'journal', 'pageno': page_num}
				
				sleep(self.sleep_sec)
				s_response = self.rsc_scraper.http.post('https://pubs.rsc.org/en/search/journalresult', data=searchdata, headers=headers)
				
				if s_response.status_code == 200:
					doc = lxml.html.fromstring(s_response.text)
					
					articles = doc.find_class("capsule capsule--article")
					
					article_info = {}
					doi_title = {}
					for article in articles:
						#print(article.text_content())
						doi = title = ''
						
						if len(article.xpath('.//a[contains(text(),"doi.org")]')) > 0:
							doi = article.xpath('.//a[contains(text(),"doi.org")]')[0].text
							doi = doi.split('org/')[1]
							doi = doi.lower()
						
						if article.find_class("capsule__title"):
							title = article.find_class("capsule__title")[0].text_content().strip()

						html_link = ''
						if len(article.xpath('.//a[text()="Article HTML"]')) > 0:
							html_link = 'https://pubs.rsc.org' + article.xpath('.//a[text()="Article HTML"]')[0].get("href")

						if html_link != '' and doi != '':
							article_info[doi] = html_link
							doi_title[doi] = title

					print('<RSC> #UIDs w/  duplicates:', len(article_info))
					duplicate_removed_uids = self.remove_duplicates(set(article_info.keys()))   # skip already downloaded articles.
					print('<RSC> #UIDs w/o duplicates:', len(duplicate_removed_uids))
									
					article_info = {k: v for k, v in article_info.items() if k in duplicate_removed_uids}
					all_new_doi_title.update({k: v for k, v in doi_title.items() if k in duplicate_removed_uids})

					""" Download articles """
					for doi, html_link in article_info.items():
						sleep(self.sleep_sec)
						r_response = self.rsc_scraper.http.get(html_link, headers=headers)

						if r_response.status_code == 200:
							file = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
							file = file.lower()	# lowercase 
							file_dir = self.path + file + '/'
							os.mkdir(file_dir)	# create a directory for each article.
							
							self.write_to_file(r_response, file_dir, file, ".html")
							self.update_uid(doi)	# add a new uid - 02-12-2020
						else:
							self.display_error_msg(r_response)
							sys.exit()
					
					num_of_results = len(articles)

					print('num_of_results:', num_of_results)
					
					if num_of_results < 100:
						break
					else:
						page_num += 1
				else:
					self.display_error_msg(s_response)
					sys.exit()

			#self.save_uids()    # save new uids in the uid file. -> changed to save uids right after write_to_file() since errors frequently occur between articles. - 02-12-2020
			
			return all_new_doi_title
		else:
			self.display_error_msg(s_response)
			sys.exit()

