import os
import abc
from lxml import etree
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class BaseParser:

	xml_parser = etree.XMLParser(ns_clean=True)
	html_parser = etree.HTMLParser()
	
	
	def __init__(self, publisher):
		# get key, destination path, uid list, and error list.
		with open('../api_key_and_archive_info.txt', 'r') as f:
			self.error_list = set()
			for line in f.readlines():
				if line.startswith('API_key'):
					key = line.split('=', 1)[0].split('/')[1].strip()
					val = line.split('=', 1)[1].strip()
					if key == publisher:
						self.api_key = val
				elif line.startswith('Path'):
					key = line.split('=', 1)[0].split('/')[1].strip()
					val = line.split('=', 1)[1].strip()
					if key == publisher:
						self.path = val
				elif line.startswith('UID_list'):
					self.uid_list = line.split('=', 1)[1].strip() # unique identifier for articles (e.g., DOI). It's to avoid duplicate downloads for the same article from different sources.
				elif line.startswith('Error_list'):
					key = line.split('=', 1)[0].split('/')[1].strip()
					val = line.split('=', 1)[1].strip()
					if key == publisher:
						self.error_list.update([x.strip() for x in val.split(',')])


	@abc.abstractmethod
	def parse(self, file):
		""" Parse articles """
