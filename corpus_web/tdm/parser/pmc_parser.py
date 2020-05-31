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
#from chemdataextractor.scrape.clean import clean
#from chemdataextractor.scrape.pub.nlm import tidy_nlm_references, space_labels
#from chemdataextractor.text.processors import Substitutor, Discard, Chain, LStrip, RStrip, LAdd


class PMCParser(BaseParser):
	"""
	Note:
	- ChemDataExtractor-Snowball performs better than my own method on cleaning text and sentence segmentation. - 4/2/2019
	
	References:
	- https://github.com/cjcourt/cdesnowball
	"""
	
	
	nxml_reader = NlmXmlReader()


	def __init__(self):
		super().__init__('PMC')
	

	def update_uid_list(self):
		num_of_empty_body_article = 0
		
		doi_list = []

		dir = self.path
		'''
		for root, dirs, files in os.walk(dir):
			for d in dirs:
				no_xml = True
				for fname in os.listdir("/home/gpark/corpus_web/tdm/archive/PMC/" + d):
					#print(fname)
					if fname.endswith('.nxml'):
						no_xml = False
						break
				if no_xml is True:
					print(d)
		
		sys.exit()
		'''
		for root, dirs, files in os.walk(dir):
			for file in files:
				if file.endswith(".nxml"):
					#print(f'>>> File: {file}')
					
					#if self.parse(os.path.join(root, file)):
					#	num_of_empty_body_article += 1
					
					doi = self.parse(os.path.join(root, file))
					if doi is not None:
						doi_list.append(doi.lower())
						
					#print(doi_list)
			
			#input("Press Enter to continue...")

		#print(num_of_empty_body_article)
		
		print(len(doi_list))
		
		with open(self.uid_list, 'a') as file:
			for doi in doi_list:
				file.write(doi + '\n')
	
	
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
		

	def parse(self, xml_file):
		tree = etree.parse(xml_file, self.xml_parser)
		root = tree.getroot()

		# clean xml and extract essential elements.
		specials, refs = self.nxml_reader.preprocess(root)

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
		article_pmc = article_meta.findtext('.//article-id[@pub-id-type="pmc"]')	# just in case doi is None.
		authors = []
		for author in article_meta.findall('.//contrib[@contrib-type="author"]'):
			name = author.find('name')
			if name is not None:
				authors.append(' '.join(name.itertext()))
		
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
			#label = root.xpath('//body//fig[@id="' + fig.id + '"]//label')[0].text
			#graphic_elem = root.xpath('//body//fig[@id="' + fig.id + '"]//graphic')[0]
			#fig_file = graphic_elem.get('{' + nsmap['xlink'] + '}href')
			#fig_file = xml_file.rsplit('/', 1)[0] + '/' + fig_file
			
			fig_elem = root.xpath('//fig[@id="' + fig.id + '"]')[0]
			label = fig_elem.findtext('label')
			fig_file = ''
			graphic_elem = fig_elem.find('graphic') 
			if graphic_elem is not None:
				nsmap = graphic_elem.nsmap	# root.nsmap may not contain all name spaces. e.g, sdata2018151.nxml - 11/06/2019
				fig_file = graphic_elem.get('{' + nsmap['xlink'] + '}href')
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
		
		uid = article_doi if article_doi is not None else article_pmc
		
		if uid is None:
			print(xml_file)
			sys.exit()
			
		data = {}
		data['uid'] = uid
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
			print('>> abs sent:', t)
		
		print('-------------------------------------------------------------------------')

		#body_text_sents = [sent.text for sent in nlp(body_text).sents]
			
		for t in body_text:
			print(t)
		
		input("Press Enter to continue...")
		'''
		# [end] debug
			
		# write data to file
		output_file = xml_file.replace('.nxml', '.json')
		if output_file == xml_file:
			logger.error('>> XML file does NOT exist!!')
			sys.exit()

		with open(output_file, 'w') as outfile:
			json.dump(data, outfile)
			
		return article_doi or article_pmc

