import os
import sys
import requests
import json
from lxml import etree
from base_parser import BaseParser
import logging

logger = logging.getLogger(__name__)

from collections import defaultdict
from chemdataextractor.doc import Document, Title, Heading, Paragraph, Caption, Citation, Footnote, Text, Sentence, Figure
from chemdataextractor.reader import ElsevierXmlReader


class ElsevierParser(BaseParser):
	"""
	Parsed data:
		- src_title: journal/book title
		- year: published year
		- pii: Publisher Item Identifier
		- article_title
		- authors
		- keywords
		- abstract
		- body
		- objects
		
	References:
		- https://www.elsevier.com/authors/author-schemas/elsevier-xml-dtds-and-transport-schemas
		- https://dev.elsevier.com/documentation/ObjectRetrievalAPI.wadl
		- https://dev.elsevier.com/guides/AffiliationRetrievalViews.htm
	"""
	
	els_xml_reader = ElsevierXmlReader()
	

	def __init__(self):
		self.elsevier_api_key = "48f5407e5647f7fc83c28611a44e5ab3"
		self.article_destination = "/home/gpark/corpus_web/tdm/archive/Elsevier/articles/"
		self.obj_destination = "/home/gpark/corpus_web/tdm/archive/Elsevier/objects/"
	
	
	def update_uid_list(self):
		#num_of_empty_body_article = 0

		doi_list = []
		for filename in os.listdir(self.article_destination):
			#print(filename)
			#if ep.parse(os.path.join(dir, filename)):
			#	num_of_empty_body_article += 1
				
			doi_list.append(self.parse(os.path.join(self.article_destination, filename)))

		#print(num_of_empty_body_article)

		with open("/home/gpark/corpus_web/tdm/archive/uid_list.txt", 'a') as file:
			for doi in doi_list:
				file.write(doi + '\n')
		'''
		pii_list = []
		for filename in os.listdir(self.article_destination):
			tree = etree.parse(os.path.join(self.article_destination, filename), BaseParser.parser)
			root = tree.getroot()

			url = root.find('.//{http://prismstandard.org/namespaces/basic/2.0/}url').text
			pii = url.rsplit('/', 1)[-1]
			pii = pii.strip()

			pii_list.append(pii)

		with open("/home/gpark/corpus_web/tdm/archive/uid_list.txt", 'a') as file:
			for pii in pii_list:
				file.write(pii + '\n')
		'''
		
	def get_objects(self, xml_file):
		tree = etree.parse(xml_file, BaseParser.parser)
		root = tree.getroot()
		
		nsmap = root.nsmap
		nsmap['default_ns'] = nsmap.pop(None) # To avoid TypeError: empty namespace prefix is not supported in XPath
		
		get_text = lambda x : x[0].text if x else None
		
		#pii = get_text(root.xpath('//xocs:pii-unformatted', namespaces=nsmap))
		url = get_text(root.xpath('//prism:url', namespaces=nsmap))
		pii = url.rsplit('/', 1)[-1]
		
		""" Object extraction """
		num_of_objs = 0

		headers = {'X-ELS-APIKEY': self.elsevier_api_key}

		for attachment in root.xpath('//xocs:attachment', namespaces=nsmap):
			eid = attachment.xpath('xocs:attachment-eid', namespaces=nsmap)
			filename = attachment.xpath('xocs:filename', namespaces=nsmap)
			
			eid = get_text(eid)
			filename = get_text(filename)

			url = "https://api.elsevier.com/content/object/eid/" + eid

			response = requests.get(url, headers=headers)

			if response.status_code == 200:
				if os.path.isdir(self.obj_destination + pii) == False:
					os.mkdir(self.obj_destination + pii)
					
				with open(self.obj_destination + pii + "/" + filename, 'wb') as file:
					for chunk in response.iter_content(2048):
						file.write(chunk)
				
				num_of_objs += 1
		
		return num_of_objs
		

	def parse(self, xml_file):
		tree = etree.parse(xml_file, BaseParser.parser)
		root = tree.getroot()

		nsmap = root.nsmap
		nsmap['default_ns'] = nsmap.pop(None) # To avoid TypeError: empty namespace prefix is not supported in XPath
		
		#for k, v in nsmap.items():
		#    print(k, v)
		
		""" Text extraction """
		get_text = lambda x : x[0].text if x else None
		
		''' Extract titles with tags to properly display them on the webpage.
		TODO: Elsevier XML tags need to be further processed unlike JATS tags.
		Among the four content types, BS and RW are about indices so ignore them.  
		# JL: Journal
		# BK: Book, EBook
		# BS: Book Series		e.g., S0065327619300115.xml (Index), S0065211317301013.xml (Index), B978008102432409987X.xml (Index), S0076687918300120.xml (Subject index)
		# RW: Reference Work	e.g., B9780128122952090012.xml, B9780081005330090011.xml (Index), B9780128097397180014.xml (Index), 
		'''
		content_type = get_text(root.xpath('//xocs:content-type', namespaces=nsmap))	# 'JL','BK','BS','RW', None
		
		if content_type == 'JL':
			#article_title = get_text(root.xpath('//ja:head/ce:title', namespaces=nsmap))	# ja: journal article. In case of journal, several 'ce:title' may exist. 
			article_title_elem = root.xpath('//ja:head/ce:title', namespaces=nsmap)	# ja: journal article. In case of journal, several 'ce:title' may exist. 
		elif content_type == 'BK':
			#article_title = get_text(root.xpath('//ce:title', namespaces=nsmap))
			article_title_elem = root.xpath('//ce:title', namespaces=nsmap)
		else:
			return [content_type, None]

		if len(article_title_elem) == 0:
			#input("Press Enter to continue...")
			return [content_type, None]
		
		article_title = etree.tostring(article_title_elem[0]).decode("utf-8")	# retrive the original value to show in the TDM webpage.
		article_title = article_title.split(">", 1)[1]		# TODO: find a better way to remove the top tag.
		article_title = article_title.rsplit("</", 1)[0]		

		return [content_type, article_title]
		
		
		
		
		# clean xml and extract essential elements.
		specials, refs = self.els_xml_reader.preprocess_xml(root)

		
		
		
		#pii = get_text(root.xpath('//xocs:pii-unformatted', namespaces=nsmap))
		url = get_text(root.xpath('//prism:url', namespaces=nsmap))
		pii = url.rsplit('/', 1)[-1]
		doi = get_text(root.xpath('//prism:doi', namespaces=nsmap))
		publisher = get_text(root.xpath('//prism:publisher', namespaces=nsmap))
		article_type = get_text(root.xpath('//prism:aggregationType', namespaces=nsmap))

		src_title = get_text(root.xpath('//xocs:srctitle', namespaces=nsmap))
		year = get_text(root.xpath('//xocs:year-nav', namespaces=nsmap))

		
		
		
		

		authors = []
		for author in root.xpath('//ce:author', namespaces=nsmap):
			given_name = get_text(author.xpath('ce:given-name', namespaces=nsmap))
			surname = get_text(author.xpath('ce:surname', namespaces=nsmap))
			authors.append(f'Given name: {given_name} / Surname: {surname}')

		keywords = []
		for keyword in root.xpath('//ce:keyword', namespaces=nsmap):
			keyword_name = get_text(keyword.xpath('ce:text', namespaces=nsmap))
			if keyword_name:
				keywords.append(keyword_name)
		
		#abstract = ''	# [my_own_method]
		abstract = []
		for abs in root.xpath('//ce:abstract', namespaces=nsmap):
			abs_title = get_text(abs.xpath('ce:section-title', namespaces=nsmap))
			if abs_title and abs_title.lower() == 'abstract':
				abs_sec = abs.xpath('ce:abstract-sec', namespaces=nsmap)
				
				#txt_list = []	# [my_own_method]
				for abs in abs_sec:
					elements = self.els_xml_reader._parse_element(abs, specials=specials, refs=refs)
					doc = Document(*elements)
					for para in doc.paragraphs:
						for sent in para.sentences:
							#print(sent.tokens)
							#print(sent.pos_tagged_tokens)
							#abstract.append(sent.serialize())
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
								
							#print(sent.tokens)
							#print(sent.pos_tagged_tokens)
							#abstract.append(sent.serialize())
							abstract.append({'sent': sent.text, 
											  #'tokens': sent.tokens, 
											  #'tokens': sent.tagged_tokens,
											  #'tags': sent.tags,
											  #'tokens': sent.raw_tokens,
											  #'pos_tagged_tokens': sent.pos_tagged_tokens,
											  #'ner_tagged_tokens': sent.ner_tagged_tokens
											  'token_pos': list(zip(token, start, end, pos)),
											  'chemical_entity': cems})
							
							#input("Press Enter to continue...")
					
					''' [my_own_method]
					for txt in abs.itertext():
						txt = txt.replace('\n', ' ').replace('\t', ' ').strip()
						txt_list.append(txt)
					'''
					
				#abstract += ' '.join(txt_list)	# [my_own_method]
		
		#body_text = ''	# [my_own_method]
		body_text = []
		
		for body_sec in root.xpath('//ce:sections/ce:section', namespaces=nsmap):
			elements = self.els_xml_reader._parse_element(body_sec, specials=specials, refs=refs)
			doc = Document(*elements)
			
			for para in doc.paragraphs:
				#print(type(para))
				#print('------------------------------ new paragraph --------------------------------')
				for sent in para.sentences:
					#body_text.append(sent.serialize())
					token = []
					start = []	# start offset
					end = []	# end offset
					for tok in sent.tokens:
						token.append(tok.text)
						start.append(tok.start - sent.start)
						end.append(tok.end - sent.start)

					pos = sent.pos_tags
					#ner = sent.ner_tags

					cems = []
					for cem in sent.cems:
						cems.append([cem.text, cem.start - sent.start, cem.end - sent.start])
						
					#body_text.append(sent.serialize())
					body_text.append({'sent': sent.text, 
									  #'tokens': sent.tokens, 
									  #'tokens': sent.tagged_tokens,
									  #'tags': sent.tags,
									  #'tokens': sent.raw_tokens,
									  #'pos_tagged_tokens': sent.pos_tagged_tokens,
									  #'ner_tagged_tokens': sent.ner_tagged_tokens
									  'token_pos': list(zip(token, start, end, pos)),
									  'chemical_entity': cems})
					#print(sent)
					
			''' [my_own_method]	
			# For now, remove references, formulas, and tables in texts. - 03/20/2019
			# !! if the etree.strip_elements is used inside for loop below, not all texts are retrieved. 
			#etree.strip_elements(body_sec, '{' + nsmap.get('mml') + '}math')
			
			txt_list = []
			
			for ele in body_sec.iter():
				#print(ele.tag)
				#print(etree.QName(ele.tag).localname)

				# Ignore namespaces using QName.
				if etree.QName(ele.tag).localname == 'section-title':
					txt_list.append(''.join(ele.itertext()) + '. ')	# dot(. ) is added to let spaCy recognize it's a separate sentence. newline ('\n') is not working well in spaCy.
					
				if etree.QName(ele.tag).localname == 'para':
					for txt in ele.itertext():
						txt = txt.replace('\n', ' ').replace('\t', ' ').strip()
						txt_list.append(txt)

			body_text += ' '.join(txt_list)
			'''
		
		figure_caption = []
		
		# In case of Elsevier XML, Figures are not inside of body text.
		figures = [el[0] for el in specials.values() if len(el) > 0 and isinstance(el[0], Figure)]
		for fig in figures:
			for sent in fig.caption:
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
						
					figure_caption.append({'fig_id': fig.id,
										   'sent': sent.text, 
										   'token_pos': list(zip(token, start, end, pos)),
										   'chemical_entity': cems})
					
		# debug for checking the number of articles w/o body text
		'''
		if len(body_text) == 0:
			print(xml_file.rsplit('/', 1)[-1])
			return True
		else:
			return False
		'''
		# [end] debug
		
		""" Object extraction """
		num_of_objs = 0
		
		'''
		os.mkdir(self.obj_destination + pii)

		headers = {'X-ELS-APIKEY': self.elsevier_api_key}

		for attachment in root.xpath('//xocs:attachment', namespaces=nsmap):
			eid = attachment.xpath('xocs:attachment-eid', namespaces=nsmap)
			filename = attachment.xpath('xocs:filename', namespaces=nsmap)
			
			eid = get_text(eid)
			filename = get_text(filename)

			url = "https://api.elsevier.com/content/object/eid/" + eid

			response = requests.get(url, headers=headers)

			if response.status_code == 200:
				with open(self.obj_destination + pii + "/" + filename, 'wb') as file:
					for chunk in response.iter_content(2048):
						file.write(chunk)
				
				num_of_objs += 1
		'''
		
		uid = doi if doi is not None else pii
		
		if uid is None:
			print(xml_file)
			sys.exit()
		
		
		data = {}
		data['uid'] = uid
		data['publisher'] = publisher
		data['type'] = article_type
		data['title'] = article_title
		data['year'] = year
		data['author'] = authors
		data['keywords'] = keywords
		data['abstract'] = abstract
		data['body_text'] = body_text
		data['figure_caption'] = figure_caption

		
		# [start] debug
		'''
		logger.debug('\n'
					 f'doi: {doi}\n'
					 f'pii: {pii}\n'
					 f'publisher: {publisher}\n'
					 f'type: {type}\n'
					 f'article_title: {article_title}\n'
					 f'year: {year}\n'
					 f'src_title: {src_title}\n'
					 f'authors: {authors}\n'
					 f'keywords: {keywords}\n'
					 #f'abstract: {abstract}\n'
					 #f'body: {body}\n'
					 f'num_of_objs: {num_of_objs}\n')
		
		#abs_txt_sents = [sent.text for sent in nlp(abstract).sents]
		
		for t in abstract:
			print('>> abs sent:', t['sent'])
		
		#print('-------------------------------------------------------------------------')
		
		#body_text_sents = [sent.text for sent in nlp(body_text).sents]
			
		for t in body_text:
			print('>> sent:', t['sent'])
		
		#input("Press Enter to continue...")
		'''
		
		print(doi)
		# [end] debug
		
		# write data to file
		output_filename = xml_file.replace('.xml', '.json')
		if output_filename == xml_file:
			logger.error('>> XML file does NOT exist!!')
			sys.exit()
		
		with open(output_filename, 'w') as outfile:
			json.dump(data, outfile)
		
		return uid
		

		
		""" old way w/o using XPath
		meta = root.find('.//{' + nsmap.get('xocs') + '}meta')
		src_title = meta.find('{' + nsmap.get('xocs') + '}srctitle').text
		year = meta.find('{' + nsmap.get('xocs') + '}year-nav').text
		pii = meta.find('{' + nsmap.get('xocs') + '}pii-unformatted').text

		article_title = root.find('.//{' + nsmap.get('ce') + '}title').text
		authors = []
		for author in root.iter('{' + nsmap.get('ce') + '}author'):
			given_name = author.find('{' + nsmap.get('ce') + '}given-name').text
			surname = author.find('{' + nsmap.get('ce') + '}surname').text
			authors.append(given_name + ' ' + surname)

		keywords = []
		for keyword in root.iter('{' + nsmap.get('ce') + '}keyword'):
			keyword_name = keyword.find('{' + nsmap.get('ce') + '}text').text
			keywords.append(keyword_name)

		abs_sec = root.find('.//{' + nsmap.get('ce') + '}abstract-sec')
		abstract = ''.join(abs_sec.itertext())

		print(src_title)
		print(year)
		print(pii)
		print(article_title)
		print(authors)
		print(keywords)
		print(abstract)

		os.mkdir("../archive/Elsevier/objects/" + pii)

		headers = {
		'X-ELS-APIKEY': self.elsevier_api_key,
		}

		for attachment in root.iter('{' + nsmap.get('xocs') + '}attachment'):
			eid = attachment.find('{' + nsmap.get('xocs') + '}attachment-eid').text
			filename = attachment.find('{' + nsmap.get('xocs') + '}filename').text

			url = "https://api.elsevier.com/content/object/eid/" + eid

			response = requests.get(url, headers=headers)

			if response.status_code == 200:
				with open("../archive/Elsevier/objects/" + pii + "/" + filename, 'wb') as file:
					for chunk in response.iter_content(2048):
						file.write(chunk)
		"""

