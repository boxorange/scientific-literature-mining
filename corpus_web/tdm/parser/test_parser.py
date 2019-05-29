import os
import sys
from lxml import etree
from ftplib import FTP
import json
import requests

from elsevier_parser import ElsevierParser
from springer_parser import SpringerParser
from pmc_parser import PMCParser
from pdf_parser import PDFParser

import time
start_time = time.time()


##################################################################################################
""" Update UID list """

ep = ElsevierParser()
sp = SpringerParser()
pp = PMCParser()
pdf_p = PDFParser()

ep.update_uid_list()
sp.update_uid_list()
pp.update_uid_list()
pdf_p.update_uid_list('APS')
pdf_p.update_uid_list('ACS')
pdf_p.update_uid_list('Wiley')
pdf_p.update_uid_list('IUCr')
pdf_p.update_uid_list('RSC')

sys.exit()

##################################################################################################
""" Elsevier """

ep = ElsevierParser()

#cnt_no_body_article = 0
cnt = 0

dir = "/home/gpark/corpus_web/tdm/archive/Elsevier/articles"
file_list = os.listdir(dir)

#chk_idx = file_list.index("S037015731830036X.xml")	# to re-start after the last downloaded article.
#file_list = file_list[chk_idx + 1:]

#file_list = ['/home/gpark/corpus_web/tdm/archive/Elsevier/articles/S003960280700461X.xml']

from collections import defaultdict
tmp = defaultdict(int) # default value of int is 0

for filename in file_list:
	if filename.endswith(".xml"):
		
		#start_time = time.time()
		print('>> filename: ', filename)
		
		ret = ep.parse(os.path.join(dir, filename))
		
		content_type = ret[0]
		title = ret[1]
		#if content_type in ['BS', 'RW']:
		#	input("Press Enter to continue...")
		
		if content_type is None:
			tmp['none'] += 1
		else:
			tmp[content_type] += 1

		
		for k, v in tmp.items():
			print(k, v)
			
		json_file = filename.replace('.xml', '.json')
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


		
		#if ep.parse(os.path.join(dir, filename)) == True:	# len(body_text) == 0 -> True
		#	cnt_no_body_article += 1
		
		#print("--- %s seconds ---" % (time.time() - start_time))
		cnt += 1
		print(">> the number of processed files: ", cnt)
		
		#num_of_objs = ep.get_objects(os.path.join(dir, filename))
		#print(filename, ': ', num_of_objs)
		
		#input("Press Enter to continue...")

#print(cnt_no_body_article)

sys.exit()


##################################################################################################
""" Springer """

sp = SpringerParser()
#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/101038s41467019083472.xml")	# article
#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/101038s4159801701840y.xml")	# article
#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/10100797898113121441.xml")	# book chapter
#sp.parse("/home/gpark/corpus_web/tdm/archive/Springer/articles/101007978331962870733.xml")	# book chapter

cnt_no_body_article = 0
cnt = 0

dir = "/home/gpark/corpus_web/tdm/archive/Springer/articles"
for filename in os.listdir(dir):
	if filename.endswith(".xml"):
	
		#start_time = time.time()
		print('>> filename: ', filename)
		
		if sp.parse(os.path.join(dir, filename)) == True:	# len(body_text) == 0 -> True
			cnt_no_body_article += 1
		
		#print("--- %s seconds ---" % (time.time() - start_time))
		cnt += 1
		print(">> the number of processed files: ", cnt)
		#input("Press Enter to continue...")		

print(cnt_no_body_article)

sys.exit()


##################################################################################################
""" PMC """

pp = PMCParser()
#pp.parse("/home/gpark/corpus_web/tdm/archive/PMC/PMC6199725/40168_2018_Article_574.nxml")
#pp.parse("/home/gpark/corpus_web/tdm/archive/PMC/PMC6337889/s-26-00124.nxml")
#pp.parse("/home/gpark/corpus_web/tdm/archive/PMC/PMC5413562/fphys-08-00267.nxml")
#pp.parse("/home/gpark/corpus_web/tdm/archive/PMC/PMC6296299/SC-009-C8SC03549K.nxml")
#pp.parse("/home/gpark/corpus_web/tdm/archive/PMC/PMC5432002/41598_2017_Article_1840.nxml")

cnt_no_body_article = 0
cnt = 0

dir = "/home/gpark/corpus_web/tdm/archive/PMC/"
for root, dirs, files in os.walk(dir):
	for file in files:
		if file.endswith(".nxml"):
			print('>> file: ', file)
			
			#start_time = time.time()
			
			if pp.parse(os.path.join(root, file)) == True:	# len(body_text) == 0 -> True
				cnt_no_body_article += 1
				
			#print("--- %s seconds ---" % (time.time() - start_time))
			cnt += 1
			print(">> the number of processed files: ", cnt)

print(cnt_no_body_article)

sys.exit()


##################################################################################################
""" PDF (under development) """ 
#pdf_p = PDFParser()

dir = "/home/gpark/corpus_web/tdm/archive/RSC"
for filename in os.listdir(dir):
	if filename.endswith(".pdf"):
		print(filename)
		pdf_p.parse(os.path.join(dir, filename))
		
		input("Press Enter to continue...")


cnt_article_w_keyword = 0
terms = ['EXAFS', 'XANES', 'NEXAFS', 'pair distribution function']
terms = [x.lower() for x in terms]	# lowercase

dir = "/home/gpark/corpus_web/tdm/archive/IOP"
for root, dirs, files in os.walk(dir):
	for file in files:
		if file.endswith(".pdf"):
			print('>> file: ', file)
			if pdf_p.parse(os.path.join(root, file), terms) == True:	# len(body_text) == 0 -> True
				cnt_article_w_keyword += 1

print(cnt_article_w_keyword)


print("--- %s seconds ---" % (time.time() - start_time))
