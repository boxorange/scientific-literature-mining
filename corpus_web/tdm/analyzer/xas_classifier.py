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
		

def analyze_text(dirs):
	counter = dict.fromkeys(transition_metals.keys(), 0)
	counter.update(dict.fromkeys([x.lower() for x in transition_metals.values()], 0))

	article_by_metal = {}

	no_figure_sent = {}

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
				# Ignore downloaded json files, and only use a generated json which has the same name of an original article.
				if file.endswith(".json") and \
					(os.path.exists(os.path.join(root, file.replace(".json", ".xml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".nxml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".html")))):
					
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


def get_info_from_body_text(fig_id, body_text):
	"""
	TODO: fig id in body text (e.g., Figure 3) can be different from the one in captions (Fig. 3). So, modify this. - 07/30/2019
	
	"""
	fig_num = re.sub('[^0-9]', '', fig_id)

	if fig_num.isdigit() == False:
		print(">> Error: ", fig_num)
		exit()

	for sentence in body_text:
		token_pos = sentence["token_pos"]
		
		found = False
		for idx, tok in enumerate(token_pos):
			word = re.sub(r"[\W_]", "", tok[0])	# remove non-alphanumeric characters.
			word = word.lower()

			if word in ['figure', 'fig']:
				for tok_2 in token_pos[idx + 1:]:
					word_2 = tok_2[0]

					'''
					Examples
					- 1. Fig. 6b -> '6b' is a token.
					- 2. Fig. 1 vs. Fig. 10
					- 3. Figure 6(a,b) -> 6(a,b) is a token. -> \PMC\PMC6202349\41598_2018_Article_33976.json
					'''
					if word_2 == fig_num or re.match("^" + fig_num + "[A-Za-z]*", word_2):	
						found = True
						break
					if word_2[0].isalpha():
						break
			
			if found is True:
				break
			
		if found is True:
			print(">> Body sentence:", sentence["sent"])
			print(">> chemical_entity:", sentence["chemical_entity"])

		
	


def find_region(sent, lc_alnum_tokens):
	region = []
	# e.g. "Rh K-edge X-ray absorption near-edge structure spectra."
	s = re.sub('[^a-zA-Z0-9]+', ' ', sent)	# repalce non-alphanumeric with a space.
	s = ' '.join(s.split())	# replace multiple spaces with one.
	s = s.lower()	# lowercase
	
	if 'exafs' in lc_alnum_tokens or "Extended X Ray Absorption Fine Structure".lower() in s:
		region.append('EXAFS')
	
	if ('xanes' in lc_alnum_tokens or "X ray absorption near edge structure".lower() in s or 
		'nexafs' in lc_alnum_tokens or "near edge X ray absorption fine structure".lower() in s):
		region.append('XANES')
	#else:
	#	print(sent)
		#input("Press Enter to continue...")

	return region
					

def find_element(tokens):
	elem = []
	for tok in tokens:
		for el in periodictable.elements: 
			if tok == el.symbol or tok.lower() == el.name.lower():
				if el.symbol in transition_metals:
					elem.append(el.symbol)
	return elem


def find_xas_result(figures, body_text):
	"""
	Test cases:
	1. more than one 'edge'
		-> ADVS-2-0p.json - http://doi.org/10.1002/advs.201500022
	2. multiple elements and edges
		-> 101038s415240180067x.json - 101038s414270180056z.json
	3. hyphen unicode symbol
		-> ADVS-4-na.json - http://doi.org/10.1002/advs.201700465
	4. tokens unsplit by hyphen e.g., Cu-K, L-edge
		-> 101186s4049401500425.json - http://doi.org/10.1186/s40494-015-0042-5
		-> S0022459618304250.json - http://doi.org/10.1016/j.jssc.2018.09.039
	5. TODO - more than one region
		-> Beilstein_J_Nanotechnol-02-198.json - http://doi.org/10.3762/bjnano.2.23
		-> S0031018218303808.json - http://doi.org/10.1016/j.palaeo.2018.12.014
	6. TODO - element names appear after the edge.
		-> ncomms8345.json - http://doi.org/10.1038/ncomms8345
	"""
	ret_val = []

	chem_symbols = transition_metals.keys()
	chem_names = transition_metals.values()
					
	for fig in figures:
		fig_id = fig['fig_id']
		#label = fig['label']
		#caption = ' '.join([x['sent'] for x in fig['caption']])
		#caption = fig['caption']
		#fig_file = fig['fig_file']
		
		for elem in fig['caption']:
			sent = elem['sent']
			token_pos = elem['token_pos']
			cems = elem['chemical_entity']
			
			if len(cems) > 0:
				# split 'edge' with hyphen unicode string.
				tokens = []
				for x in token_pos:
					if '\u2010edge' in x[0].lower():	# \u2010 -> hyphen unicode character
						tokens.extend(x[0].split('\u2010'))
					elif '-' in x[0]:	# sometimes tokens unsplit by hyphen exist.
						tokens.extend(x[0].split('-'))
					else:
						tokens.append(x[0])

				#alnum_tokens = [x for x in tokens if x.isalnum()]	# isalnum() -- alphanumeric tokens -- excludes words with special characters e.g., "K-edge", "L3,2"
				alpha_tokens = [x for x in tokens if re.search('[a-zA-Z]', x)]	# elements having at least an alphabet character.
				lc_alpha_tokens = [x.lower() for x in alpha_tokens]	# lowercase

				# 1. get the word 'edge(s)' indices.
				edge_idx = [idx for idx, tok in enumerate(lc_alpha_tokens) if tok == 'edge' or tok == 'edges']

				# If there are more than an edge, the next edge segment must not consider the first edge segment.
				# e.g., a) XANES Mn L3,2‐edges of LNMO‐20, LNMO‐20 cycled, LNMO‐0, LNMO‐0 cycled, and standard MnO, Mn2O3, MnO2; b) Fe L3‐edges of standard FePO4, LNMO‐20 and LNMO‐20 after 100 battery cycles collected in TEY mode.
				prev_edge_idx = -1
				for idx in edge_idx:
					if prev_edge_idx > -1:
						partial_tokens = alpha_tokens[prev_edge_idx + 1:idx]
					else:
						partial_tokens = alpha_tokens[:idx]
						
					#partial_tokens.reverse()
					
					prev_edge_idx = idx

					# 2. check if it's one of the types of XAS edges (K/L/M) that must appear before 'edge(s)', and get categories of edge(s) (K/L/M) and their indices.
					# possible names: Cu K-edge | L3 and L2 edges of Ca | Mo K edge | Au L3-edge | Au-L3 edge | Re LIII-edge | Fe LII,III edges | Fe K-edge—Mn K-edge | L3,2 edges of Mn | Ni K-, Co K-, and Ru K-edge | Iron K-Edge XAFS
					regex = '^[LM][iI0-9]+'	# 'K' isn't followed by numbers.
					cat_idx = {idx: tok[0] for idx, tok in enumerate(partial_tokens) if tok in ["K", "L", "M"] or re.match(regex, tok)}
					
					# If there are multiple categories, the next category segment must not consider the first category segment.
					# e.g., K K, Co L, Mn L and O K edges
					prev_cat_idx = -1
					for idx, type_of_edge in cat_idx.items():
						# Element can appear before/after 'K/L/M'.
						# TODO: handle element names after the edge.
						# e.g., "(a,b) K-edge XANES patterns of Co (a) and Mn (b) in the synthesized spinels and the reference oxides.", [ncomms8345.json, http://doi.org/10.1038/ncomms8345]
						# Don't use index() since it only captures the first occurance of given string. e.g., Ni L3, e Co L3, and f Mn L3 edges,
						
						#another_partial_tokens = partial_tokens[idx + 1:]
						
						if prev_cat_idx > -1:
							another_partial_tokens = partial_tokens[prev_cat_idx + 1:idx]
						else:
							another_partial_tokens = partial_tokens[:idx]
						
						prev_cat_idx = idx
											
						element = find_element(another_partial_tokens)
						
						# TODO: region is more than one. 
						#		The difficulty is that regions can appear anywhere in the sentence unlike element names that mostly appear before edges.
						# e.g., "Zr K-edge (a) normalized XANES, (b) k\n3-weighted EXAFS" -> Beilstein_J_Nanotechnol-02-198.json, http://doi.org/10.3762/bjnano.2.23
						#       "The EXAFS spectra of Fe and the XANES spectra of Mo can be classified into roughly four types" -> S0031018218303808.json, http://doi.org/10.1016/j.palaeo.2018.12.014]
						region = find_region(sent, lc_alpha_tokens)

						if region and element:
							
							# TODO: complete the function.
							#get_info_from_body_text(fig_id, body_text)

							
							for r in region:
								for e in element:
									#ret_val.append({'fig_id': fig_id, 'label': label, 'caption': caption, 'fig_file': fig_file, 'region': r, 'element': e, 'edge': type_of_edge})
									ret_val.append({'fig_id': fig_id, 'region': r, 'element': e, 'edge': type_of_edge})
									
									print('\n>> fig_id: ', fig_id)
									print('>> sentence: ', sent)
									print('>> cems: ', cems)
									print('>> cat_idx: ', cat_idx)
									print('>> partial_tokens: ', partial_tokens)
									print('>> another_partial_tokens: ', another_partial_tokens)
									print('>> region: ', r, ' / element: ', e, ' / edge: ', type_of_edge)
							
							print('-----------------------------------------------------------------------')

	return ret_val


def iterate_dir(dirs):
	for dir in dirs:
		for root, dirs, files in os.walk(dir):
			for file in files:
				# Ignore downloaded json files, and only use a generated json which has the same name of an original article.
				if file.endswith(".json") and \
					(os.path.exists(os.path.join(root, file.replace(".json", ".xml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".nxml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".html")))):

					# debugging...
					#if file not in ['ADVS-2-0p.json', 'S0022459618304250.json']:
					#if file != '101038s414270180056z.json':
					#	continue

				
					with open(os.path.join(root, file), "r+") as f:
						data = json.load(f)
						
						uid = data['uid']
						year = data['year']
						title = data['title']
						body_text = data['body_text']
						figures = data['figures']
						
						print('-----------------------------------------------------')
						print('>>>>>>>>>>>>>>>>>>>>>>>>> File:', file)

						results = find_xas_result(figures, body_text)
						
						if len(results) > 0:
							print(results)
							#input("Press Enter to continue...")
						

						# reference: https://stackoverflow.com/questions/9427163/remove-duplicate-dict-in-list-in-python
						data['xas_info'] = [dict(t) for t in {tuple(d.items()) for d in results}]	# remove duplicates
						
						# reference: https://stackoverflow.com/questions/21035762/python-read-json-file-and-modify
						f.seek(0)        # <--- should reset file position to the beginning.
						json.dump(data, f)
						f.truncate()     # remove remaining part

						#input("Press Enter to continue...")
						
						#print("http://doi.org/" + uid)



def create_debug_files_for_sample_selection(dirs):
	"""
	Note:
		to select random samples for evaulation, it generates a list of articles having a xas result for each publisher.
	"""
	ret = []
	for dir in dirs:
		for root, dirs, files in os.walk(dir):
			for file in files:
				# Ignore downloaded json files, and only use a generated json which has the same name of an original article.
				if file.endswith(".json") and \
					(os.path.exists(os.path.join(root, file.replace(".json", ".xml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".nxml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".html")))):
					 
					with open(os.path.join(root, file), "r+") as f:
						data = json.load(f)
						
						uid = data['uid']
						year = data['year']
						title = data['title']
						figures = data['figures']
						
						if len(figures) > 0:
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

	with open('debug_file_elsevier.txt', 'w') as outfile:
		for el in ret:
			outfile.write(el + '\n')


def create_xas_tree_json(dirs):
	xas_tree = [{ "id": "xas", "parent": "#", "text": "XAS", "count": 0 },
				{ "id": "exafs", "parent": "xas", "text": "EXAFS", "count": 0 },
				{ "id": "xanes", "parent": "xas", "text": "XANES", "count": 0 }]

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
				# Ignore downloaded json files, and only use a generated json which has the same name of an original article.
				if file.endswith(".json") and \
					(os.path.exists(os.path.join(root, file.replace(".json", ".xml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".nxml"))) or \
					 os.path.exists(os.path.join(root, file.replace(".json", ".html")))):
					 
					# debugging...
					#if file not in ['ADVS-2-0p.json', 'S0022459618304250.json']:
					#if file != '41598_2019_Article_38974.json':
					#	continue

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
							fig_id = xi['fig_id']
							label = ''
							caption = ''
							fig_file = ''
							
							for fig in data['figures']:
								if fig_id == fig['fig_id']:
									label = fig['label']
									caption = [x['sent'] for x in fig['caption']]
									fig_file = fig['fig_file']
									break
							
							region = xi['region']
							element = xi['element']
							edge = xi['edge']

							if region is not None and element is not None and edge is not None:					
								xas_class = region.lower() + '_' + element + '_' + edge.lower()
								
								# TODO: find a better way. this is a very naive way. - 11/08/2019
								existing_class = False
								for node in xas_tree:
									if node['id'].rsplit('_', 1)[0] == uid and node['parent'] == xas_class:
										node['data'].append({'fig_label': label,
															 'fig_caption': caption,
															 'fig_file': fig_file})
										existing_class = True				 
										break
								
								if existing_class == False:
									xas_tree.append({"id": uid + '_' + str(num), 
													 "parent": xas_class, 
													 "text": '[' + year + '] ' + title,
													 "a_attr": {'href': 'http://doi.org/' + uid},
													 "type": "paper",
													 "data": [{'fig_label': label,
															  'fig_caption': caption,
															  'fig_file': fig_file}]
													}) 
									num += 1

									'''
									TODO: use the jsTree funciton. - 11/08/2019
										 https://github.com/vakata/jstree/blob/master/src/misc.js#L181
										 https://github.com/vakata/jstree/issues/2104
									'''
									for node in xas_tree:
										if node['id'] == region.lower() + '_' + element + '_' + edge.lower():
											node['count'] += 1
										if node['id'] == region.lower() + '_' + element:
											node['count'] += 1	
										if node['id'] == region.lower():
											node['count'] += 1
										if node['id'] == "xas":
											node['count'] += 1

	xas_tree = [x for x in xas_tree if 'count' not in node or node['count'] > 0]
	
	filtered_xas_tree = []
	for node in xas_tree:	# remove empty elements
		if 'count' not in node:
			filtered_xas_tree.append(node)
		elif node['count'] > 0:
			filtered_xas_tree.append(node)
		
	for node in filtered_xas_tree:
		if 'count' in node:
			node['text'] = node['text'] + " (" + str(node['count']) + ")"

	with open('data/xas_classifier_data/xas_tree_new.json', 'w') as outfile:
		json.dump(filtered_xas_tree, outfile)


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
	for paper_link, true_cls in true_sample.items():
		if paper_link in pred_sample:
			pred_cls = pred_sample[paper_link]
			same_cls = list(set(true_cls) & set(pred_cls)) 
			y_true.extend(same_cls)
			y_pred.extend(same_cls)
			
			y_true.extend(list(set(true_cls) - set(pred_cls)))
			y_pred.extend(list(set(pred_cls) - set(true_cls)))
			
			if len(y_pred) < len(y_true):	# when the alg misses true classes. e.g., true: XANES_Ni_K, EXAFS_Ni_K <-> pred: XANES_Ni_K
				y_pred.extend(['none'] * (len(y_true) - len(y_pred)))
			elif len(y_pred) > len(y_true):	# when the alg predicts more (wrong) classes. e.g, true: XANES_Ni_K <-> pred: XANES_Ni_K, EXAFS_Ni_K
				del y_pred[len(y_true):]
		else:
			y_true.extend(true_cls)
			y_pred.extend(['none'] * len(true_cls))
	
	
	for elem in y_true:
		print(elem)
	
	print('------------------------------------------------')
	
	for elem in y_pred:
		print(elem)
		
	#y_true = np.array(y_true)
	#y_pred = np.array(y_pred)
	
	# ignore 'none' class, and consider the true classes.
	print(classification_report(y_true, y_pred, labels=np.unique(y_true)))


def main():
	dirs = []
	dirs.append("/home/gpark/corpus_web/tdm/archive/PMC/")
	dirs.append("/home/gpark/corpus_web/tdm/archive/Springer/")
	dirs.append("/home/gpark/corpus_web/tdm/archive/Elsevier/")
	dirs.append("/home/gpark/corpus_web/tdm/archive/RSC/")
	
	#analyze_text(dirs)		# debugging

	iterate_dir(dirs)
	create_xas_tree_json(dirs)
	#create_debug_files_for_sample_selection(dirs)
	
	#evaluate_model()
	
	# count the number of end node (paper) in the tree.
	'''
	num = set()
	with open('xas_tree.json', "r") as f:	# read predicted values.
		data = json.load(f)

		for elem in data:
			if 'type' in elem:	# filter out non-articles.
				num.add(elem['id'])
	
	print(len(num))
	'''
	
if __name__ == "__main__":
	main()