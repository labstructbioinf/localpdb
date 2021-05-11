import logging
import urllib.request
import urllib.error
import time
from ftplib import FTP
from urllib.parse import urlparse
from datetime import datetime
from localpdb.utils.os import set_last_modified

logger = logging.getLogger(__name__)


def get_last_modified(url, ftp=False):
    """
    Fetches the 'Last-Modified' value of the remote URL
    @param url: URL addres to fetch the 'Last-Modified' date
    @param ftp: flag whether remote URL points to the FTP server
    @return: timetuple of the 'Last-Modified' date
    """
    if ftp:
        parsed_url = urlparse(url)
        ftp = FTP(parsed_url.netloc)
        ftp.login()
        ts = ftp.voidcmd("MDTM {}".format(parsed_url.path))[4:].strip()
        ftp.close()
        last_modified = '{yy}-{mo}-{dd} {hh}:{mm}:{ss}'.format(yy=ts[:4], mo=ts[4:6], dd=ts[6:8], hh=ts[8:10],
                                                               mm=ts[10:12], ss=ts[12:14])
        last_modified = datetime.strptime(last_modified, '%Y-%m-%d %H:%M:%S')
        return time.mktime(last_modified.timetuple())
    else:
        conn = urllib.request.urlopen(url, timeout=30)
        last_modified = time.strptime(conn.headers['last-modified'], '%a, %d %b %Y %H:%M:%S %Z')
        conn.close()
        return time.mktime(last_modified)


def download_url(url, dest, ftp=False):
    """
    Method for handling downloads and replicating modification timestamps
    @param url: url to download
    @param dest: destination of the downloaded file
    @param ftp: True if ftp protocol is used for downloads.
    @return True/False denoting whether download was successful or not
    """
    try:
        urllib.request.urlretrieve(url, dest)
        logger.debug(f'Downloaded url: \'{url}\' to destination: \'{dest}\'')
        # Set remote 'last-modified' date for verification purposes
        last_modified = get_last_modified(url, ftp=ftp)
        set_last_modified(dest, last_modified)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError):
        logger.error(f'Failed to download url: \'{url}\' to destination: \'{dest}\'')
        return False
