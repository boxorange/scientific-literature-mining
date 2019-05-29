import os
import abc
from lxml import etree
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class BaseParser:
	parser = etree.XMLParser(ns_clean=True)

	@abc.abstractmethod
	def parse(self, file):
		""" Parse articles """
