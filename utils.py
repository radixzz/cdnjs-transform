import os
import sys
import json
import ijson
import requests

def read_json_stream(path):
  with open(path, 'r', encoding="utf-8") as file:
    return ijson.parse(file)

def read_json(path):
  try:
    with open(path, 'r', encoding="utf-8") as file:
      return json.load(file)
  except Exception as e:
    print('read_json error:', path, str(e))

def write_json(path, content):
  try:
    with open(path, 'w') as file:
      json.dump(content, file)
  except Exception as e:
    print('write_json error:', str(e))

def write_file(path, content):
  try:
    with open(path, 'w') as file:
      file.write(content)
  except Exception as e:
    print('write_file error:', str(e))

def read_file(path):
  try:
    with open(path, 'r', encoding="utf-8") as file:
      return file.read()
  except Exception as e:
    print('read_file error:', str(e))

def get_dir_list(path):
  return [ name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name)) ]

def download_file(url, dest_path):
  print("Downloading file from: {0}".format(url))
  with requests.get(url, stream=True) as req:
    req.raise_for_status()
    total_length = req.headers.get('content-length')
    total_transfer = 0
    if total_length is None:
      print("Unknown content-length")
    else:
      print("Total Size: {0}Kb".format(total_length / 1024))
    with open(dest_path, 'wb') as f:
      for chunk in req.iter_content(chunk_size=1024*32):
        if chunk:
          total_transfer += len(chunk)
          size_mb = total_transfer / 1024 / 1024
          f.write(chunk)
          sys.stdout.write("\rDownloaded: {:10.2f} MB".format(size_mb))
          sys.stdout.flush()
