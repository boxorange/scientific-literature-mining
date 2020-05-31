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


class RSCParser(BaseParser):
	"""
	Note:
	- 
	
	References:
	- 
	"""
	
	rsc_html_reader = RscHtmlReader()
	rsc_scraper = RSC.RscSearchScraper()
	

	def __init__(self):
		super().__init__('RSC')
		self.sleep_sec = 10	# Keep delays to 10-20 seconds between requests.
	

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
					logger.error('No DOI: ' + file)
				else:
					doi_list.add(scrape.doi.lower())

		existing_uids = set([line.strip().lower() for line in open(self.uid_list)])
		
		doi_list.difference_update(existing_uids)   # remove any duplicates

		with open(self.uid_list, 'a') as file:
			for doi in doi_list:
				file.write("%s\n" % doi)
	
	
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
			print('<get_object()> Figures are already downloaded!!')
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
					logger.error(error_msg)

		print('<get_object()> Total figures:', len(scrape.figures), '/ Downloaded figure:', num_of_downloaded_objs)

	
	def get_sentence(self, elem, para_id_prefix, start_para_idx, specials, refs, sec_title=''):
		sents = []
		
		elements = self.rsc_html_reader._parse_element(elem, specials=specials, refs=refs)
		doc = Document(*elements)
		para_idx = start_para_idx
		for para in doc.paragraphs:
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
							  'para_id': para_id_prefix + '_para_' + str(para_idx), 
							  'sent': sent.text, 
							  'token_pos': list(zip(token, start, end, pos)),
							  'chemical_entity': cems})
			para_idx += 1

		return para_idx, sents


	def parse(self, html_file):
		"""
		TODO: clean body texts. 02-11-2020
		Unlike other XML files, tags for body texts are not quite consistent. 
		For now, use CDE's reader to get body texts, and they have not only body texts but other preceding texts such as abstract.
		CDE's scraper can only body texts (scrape.paragraphs), but they are pure strings unlike Sentence instances.
		-> Exclude abstract and its preceding text from body text by last sentence of abstract in body text. 02-18-2020
		"""
		htmlstring = open(html_file).read()
		
		'''
		Remove encoding declaration since it causes the following error when Selector reads the string.
			-> ValueError: Unicode strings with encoding declaration are not supported. Please use bytes input or XML fragments without declaration.
		'''
		htmlstring = re.sub(r'<\?xml.*\?>', '', htmlstring)

		tree = etree.parse(html_file, self.html_parser)
		root = tree.getroot()

		# clean xml and extract essential elements.
		specials, refs = self.rsc_html_reader.preprocess(root)

		document = html.fromstring(htmlstring)
		
		title = document.findtext('.//title')	# this title is only used to filter out the following error. The title from scrape below is used for JSON file.
		if title.strip() == 'RSC - Page load error':	# e.g., 101039c1jm11358e.html
			logger.error('RSC - Page load error')
			return None
		
		abstract_element = document.find_class("abstract")
		abstract = []
		start_para_idx = 1
		for abs in abstract_element:
			para_id_prefix = 'abs'
			start_para_idx, sents = self.get_sentence(abs, para_id_prefix, start_para_idx, specials, refs)
			abstract.extend(sents)	
			
		''' Body Text '''
		f = open(html_file, 'rb')
		doc = Document.from_file(f, readers=[self.rsc_html_reader])
		
		body_text = []
		sec_title = ''
		para_id_prefix = 'body'
		para_idx = 1
		for elem in doc.elements:
			if isinstance(elem, Heading):
				sec_title = elem.text
			elif isinstance(elem, Paragraph):
				for sent in elem.sentences:
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

					body_text.append({'section_title': sec_title, 
									  'para_id': para_id_prefix + '_para_' + str(para_idx), 
									  'sent': sent.text, 
									  'token_pos': list(zip(token, start, end, pos)),
									  'chemical_entity': cems})
				para_idx += 1

		# Exclude abstract and its preceding text from body text. 02-18-2020
		cut_off = -1
		#if len(abstract) != 0 and len(body_text) != 0 and all(elem in body_text for elem in abstract): # Sometimes, abstract and body have different whitespaces. e.g., 101039c005501h.json
		if len(abstract) != 0 and len(body_text) != 0:
			if len(abstract) < 3:	# debugging
				print('Abstract is a single sentence!!')
			for idx in range(len(body_text)):
				# compare only sent and remove leading and trailing whitespaces. Sometimes, abstract and body have different whitespaces. e.g., 101039c005501h.json
				# also compare preceding two sentences of the last one to increase accuracy. Some abstracts are a single sentence. e.g., 101039c2cp23070d.html
				#if abstract[-1]['sent'].strip() == body_text[idx]['sent'].strip() and abstract[-2]['sent'].strip() == body_text[idx-1]['sent'].strip() and abstract[-3]['sent'].strip() == body_text[idx-2]['sent'].strip():	
				if len(re.sub(r"[^a-zA-Z]", '', abstract[-1]['sent'])) > 0:	# ignore sents having non-alphabets such as '.', '\n'
					if re.sub(r'\s+', '', abstract[-1]['sent']) == re.sub(r'\s+', '', body_text[idx]['sent']):
						cut_off = idx + 1
						break
				
		if cut_off != -1:
			body_text = body_text[cut_off:]	
		
		
		''' Figures '''	
		sel = Selector.from_text(htmlstring)
		scrape = RscHtmlDocument(sel)

		figures = []
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

		data = {}
		data['uid'] = scrape.doi
		data['publisher'] = scrape.publisher + (' - ' + scrape.journal if scrape.journal is not None else '')
		data['type'] = 'journal' if scrape.journal is not None else ''
		data['title'] = scrape.title
		data['year'] = ''
		if scrape.published_date is not None:
			data['year'] = scrape.published_date.strftime("%Y")
		elif scrape.online_date is not None:
			data['year'] = scrape.online_date.strftime("%Y")
		data['author'] = scrape.authors
		data['keywords'] = []
		data['abstract'] = abstract
		data['body_text'] = body_text
		data['figures'] = figures

		# debug
		'''
		if data['year'] == '':
			print('year is unknown.')`
			input('enter')
		
		if data['type'] == '':
			print('journal is unknown!!')	# E.g., 101039c5md00579e.html, 101039c5md00579e.html has no journal value and only abstract.
			input('enter')
		'''

		# write data to file
		output_filename = html_file.replace('.html', '.json')
		if output_filename == html_file:
			logger.error('>> HTML file does NOT exist!!')
			sys.exit()
		
		with open(output_filename, 'w') as outfile:
			json.dump(data, outfile)
		
		return scrape.doi

