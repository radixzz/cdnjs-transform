import os
import ijson
import sys
from pathlib import Path
from datetime import datetime
import logging
import coloredlogs

from .util import read_json
from .util import write_json
from .util import read_file
from .util import write_file
from .util import download_file
from .util import mkdir_p

logger = logging.getLogger('transformer')

def abs_path(path):
  return (Path(__file__).parent / path).resolve()

class Transformer:
  def __init__(self, config_path):
    config = read_json(config_path)
    self.max_versions_per_lib = config['max_versions_per_lib']
    self.lib_url_template = config['lib_url_template']
    self.cache_etag_path = abs_path(config['cache_etag_path'])
    self.downloads_path = abs_path(config['downloads_path'])
    self.versions_path = abs_path(config['versions_path'])
    self.builds_path = abs_path(config['builds_path'])
    self.cdnjs_api = config['cdnjs_api']


  def transform_cdnjs_file(self, path):
    output = {
      'created_at': str(datetime.today()),
      'url_template': self.lib_url_template,
      'items': [],
    }
    current = None
    count = 0
    with open(path, 'r', encoding="utf-8") as file:
      stream = ijson.parse(file)
      for prefix, event, value in stream:
        if (prefix, event) == ('results.item.name', 'string'):
          if current != None:
            output['items'].append(current)
            count += 1
            sys.stdout.write("\rProcessing Libraries: {0} done".format(count))
            sys.stdout.flush()
          current = {
            'n': value,
            'd': '',
            'f': '',
            'v': [],
          }
        if (prefix, event) == ('results.item.assets.item.version', 'string'):
          if (len(current['v']) < self.max_versions_per_lib):
            current['v'].append(value)
        if (prefix, event) == ('results.item.description', 'string'):
          current['d'] = value
        if (prefix, event) == ('results.item.filename', 'string'):
          current['f'] = value
      sys.stdout.write("\n")
    logger.info('Transform done.')
    return output

  def get_build_version(self):
    version = 0
    if (os.path.isfile(self.versions_path)):
      version = int(read_file(self.versions_path))
    return version

  def write_build_version(self, version):
    write_file(self.versions_path, version)

  def write_output(self, struct):
    name =self.get_current_build_path()
    write_json(name, struct)
    size = "{:.2f} KB".format(os.path.getsize(name) / 1024)
    logger.info('New build created at: {0} ({1})'.format(name, size))

  def init_paths(self):
    mkdir_p(self.builds_path)
    mkdir_p(self.downloads_path)

  def get_current_build_path(self):
    version = self.get_build_version()
    return "{0}/libraries_{1}.json".format(self.builds_path, version)

  def get_last_download_etag(self):
    if os.path.exists(self.cache_etag_path):
      return read_file(self.cache_etag_path)
    else:
      return ''

  def set_last_download_etag(self, etag):
    if type(etag) == str:
      write_file(self.cache_etag_path, etag)

  def start(self):
    self.init_paths()
    # Download cdnjs API JSON response to file
    logger.info('Trying to download: %s' % self.cdnjs_api)
    download_path = '{0}/raw_libraries.json'.format(self.downloads_path)
    last_etag = self.get_last_download_etag()
    logger.info('Destination path: %s' % download_path)
    new_etag = download_file(self.cdnjs_api, download_path, last_etag)
    if new_etag is None:
      logger.info('File already in cache')
    self.set_last_download_etag(new_etag)
    # Transform the file into new JSON struct
    struct = self.transform_cdnjs_file(download_path)
    version = self.get_build_version() + 1
    self.write_build_version(str(version))
    self.write_output(struct)

if __name__ == '__main__':
  coloredlogs.install(level='INFO', logger=logger)
  logging.basicConfig(filename=abs_path('transformer.log'))
  logger.info('Creating Transformer')
  transformer = Transformer(abs_path('config.json'))
  transformer.start()
