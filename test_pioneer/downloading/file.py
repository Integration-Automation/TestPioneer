import shutil
import urllib.request

from test_pioneer.logging.loggin_instance import test_pioneer_logger


def download_file(url: str, file_name: str):
    test_pioneer_logger.info("file_download.py download_file"
                            f" url: {url} "
                            f" file_name: {file_name}")
    with urllib.request.urlopen(url) as response, open(file_name, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)