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


class IOPParser(BaseParser):
	"""
	Note:
	- IOP article (PDF) has a meta file (.article) that contains meta information of the article in XML format.
	- Some files don't have .article.
		e.g., /home/gpark/corpus_web/tdm/archive/IOP/1674-1137/41/10/101001/cpc_41_10_101001.pdf
	
	References:
	- http://ej.iop.org/dtd/header.dtd
	"""
	
	nxml_reader = NlmXmlReader()
	
	
	def __init__(self):
		super().__init__('IOP')	# TODO: 'IOP' is just temporary name. Fix it after the code complete.
	

	def parse(self, xml_file):
		'''
		document encoding is ISO-8859-1, and if resolve_entities is set to True, then XMLSyntaxError occurs.
		'''
		xml_parser = etree.XMLParser(encoding='ISO-8859-1', resolve_entities=False)
		tree = etree.parse(xml_file, xml_parser)
		
		#try:
		#	tree = etree.parse(xml_file, self.parser)
		#except etree.XMLSyntaxError:
		#	pass
		
		# debug
		docinfo = tree.docinfo
		encoding_info = docinfo.encoding
		
		if encoding_info != 'ISO-8859-1':
			print(encoding_info)
			input("Press Enter to continue...")

		root = tree.getroot()
			
		title = root.find('.//title_full')
		title = etree.tostring(title).decode("utf-8")	# retrive the original value to show in the TDM webpage.
		title = title.split(">", 1)[1]		# TODO: find a better way to remove the top tag.
		title = title.rsplit("</", 1)[0]
		doi = root.findtext('.//doi')
	
		# year checking priority: (1) date_history[epub] (2) date_cover (3) date_online[header]
		year = None
		year_elem = root.find('.//date_history')
		if year_elem is not None:
			year = year_elem.get('epub')
			if year is not None:
				year = year.split('-')[0]		
		if year is None:
			year_elem = root.find('.//date_cover')
			if year_elem is not None:
				year = root.findtext('.//date_cover')
				year = year.split('-')[0]
		if year is None:
			year_elem = root.find('.//date_online')
			if year_elem is not None:
				year = year_elem.get('header')
				if year is not None:
					year = year.split('-')[0]

		authors = []
		#for author in root.findall('.//author_granular'):
		#	given = author.findtext('given')
		#	surname = author.findtext('surname')
		#	authors.append(given + ' ' + surname)
		for author in root.findall('.//author'):	# not all article has <author_granular> tag
			authors.append(author.text)
		
		
		abstract = []
		abstract_element = root.find('.//header_text') # not all article has [heading="Abstract"]
		#abstract = ''
		#if abstract_element is not None:
		#	abstract = ' '.join(abstract_element.itertext())
		#	abstract = abstract.strip()
		
		if abstract_element is not None: 
			# TODO: Fix the CDE related error - AttributeError: 'cython_function_or_method' object has no attribute 'lower'
			# e.g., jopt13_9_090201.pdf, jopt13_11_114001.pdf
			try:
				elements = self.nxml_reader._parse_element(abstract_element)
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
			except: 
				print('>> Error:', xml_file)
				pass
									  
		copyright_text = root.findtext('.//copyright_text')	# this will be used to remove copy right text from the extracted text from PDF.
		
		if doi is None:
			input("Press Enter to continue...")
		
		logger.debug(#f'\n>>> Journal Title: {journal_title}\n'
					 #f'>>> Publisher: {publisher}\n'
					 #f'>>> Article Type: {article_type}\n'
					 f'\n>>> Encoding: {encoding_info}\n'
					 f'>>> Title: {title}\n'
					 f'>>> Year: {year}\n'
					 f'>>> UID: {doi}\n'
					 f'>>> Authors: {authors}\n'
					 f'>>> Abstract:\n{abstract}\n'
					 f'>>> CopyRight:\n{copyright_text}\n')
					 #f'>>> Keywords: {keywords}\n')
					 #f'>>> Body Text:\n{body_text}\n')
		
		metadata = {}
		metadata['uid'] = doi
		metadata['publisher'] = 'IOP'
		metadata['type'] = 'journal-article'	# TODO: exclude non journal articles.
		metadata['title'] = title
		metadata['year'] = year
		metadata['author'] = authors
		metadata['abstract'] = abstract
		
		return [metadata, copyright_text]

