import abc
import json
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class BaseDownloader:
	
	archive_path = "/home/gpark/corpus_web/tdm/archive/" # archive folder
	uid_list = "/home/gpark/corpus_web/tdm/archive/uid_list.txt" # unique identifier for articles (e.g., DOI). It's to avoid duplicate downloads for the same article from different sources.

	existing_uids = set([line.strip() for line in open(uid_list)])
	to_be_saved_uids = set()	# update the uid_list file at a time to reduce File I/O


	def check_uids(self, new_uids):
		ret_uids = new_uids.copy()  # ret_uids is used to compare for debugging.
		ret_uids.difference_update(BaseDownloader.existing_uids)   # remove any duplicates

		if len(ret_uids) != len(new_uids):
			for duplicate_uid in new_uids.intersection(BaseDownloader.existing_uids):
				logger.debug(f'>> Existing id: {duplicate_uid}')
		
		BaseDownloader.existing_uids.update(ret_uids)
		BaseDownloader.to_be_saved_uids.update(ret_uids)

		return ret_uids


	def save_uids(self):
		with open(BaseDownloader.uid_list, 'a') as file:
			for uid in BaseDownloader.to_be_saved_uids:
				file.write("%s\n" % uid)
		
		BaseDownloader.to_be_saved_uids.clear()


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
