import os
import sys
import requests
import json
import re
from time import sleep
from lxml import etree, html
from base_parser import BaseParser

import chemdataextractor.scrape.pub.rsc as RSC
from chemdataextractor.scrape import Selector
from chemdataextractor.scrape.pub.rsc import RscHtmlDocument
from chemdataextractor.doc import Document, Title, Heading, Paragraph, Caption, Citation, Footnote, Text, Sentence, Figure
from chemdataextractor.reader.rsc import RscHtmlReader

import logging

logger = logging.getLogger(__name__)


class AAASParser(BaseParser):
	"""
	Note:
	- 
	
	References:
	- 
	"""
	
	rsc_html_reader = RscHtmlReader()
	#rsc_scraper = RSC.RscSearchScraper()
	

	def __init__(self):
		super().__init__('AAAS')
		#self.sleep_sec = 10	# Keep delays to 10-20 seconds between requests.
	

	def update_uid_list(self):
		num_of_empty_body_article = 0

		doi_list = set()

		dir = self.path
		for file in os.listdir(dir):
			if file.endswith(".html"):
				htmlstring = open(os.path.join(dir, file)).read()
				htmlstring = re.sub(r'<\?xml.*\?>', '', htmlstring)

				sel = Selector.from_text(htmlstring)
				scrape = RscHtmlDocument(sel)
				if scrape.doi is None:
					print('No DOI:', file)
				else:
					doi_list.add(scrape.doi.lower())

		existing_uids = set([line.strip().lower() for line in open(self.uid_list)])
		
		doi_list.difference_update(existing_uids)   # remove any duplicates

		with open(self.uid_list, 'a') as file:
			for doi in doi_list:
				file.write("%s\n" % doi)
	
	"""
	def get_object(self, html_file):
		htmlstring = open(html_file).read()
		'''
		Remove encoding declaration since it causes the following error when Selector reads the string.
			-> ValueError: Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
		'''
		htmlstring = re.sub(r'<\?xml.*\?>', '', htmlstring)
		
		sel = Selector.from_text(htmlstring)
		scrape = RscHtmlDocument(sel)
		
		location = html_file.rsplit('/', 1)[0]

		# skip already downloaded files. Count the number of files except html and json file.
		if len(scrape.figures) == len([name for name in os.listdir(location) if name.endswith('.html') == False and name.endswith('.json') == False]):
			print('<get_objects()> Figures are already downloaded!!')
			return

		num_of_downloaded_objs = 0
		
		headers = {'User-Agent': 'TDMCrawler; mailto: gpark@bnl.gov; BNL CSI Literature mining project'}
		
		for fig in scrape.figures:
			if fig.url is not None:
				fig_url = 'https://pubs.rsc.org' + fig.url
				
				#sleep(self.sleep_sec)
				response = self.rsc_scraper.http.get(fig_url, headers=headers)

				if response.status_code == 200:
					filename = fig.url.rsplit('/', 1)[1]

					with open(location + "/" + filename, 'wb') as file:
						for chunk in response.iter_content(2048):
							file.write(chunk)
							
					num_of_downloaded_objs += 1
				else:
					error_msg = f'>> ERROR Code: {response.status_code}\n' + \
								f'>> URL: {response.url}\n' + \
								f'>> Resp txt: {response.text}'
					#logger.error(error_msg)
					print(error_msg)

		print('>> Total figures:', len(scrape.figures), '/ Downloaded figure:', num_of_downloaded_objs)
	"""
	
	def get_sentence(self, paragraph, para_id, specials, refs, sec_title=''):
		sents = []

		elements = self.rsc_html_reader._parse_element(paragraph, specials=specials, refs=refs)
		doc = Document(*elements)
		for para in doc.paragraphs: # Document object doesn't have direct access to sentences.
			for sent in para.sentences:
				token = []
				start = []
				end = []
				for tok in sent.tokens:
					token.append(tok.text)
					start.append(tok.start - sent.start)
					end.append(tok.end - sent.start)

				pos = sent.pos_tags

				cems = []
				for cem in sent.cems:
					cems.append([cem.text, cem.start - sent.start, cem.end - sent.start])

				sents.append({'section_title': sec_title, 
							  'para_id': para_id, 
							  'sent': sent.text, 
							  'token_pos': list(zip(token, start, end, pos)),
							  'chemical_entity': cems})
		
		# debug
		if len(sents) > 0 and para_id is None:
			for _ in sents:
				print(_)
			input('!!! para_id is none !!!')
		
		return sents
		

	def parse(self, html_file):
		"""
		TODO: handle figures
		"""
		htmlstring = open(html_file).read()
		
		'''
		Remove encoding declaration since it causes the following error when Selector reads the string.
			-> ValueError: Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
		'''
		htmlstring = re.sub(r'<\?xml.*\?>', '', htmlstring)

		document = html.fromstring(htmlstring)
		
		publisher = document.find('.//meta[@name="DC.Publisher"]').get('content')
		article_type = document.find('.//meta[@name="category"]').get('content')
		article_title = document.find('.//meta[@name="DC.Title"]').get('content')
		year = document.find('.//meta[@name="DC.Date"]').get('content')
		article_doi = document.find('.//meta[@name="DC.Identifier"]').get('content')
		authors = [author.get('content') for author in document.findall('.//meta[@name="DC.Contributor"]')]
		keywords = []
		for keyword in document.find_class("kwd"):
			keyword_name = keyword.text
			if keyword_name:
				keywords.append(keyword_name)
		
		tree = etree.parse(html_file, self.html_parser)
		root = tree.getroot()

		# clean xml and extract essential elements.
		specials, refs = self.rsc_html_reader.preprocess(root)

		abstract_element = document.find_class("section abstract")
		abstract_paragraphs = []
		for elem in abstract_element:
			abstract_paragraphs.extend(elem.findall('.//p'))	# paragraphs

		abstract = []
		para_idx = 1	# used when id is not available from article.
		for para in abstract_paragraphs:
			para_id = para.get('id')
			if para_id is None:
				para_id = 'abs_para_' + str(para_idx)
				para_idx += 1
			abstract.extend(self.get_sentence(para, para_id, specials, refs))

		fulltext_cls = document.find_class("article fulltext-view")
		#sections = fulltext[0].find_class("section")	# some texts do not belong to sections. e.g., 101126scienceabb4218.html
		#body_sections = [sec for sec in sections if sec.get('class') not in ['section abstract', 'section app', 'section ref-list']]
		
		body_elem = []
		for fulltext in fulltext_cls:
			for elem in fulltext:
				if elem.tag == 'div':
					if elem.get('class') not in ['section abstract', 'section app', 'section ref-list']:
						body_elem.append(elem)
				elif elem.tag == 'p':
					body_elem.append(elem)
			break	# article fulltext-view must be a single element, so just check the first one.
		
		body_text = []
		para_idx = 1	# used when id is not available from article.
		for elem in body_elem:
			if elem.tag == 'div':
				heading = elem.xpath(".//*[starts-with(name(),'h')]")
				sec_title = heading[0].text if len(heading) > 0 else ''
				for para in elem.findall('.//p'):	# paragraphs
					para_id = para.get('id')
					if para_id is None:
						para_id = 'body_para_' + str(para_idx)
						para_idx += 1
					body_text.extend(self.get_sentence(para, para_id, specials, refs, sec_title=sec_title))
			elif elem.tag == 'p':
				para_id = elem.get('id')
				if para_id is None:
					para_id = 'body_para_' + str(para_idx)
					para_idx += 1
				body_text.extend(self.get_sentence(elem, para_id, specials, refs))
		
		# For articles that don't have body texts such as letters or editorial, just store descriptions in meta data. e.g., 101126scienceabb6502.html, 101126scienceabb8034.html
		# Determined not to consider this type of articles. 
		#if len(abstract) == 0 and len(body_text) == 0:
			#<meta name="DC.Description" content="As pandemic coro...."

		figures = []
		'''
		sel = Selector.from_text(htmlstring)
		scrape = RscHtmlDocument(sel)

		
		for fig in scrape.figures:
			id = fig.reference if fig.reference is not None else fig.label
			label = fig.label
			
			if id is None:	# e.g., 101039b918103b.html has an image having only url information.
				print('figure id is none.')
				continue
			
			fig_file = html_file.rsplit('/', 1)[0] + '/' + fig.url.rsplit('/', 1)[1]
				
			caption = []
			#cap = Text(fig.caption)
			#print(cap.sentences)
			if fig.caption is not None:
				for sent in Text(fig.caption):
					token = []
					start = []	# start offset
					end = []	# end offset
					for tok in sent.tokens:
						token.append(tok.text)
						start.append(tok.start - sent.start)
						end.append(tok.end - sent.start)

					pos = sent.pos_tags

					cems = []
					for cem in sent.cems:
						cems.append([cem.text, cem.start - sent.start, cem.end - sent.start])
						
					caption.append({'sent': sent.text, 
									'token_pos': list(zip(token, start, end, pos)),
									'chemical_entity': cems})

			figures.append({'fig_id': id,
							'label': label,
							'caption': caption, 
							'fig_file': fig_file})
		'''
		
		data = {}
		data['uid'] = article_doi
		data['publisher'] = publisher
		data['type'] = article_type
		data['title'] = article_title
		data['year'] = year
		data['author'] = authors
		data['keywords'] = keywords
		data['abstract'] = abstract
		data['body_text'] = body_text
		data['figures'] = figures
		
		
		print('https://doi.org/' + article_doi)
		print(article_type)
		print(article_title)

		# write data to file
		output_file = html_file.replace('.html', '.json')
		if output_file == html_file:
			logger.error('>> HTML file does NOT exist!!')
			sys.exit()
		
		with open(output_file, 'w') as outfile:
			json.dump(data, outfile)
		
		return article_doi

