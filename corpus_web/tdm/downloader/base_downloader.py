import abc
import json
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class BaseDownloader:
	
	
	def __init__(self, publisher):
		# get key, destination path, uid list, and error list.
		with open('/home/gpark/corpus_web/tdm/api_key_and_archive_info.txt', 'r') as f:
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
		
		self.existing_uids = set([line.strip().lower() for line in open(self.uid_list)])
		#to_be_saved_uids = set()	# update the uid_list file at a time to reduce File I/O
	

	def remove_duplicates(self, new_uids):
		ret_uids = new_uids.copy()  # keep the original list for debugging.

		ret_uids = set([x.lower() for x in ret_uids])
		ret_uids.difference_update(self.existing_uids)   # remove any duplicates
		
		#self.existing_uids.update(ret_uids)
		#self.to_be_saved_uids.update(ret_uids)
		
		# debugging
		if len(ret_uids) != len(new_uids):	
			tmp = new_uids.copy()
			tmp = set([x.lower() for x in tmp])
			for duplicate_uid in tmp.intersection(self.existing_uids):
				logger.debug(f'>> Existing id: {duplicate_uid}')

		return ret_uids
	
	
	def update_uid(self, uid):
		with open(self.uid_list, 'a') as file:
			file.write("%s\n" % uid)
		
		self.existing_uids.add(uid)

	''' deprecated - changed to save uids right after write_to_file() since errors frequently occur between articles. - 02-12-2020
	def save_uid(self):
		with open(self.uid_list, 'a') as file:
			for uid in self.to_be_saved_uids:
				file.write("%s\n" % uid)
		
		self.to_be_saved_uids.clear()
	'''

	def write_to_file(self, response, destination, filename, extension):
		with open(destination + filename + extension, 'wb') as file:
			for chunk in response.iter_content(2048):
				file.write(chunk)


	def display_error_msg(self, response, member=None):
		error_msg = (f'\n>> Member: {member}\n' if member is not None else '\n') + \
					 f'>> ERROR Code: {response.status_code}\n' + \
					 f'>> URL: {response.url}\n' + \
					 f'>> Resp txt: {response.text}'
		logger.error(error_msg)


	@abc.abstractmethod
	def retrieve_articles(self, query):
		""" Find and download articles using the given query """
