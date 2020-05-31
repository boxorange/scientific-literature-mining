import os
import sys
import time
from lxml import etree
import json
import requests

from base_parser import BaseParser
from elsevier_parser import ElsevierParser
from springer_parser import SpringerParser
from pmc_parser import PMCParser
from pdf_parser import PDFParser
from rsc_parser import RSCParser
from aaas_parser import AAASParser


def update_uid_list():
	ep = ElsevierParser()
	sp = SpringerParser()
	pp = PMCParser()
	pdf_p = PDFParser()
	rp = RSCParser()

	#ep.update_uid_list()
	#sp.update_uid_list()
	#pp.update_uid_list()
	#pdf_p.update_uid_list('APS')
	#pdf_p.update_uid_list('ACS')
	#pdf_p.update_uid_list('Wiley')
	#pdf_p.update_uid_list('IUCr')
	#pdf_p.update_uid_list('RSC')
	#pdf_p.update_uid_list('IOP_JSON')
	rp.update_uid_list()


def parse_Elsevier():
	ep = ElsevierParser()

	#cnt_no_body_article = 0
	cnt = 0

	dir = ep.path
	
	#file_list = os.listdir(dir)
	#chk_idx = file_list.index("S037015731830036X.xml")	# to re-start after the last downloaded article.
	#file_list = file_list[chk_idx + 1:]

	#file_list = ['/home/gpark/corpus_web/tdm/archive/Elsevier/articles/S003960280700461X.xml']

	#from collections import defaultdict
	#tmp = defaultdict(int) # default value of int is 0
	
	# when an error occurs, to start after the last processed file.
	check_point_found = False
	
	# to reduce the parsing time, split the collection into several partitions.
	# TODO: However, the concurrent requests cause RATE_LIMIT_EXCEEEDED (ERROR Code: 429) 
	partition_start = 90000
	partition_end = 110000
	
	
	#flag = False

	for root, dirs, files in os.walk(dir):
		for file in files:
			# Ignore object xml files (downloaded xml files as supplementary object), and only parse article xml files of which the directory has the same name. Skip already parsed articles.
			if file.endswith(".xml") and file.rsplit('.', 1)[0] == root.rsplit('/', 1)[1] and os.path.isfile(os.path.join(root, file.replace('.xml', '.json'))) == False: 
			#if file.endswith(".xml") and file.rsplit('.', 1)[0] == root.rsplit('/', 1)[1]:			
				#start_time = time.time()

				# when an error occurs, to start after the last processed file.
				'''
				if check_point_found == False:
					if file == 'S0022286006004984.xml':
						check_point_found = True
					cnt += 1
					continue
				'''
				
				'''
				if check_point_found == False:
					if partition_start == cnt:
						check_point_found = True
					else:
						cnt += 1
					continue
				'''
				
				#if file != 'S1359836819305943.xml':	# debugging
				#	flag = True
				#	continue
				
				# list of parsing error files.
				if file in ep.error_list:
					cnt += 1
					continue

				print('>> file:', file)
				
				#if flag:
				#	input()
				#continue

				# Download objects.
				num_of_objs = ep.get_object(os.path.join(root, file))
				if num_of_objs > 0:
					print('>> num of objects:', num_of_objs)
				
				# Parse articles.
				ret = ep.parse(os.path.join(root, file))

				cnt += 1
				
				# when checking the number of articles with a body text.
				#if ep.parse(os.path.join(root, file)) == True:	# len(body_text) == 0 -> True
				#	cnt_no_body_article += 1
				
				'''
				content_type = ret[0]
				title = ret[1]
				#if content_type in ['BS', 'RW']:
				#	input("Press Enter to continue...")
				
				if content_type is None:
					tmp['none'] += 1
				else:
					tmp[content_type] += 1
				'''
				
				'''
				for k, v in tmp.items():
					print(k, v)
					
				json_file = file.replace('.xml', '.json')
				if title is None:
					if os.path.exists(os.path.join(dir, json_file)):
						os.remove(os.path.join(dir, json_file))
					else:
						print("The file does not exist")
				else:
					with open(os.path.join(dir, json_file), "r+") as f:
						data = json.load(f)
						data['title'] = title

						f.seek(0)        # <--- should reset file position to the beginning.
						json.dump(data, f)
						f.truncate()     # remove remaining part
				'''
				
				#print("--- %s seconds ---" % (time.time() - start_time))
				print(">> the number of processed files:", cnt)
				
				'''
				if partition_end == cnt:
					sys.exit()
				'''
				#input("Press Enter to continue...")

	#print(cnt_no_body_article)


def parse_Springer():
	sp = SpringerParser()
	#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/101038s41467019083472.xml")	# article
	#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/101038s4159801701840y.xml")	# article
	#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/10100797898113121441.xml")	# book chapter
	#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/101007978331962870733.xml")	# book chapter

	cnt_no_body_article = 0
	cnt = 0
	
	# when an error occurs, to start after the last processed file.
	check_point_found = False

	dir = sp.path
	for root, dirs, files in os.walk(dir):
		for file in files:
			if file.endswith(".xml") and os.path.isfile(os.path.join(root, file.replace('.xml', '.json'))) == False: # skip already parsed articles.
			#if file.endswith(".xml"):
	
				# when an error occurs, to start after the last processed file.
				'''
				if check_point_found == False:
					if file == '':
						check_point_found = True
					continue
				'''
				
				# list of parsing error files.
				if file in sp.error_list:
					continue

				#if file != '101007102011121.xml':	# debugging
				#	continue
				
				file_stat = os.stat(os.path.join(root, file))
				file_size = file_stat.st_size / (1024 * 1024) # file size in MegaBytes.

				if file_size >= 2:	# skip for large files (bigger than 2M)
					continue

				#start_time = time.time()
				print('>> file:', file)

				if sp.parse(os.path.join(root, file)) == True:	# len(body_text) == 0 -> True
					cnt_no_body_article += 1
				
				#print("--- %s seconds ---" % (time.time() - start_time))
				cnt += 1
				print(">> the number of processed files: ", cnt)
				
				#input("Press Enter to continue...")		

	#print(cnt_no_body_article)


def parse_PMC():
	pp = PMCParser()

	cnt_no_body_article = 0
	cnt = 0

	dir = pp.path
	for root, dirs, files in os.walk(dir):
		for file in files:
			if file.endswith(".nxml") and os.path.isfile(os.path.join(root, file.replace('.nxml', '.json'))) == False: # skip already parsed articles.
			#if file.endswith(".nxml"):
				# list of parsing error files. Since some of nxml article have the same name in PMC, so compare pmc id instead.
				pmc_id = root.rsplit('/', 1)[1]	# directory is the pmc id.
				#if file == "ADVS-2-0p.nxml":
				#if file == "sdata2018151.nxml":
				if pmc_id in pp.error_list:
					continue

				print('>> file:', os.path.join(root, file))

				#start_time = time.time()
				
				if pp.parse(os.path.join(root, file)) == True:	# len(body_text) == 0 -> True
					cnt_no_body_article += 1
				
				#print("--- %s seconds ---" % (time.time() - start_time))
				print(">> the number of processed files: ", cnt)
				
				#input("Press Enter to continue...")
				
				cnt += 1

	print(cnt_no_body_article)


def parse_RSC():
	rp = RSCParser()
	
	cnt_no_body_article = 0
	cnt = 0
	
	# when an error occurs, to start after the last processed file.
	check_point_found = False

	dir = rp.path

	for root, dirs, files in os.walk(dir):
		for file in files:
			# Ignore object html files (downloaded html files as supplementary object), and only parse article html files of which the directory has the same name. Skip already parsed articles.
			if file.endswith(".html") and file.rsplit('.', 1)[0] == root.rsplit('/', 1)[1] and os.path.isfile(os.path.join(root, file.replace('.html', '.json'))) == False: 
			#if file.endswith(".html") and file.rsplit('.', 1)[0] == root.rsplit('/', 1)[1]: 
	
				print('>> file:', file)
				
				#if file != "101039c2cs15332g.html":
				#	continue
				
				# when an error occurs, to start after the last processed file.
				'''
				if check_point_found == False:
					if file == '101039c8cc05176c.html':
						check_point_found = True
					
					cnt += 1
					print(">> the number of processed files: ", cnt)
					continue
				'''
					
				# list of parsing error files. Error files except for 'RSC - Page load error' files. e.g., 101039c1jm11358e.html
				if file in rp.error_list:
					continue
					
				#if file != '101039a900229d.html':	# debugging
				#	continue
				
				'''
				There are two options: 1) download objects of articles. 2) parse articles.
				'''
				# Download objects.
				rp.get_object(os.path.join(root, file))

				#start_time = time.time()
				
				# Parse articles.
				ret = rp.parse(os.path.join(root, file))
				
				# when checking the number of articles with a body text.
				#if rp.parse(os.path.join(root, file)) == True:	# len(body_text) == 0 -> True
				#	cnt_no_body_article += 1
				
				#print("--- %s seconds ---" % (time.time() - start_time))
				cnt += 1
				print(">> the number of processed files: ", cnt)
				
				#input("Press Enter to continue...")

	print(cnt_no_body_article)


def parse_AAAS():
	ap = AAASParser()
	
	cnt_no_body_article = 0
	cnt = 0
	
	# when an error occurs, to start after the last processed file.
	check_point_found = False

	dir = ap.path

	for root, dirs, files in os.walk(dir):
		for file in files:
			# Ignore object html files (downloaded html files as supplementary object), and only parse article html files of which the directory has the same name. Skip already parsed articles.
			if file.endswith(".html") and file.rsplit('.', 1)[0] == root.rsplit('/', 1)[1] and os.path.isfile(os.path.join(root, file.replace('.html', '.json'))) == False: 
			#if file.endswith(".html") and file.rsplit('.', 1)[0] == root.rsplit('/', 1)[1]: 

				print('>> file:', file)
				
				#if file != "101126science36764841284.html":	# debugging
				#	continue
				
				# when an error occurs, to start after the last processed file.
				'''
				if check_point_found == False:
					if file == '101126scienceaan1411.html':
						check_point_found = True
					
					cnt += 1
					print(">> the number of processed files: ", cnt)
					continue
				'''
				
				# list of parsing error files. Error files except for 'RSC - Page load error' files. e.g., 101039c1jm11358e.html
				if file in ['']:
					continue
				
				'''
				There are two options: 1) download objects of articles. 2) parse articles.
				'''
				# Download objects.
				#ap.get_object(os.path.join(root, file))

				#start_time = time.time()
				
				# Parse articles.
				ret = ap.parse(os.path.join(root, file))
				
				# when checking the number of articles with a body text.
				#if ap.parse(os.path.join(root, file)) == True:	# len(body_text) == 0 -> True
				#	cnt_no_body_article += 1
				
				#print("--- %s seconds ---" % (time.time() - start_time))
				cnt += 1
				print(">> the number of processed files: ", cnt)

	#print(cnt_no_body_article)


def parse_PDF():
	pdf_p = PDFParser()
	'''
	dir = "/home/gpark/corpus_web/tdm/archive/RSC"
	for filename in os.listdir(dir):
		if filename.endswith(".pdf"):
			print(filename)
			pdf_p.parse(os.path.join(dir, filename))
			
			input("Press Enter to continue...")
	'''

	cnt_article_w_keyword = 0
	terms = ['EXAFS', 'XANES', 'NEXAFS', 'pair distribution function']
	terms = [x.lower() for x in terms]	# lowercase

	num_of_files = 0

	#check_point_found = False

	dir = "/home/gpark/corpus_web/tdm/archive/IOP_JSON"


	# debugging
	file_doi = {}
	for file in os.listdir(dir):
		if file.endswith(".json"):
			with open(os.path.join(dir, file), "r") as read_file:
				data = json.load(read_file)
				
				body_text = data['body_text']
				
				found = False
				for sent in body_text:
					tokens = sent['sent'].split()
					tokens = [x.lower() for x in tokens]
					
					if any(elem in tokens for elem in terms[:3]):
						found = True
						break

				if found is True:
					pdf_file = file.replace('.json', '.pdf')
					file_doi[pdf_file] = data['uid']

	with open("iop_filtered_list.txt", 'a') as out_file:
		for file, doi in file_doi.items():
			out_file.write(file + ' -> https://doi.org/' + doi + '\n')
						
	sys.exit()
	# debugging
				

	for root, dirs, files in os.walk(dir):
		dirs.sort(reverse=True)	# it will traverse the subdirectories in reverse lexicographic order of their names.
		for file in files:
			if file.endswith(".pdf"):
				
				''' when an error occurs, to start after the last processed file.
				if check_point_found == False:
					if file == 'epl_38_6_453.pdf':
						check_point_found = True
						continue
					else:
						continue
				'''
				
				iop_meta_file = os.path.join(root, '.article')
				
				if os.path.exists(iop_meta_file) == False:
					continue
					
				pdf_p.parse(os.path.join(root, file), terms, iop_meta_file)
				
				num_of_files += 1
				
				print('>> file: ', os.path.join(root, file) , ' / num_of_files: ', num_of_files)
					
				#input("Press Enter to continue...")
				
				#if file in ['jpmater_1_1_01LT02.pdf', 'jpmater_1_1_015010.pdf', 'jpmater_1_1_015006.pdf', 'mfm_1_1_015005.pdf']:
				#if file in ['jpco_3_1_015002.pdf']:
				#	input("Press Enter to continue...")
				
				
				#if pdf_p.parse(os.path.join(root, file), terms) == True:	# len(body_text) == 0 -> True
				#	cnt_article_w_keyword += 1

	print(cnt_article_w_keyword)

	#e.parse_XML_Elsevier("../archive/Elsevier/articles/S0022328X0101453X.xml")
	#e.parse_XML_Springer("../archive/Springer/101007s007750181608y.xml")
	#e.parse_XML_PMC("../archive/PMC/PMC6281269/pone.0208355.nxml")

	#response = requests.get('https://api.crossref.org/members?query=IUCr').json()
	#print(json.dumps(response, indent=4, sort_keys=True))

	#e = Parser()
	#e.parse_PDF_by_Tesseract('wiley_test.pdf')
	#e.parse_PDF_by_PDFMiner('wiley_test.pdf')
	#e.parse_PDF_by_others('wiley_test.pdf')
	#e.parse_PDF_by_PyMuPDF('RSC_101039b001065k.pdf')


def main():
	start_time = time.time()

	#update_uid_list()	# TODO: find a way to get uids for downloaded articles that can't be parsed into JSON files (e.g., some of Elsevier articles).

	parse_Elsevier()
	parse_Springer()
	parse_RSC()
	parse_AAAS()
	parse_PMC()

	#parse_PDF()
	
	print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == "__main__":
	main()

