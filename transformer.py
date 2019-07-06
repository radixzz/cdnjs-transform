import os
import ijson
import sys
from datetime import datetime
from utils import read_json
from utils import write_json
from utils import read_file
from utils import write_file
from utils import download_file
from utils import init_log
from utils import log_info
from utils import log_error
from utils import mkdir_p

init_log('transformer.log')

class Transformer:
  def __init__(self, config_path):
    config = read_json(config_path)
    self.max_versions_per_lib = config['max_versions_per_lib']
    self.lib_url_template = config['lib_url_template']
    self.cache_etag_file = config['cache_etag_file']
    self.downloads_path = config['downloads_path']
    self.versions_file = config['versions_file']
    self.builds_path = config['builds_path']
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
    log_info('Processing done.')
    return output

  def get_next_build_version(self):
    version = 0
    if (os.path.isfile(self.versions_file)):
      version = int(read_file(self.versions_file)) + 1
    return version

  def write_build_version(self, version):
    write_file(self.versions_file, version)

  def write_output(self, struct, version):
    self.write_build_version(str(version))
    name = "{0}/libraries_{1}.json".format(self.builds_path, version)
    write_json(name, struct)
    size = "{:.2f} KB".format(os.path.getsize(name) / 1024)
    log_info('New build created at: {0} ({1})'.format(name, size))

  def init_paths(self):
    mkdir_p(self.builds_path)
    mkdir_p(self.downloads_path)

  def get_last_download_etag(self):
    if os.path.exists(self.cache_etag_file):
      return read_file(self.cache_etag_file)
    else:
      return ''

  def set_last_download_etag(self, etag):
    if type(etag) == str:
      write_file(self.cache_etag_file, etag)

  def start(self):
    self.init_paths()
    # Download cdnjs API JSON response to file
    download_path = '{0}/raw_libraries.json'.format(self.downloads_path)
    last_etag = self.get_last_download_etag()
    new_etag = download_file(self.cdnjs_api, download_path, last_etag)
    self.set_last_download_etag(new_etag)
    # Transform the file into new JSON struct
    struct = self.transform_cdnjs_file(download_path)
    version = self.get_next_build_version()
    self.write_output(struct, version)

if __name__ == '__main__':
  log_info('Creating Transformer')
  transformer = Transformer('config.json')
  transformer.start()
