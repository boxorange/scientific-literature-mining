import os
import re
import six
import json

import numpy as np
from sklearn.metrics import classification_report, precision_recall_fscore_support

import csv

# reference: http://www.reflectometry.org/danse/docs/elements/guide/using.html
import periodictable


"""

- The first letter of the chemical symbol is always capitalized. If the symbol has two letters, the second letter is always lowercase.

"""
transition_metals = {'Sc':	'Scandium',
					'Ti':	'Titanium',
					'V':	'Vanadium',
					'Cr':	'Chromium',
					'Mn':	'Manganese',
					'Fe':	'Iron',
					'Co':	'Cobalt',
					'Ni':	'Nickel',
					'Cu':	'Copper',
					'Zn':	'Zinc',
					'Y':	'Yttrium',
					'Zr':	'Zirconium',
					'Nb':	'Niobium',
					'Mo':	'Molybdenum',
					'Tc':	'Technetium',
					'Ru':	'Ruthenium',
					'Rh':	'Rhodium',
					'Pd':	'Palladium',
					'Ag':	'Silver',
					'Cd':	'Cadmium',
					'La':	'Lanthanum',
					'Hf':	'Hafnium',
					'Ta':	'Tantalum',
					'W':	'Tungsten',
					'Re':	'Rhenium',
					'Os':	'Osmium',
					'Ir':	'Iridium',
					'Pt':	'Platinum',
					'Au':	'Gold',
					'Hg':	'Mercury'}

def find_sent(text, transition_metals, uid):
	ret_sents = []
	
	count_checker = dict.fromkeys(transition_metals.keys(), False)
	count_checker.update(dict.fromkeys([x.lower() for x in transition_metals.values()], False))

	chem_symbols = transition_metals.keys()
	chem_names = transition_metals.values()

	for sent in text:
		cems = sent['chemical_entity']
		
		if len(cems) > 0:
			#highlighted_sent = sent['sent']
			tokens = [x[0] for x in sent['token_pos']]
			alnum_tokens = [x for x in tokens if x.isalnum()]	# alphanumeric tokens. It also ignores words with special characters e.g., "in-plane"
			lc_alnum_tokens = [x.lower() for x in alnum_tokens]	# lowercase
			
			idx = lc_alnum_tokens.index('edge') if 'edge' in lc_alnum_tokens else None
			if idx is None:
				idx = lc_alnum_tokens.index('edges') if 'edges' in lc_alnum_tokens else None
			
			
			#if any(elem in lc_alnum_tokens for elem in ['edge', 'edges']):
			#if 'edge' in lc_alnum_tokens:
			if idx is not None:
				# check if it's one of the types of XAS edges (K/L/M)
				# K/L/M must appear before 'edge(s)'
				partial_tokens = alnum_tokens[:idx]
				partial_tokens.reverse()
				
				isXASEdge = False
				for tok in partial_tokens:
					if tok.startswith(("K", "L", "M")):	# must use a tuple.
						isXASEdge = True
						break
				
				if isXASEdge is True:
					if any(elem in alnum_tokens for elem in chem_symbols) or any(elem.lower() in lc_alnum_tokens for elem in chem_names):
						#print(sent['sent'])
						
						#for k, v in transition_metals.items()
						#	for tok in tokens:

						match_tokens = set()
						for symbol, name in transition_metals.items():
							for tok in alnum_tokens:
								if tok == symbol:
									match_tokens.add(tok)
									
									if count_checker[tok] == False:
										count_checker[tok] = True
										counter[tok] += 1
										if tok in article_by_metal:
											article_by_metal[tok].append(uid)
										else:
											article_by_metal[tok] = [uid]
								elif tok.lower() == name.lower():
									match_tokens.add(tok)
									
									if count_checker[tok.lower()] == False:
										count_checker[tok.lower()] = True
										counter[tok.lower()] += 1
										if tok in article_by_metal:
											article_by_metal[tok.lower()].append(uid)
										else:
											article_by_metal[tok.lower()] = [uid]

						for tok in tokens:
							if tok.lower().startswith("fig") == False:
								sentence = sent['sent']
								no_figure_sent[sentence] = "http://doi.org/" + uid								

							
						#print(sent['sent'])
						#print(match_tokens)
						#print(cems)
						#print('----------------------------------------')
						
						ret_sents.append([sent['sent'], ', '.join(match_tokens), ', '.join(str(item) for cem in cems for item in cem)])
	
	return ret_sents
		

def analyze_text():
	counter = dict.fromkeys(transition_metals.keys(), 0)
	counter.update(dict.fromkeys([x.lower() for x in transition_metals.values()], 0))

	article_by_metal = {}

	no_figure_sent = {}

	dirs = []
	dirs.append("/home/gpark/corpus_web/tdm/archive/PMC/")
	dirs.append("/home/gpark/corpus_web/tdm/archive/Springer/articles")
	dirs.append("/home/gpark/corpus_web/tdm/archive/Elsevier/articles")

	results = []
	total_articles = 0

	pdf_term = ['pair distribution function', 'pair distribution functions']
	exafs_xanes_term = ['exafs', 'xanes', 'nexafs']

	pdf_included_articles = 0
	exafs_xanes_included_articles = 0

	pdf_term_article_list = []
	NO_exafs_xanes_term_article_list = []

	for dir in dirs:
		for root, dirs, files in os.walk(dir):
		#	results.extend([os.path.join(root, file) for file in files if file.endswith(".json")])
			for file in files:
				if file.endswith(".json"):
					with open(os.path.join(root, file), "r") as read_file:
						data = json.load(read_file)
						
						uid = data['uid']
						year = data['year']
						title = data['title']
						
						sents = find_sent(data['abstract'], transition_metals, uid)
						sents.extend(find_sent(data['body_text'], transition_metals, uid))

						print("http://doi.org/" + uid)
											
						if len(sents) > 0:
							title_year = '[' + str(year) + '] ' + title
							sents.insert(0, title_year)
							
							sents.insert(1, uid)
							'''
							print(sents[0])
							print(sents[1])
							
							for elem in sents[2:]:
								for item in elem:
									print(item)
								print('----------------------------------')
							
							input("Press Enter to continue...")
							'''

							results.append(sents)
							total_articles += 1
							
							pdf_term_checker = False
							exafs_xanes_term_checker = False
							'''
							print(type(data['abstract']))
							print(type(data['body_text']))
							if isinstance(data['abstract'], six.string_types):
								print('>> Abstract !!!')
								print(data['abstract'])
							if isinstance(data['body_text'], six.string_types):
								print('>> BODY !!!')
								print(data['body_text'])
							
							if isinstance(data['abstract'], list) and isinstance(data['body_text'], list):
								text = data['abstract'] + data['body_text']
							elif isinstance(data['abstract'], list) and isinstance(data['body_text'], list)
							'''
							
							text = data['abstract'] if len(data['abstract']) > 0 else []
							text.extend(data['body_text'] if len(data['body_text']) > 0 else [])
							#print('>> Abstract !!!')
							#print(data['abstract'])
							#print('>> BODY !!!')
							#print(data['body_text'])
							#print(text)
							#print(len(text))
							#input("Press Enter to continue...")
								
							for sent in text:
								tokens = [x[0] for x in sent['token_pos']]
								alnum_tokens = [x for x in tokens if x.isalnum()]	# alphanumeric tokens
								lc_alnum_tokens = [x.lower() for x in alnum_tokens]	# lowercase
								
								#print(lc_alnum_tokens)
								
								if pdf_term_checker == False:
									if any(term in sent['sent'].lower() for term in pdf_term):
										pdf_term_checker = True
										#global pdf_included_articles
										pdf_included_articles += 1
										
								if exafs_xanes_term_checker == False:
									if any(term in lc_alnum_tokens for term in exafs_xanes_term):
										exafs_xanes_term_checker = True
										#global exafs_xanes_included_articles
										exafs_xanes_included_articles += 1
										
								if pdf_term_checker == True and exafs_xanes_term_checker == True:
									break
						
							if pdf_term_checker is True:
								pdf_term_article_list.append({'file': file, 'link': 'http://doi.org/' + uid})
							if exafs_xanes_term_checker is False:
								NO_exafs_xanes_term_article_list.append({'file': file, 'link': 'http://doi.org/' + uid})
								#print(file)
								#print('http://doi.org/' + uid)
								#input("Press Enter to continue...")

	total_articles = '{0:,d}'.format(total_articles)
	pdf_included_articles = '{0:,d}'.format(pdf_included_articles)
	exafs_xanes_included_articles = '{0:,d}'.format(exafs_xanes_included_articles)
	print('>> total_articles: ', total_articles)
	print('>> pdf_included_articles: ', pdf_included_articles)
	print('>> exafs_xanes_included_articles: ', exafs_xanes_included_articles)


	for metal, uids in article_by_metal.items():
		print(metal, ': ', len(uids))
		
		with open('articles_by_metal/' + metal + '.txt', 'w') as outfile:
			for uid in uids:
				outfile.write('http://doi.org/' + uid + '\n')


	with open('results.txt', 'w') as outfile:
		for result in results:
			outfile.write('>> Title: ' + result[0] + '\n')
			outfile.write('>> DOI: https://doi.org/' + result[1] + '\n')
			outfile.write('--------------------------------------------------------------------------\n')
			for elem in result[2:]:
				#for item in elem:
				#	outfile.write(item + '\n')
				outfile.write('>> Sent: ' + elem[0] + '\n')
				outfile.write('>> Match_tokens: ' + elem[1] + '\n')
				outfile.write('>> Cems: ' + elem[2] + '\n')
				outfile.write('--------------------------------------------------------------------------\n')
			outfile.write('#############################################################################\n')

	with open('pdf_term_article_list.txt', 'w') as outfile:
		for article in pdf_term_article_list:
			outfile.write(article['file'] + ' -> ' + article['link'] + '\n')

	with open('NO_exafs_xanes_term_article_list.txt', 'w') as outfile:
		for article in NO_exafs_xanes_term_article_list:
			outfile.write(article['file'] + ' -> ' + article['link'] + '\n')

	with open('NO_figure_sents.txt', 'w') as outfile:
		for sent, doi in no_figure_sent.items():
			outfile.write(sent + ' -> ' + doi + '\n')


def find_region(sent, lc_alnum_tokens):
	'''
	TODO: check if region is more than one. A sentence may contain both 'EXAFS' and 'XANES'.
	'''
	region = None
	# e.g. "Rh K-edge X-ray absorption near-edge structure spectra."
	s = re.sub('[^0-9a-zA-Z]+', ' ', sent)	# repalce non-alphanumeric with a space.
	s = ' '.join(s.split())	# replace multiple spaces with one.
	s = s.lower()	# lowercase
	
	if 'exafs' in lc_alnum_tokens or "Extended X Ray Absorption Fine Structure".lower() in s:
		region = 'EXAFS'
	elif ('xanes' in lc_alnum_tokens or "X ray absorption near edge structure".lower() in s or 
		  'nexafs' in lc_alnum_tokens or "near edge X ray absorption fine structure".lower() in s):
		region = 'XANES'
	#else:
	#	print(sent)
		#input("Press Enter to continue...")

	return region
					

def find_element(tokens):
	for tok in tokens:
		for el in periodictable.elements: 
			if tok == el.symbol or tok.lower() == el.name.lower():
				if el.symbol in transition_metals:
					return el.symbol
				else:
					return None
	return None


def find_xas_result(elements):
	ret_val = []

	chem_symbols = transition_metals.keys()
	chem_names = transition_metals.values()

	for elem in elements:
		sent = elem['sent']
		token_pos = elem['token_pos']
		cems = elem['chemical_entity']
		
		if len(cems) > 0:
			tokens = [x[0] for x in token_pos]
			alnum_tokens = [x for x in tokens if x.isalnum()]	# alphanumeric tokens. It also ignores words with special characters e.g., "in-plane"
			lc_alnum_tokens = [x.lower() for x in alnum_tokens]	# lowercase
			
			idx = lc_alnum_tokens.index('edge') if 'edge' in lc_alnum_tokens else None
			if idx is None:
				idx = lc_alnum_tokens.index('edges') if 'edges' in lc_alnum_tokens else None
			
			#if any(elem in lc_alnum_tokens for elem in ['edge', 'edges']):
			#if 'edge' in lc_alnum_tokens:
			if idx is not None:
				# check if it's one of the types of XAS edges (K/L/M)
				# K/L/M must appear before 'edge(s)'
				partial_tokens = alnum_tokens[:idx]
				partial_tokens.reverse()
				
				#isXASEdge = False
				type_of_edge = None
				# possible names: Cu K-edge | L3 and L2 edges of Ca | Mo K edge | Au L3-edge | Au-L3 edge | Re LIII-edge | Fe LII,III edges | Fe K-edge—Mn K-edge | L3,2 edges of Mn | Ni K-, Co K-, and Ru K-edge | Iron K-Edge XAFS
				# 'K' isn't followed by numbers.
				regex = '^[LM][iI0-9]+$'
				for tok_idx, tok in enumerate(partial_tokens):
					#if tok.startswith(("K", "L", "M")):	# must use a tuple.
					#	isXASEdge = True
					#	break
					if tok in ["K", "L", "M"] or re.match(regex, tok):
						if tok.startswith('K'):
							# debug - in case of multiple edge types which shouldn't exist!!
							if type_of_edge is not None and type_of_edge != 'K':
								print(sent)
								print(tok)
								#input("Press Enter to continue...")
							
							type_of_edge = 'K'
						elif tok.startswith('L'):
							# debug - in case of multiple edge types which shouldn't exist!!
							if type_of_edge is not None and type_of_edge != 'L':
								print(sent)
								print(tok)
								#input("Press Enter to continue...")
							
							type_of_edge = 'L'
						elif tok.startswith('M'):
							# debug - in case of multiple edge types which shouldn't exist!!
							if type_of_edge is not None and type_of_edge != 'M':
								print(sent)
								print(tok)
								#input("Press Enter to continue...")
								
							type_of_edge = 'M'
						
						if type_of_edge:
							# Element must appear before 'K/L/M'
							# Don't use index() since it only captures the first occurance of given string. e.g., Ni L3, e Co L3, and f Mn L3 edges,
							another_partial_tokens = partial_tokens[tok_idx + 1:]

							element = find_element(another_partial_tokens)
							region = find_region(sent, lc_alnum_tokens)
							
							print('>> sentence: ', sent)
							print('>> cems: ', cems)
							print('>> another_partial_tokens: ', another_partial_tokens)
							print('>> region: ', region, ' / element: ', element, ' / edge: ', type_of_edge)
									
							ret_val.append({'region': region, 'element': element, 'edge': type_of_edge})
							
							
				'''
				if type_of_edge:
					if any(elem in alnum_tokens for elem in chem_symbols) or any(elem.lower() in lc_alnum_tokens for elem in chem_names):
						for symbol, name in transition_metals.items():
							for tok in alnum_tokens:
								if tok == symbol or tok.lower() == name.lower():
									region = None
									# e.g. "Rh K-edge X-ray absorption near-edge structure spectra."
									s = re.sub('[^0-9a-zA-Z]+', ' ', sent['sent'])	# repalce non-alphanumeric with a space.
									s = ' '.join(s.split())	# replace multiple spaces with one.
									s = s.lower()	# lowercase
									
									if 'exafs' in lc_alnum_tokens or "Extended X Ray Absorption Fine Structure".lower() in s:
										region = 'EXAFS'
									elif ('xanes' in lc_alnum_tokens or "X ray absorption near edge structure".lower() in s or 
										  'nexafs' in lc_alnum_tokens or "near edge X ray absorption fine structure".lower() in s):
										region = 'XANES'
									else:
										print(sent['sent'])
										#input("Press Enter to continue...")
									
									print('>> region: ', region, ' / element: ', tok, ' / edge: ', type_of_edge)
									
									ret_val.append({'region': region, 'element': symbol, 'edge': type_of_edge})
				'''
	return ret_val


def iterate_dir(dirs):

	ret = []
	
	for dir in dirs:
		for root, dirs, files in os.walk(dir):
			for file in files:
				if file.endswith(".json"):
					with open(os.path.join(root, file), "r+") as f:
						data = json.load(f)
						
						uid = data['uid']
						year = data['year']
						title = data['title']
						figure_caption = data['figure_caption']
						
						if len(figure_caption) > 0:
							body_text = data['body_text']
							
							for elem in body_text:
								sent = elem['sent']
								token_pos = elem['token_pos']
								tokens = [x[0] for x in token_pos]
								alnum_tokens = [x for x in tokens if x.isalnum()]	# alphanumeric tokens. It also ignores words with special characters e.g., "in-plane"
								lc_alnum_tokens = [x.lower() for x in alnum_tokens]	# lowercase
								region = find_region(sent, lc_alnum_tokens)
								transition_metal = find_element(alnum_tokens)
								
								if region is not None and transition_metal is not None:
									#print(file, ' -> ', "http://doi.org/" + uid)
									ret.append(file + ' -> ' + "http://doi.org/" + uid)
									#input("Press Enter to continue...")
									break
							
							
						'''

						results = find_xas_result(figure_caption)
						
						# reference: https://stackoverflow.com/questions/9427163/remove-duplicate-dict-in-list-in-python
						data['xas_info'] = [dict(t) for t in {tuple(d.items()) for d in results}]
						
						# reference: https://stackoverflow.com/questions/21035762/python-read-json-file-and-modify
						f.seek(0)        # <--- should reset file position to the beginning.
						json.dump(data, f)
						f.truncate()     # remove remaining part

						#input("Press Enter to continue...")
						
						#print("http://doi.org/" + uid)
						
						'''
						
	with open('debug_file_elsevier.txt', 'w') as outfile:
		for el in ret:
			outfile.write(el + '\n')


def create_xas_tree_json(dirs):

	xas_tree = [
				   { "id": "xas", "parent": "#", "text": "XAS", "count": 0 },
				   { "id": "exafs", "parent": "xas", "text": "EXAFS", "count": 0 },
				   { "id": "xanes", "parent": "xas", "text": "XANES", "count": 0 }
				]

	for symbol in transition_metals.keys():
		xas_tree.append({ "id": 'exafs_' + symbol, "parent": "exafs", "text": symbol, "count": 0 })
		xas_tree.append({ "id": 'xanes_' + symbol, "parent": "xanes", "text": symbol, "count": 0 })
		
		xas_tree.append({ "id": 'exafs_' + symbol + "_k", "parent": 'exafs_' + symbol, "text": "K-edge", "count": 0 })
		xas_tree.append({ "id": 'exafs_' + symbol + "_l", "parent": 'exafs_' + symbol, "text": "L-edge", "count": 0 })
		xas_tree.append({ "id": 'exafs_' + symbol + "_m", "parent": 'exafs_' + symbol, "text": "M-edge", "count": 0 })
		
		xas_tree.append({ "id": 'xanes_' + symbol + "_k", "parent": 'xanes_' + symbol, "text": "K-edge", "count": 0 })
		xas_tree.append({ "id": 'xanes_' + symbol + "_l", "parent": 'xanes_' + symbol, "text": "L-edge", "count": 0 })
		xas_tree.append({ "id": 'xanes_' + symbol + "_m", "parent": 'xanes_' + symbol, "text": "M-edge", "count": 0 })
	
	
	for dir in dirs:
		for root, dirs, files in os.walk(dir):
			for file in files:
				if file.endswith(".json"):
					with open(os.path.join(root, file), "r") as f:
						data = json.load(f)
						
						uid = data['uid']
						year = data['year']
						title = data['title']
						
						xas_info = data['xas_info']
						
						if uid is None:
							print(file)
							sys.exit()

						num = 0
						for xi in xas_info:
							region = xi['region']
							element = xi['element']
							edge = xi['edge']
							
							if region is not None and element is not None and edge is not None:
								xas_tree.append({"id": uid + '_' + str(num), 
												 "parent": region.lower() + '_' + element + '_' + edge.lower(), 
												 "text": '[' + year + '] ' + title,
												 "a_attr": {'href': 'http://doi.org/' + uid},
												 "type": "paper"})
								num += 1
								
								for node in xas_tree:
									if node['id'] == region.lower() + '_' + element + '_' + edge.lower():
										node['count'] += 1
									if node['id'] == region.lower() + '_' + element:
										node['count'] += 1	
									if node['id'] == region.lower():
										node['count'] += 1
									if node['id'] == "xas":
										node['count'] += 1

						#for l in li:
						#	print(l)
							
						#input("Press Enter to continue...")
	
	for node in xas_tree:
		if 'count' in node:
			node['text'] = node['text'] + " (" + str(node['count']) + ")"
	
	with open('xas_tree.json', 'w') as outfile:
			json.dump(xas_tree, outfile)


def evaluate_model():
	true_sample = {}
	pred_sample = {}

	with open('training_set.csv') as csvfile:	# read actual values.
		csv_reader = csv.reader(csvfile, delimiter=',')
		next(csv_reader)	# skip the top row which is the header.
	
		# header - No, Publisher, DOI, Sample, Element(s), Spectral regions, Types of Edge, JSON File, Classification Error, Comments
		for row in csv_reader:
			link = row[2].strip()
			elem = row[4].strip()
			spectroscopy = row[5].strip()
			edge = row[6].strip()
			
			#print(elem,spectroscopy,edge)
						
			key = link.split(':', 1)[1]		# ignore 'http(s)' because the same links sometimes use different protocol (http vs https). 
			val = (spectroscopy + '_' + elem + '_' + edge).lower()
			
			if key in true_sample:
				true_sample[key].append(val)
			else:
				true_sample[key] = [val]

	with open('xas_tree.json', "r") as f:	# read predicted values.
		data = json.load(f)
		#pred_sample = [elem for elem in data if 'type' in elem]	# filter out non-articles.

		for elem in data:	
			if 'type' in elem:	# filter out non-articles.
				key = elem['a_attr'].get('href').split(':', 1)[1]	# ignore 'http(s)' because the same links sometimes use different protocol (http vs https). 
				val = elem['parent'].lower()
				
				if key in pred_sample:
					pred_sample[key].append(val)
				else:
					pred_sample[key] = [val]
	
	y_true = []
	y_pred = []
	for paper, cls in true_sample.items():
		if paper in pred_sample:
			same_cls = list(set(cls) & set(pred_sample[paper])) 
			y_true.extend(same_cls)
			y_pred.extend(same_cls)
			
			y_true.extend(list(set(cls) - set(pred_sample[paper])))
			y_pred.extend(list(set(pred_sample[paper]) - set(cls)))
			
			if len(y_pred) < len(y_true):
				y_pred.extend(['none'] * (len(y_true) - len(y_pred)))
		else:
			y_true.extend(cls)
			y_pred.extend(['none'] * len(cls))
	
	
	for elem in y_true:
		print(elem)
	
	print('------------------------------------------------')
	
	for elem in y_pred:
		print(elem)
		
	#y_true = np.array(y_true)
	#y_pred = np.array(y_pred)
	
	# ignore 'none' class, and consider the true classes.
	print(classification_report(y_true, y_pred, labels=np.unique(y_true)))
	
	
if __name__ == "__main__":
	#analyze_text()
	
	#dirs = []
	#dirs.append("/home/gpark/corpus_web/tdm/archive/PMC/")
	#dirs.append("/home/gpark/corpus_web/tdm/archive/Springer/articles")
	#dirs.append("/home/gpark/corpus_web/tdm/archive/Elsevier/articles")
	
	#iterate_dir(dirs)
	#create_xas_tree_json(dirs)
	
	#evaluate_model()
	
	num = set()
	with open('xas_tree.json', "r") as f:	# read predicted values.
		data = json.load(f)

		for elem in data:
			if 'type' in elem:	# filter out non-articles.
				num.add(elem['id'])
	
	print(len(num))

	