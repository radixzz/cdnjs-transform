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

  def sort_versions(self, arr, latest_version):
    result = sorted(arr, key=atomize_version, reverse=True)
    result.insert(0, latest_version)
    return list(dict.fromkeys(result))

  def add_item(self, fields):
    # extract fields to vars (index belongs to fields match)
    library_name    = fields[0][0]
    latest_version  = fields[1][0]
    filename        = fields[2][0]
    description     = fields[3][0]
    keywords        = fields[4]
    versions        = fields[5]
    # optimize contents
    trunc_description = util.trunc_string(description, 200)
    sorted_versions = self.sort_versions(versions, latest_version)
    comma_versions = ','.join(sorted_versions[:self.config.max_versions_per_lib])
    comma_keywords = ','.join(keywords[:10])
    # append stride
    self.items += [
      library_name,
      filename,
      trunc_description,
      comma_keywords,
      comma_versions
    ]
    # report completed libraries (stride = 5)
    count = round(len(self.items) / 5)
    sys.stdout.write("\rProcessing Libraries: {0} done".format(count))
    sys.stdout.flush()

  def transform_cdnjs_file(self, path):
    current = {}
    fields_match = [
      ('results.item.name', 'string'),
      ('results.item.version', 'string'),
      ('results.item.filename', 'string'),
      ('results.item.description', 'string'),
      ('results.item.keywords.item', 'string'),
      ('results.item.assets.item.version', 'string')
    ]
    with open(path, 'r', encoding="utf-8") as file:
      stream = ijson.parse(file)
      for prefix, event, value in stream:
        for idx, field in enumerate(fields_match):
          if (prefix, event) == field:
            # if current match is the name and current has all the fields. Commit library
            if (prefix, event) == fields_match[0] and len(current) == len(fields_match):
              self.add_item(current)
              current = {}
            if idx not in current: current[idx] = []
            current[idx].append(value)
      sys.stdout.write("\n")
    logger.info('Transform done.')

  def get_libs_struct(self):
    return {
      'created_at': str(datetime.today()),
      'url_template': self.config.lib_url_template,
      'stride_format': ['name', 'filename', 'description', 'keywords', 'versions'],
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
