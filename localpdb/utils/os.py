import os
import sys
import logging
import coloredlogs
import contextlib
import signal
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging_handlers(tmp_path='/tmp'):
    """
    Sets up logger handlers for localpdb_setup and localpdb_update scripts
    @param tmp_path: directory where log file will be temporarily stored
    @return: temporary log filename, tuple with configured logging handlers
    """
    fn_log = '{}/localpdb_setup_{}.log'.format(tmp_path, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    fh_hdlr = logging.FileHandler(fn_log, mode='w', encoding='utf8')
    fh_hdlr.setLevel(logging.DEBUG)
    fh_hdlr.setFormatter(logging.Formatter('[%(asctime)s] [%(filename)s] %(levelname)s - %(message)s'))
    cnsl_hdlr = logging.StreamHandler(sys.stdout)
    cnsl_hdlr.setLevel(logging.INFO)
    cnsl_hdlr.setFormatter(coloredlogs.ColoredFormatter('%(message)s'))
    return fn_log, (fh_hdlr, cnsl_hdlr)


def create_directory(path):
    """
    Creates directory with additional verbosity and checks
    @param path: path to the created directory
    @return: True if created properly
    """
    path = Path(path)
    if path.is_dir():
        if len(os.listdir(path)):
            logger.debug(f'Directory \'{path}\' already exists and is not empty.')
        else:
            logger.debug(f'Directory \'{path}\' already exists and is empty.')
        return True
    else:
        try:
            path.mkdir()
        except PermissionError:
            logger.error(f'No write permission in directory: \'{path}\'.')
            sys.exit(1)
        except FileExistsError:
            logger.error(f'Cannot create directory: \'{path}\' - file with this name already exist.')
            sys.exit(1)


def set_last_modified(fn, date):
    """
    Sets the last modified date of the local file
    @param fn: filename to set the last modified date
    @param date: date in the timetuple format
    """
    os.utime(fn, (date, date))


def _sigterm_handler(signum, frame):
    sys.exit(0)
_sigterm_handler.__enter_ctx__ = False


@contextlib.contextmanager
def clean_exit(callback=None, append=False):
    """A context manager which properly handles SIGTERM and SIGINT
    Modified version of the handle_exit function
    Giampaolo Rodola' <g.rodola [AT] gmail [DOT] com>
    License: MIT
    """
    killed = False
    old_handler = signal.signal(signal.SIGTERM, _sigterm_handler)
    if (old_handler != signal.SIG_DFL) and (old_handler != _sigterm_handler):
        if not append:
            raise RuntimeError("there is already a handler registered for "
                               "SIGTERM: %r" % old_handler)

        def handler(signum, frame):
            try:
                _sigterm_handler(signum, frame)
            finally:
                old_handler(signum, frame)
                killed = True

        signal.signal(signal.SIGTERM, handler)

    if _sigterm_handler.__enter_ctx__:
        raise RuntimeError("can't use nested contexts")
    _sigterm_handler.__enter_ctx__ = True

    try:
        yield
    except KeyboardInterrupt:
        killed = True
        sys.exit(1)
    except SystemExit as err:
        # code != 0 refers to an application error (e.g. explicit
        # sys.exit('some error') call).
        # We don't want that to pass silently.
        # Nevertheless, the 'finally' clause below will always
        # be executed.
        killed = True
        if err.code != 0:
            raise
    finally:
        _sigterm_handler.__enter_ctx__ = False
        if callback is not None and killed:
            logger.error('Script abruptly terminated! Cleaning temporary files...')
            callback()


def os_cmd(cmd):
    """
    Wrapper around subprocess
    @param cmd: command to be run
    @return: exit code of the process and tuple of stdout and stderr of the process
    """
    p = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, (p.stdout.decode('utf-8').split('\n'), p.stderr.decode('utf-8').split('\n'))
