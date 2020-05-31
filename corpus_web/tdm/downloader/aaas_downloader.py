import os
import sys
import datetime as DT
from time import sleep
import json
import requests
from base_downloader import BaseDownloader
import logging

logger = logging.getLogger(__name__)

#from lxml import etree
from lxml.html import parse, fromstring


class AAASDownloader(BaseDownloader):
	"""
	Note:
	- search address: http://science.sciencemag.org/search
	- crawl address: http://science.sciencemag.org/content
	
	References:
	- cdesnowball-master\chemdataextractor\scrape\selector.py
	- cdesnowball-master\chemdataextractor\scrape\pub\rsc.py
	"""
	

	def __init__(self):
		super().__init__('AAAS')
		self.sleep_sec = 5	# the max speed is one request every 5 seconds.
	
	
	def retrieve_articles(self, keywords, year=None, enable_sleep=True):
		headers = {'User-Agent': 'Mozilla/5.0; mailto: gpark@bnl.gov; BNL CSI Literature mining project', 'Accept': 'text/html'}
		
		'''
		# TODO: for some reason, param doesn't work. 
		params = {
					#'searchTerm': 'exafs'
					'text_abstract_title': 'exafs',
					'text_abstract_title_flags': 'match-all',
					'format_result': 'condensed',	# standard, condensed
					'numresults': '100',
					'sort': 'relevance-rank'
				}
		#s_response = requests.get("http://science.sciencemag.org/search", headers=headers, params=params)
		'''
		
		# parameters
		num_of_results = '100'
		sort = 'relevance-rank'
		result_fmt = 'condensed'	# standard, condensed
		
		'''
		Keyword search option:
		- match-any: To find documents where at least one of your search terms must appear in returned documents.
		- match-all: To find documents where all of your search terms must appear in returned documents, even if they are far apart from each other.
		- match-phrase: To find documents where your search terms appear together.
		
		CASE SENSITIVITY: https://www.sciencemag.org/site/help/readers/search.xhtml#section_case-sensitivity
		'''
		search_option = 'match-phrase'
		
		base_url = "https://science.sciencemag.org"
		
		doi_link = {}
		doi_title = {}	# this is to save the history of downloads.
		for keyword in keywords:
			search_url = base_url + "/search/text_abstract_title:" + keyword \
						 + " text_abstract_title_flags:" + search_option \
						 + " jcode:sci||sigtrans||scitransmed||advances||immunology||robotics" \
						 + " numresults:" + num_of_results \
						 + " sort:" + sort \
						 + " format_result:" + result_fmt
			
			if year is not None:
				today = DT.date.today()
				week_ago = today - DT.timedelta(days=7)
				search_url += " limit_from:" + week_ago.strftime("%Y-%m-%d") + " limit_to:" + today.strftime("%Y-%m-%d")

			# search articles.
			while True:
				if enable_sleep:
					sleep(self.sleep_sec)
				s_response = requests.get(search_url, headers=headers)

				#print(s_response.url)
				#print(s_response.headers)

				if s_response.status_code == 200:
					#page = parse(s_response.content).getroot()
					page = fromstring(s_response.content, base_url=s_response.url)
					
					#cls.from_response(response, parser=HTMLParser, translator=CssHTMLTranslator, fmt='html', namespaces=namespaces)
					#cls.from_text(response.content, response.url, parser, translator, fmt, namespaces=namespaces, encoding=response.encoding)
					#root = fromstring(text, parser=parser(recover=True, encoding=cls._get_encoding(text, encoding)), base_url=base_url)
					
					# this makes links absolute by the given url. 
					# e.g., /content/314/5800/821.full -> https://science.sciencemag.org/content/314/5800/821.full
					# 		http://advances.sciencemag.org/content/3/8/e1603068.full -> http://advances.sciencemag.org/content/3/8/e1603068.full
					page.make_links_absolute()

					articles = page.findall('.//article')
					
					for article_elem in articles:
						info_link = article_elem.find_class("highwire-cite-linked-title")[0].attrib['href']	# to find DOI, get the article's information page
						
						if enable_sleep:
							sleep(self.sleep_sec)
						i_response = requests.get(info_link, headers=headers)
						
						if i_response.status_code == 200:
							info_page = fromstring(i_response.content)

							doi = info_page.find('.//meta[@name="DC.Identifier"]').attrib['content']
							doi = doi.lower()
							title = info_page.find('.//meta[@name="DC.Title"]').attrib['content']
														
							html_text = article_elem.find_class("highwire-variant-link variant-full-text")

							link = ''
							if len(html_text) > 0:	# if html text is provided,
								link = html_text[0].attrib['href']
							else:	# no HTML text
								abstract = article_elem.find_class("highwire-variant-link variant-abstract")
								pdf_text = article_elem.find_class("highwire-variant-link variant-full-textpdf link-icon")
								
								# TODO: add abstract!!
								if len(pdf_text) > 0:	# if html text is provided,
									link = pdf_text[0].attrib['href']
							
							if link:
								doi_link[doi] = link
								doi_title[doi] = title

						else:
							# Sometimes, Page Not Found (404 error) occurs. Don't exit, but ignore it.
							# e.g., "New Approaches to Surface Structure Determinations" - https://science.sciencemag.org/content/214/4518/300
							print("<AAAS-retrieve_articles()> Error!! info_link:", info_link)
							self.display_error_msg(i_response)

					# reference: https://lxml.de/3.1/api/private/lxml.html.HtmlElement-class.html
					next_page = page.find_class("pager-next")	# find_class returns a list.

					if len(next_page) > 0:
						link = next_page[0].find('a')
						if link is not None:
							search_url = link.attrib['href']
					else:
						break
				else:
					self.display_error_msg(s_response)
					sys.exit()

		print("<AAAS-retrieve_articles()> Before uids:", len(doi_link))
		duplicate_removed_uids = self.remove_duplicates(set(doi_link.keys()))   # skip already downloaded articles.
		print("<AAAS-retrieve_articles()> After uids:", len(duplicate_removed_uids))

		doi_link = {k: v for k, v in doi_link.items() if k in duplicate_removed_uids}
		doi_title = {k: v for k, v in doi_title.items() if k in duplicate_removed_uids}

		""" Download articles """
		for doi, link in doi_link.items():
			if enable_sleep:
				sleep(self.sleep_sec)
			r_response = requests.get(link, headers=headers)
			#r_response = requests.get("https://science.sciencemag.org/content/sci/275/5305/1452/F1.medium.gif", headers=headers)
			
			if r_response.status_code == 200:
				file = ''.join(i for i in doi if i.isalnum())   # special characters are removed for filenames.
				file = file.lower()	# lowercase 
				file_dir = self.path + file + '/'
				os.mkdir(file_dir)	# create a directory for each article.
				
				file_ext = ".pdf" if link.endswith('pdf') else ".html"
				self.write_to_file(r_response, file_dir, file, file_ext)
				self.update_uid(doi)	# add a new uid - 02-12-2020
			else:
				self.display_error_msg(r_response)
				sys.exit()
		
		#self.save_uids()    # save new uids in the uid file. -> changed to save uids right after write_to_file() since errors frequently occur between articles. - 02-12-2020
		
		return doi_title
