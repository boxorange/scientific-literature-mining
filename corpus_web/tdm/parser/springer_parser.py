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
from chemdataextractor.reader import NlmXmlReader


class SpringerParser(BaseParser):
	"""
	Note:
		- Springer and PMC use the same function for article.
		- Springer has journal articles and book chapters.
		  Article format (root element: <article>): https://jats.nlm.nih.gov/archiving/tag-library/1.1/index.html
		  Book chapter format (root element: <book-part-wrapper>): https://jats.nlm.nih.gov/extensions/bits/tag-library/2.0/index.html
	
	TODO:
		- Springer and PMC have the same format, so think about combining the methods.
		- Text needs to contain tag attributes to find figures, tables, and supplementary materials.
		  Text needs to handle spaces caused by tags. For now, simply join strings with a space.
		  
	Parsed data:
		- journal_title
		- publisher
		- article_title
		- year
		- uid: doi
		- authors
		- abstract
		- keywords
		- body
		
	References:
		- https://jats.nlm.nih.gov/archiving/tag-library/1.2/
		- https://dtd.nlm.nih.gov/publishing/
		- https://jats.nlm.nih.gov/archiving/
	"""
	
	nxml_reader = NlmXmlReader()
	
	
	def __init__(self):
		super().__init__('Springer')
		
		self.book_chp_img_link = "https://media.springernature.com/lw685/springer-static/image/chp:"
		self.article_img_link = "https://media.springernature.com/lw685/springer-static/image/art:"


	def update_uid_list(self):
		num_of_empty_body_article = 0

		doi_list = set()

		dir = self.path
		for filename in os.listdir(dir):
			if filename.endswith(".xml"):
				#print(filename)
				#if sp.parse(os.path.join(dir, filename)):
				#	num_of_empty_body_article += 1
				
				if filename in ['101007JHEP072017078.xml']:
					continue

				doi_list.add(self.parse(os.path.join(dir, filename), 'just_uid').lower())
				
				#input("Press Enter to continue...")

		#print(num_of_empty_body_article)
		
		existing_uids = set([line.strip() for line in open(self.uid_list)])
		
		doi_list.difference_update(existing_uids)   # remove any duplicates

		with open(self.uid_list, 'a') as file:
			for doi in doi_list:
				file.write("%s\n" % doi)
	
	
	def get_sentence(self, elem, para_id_prefix, start_para_idx, specials, refs, sec_title=''):
		sents = []
		
		elements = self.nxml_reader._parse_element(elem, specials=specials, refs=refs)
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
		

	def parse_book_chapter(self, root, specials, refs, output_file, option):
		''' Book Meta '''
		book_meta = root.find('.//book-meta')
		book_title = book_meta.findtext('.//book-title')
		publisher = book_meta.findtext('.//publisher-name')
		
		''' Chapter Meta '''
		chapter = root.find('.//book-part[@book-part-type="chapter"]')
		chapter_meta = chapter.find('.//book-part-meta')
		#chapter_title = chapter_meta.findtext('.//title-group/title')
		chapter_title = chapter_meta.find('.//title-group/title')
		chapter_title = etree.tostring(chapter_title).decode("utf-8")	# retrive the original value to show in the TDM webpage.
		chapter_title = chapter_title.split(">", 1)[1]		# TODO: find a better way to remove the top tag.
		chapter_title = chapter_title.rsplit("</", 1)[0]
		
		year = chapter_meta.findtext('.//pub-date/year')
		chapter_doi = chapter_meta.findtext('.//book-part-id[@book-part-id-type="doi"]')
		authors = []
		for author in chapter_meta.findall('.//contrib[@contrib-type="author"]'):
			name = author.find('name')
			if name is not None:
				authors.append(' '.join(name.itertext()))
		
		if option == 'just_uid':
			return chapter_doi

		# Ref: https://github.com/titipata/pubmed_parser/blob/master/pubmed_parser/pubmed_oa_parser.py
		abstract_element = chapter_meta.findall('.//abstract')	# abstract element can be more than one.
		abstract = []
		start_para_idx = 1
		for abs in abstract_element:
			para_id_prefix = 'abs'
			start_para_idx, sents = self.get_sentence(abs, para_id_prefix, start_para_idx, specials, refs)
			abstract.extend(sents)
			
		keywords = []
		for keyword in chapter_meta.findall('.//kwd'):
			keywords.append(''.join(keyword.itertext()))
		
		''' Body Text '''
		# https://github.com/TypesetIO/jsuite/blob/master/jsuite/content.py
		# body_text = " ".join([x.strip() for x in node.itertext() if x.strip() is not ""])
		#bodies = chapter.findall('.//body')	# body element must be one, but for just in case.
		body_element = chapter.find('.//body')	
		
		# debug
		#if len(bodies) > 1:
		#	logger.debug(f'More than 1 body: {xml_file}')
		#	sys.exit()
		
		body_text = []
		if body_element is not None:
			sec_title = ''
			start_para_idx = 1
			for elem in body_element:	# for simplicity, only consider direct section titles (ignore sub-section titles) - 04-12-20
				sec_title = elem.findtext('title') if elem.tag == 'sec' else ''
				para_id_prefix = 'body'
				start_para_idx, sents = self.get_sentence(elem, para_id_prefix, start_para_idx, specials, refs, sec_title=sec_title)
				body_text.extend(sents)
		
		figures = []
		fig_element = [el[0] for el in specials.values() if len(el) > 0 and isinstance(el[0], Figure)]
		for fig in fig_element:
			if fig.id is None:
				continue
			'''
			fig_element doesn't have other information other than caption, so other informaion needs to be retrieved from separate xml parsing. - 11/5/2019
			'''
			fig_elem = root.xpath('//fig[@id="' + fig.id + '"]')[0]
			label = fig_elem.findtext('label')
			fig_file = ''
			graphic_elem = fig_elem.find('graphic') 
			if graphic_elem is not None:
				nsmap = graphic_elem.nsmap	# root.nsmap may not contain all name spaces. e.g, sdata2018151.nxml - 11/06/2019
				fig_link = graphic_elem.get('{' + nsmap['xlink'] + '}href')
				fig_file = fig_link.rsplit('/', 1)[1] if '/' in fig_link else fig_link
				
				# skip already downloaded files.
				if os.path.isfile(output_file.rsplit('/', 1)[0] + '/' + fig_file):	
					fig_file = output_file.rsplit('/', 1)[0] + '/' + fig_file
				else:
					url = self.article_img_link + chapter_doi + '/MediaObjects/' + fig_file	
					response = requests.get(url)
					
					if response.status_code == 200:
						with open(output_file.rsplit('/', 1)[0] + '/' + fig_file, 'wb') as file:
							for chunk in response.iter_content(2048):
								file.write(chunk)
						fig_file = output_file.rsplit('/', 1)[0] + '/' + fig_file
					else:
						fig_file = ''
						error_msg = f'>> ERROR Code: {response.status_code}\n' + \
									f'>> URL: {response.url}\n' + \
									f'>> Resp txt: {response.text}'
						print(error_msg)

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
										   
		# [start] debug
		'''
		if len(body_text) == 0:
			return True
		else:
			return False
		'''
		# [end] debug
		
		data = {}
		data['uid'] = chapter_doi
		data['publisher'] = publisher
		data['type'] = 'book-chapter'
		data['title'] = chapter_title
		data['year'] = year
		data['author'] = authors
		data['keywords'] = keywords
		
		data['abstract'] = abstract
		#abstract_sents = []
		#for ele in abstract:
		#	abstract_sents.extend([sent.text for sent in nlp(ele).sents])
		#data['abstract_sents'] = abstract_sents
		#data['abstract_sents'] = [sent.text for sent in nlp(abstract).sents] if abstract != '' else ''
		
		data['body_text'] = body_text
		#body_text_sents = []
		#for ele in body_text:
		#	body_text_sents.extend([sent.text for sent in nlp(ele).sents])
		#data['body_text_sents'] = body_text_sents
		#data['body_text_sents'] = [sent.text for sent in nlp(body_text).sents] if body_text != '' else ''
		
		data['figures'] = figures
				
		# [start] debug
		'''
		logger.debug(f'\n>>> Book Title: {book_title}\n'
					 f'>>> Publisher: {publisher}\n'
					 f'>>> Chapter Title: {chapter_title}\n'
					 f'>>> Year: {year}\n'
					 f'>>> UID: {chapter_doi}\n'
					 f'>>> Authors: {authors}\n'
					 f'>>> Abstract:\n{abstract}\n'
					 f'>>> Keywords: {keywords}\n'
					 f'>>> Body Text:\n{body_text}\n')
		'''
		# [end] debug
		
		# write data to file
		with open(output_file, 'w') as outfile:
			json.dump(data, outfile)
			
		return chapter_doi


	def parse_article(self, root, specials, refs, output_file, option):
		''' Journal Meta '''
		journal_meta = root.find('.//journal-meta')
		journal_title = journal_meta.findtext('.//journal-title')
		publisher = journal_meta.findtext('.//publisher-name')
		
		article_type = root.get('article-type') if root.tag == 'article' else root.find('.//article').get('article-type')
		
		''' Article Meta '''
		article_meta = root.find('.//article-meta')
		#article_title = article_meta.findtext('.//article-title')
		article_title = article_meta.find('.//article-title')
		article_title = etree.tostring(article_title).decode("utf-8")	# retrive the original value to show in the TDM webpage.
		article_title = article_title.split(">", 1)[1]		# TODO: find a better way to remove the top tag.
		article_title = article_title.rsplit("</", 1)[0]

		year = article_meta.findtext('.//pub-date/year')
		article_doi = article_meta.findtext('.//article-id[@pub-id-type="doi"]')
		authors = []
		for author in article_meta.findall('.//contrib[@contrib-type="author"]'):
			name = author.find('name')
			if name is not None:
				authors.append(' '.join(name.itertext()))
			
		if option == 'just_uid':
			return article_doi
		
		# Ref: https://github.com/titipata/pubmed_parser/blob/master/pubmed_parser/pubmed_oa_parser.py
		abstract_element = article_meta.findall('.//abstract')	# abstract element can be more than one.
		abstract = []
		start_para_idx = 1
		for abs in abstract_element:
			para_id_prefix = 'abs'
			start_para_idx, sents = self.get_sentence(abs, para_id_prefix, start_para_idx, specials, refs)
			abstract.extend(sents)
			
		keywords = []
		for keyword in article_meta.findall('.//kwd'):
			keywords.append(''.join(keyword.itertext()))
		
		''' Body Text '''
		# remove bibliographic citations
		#etree.strip_elements(body, 'xref')
		# Ref: https://stackoverflow.com/questions/7981840/how-to-remove-an-element-in-lxml
		#for bib in body.findall('.//xref[@ref-type="bibr"]'):	# the same as root.xpath('//body//xref[@ref-type="bibr"]')
		#	bib.getparent().remove(bib)
		# 	bib.clear()
			
		#paragraphs = root.findall('.//body//p') # the same as root.xpath('//body//p')
		#bodies = root.findall('.//body')	# body element must be one, but for just in case.
		body_element = root.find('.//body')	
		
		# debug
		#if len(bodies) > 1:
		#	logger.debug(f'More than 1 body: {xml_file}')
		#	sys.exit()

		body_text = []
		if body_element is not None:
			sec_title = ''
			start_para_idx = 1
			for elem in body_element:	# for simplicity, only consider direct section titles (ignore sub-section titles) - 04-12-20
				sec_title = elem.findtext('title') if elem.tag == 'sec' else ''
				para_id_prefix = 'body'
				start_para_idx, sents = self.get_sentence(elem, para_id_prefix, start_para_idx, specials, refs, sec_title=sec_title)
				body_text.extend(sents)
		
		figures = []
		fig_element = [el[0] for el in specials.values() if len(el) > 0 and isinstance(el[0], Figure)]
		for fig in fig_element:
			if fig.id is None:
				continue
			'''
			fig_element doesn't have other information other than caption, so other informaion needs to be retrieved from separate xml parsing. - 11/5/2019
			'''
			fig_elem = root.xpath('//fig[@id="' + fig.id + '"]')[0]
			label = fig_elem.findtext('label')
			fig_file = ''
			graphic_elem = fig_elem.find('graphic') 
			if graphic_elem is not None:
				nsmap = graphic_elem.nsmap	# root.nsmap may not contain all name spaces. e.g, sdata2018151.nxml - 11/06/2019
				fig_link = graphic_elem.get('{' + nsmap['xlink'] + '}href')
				fig_file = fig_link.rsplit('/', 1)[1] if '/' in fig_link else fig_link
				
				# skip already downloaded files.
				if os.path.isfile(output_file.rsplit('/', 1)[0] + '/' + fig_file):	
					fig_file = output_file.rsplit('/', 1)[0] + '/' + fig_file
				else:
					url = self.article_img_link + article_doi + '/MediaObjects/' + fig_file	
					response = requests.get(url)
					
					if response.status_code == 200:
						with open(output_file.rsplit('/', 1)[0] + '/' + fig_file, 'wb') as file:
							for chunk in response.iter_content(2048):
								file.write(chunk)
						fig_file = output_file.rsplit('/', 1)[0] + '/' + fig_file
					else:
						fig_file = ''
						error_msg = f'>> ERROR Code: {response.status_code}\n' + \
									f'>> URL: {response.url}\n' + \
									f'>> Resp txt: {response.text}'
						print(error_msg)

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

		# [start] debug
		#if abstract == '':
		#	print(f'>>> NO paragraph!! - {xml_file}')
			#sys.exit()		
		#else:
		#	print(abstract)
		
		#if body_text == '':
		#	print(f'>>> NO body!! - {xml_file}')
		#else:
		#	print(body_text)
		'''
		if len(body_text) == 0:
			return True
		else:
			return False
		'''
		# [end] debug
		
		data = {}
		data['uid'] = article_doi
		data['publisher'] = publisher
		# For PMC, root tag is article. #data['type'] = root.find('.//article').get('article-type')
		data['type'] = article_type
		data['title'] = article_title
		data['year'] = year
		data['author'] = authors
		data['keywords'] = keywords
		
		data['abstract'] = abstract
		#abstract_sents = []
		#for ele in abstract:
		#	abstract_sents.extend([sent.text for sent in nlp(ele).sents])
		#data['abstract_sents'] = abstract_sents
		#data['abstract_sents'] = [sent.text for sent in nlp(abstract).sents] if abstract != '' else ''
		
		data['body_text'] = body_text
		#body_text_sents = []
		#for ele in body_text:
		#	body_text_sents.extend([sent.text for sent in nlp(ele).sents])
		#data['body_text_sents'] = body_text_sents
		#data['body_text_sents'] = [sent.text for sent in nlp(body_text).sents] if body_text != '' else ''

		data['figures'] = figures
		
		# [start] debug
		'''
		logger.debug(f'\n>>> Journal Title: {journal_title}\n'
					 f'>>> Publisher: {publisher}\n'
					 f'>>> Article Type: {article_type}\n'
					 f'>>> Article Title: {article_title}\n'
					 f'>>> Year: {year}\n'
					 f'>>> UID: {article_doi}\n'
					 f'>>> Authors: {authors}\n'
					 f'>>> Abstract:\n{abstract}\n'
					 f'>>> Keywords: {keywords}\n')
					 #f'>>> Body Text:\n{body_text}\n')

		#abs_txt_sents = [sent.text for sent in nlp(abstract).sents]
		
		for t in abstract:
			print('>> abs sent:', t['sent'])
		
		print('-------------------------------------------------------------------------')

		#body_text_sents = [sent.text for sent in nlp(body_text).sents]
			
		for t in body_text:
			print(t['sent'])
		
		input("Press Enter to continue...")
		'''
		print(article_doi)
		# [end] debug
		
		# write data to file
		with open(output_file, 'w') as outfile:
			json.dump(data, outfile)
						
		return article_doi

	
	def parse(self, xml_file, option='all'):	# option='just_uid' doesn't do full parsing, just return doi.
		tree = etree.parse(xml_file, self.xml_parser)
		root = tree.getroot()
		
		# clean xml and extract essential elements.
		specials, refs = self.nxml_reader.preprocess(root)
		
		ret = None
		
		output_file = xml_file.replace('.xml', '.json')
		if output_file == xml_file:
			logger.error('>> XML file does NOT exist!!')
			sys.exit()

		''' First, check if it is an article or a chapter. '''
		if root.tag == 'book-part-wrapper' or root.find('.//book-part-wrapper') is not None:
			ret = self.parse_book_chapter(root, specials, refs, output_file, option)
		elif root.tag == 'article' or root.find('.//article') is not None:
			ret = self.parse_article(root, specials, refs, output_file, option)
		else:
			logger.error(f'!! Format Error: {xml_file}')
			sys.exit()
		
		if ret is None:
			print(xml_file)
			sys.exit()
			
		return ret

