from pathlib import Path
from package import Transformer

def abs_path(path):
  return (Path(__file__).parent / path).resolve()

if __name__ == '__main__':
  trans = Transformer({
    'builds_path': abs_path('builds'),
    'downloads_path': abs_path('tmp'),
    'versions_path': abs_path('builds_version'),
    'cache_etag_path': abs_path('etag'),
    'lib_url_template': 'https://cdnjs.cloudflare.com/ajax/libs/{n}/{v}/{f}',
    'cdnjs_api': 'https://api.cdnjs.com/libraries?fields=name,filename,description,assets,version,keywords',
    'max_versions_per_lib': 10
  })
  trans.start()
