import os
import ijson
import sys
from datetime import datetime
from utils import read_json
from utils import write_json
from utils import read_file
from utils import write_file
from utils import get_dir_list
from utils import download_file
from utils import read_json_stream

class Indexer:
  def __init__(self, config_path):
    config = read_json(config_path)
    self.lib_path = config['lib_path']
    self.lib_url_template = config['lib_url_template']
    self.output_path = config['output_path']
    self.versions_file = config['versions_file']
    self.cdnjs_api = config['cdnjs_api']

  def get_file_struct(self, path):
    """ Builds a list of libraries at the give path """
    output = {
      'created_at': str(datetime.today()),
      'url_template': self.lib_url_template,
      'items': []
    }
    for name in get_dir_list(path):
      inner_path = os.path.join(path, name)
      entry = self.format_entry(inner_path)
      output['items'].append(entry)
    return output

  def format_entry(self, path):
    """ Extracts and formats package's info at the given path """
    try:
        pkg = read_json(os.path.join(path, 'package.json'))
        # extract all versions by looking into each folder's name
        versions = [ pkg['version'] ]
        for dir_name in get_dir_list(path):
          if dir_name not in versions:
            versions.append(dir_name)
        return {
          'n': pkg['name'],
          'd': pkg['description'],
          'f': pkg['filename'],
          'v': versions
        }
    except Exception as e:
        print('format_entry error:', path, str(e))

  def transform_cdnjs_file(self):
    output = {
      'created_at': str(datetime.today()),
      'url_template': self.lib_url_template,
      'items': [],
    }
    current = None
    count = 0
    with open('raw_libraries.json', 'r', encoding="utf-8") as file:
      stream = ijson.parse(file)
      for prefix, event, value in stream:
        if (prefix, event) == ('results.item.name', 'string'):
          if current != None:
            output['items'].append(current)
            count += 1
            sys.stdout.write("\rProcessed Libraries: {0}".format(count))
            sys.stdout.flush()
          current = {
            'name': value,
            'description': '',
            'filename': '',
            'versions': [],
          }
        if (prefix, event) == ('results.item.assets.item.version', 'string'):
          current['versions'].append(value)
        if (prefix, event) == ('results.item.description', 'string'):
          current['description'] = value
        if (prefix, event) == ('results.item.filename', 'string'):
          current['filename'] = value
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
    if not os.path.exists(self.output_path):
      os.mkdir(self.output_path)
    name = "{0}/libraries_{1}.json".format(self.output_path, version)
    write_json(name, struct)


  def start(self):
    # download_file(self.cdnjs_api, 'raw_libraries.json')
    struct = self.transform_cdnjs_file()
    version = self.get_next_build_version()
    self.write_output(struct, version)
    # struct = self.get_file_struct(self.lib_path)
    # version = self.get_next_build_version()
    # self.write_output(struct, version)

if __name__ == '__main__':
  indexer = Indexer('config.json')
  indexer.start()
