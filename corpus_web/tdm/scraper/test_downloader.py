import os
import sys
import time
import json
import requests

from pmc_downloader import PMCDownloader
from elsevier_downloader import ElsevierDownloader
from springer_downloader import SpringerDownloader
from aps_downloader import APSDownloader
from crossref_downloader import CrossrefDownloader


start_time = time.time()

# terms = ['EXAFS', 'XANES', 'NEXAFS', 'pair distribution function']
terms = ['EXAFS', 'XANES', 'NEXAFS']	# phrase and exact searching is not working in Crossref.

# create a request query
# https://dev.elsevier.com/tips/ScienceDirectSearchTips.htm
query = ''
for i in range(0, len(terms)): 
	if ' ' in terms[i]:
		query += f'"{terms[i]}"'
	else:
		query += terms[i]
		
	if i != (len(terms)-1):
		query += ' OR '	# space works the same as +

query = query.strip()


##################################################################################################
""" PMC """
pd = PMCDownloader()
pd.retrieve_articles(query)


##################################################################################################
""" Elsevier """
ed = ElsevierDownloader()
ed.retrieve_articles(query)

##################################################################################################
""" Springer """
sd = SpringerDownloader()
sd.retrieve_articles(query)

##################################################################################################
""" Crossref """
cd = CrossrefDownloader()
cd.retrieve_articles(query)

print("--- %s seconds ---" % (time.time() - start_time))


