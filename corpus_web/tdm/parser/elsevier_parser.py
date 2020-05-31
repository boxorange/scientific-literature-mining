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
		super().__init__('Elsevier')
	
	
	def update_uid_list(self):
		#num_of_empty_body_article = 0
		
		cnt = 0

		doi_list = set()
		for filename in os.listdir(self.path):
			#print(filename)
			#if ep.parse(os.path.join(dir, filename)):
			#	num_of_empty_body_article += 1

			if filename.endswith(".xml") and os.path.isfile(os.path.join(self.path, filename.replace('.xml', '.json'))) == False:
				if filename in ['S0960894X06003441.xml', 'S0040403904026243.xml', 
								'S0040402013003669.xml', 'S0960894X10000120.xml', 
								'S0040403908011490.xml', 'S0040403904000334.xml']:
					continue
				
				cnt += 1
				
				print(filename, ' / count: ', cnt)
				
				doi_list.add(self.parse(os.path.join(self.path, filename), 'just_uid').lower())
		
		#print(num_of_empty_body_article)
		
		existing_uids = set([line.strip() for line in open(self.uid_list)])
		
		doi_list.difference_update(existing_uids)   # remove any duplicates

		with open(self.uid_list, 'a') as file:
			for doi in doi_list:
				file.write("%s\n" % doi)

		
		'''
		pii_list = []
		for filename in os.listdir(self.path):
			tree = etree.parse(os.path.join(self.path, filename), self.parser)
			root = tree.getroot()

			url = root.find('.//{http://prismstandard.org/namespaces/basic/2.0/}url').text
			pii = url.rsplit('/', 1)[-1]
			pii = pii.strip()

			pii_list.append(pii)

		with open("/home/gpark/corpus_web/tdm/archive/uid_list.txt", 'a') as file:
			for pii in pii_list:
				file.write(pii + '\n')
		'''
	
	
	def get_object(self, xml_file):
		tree = etree.parse(xml_file, self.xml_parser)
		root = tree.getroot()
		
		nsmap = root.nsmap
		nsmap['default_ns'] = nsmap.pop(None) # To avoid TypeError: empty namespace prefix is not supported in XPath
		
		get_text = lambda x : x[0].text if x else None
		
		#pii = get_text(root.xpath('//xocs:pii-unformatted', namespaces=nsmap))
		url = get_text(root.xpath('//prism:url', namespaces=nsmap))
		pii = url.rsplit('/', 1)[-1]
		
		#if os.path.isdir(self.obj_destination + pii) == True:	# skip already downloaded files.
		#	return 0
		for file in os.listdir(xml_file.rsplit('/', 1)[0]):	# assume that if a folder has any img file, then the objects were already downloaded.
			img_ext = [".jpg", ".jpeg", ".gif", ".png", ".tiff", ".svg"]	
			if file.endswith(tuple(img_ext)):
				return 0
		
		""" Object extraction """
		num_of_objs = 0

		headers = {'X-ELS-APIKEY': self.api_key}

		for attachment in root.xpath('//xocs:attachment', namespaces=nsmap):
			eid = attachment.xpath('xocs:attachment-eid', namespaces=nsmap)
			filename = attachment.xpath('xocs:filename', namespaces=nsmap)
			
			eid = get_text(eid)
			filename = get_text(filename)

			url = "https://api.elsevier.com/content/object/eid/" + eid

			response = requests.get(url, headers=headers)

			if response.status_code == 200:
				with open(self.path + pii + "/" + filename, 'wb') as file:
					for chunk in response.iter_content(2048):
						file.write(chunk)
				
				num_of_objs += 1
			else:
				error_msg = f'>> ERROR Code: {response.status_code}\n' + \
							f'>> URL: {response.url}\n' + \
							f'>> Resp txt: {response.text}'
				#logger.error(error_msg)
				print(error_msg)
		
		return num_of_objs
	

	def get_sentence(self, paragraph, para_id, specials, refs, sec_title=''):
		sents = []
		
		elements = self.els_xml_reader._parse_element(paragraph, specials=specials, refs=refs)
		doc = Document(*elements)
		for para in doc.paragraphs:	# Document object doesn't have direct access to sentences.
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

		return sents
	

	def iter_section(self, section, sec_title, para_idx, body_text, nsmap, specials, refs, get_text):
		for parsec in section.xpath('./ce:section | ./ce:para', namespaces=nsmap):
			if etree.QName(parsec).localname == 'section':
				sec_title = get_text(parsec.xpath('ce:section-title', namespaces=nsmap))
				self.iter_section(parsec, sec_title, para_idx, body_text, nsmap, specials, refs, get_text)
			elif etree.QName(parsec).localname == 'para':
				para_id = parsec.get('id')
				if para_id is None:
					para_id = 'body_para_' + str(para_idx)
					para_idx += 1
				body_text.extend(self.get_sentence(parsec, para_id, specials, refs, sec_title=sec_title))
		

	def parse(self, xml_file, option='all'):	# option='just_doi' doesn't do full parsing, just return doi.
		tree = etree.parse(xml_file, self.xml_parser)
		root = tree.getroot()

		nsmap = root.nsmap
		nsmap['default_ns'] = nsmap.pop(None) # To avoid TypeError: empty namespace prefix is not supported in XPath

		get_text = lambda x : x[0].text if x else None
		
		''' 
		There are five content types in Elsevier. Among them, BS and RW are about indices, and handbooks are also a type of reference work, so ignore them.
		If an article is a normal journal or book chapter, it must have a title. If not, ignore them.
		- Ref for <content-type>: https://dev.elsevier.com/tips/ArticleMetadataTips.htm
		# JL - Journal
		# BK - Book, EBook
		# BS - Book Series		e.g., S0065327619300115.xml (Index), S0065211317301013.xml (Index), B978008102432409987X.xml (Index), S0076687918300120.xml (Subject index)
		# HB - Handbook Series	e.g., B9780444634399200017.xml (Index), S1570002X08800249.xml (handbook article)
		# RW - Reference Work	e.g., B9780128122952090012.xml (Index), B9780081005330090011.xml (Index), B9780128097397180014.xml (Index), 
		
		TODO: Extract titles with tags to properly display them on the webpage. Elsevier XML tags need to be further processed unlike JATS tags.
		'''
		content_type = get_text(root.xpath('//xocs:content-type', namespaces=nsmap))	# 'JL','BK','HB','BS','RW',None
		
		if content_type == 'JL':
			#article_title = get_text(root.xpath('//ja:head/ce:title', namespaces=nsmap))	# ja: journal article. In case of journal, several 'ce:title' may exist. 
			article_title_elem = root.xpath('//ja:head/ce:title', namespaces=nsmap)	# ja: journal article. In case of journal, several 'ce:title' may exist. 
		elif content_type == 'BK':
			#article_title = get_text(root.xpath('//ce:title', namespaces=nsmap))
			article_title_elem = root.xpath('//ce:title', namespaces=nsmap)
		else:
			url = get_text(root.xpath('//prism:url', namespaces=nsmap))
			pii = url.rsplit('/', 1)[-1]
			doi = get_text(root.xpath('//prism:doi', namespaces=nsmap))
			return doi if doi is not None else pii
			#return [content_type, None]

		if len(article_title_elem) == 0:
			#input("Press Enter to continue...")
			url = get_text(root.xpath('//prism:url', namespaces=nsmap))
			pii = url.rsplit('/', 1)[-1]
			doi = get_text(root.xpath('//prism:doi', namespaces=nsmap))
			return doi if doi is not None else pii
			#return [content_type, None]
		
		article_title = etree.tostring(article_title_elem[0]).decode("utf-8")	# retrive the original value to show in the TDM webpage.
		article_title = article_title.split(">", 1)[1]		# TODO: find a better way to remove the top tag.
		article_title = article_title.rsplit("</", 1)[0]		
		#return [content_type, article_title]
		
		# clean xml and extract essential elements.
		specials, refs = self.els_xml_reader.preprocess(root)

		#pii = get_text(root.xpath('//xocs:pii-unformatted', namespaces=nsmap))
		url = get_text(root.xpath('//prism:url', namespaces=nsmap))
		pii = url.rsplit('/', 1)[-1]
		doi = get_text(root.xpath('//prism:doi', namespaces=nsmap))
		publisher = get_text(root.xpath('//prism:publisher', namespaces=nsmap))
		article_type = get_text(root.xpath('//prism:aggregationType', namespaces=nsmap))

		src_title = get_text(root.xpath('//xocs:srctitle', namespaces=nsmap))
		year = get_text(root.xpath('//xocs:year-nav', namespaces=nsmap))

		uid = doi if doi is not None else pii
		
		if uid is None:
			print(xml_file)
			sys.exit('!!! UID does not exsit!!!')
		
		if option == 'just_uid':
			return uid

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
		
		abstract = []
		para_idx = 1	# used when id is not available from article.
		for abs in root.xpath('//ce:abstract', namespaces=nsmap):
			abs_title = get_text(abs.xpath('ce:section-title', namespaces=nsmap))
			if abs_title and abs_title.lower() == 'abstract':
				for abs_sec in abs.xpath('ce:abstract-sec', namespaces=nsmap):
					for para in abs_sec.xpath('ce:simple-para', namespaces=nsmap):
						para_id = para.get('id')
						if para_id is None:
							para_id = 'abs_para_' + str(para_idx)
							para_idx += 1
						abstract.extend(self.get_sentence(para, para_id, specials, refs))
		
		'''
		The elements article, item-info, jid, aid, head, body and tail, which have no prefix, are in the namespace http://www.elsevier.com/xml/ja/dtd
		<!ELEMENT ce:sections ( %parsec; )>
		<!ENTITY % parsec "( ce:para | ce:section )+">
		<!ELEMENT ce:section ( ( ( ce:section-title | ( ce:label, ce:section-title? ) ), %parsec; ) | ce:section+ )>
		<!ELEMENT ce:para ( %par.data; )*>
		
		TODO: For now, if a paragraph doesn't have a section title or heading, the preceding one will be used, which may not be true all the time.
		'''
		body_text = []
		para_idx = 1	# used when id is not available from article.
		sec_title = ''
		body_sections = root.xpath('//ja:body/ce:sections', namespaces=nsmap)
		for bs in body_sections: # if exists, there must be one 'sections' element.
			for parsec in bs.xpath('./ce:section | ./ce:para', namespaces=nsmap):
				if etree.QName(parsec).localname == 'section':
					sec_title = get_text(parsec.xpath('ce:section-title', namespaces=nsmap))
					self.iter_section(parsec, sec_title, para_idx, body_text, nsmap, specials, refs, get_text)
				elif etree.QName(parsec).localname == 'para':
					para_id = parsec.get('id')
					if para_id is None:
						para_id = 'body_para_' + str(para_idx)
						para_idx += 1
					body_text.extend(self.get_sentence(parsec, para_id, specials, refs, sec_title=sec_title))

		figures = []
		fig_element = [el[0] for el in specials.values() if len(el) > 0 and isinstance(el[0], Figure)]
		for fig in fig_element:
			if fig.id is None:
				continue
			
			# fig_element doesn't have other information other than caption, so other informaion needs to be retrieved from separate xml parsing. - 11/5/2019
			fig_elem = root.xpath('//ce:figure[@id="' + fig.id + '"]', namespaces=nsmap)[0]
			label = fig_elem.findtext('ce:label', namespaces=nsmap)
			fig_file = ''
			fig_file_elem = fig_elem.find('ce:link', namespaces=nsmap)
			if fig_file_elem is not None:
				fig_file = fig_file_elem.get('locator')
				fig_file = xml_file.rsplit('/', 1)[0] + '/' + fig_file
				
				# find a file extension.
				if os.path.isfile(fig_file + '.jpg'):
					fig_file += '.jpg'
				elif os.path.isfile(fig_file + '.jpeg'):
					fig_file += '.jpeg'
				elif os.path.isfile(fig_file + '.gif'):
					fig_file += '.gif'
				elif os.path.isfile(fig_file + '.png'):
					fig_file += '.png'
				elif os.path.isfile(fig_file + '.tiff'):
					fig_file += '.tiff'
				elif os.path.isfile(fig_file + '.svg'):
					fig_file += '.svg'
				elif os.path.isfile(fig_file + '.sml'):
					fig_file += '.sml'
				else:
					print('!! fig_file does not exist:', fig_file)
					fig_file = ''
				
			caption = []
			
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
					
				caption.append({'sent': sent.text, 
								'token_pos': list(zip(token, start, end, pos)),
								'chemical_entity': cems})
					
			figures.append({'fig_id': fig.id,
							'label': label,
							'caption': caption, 
							'fig_file': fig_file})
					
		# debug for checking the number of articles w/o body text
		'''
		if len(body_text) == 0:
			print(xml_file.rsplit('/', 1)[-1])
			return True
		else:
			return False
		'''
		# [end] debug
		
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
		data['figures'] = figures

		
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
		
		#print(doi)
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
		'X-ELS-APIKEY': self.api_key,
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

