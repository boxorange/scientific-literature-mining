import os
import requests
import time
import json
from base_parser import BaseParser
import logging

logger = logging.getLogger(__name__)

from chemdataextractor.doc import Document, Title, Heading, Paragraph, Caption, Citation, Footnote, Text, Sentence

""" PyMuPDF """     
import sys, fitz # import the bindings

""" Tesseract """     
from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import (
	PDFInfoNotInstalledError,
	PDFPageCountError,
	PDFSyntaxError
)

#try:
#    from PIL import Image
#except ImportError:
#    import Image
import pytesseract
#import cv2

""" PDFMiner """     
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO

""" XPDF_python """        
from xpdf_python import to_text


class PDFParser:
	"""
	Note:
	- Best options for now.
		- PyMuPDF
		- Tesseract
		- PDFMiner

	- PyMuPDF and Tesseract seems to work the best followed by PDFMiner. Tesseract is slow.

	Other options
	- PyPDF2
		: PDFMiner performs better than PyPDF2.
		: Can't parse the followings.
		- APS_101103physrevb55726.pdf
	- slate (based on PDFMiner) - doesn't work
	- textract (based on Tesseract) - can't install
	- pyOCR (based on Tesseract)
	- xpdf_python (based on XPDF reader) (only text)
	- Poppler (based on XPDF reader) 
	- pdftotext (based on Poppler) https://github.com/jalan/pdftotext
	- PDFTextStream (written in Java)

	References:
	- https://www.blog.pythonlibrary.org/2018/05/03/exporting-data-from-pdfs-with-python/
	"""

	#def __init__(self):
	
	
	def update_uid_list(self, publisher):
		doi_list = []

		dir = "/home/gpark/corpus_web/tdm/archive/" + publisher
		for file in os.listdir(dir):
			if file.endswith(".json"):
				with open(os.path.join(dir, file), "r") as read_file:
					data = json.load(read_file)

				doi_list.append(data['uid'])

		with open("/home/gpark/corpus_web/tdm/archive/uid_list.txt", 'a') as file:
			for doi in doi_list:
				file.write(doi + '\n')
				
	
	def parse(self, pdf_file, keywords):
		return self.parse_PDF_by_PyMuPDF(pdf_file, keywords)	# The current adoption is PyMuPDF


	def recoverpix(self, doc, item):
		x = item[0]  # xref of PDF image
		s = item[1]  # xref of its /SMask
		pix1 = fitz.Pixmap(doc, x)
		if s == 0:                    # has no /SMask
			return pix1               # no special handling
		pix2 = fitz.Pixmap(doc, s)    # create pixmap of /SMask entry
		# check that we are safe
		if not (pix1.irect == pix2.irect and \
				pix1.alpha == pix2.alpha == 0 and \
				pix2.n == 1):
			print("pix1", pix1, "pix2", pix2)
			raise ValueError("unexpected situation")
		pix = fitz.Pixmap(pix1)       # copy of pix1, alpha channel added
		pix.setAlpha(pix2.samples)    # treat pix2.samples as alpha value
		pix1 = pix2 = None            # free temp pixmaps
		return pix


	def parse_PDF_by_PyMuPDF(self, pdf_file, keywords):
		"""
		https://github.com/rk700/PyMuPDF
		https://github.com/JorjMcKie/PyMuPDF-Utilities

		Get text - code from PyMuPDF.pdf document
		Get images - code from https://github.com/rk700/PyMuPDF/blob/master/demo/extract-img1.py

		PDF2TextJS.py - https://github.com/rk700/PyMuPDF/blob/master/examples/PDF2TextJS.py
		-> it extracts texts in a natural reading order; however, it combines wrong blocks of text together. - 1/29/2019
		"""

		start_t = time.clock()
		
		doc = fitz.open(pdf_file) # open document

		out_dir = pdf_file.rsplit('.', 1)[0]
		out_txt = out_dir.rsplit('/', 1)[-1] + '.txt'
		
		'''
		if not os.path.exists(out_dir):
			os.mkdir(out_dir)
		'''	
		
		#out = open(out_dir + '/' + out_txt, "wb") # open text output

		# Get images
		img_count = 0                           # counts extracted images
		xref_list = []                          # records images already extracted
		lenXREF = doc._getXrefLength()          # only used for information, return length of xref table (number of objects in file)

		#img_dir = "images" # found images are stored here
		#if not os.path.exists(img_dir):
		#	os.mkdir(img_dir)

		# display some file info
		print("file: %s, pages: %s, objects: %s" % (pdf_file, len(doc), lenXREF-1))
		
		text_sents = []

		for i, page in enumerate(doc): # iterate the document pages
			#text = page.getText().encode("utf-8") # get plain text (is in UTF-8)
			text = page.getText()
			#out.write(text) # write text of page
			#out.write(b"\n-----\n") # write page delimiter
			
			text = text.replace("\n", " ")
			text_sents.extend(Text(text).sentences)

			# Get images
			'''
			img_list = doc.getPageImageList(i)
			for img in img_list: # img -> [xref, smask, width, height, bpc, colorspace, alt. colorspace, name, filter]
				if img[0] in xref_list:         # this image has been processed
					continue 
				xref_list.append(img[0])        # take note of the xref
				pix = self.recoverpix(doc, img[:2]) # make pixmap from image
				if pix.n - pix.alpha < 4:      # can be saved as PNG
					pass
				else:                          # must convert CMYK first
					pix0 = fitz.Pixmap(fitz.csRGB, pix)
					pix = pix0
				
				img_name = os.path.join(out_dir, "p%i-%s.png" % (i, img[7]))
				pix.writePNG(img_name)
				img_count += 1
				pix = None                     # free Pixmap resources
			'''
			
		#out.close()

		i = 1
		for sent in text_sents:
			tokens = sent.raw_tokens
			tokens = [x.lower() for x in tokens]	# lowercase
			
			if any(elem in tokens for elem in keywords[:3]):
				print(sent)
				return True
			
			if sent.text.lower().find('pair distribution function') != -1 or sent.text.lower().find('pair distribution functions') != -1:
				print(sent)
				return True
			
			#print(f'>> sent {i}: {sent.raw_tokens}')
			#input("Press Enter to continue...")
			i += 1
		
		return False
		
		end_t = time.clock()
		print("run time", round(end_t - start_t, 2))
		print("extracted images", img_count)



	def parse_PDF_by_Tesseract(self, pdf_file):
		"""
		To use Tesseract, PDF first needs to be converted into image files.
		'pdf2image' is based on 'Poppler' package.

		list of languages: https://github.com/tesseract-ocr/langdata
		
		- Adding a parameter <lang='eng'> doesn't improve the performance (speed). It's because default lang is English.
		- dpi=600 takes more processing time than dpi=300, but no performance improvement was found.

		E.g., pytesseract.image_to_string(image, lang='eng', boxes=False, config='--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789')

		Ref
		- https://www.pyimagesearch.com/2018/09/17/opencv-ocr-and-text-recognition-with-tesseract/
		"""

		images = convert_from_path(pdf_file, dpi=300, transparent=True, fmt='tiff', thread_count=3)
		# TODO: two give the same result, but test it with further examples. (when using encode() change 'w' to 'wb')
		#text = '\n'.join(pytesseract.image_to_string(img) for img in images)
		#text = '\n'.join(pytesseract.image_to_string(img) for img in images).encode('utf-8')

		#with open('tesseract_test.txt', 'w') as file:
		#    file.write(text)

		hocr = pytesseract.image_to_pdf_or_hocr(images[5], extension='hocr')
		with open('tesseract_test.html', 'wb') as file:
			file.write(hocr)

		#print(pytesseract.image_to_boxes(images[5]))

		#i = 0
		#for img in images:
		#    img.save('test' + '_' + str(i) + '.jpeg')
		#    i += 1


		# Simple image to string
		#print(pytesseract.image_to_string(Image.open('test.tif')))
		#print(pytesseract.image_to_data(Image.open('test.tif')))
		#print(pytesseract.image_to_string(images[0]))

		#img = cv2.imread(r'test.tif')
		#print(pytesseract.image_to_string(img))
		# OR explicit beforehand converting
		#print(pytesseract.image_to_string(Image.fromarray(img)))
		#print(pytesseract.get_tesseract_version())


	def parse_PDF_by_PDFMiner(self, pdf_file):
		"""
		https://stackoverflow.com/questions/26494211/extracting-text-from-a-pdf-file-using-pdfminer-in-python
		https://www.blog.pythonlibrary.org/2018/05/03/exporting-data-from-pdfs-with-python/
		"""

		rsrcmgr = PDFResourceManager()
		retstr = StringIO()
		codec = 'utf-8'
		laparams = LAParams()
		device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
		fp = open(pdf_file, 'rb')
		interpreter = PDFPageInterpreter(rsrcmgr, device)
		password = ""
		maxpages = 0
		caching = True
		pagenos=set()

		for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
			interpreter.process_page(page)

		text = retstr.getvalue()

		fp.close()
		device.close()
		retstr.close()

		with open('pdfminer_test.txt', 'w') as file:
			file.write(text)


	def parse_PDF_by_others(self, pdf_file):
				
		'''
		from PyPDF2 import PdfFileWriter, PdfFileReader

		#test_pdf = PdfFileReader(open("../archive/APS/APS_101103physrevb55726.pdf", "rb"))
		test_pdf = PdfFileReader(open("../archive/Wiley/Wiley_101002adfm201000095.pdf", "rb"))

		# print how many pages test_pdf has:
		print("document1.pdf has %d pages." % test_pdf.getNumPages())

		for page in test_pdf.pages:
			print(page.extractText())
			print(gilchan)
			#page.extractText()
		'''

		""" XPDF_python """
		#pdf_location = '../archive/Wiley/Wiley_101002adfm201000095.pdf'
		text, number_of_pages = to_text(pdf_file)
		with open('xpdf_python_test.txt', 'w') as file:
			file.write(text)
		
		image_locs = extract_images(pdf_file)

		for ele in image_locs:
			print(ele)


		'''
		import slate
		import pdfminer

		def extract_text_from_pdf(pdf_path):
			with open(pdf_path) as fh:
				document = slate.PDF(fh, password='', just_text=1)

			for page in document:
				print(page)

		extract_text_from_pdf("../archive/Wiley/Wiley_101002adfm201000095.pdf")
		'''
