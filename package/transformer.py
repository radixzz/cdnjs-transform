import os
import ijson
import sys
import re
from distutils.version import LooseVersion
from box import Box
from pathlib import Path
from datetime import datetime
import logging
import coloredlogs

from . import util

logger = logging.getLogger('transformer')

def abs_path(path):
  return (Path(__file__).parent / path).resolve()

def atomize_version(version):
  normalized = '.'.join(re.findall(r'\d+', version))
  return LooseVersion(normalized) if normalized else LooseVersion('0.0')

class Transformer:
  def __init__(self, config):
    self.config = Box(config)
    self.items = []

  def add_item(self, fields):
    self.items += fields
    count = len(self.items)
    sys.stdout.write("\rProcessing Libraries: {0} done".format(count))
    sys.stdout.flush()

  def sort_versions(self, arr, latest_version):
    result = sorted(arr, key=atomize_version, reverse=True)
    result.insert(0, latest_version)
    return list(dict.fromkeys(result))

  def transform_cdnjs_file(self, path):
    name = ''
    desc = ''
    filename = ''
    versions = []
    keywords = []
    latest_version = ''
    with open(path, 'r', encoding="utf-8") as file:
      stream = ijson.parse(file)
      for prefix, event, value in stream:
        if (prefix, event) == ('results.item.name', 'string'):
          # if new entry found, save pending entry
          if name:
            versions = self.sort_versions(versions, latest_version)
            v_str = ','.join(versions[:self.config.max_versions_per_lib])
            k_str = ','.join(keywords[:10])
            self.add_item([name, desc, filename, v_str, k_str])
            latest_version = ''
            desc = ''
            filename = ''
            name = ''
          name = value
          versions = []
          keywords = []
        if (prefix, event) == ('results.item.version', 'string'):
          latest_version = value
        if (prefix, event) == ('results.item.keywords.item', 'string'):
          keywords.append(value)
        if (prefix, event) == ('results.item.assets.item.version', 'string'):
          versions.append(value)
        if (prefix, event) == ('results.item.description', 'string'):
          desc = util.trunc_string(value, 200)
        if (prefix, event) == ('results.item.filename', 'string'):
          filename = value
      sys.stdout.write("\n")
    logger.info('Transform done.')

  def get_libs_struct(self):
    return {
      'created_at': str(datetime.today()),
      'url_template': self.config.lib_url_template,
      'items': self.items,
    }

  def get_build_version(self):
    version = 0
    if (os.path.isfile(self.config.versions_path)):
      version = int(util.read_file(self.config.versions_path))
    return version

  def write_build_version(self, version):
    util.write_file(self.config.versions_path, version)

  def write_output(self, struct):
    name = self.get_current_build_path()
    util.write_json(name, struct)
    size = "{:.2f} KB".format(os.path.getsize(name) / 1024)
    logger.info('New build created at: {0} ({1})'.format(name, size))

  def init_paths(self):
    util.mkdir_p(self.config.builds_path)
    util.mkdir_p(self.config.downloads_path)

  def get_current_build_path(self):
    version = self.get_build_version()
    return "{0}/libraries_{1}.json".format(self.config.builds_path, version)

  def get_last_download_etag(self):
    if os.path.exists(self.config.cache_etag_path):
      return util.read_file(self.config.cache_etag_path)
    else:
      return ''

  def set_last_download_etag(self, etag):
    if type(etag) == str:
      util.write_file(self.config.cache_etag_path, etag)

  def start(self):
    self.init_paths()
    # Download cdnjs API JSON response to file
    logger.info('Trying to download: %s' % self.config.cdnjs_api)
    download_path = '{0}/raw_libraries.json'.format(self.config.downloads_path)
    last_etag = self.get_last_download_etag()
    logger.info('Destination path: %s' % download_path)
    new_etag = util.download_file(self.config.cdnjs_api, download_path, last_etag)
    if new_etag is None:
      logger.info('File already in cache')
    self.set_last_download_etag(new_etag)
    # Transform the file into new JSON struct
    self.transform_cdnjs_file(download_path)
    struct = self.get_libs_struct()
    version = self.get_build_version() + 1
    self.write_build_version(str(version))
    self.write_output(struct)
