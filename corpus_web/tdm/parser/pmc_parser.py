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


	def update_uid_list(self):
		num_of_empty_body_article = 0
		
		doi_list = []

		dir = "/home/gpark/corpus_web/tdm/archive/PMC/"
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
						doi_list.append(doi)
						
					#print(doi_list)
			
			#input("Press Enter to continue...")

		#print(num_of_empty_body_article)
		
		print(len(doi_list))
		
		with open("/home/gpark/corpus_web/tdm/archive/uid_list.txt", 'a') as file:
			for doi in doi_list:
				file.write(doi + '\n')


	def parse(self, xml_file):
		tree = etree.parse(xml_file, BaseParser.parser)
		root = tree.getroot()

		# clean xml and extract essential elements.
		specials, refs = self.nxml_reader.preprocess_xml(root)

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
			authors.append(' '.join(name.itertext()))

		# Ref: https://github.com/titipata/pubmed_parser/blob/master/pubmed_parser/pubmed_oa_parser.py
		abstract_element = article_meta.findall('.//abstract')	# abstract element can be more than one.

		#txt_list = []	# [my_own_method]
		abstract = []
		
		for abs in abstract_element:
			elements = self.nxml_reader._parse_element(abs, specials=specials, refs=refs)
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
			# remove bibliographic citations
			#for bib in abs.findall('.//xref[@ref-type="bibr"]'):
			#	bib.getparent().remove(bib)
			
			# For now, remove references, formulas, and tables in texts. - 03/20/2019
			etree.strip_elements(abs, 'xref', 'inline-formula', 'tex-math', 'table-wrap')
			
			#for e in abs.iter():	# this doesn't retrive all text, but itertext() does.
			#	print(e.text)
			
			# The reason why iter() is not used like body text is that abstract may not have <p>.
			for txt in abs.itertext():
				txt = txt.replace('\n', ' ').replace('\t', ' ').strip()
				txt_list.append(txt)
					
				
				#if abs.text:
				#	if ele.tag == 'title':
				#		txt_list += ('\n' + ''.join(abs.itertext()) + '\n')
						#txt_list += ('\n' + abs.text + '\n')
				#	elif abs.tag == 'p':
					#else:
				#		txt_list += (''.join(abs.itertext()) + '\n')
				#		print(abs.itertext())
			'''
			
		#abstract = ' '.join(txt_list)	# [my_own_method]

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

		#txt_list = []	# [my_own_method]
		body_text = []
		
		#for body in bodies:
		if body_element is not None:
			elements = self.nxml_reader._parse_element(body_element, specials=specials, refs=refs)
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
			# Error occurs: texts are not fully retrieved. - 4/2/2019
			# 41598_2018_Article_34076.nxml -> The calculations of the spectral-dependent reflection in the vicinity of the boron K-threshold (Fig.
			etree.strip_elements(body_element, 'xref', 'inline-formula', 'tex-math', 'table-wrap')
			
			for ele in body_element.iter():
				#print(f'>>> Tag: {ele.tag}\n >>> Text: {ele.text}')
				
				# Just include section titles. Don't include Fig's and Table's titles.
				if ele.tag == 'title' and ele.getparent().tag in ['body', 'sec']:
					#txt_list.append('\n' + ''.join(ele.itertext()) + '\n')
					txt_list.append(''.join(ele.itertext()) + '. ')	# dot(. ) is added to let spaCy recognize it's a separate sentence. newline ('\n') is not working well in spaCy.
					
				if ele.tag == 'p' and ele.getparent().tag not in ['caption', 'fn', 'table-wrap-foot', 'supplementary-material']:
					#etree.strip_elements(ele, 'xref', 'inline-formula', 'tex-math')	# it's not working here!

					for txt in ele.itertext():
						txt = txt.replace('\n', ' ').replace('\t', ' ').strip()
						txt_list.append(txt)
					#txt_list.append(''.join(ele.itertext()))
					#txt_list.append('\n')
				
				
				#txt_list = ''
				
				#for ele in paragraph:	# body element must be one.
					#print(f'>>> Tag: {ele.tag}\n >>> Text: {ele.text}')
				#	if ele.text:
				#		if ele.tag == 'p':
				#			print(ele.getparent().tag)
				#			txt_list += (''.join(ele.itertext()) + '\n')
							#for txt in ele.itertext()
							#abs_txt.append(txt)
						#elif ele.tag == 'title':	# this includes Fig's and Table's titles, so just ignore titles for now.
						#	txt_list += ('\n' + ''.join(ele.itertext()) + '\n')
				
			body_text = ' '.join(txt_list)
			'''
		else:
			body_text = ''
		
		figure_caption = []
		
		figures = [el[0] for el in specials.values() if len(el) > 0 and isinstance(el[0], Figure)]
		for fig in figures:
			#print(figure)
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

		data['figure_caption'] = figure_caption

		
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
		output_filename = xml_file.replace('.nxml', '.json')
		if output_filename == xml_file:
			logger.error('>> XML file does NOT exist!!')
			sys.exit()
		
		with open(output_filename, 'w') as outfile:
			json.dump(data, outfile)
		
		
		return article_doi or article_pmc

