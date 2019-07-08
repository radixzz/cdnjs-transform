import os
import sys
import json
import requests
import errno

def read_json(path):
  try:
    with open(path, 'r', encoding="utf-8") as file:
      return json.load(file)
  except IOError as e:
    raise e

def write_json(path, content):
  try:
    with open(path, 'w') as file:
      json.dump(content, file)
  except IOError as e:
    raise e

def write_file(path, content):
  try:
    with open(path, 'w') as file:
      file.write(content)
  except IOError as e:
    raise e

def read_file(path):
  try:
    with open(path, 'r', encoding="utf-8") as file:
      return file.read()
  except IOError as e:
    raise e

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def download_file(url, dest_path, etag):
  result_etag = None
  try:
    with requests.get(url, stream=True) as req:
      req.raise_for_status()
      if (req.headers['etag'] != etag or not os.path.exists(dest_path)):
        result_etag = req.headers['etag']
        total_length = req.headers.get('content-length')
        total_transfer = 0
        if total_length is not None:
          with open(dest_path, 'wb') as f:
            for chunk in req.iter_content(chunk_size=1024*32):
              if chunk:
                total_transfer += len(chunk)
                size_mb = total_transfer / 1024 / 1024
                f.write(chunk)
                sys.stdout.write("\rDownloaded: {:.2f} MB".format(size_mb))
                sys.stdout.flush()
          sys.stdout.write("\n")
  except Exception as e:
    raise e
  return result_etag
