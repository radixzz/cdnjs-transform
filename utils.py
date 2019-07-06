import os
import sys
import json
import requests
import errno
import logging
import coloredlogs

logger = logging.getLogger(__name__)

def init_log(filename):
  coloredlogs.install(level='INFO', logger=logger)
  logging.basicConfig(
    filename=filename
  )

def log_info(*args, **kwargs):
  logger.info(*args, **kwargs)

def log_error(*args, **kwargs):
  logger.error(*args, **kwargs)

def read_json(path):
  try:
    with open(path, 'r', encoding="utf-8") as file:
      return json.load(file)
  except Exception as e:
    log_error('read_json error:', path, str(e))

def write_json(path, content):
  try:
    with open(path, 'w') as file:
      json.dump(content, file)
  except Exception as e:
    log_error('write_json error:', str(e))

def write_file(path, content):
  try:
    with open(path, 'w') as file:
      file.write(content)
  except Exception as e:
    log_error('write_file error:', str(e))

def read_file(path):
  try:
    with open(path, 'r', encoding="utf-8") as file:
      return file.read()
  except Exception as e:
    log_error('read_file error:', str(e))

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            log_error('mkdir_p error while creating: ', path)
            raise

def download_file(url, dest_path, etag):
  result_etag = None
  try:
    with requests.get(url, stream=True) as req:
      log_info("Downloading file from: {0}".format(url))
      req.raise_for_status()
      result_etag = req.headers['etag']
      log_info('Etag: {0}'.format(result_etag))
      if (result_etag != etag or not os.path.exists(dest_path)):
        total_length = req.headers.get('content-length')
        total_transfer = 0
        log_info("Destination file: {0}".format(dest_path))
        if total_length is None:
          log_info("Unknown content-length")
        else:
          log_info("Total Size: {0}Kb".format(total_length / 1024))
        with open(dest_path, 'wb') as f:
          for chunk in req.iter_content(chunk_size=1024*32):
            if chunk:
              total_transfer += len(chunk)
              size_mb = total_transfer / 1024 / 1024
              f.write(chunk)
              sys.stdout.write("\rDownloaded: {:.2f} MB".format(size_mb))
              sys.stdout.flush()
        sys.stdout.write("\n")
        log_info('Download complete.')
      else:
        log_info('Already cached.')
  except Exception as e:
    log_error('\ndownload_file error:', str(e))
  return result_etag
