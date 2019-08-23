import ctypes
import logging
import os

CLONE_NEWNET = 0x40000000


def switch_namespace(netns_pid):
    libc = ctypes.CDLL('libc.so.6', use_errno=True)
    log = logging.getLogger(__name__)

    def errcheck(ret, func, args):
        if ret == -1:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))

    libc.setns.errcheck = errcheck
    try:
        with open('/proc/{:d}/ns/net'.format(netns_pid)) as fd:
            libc.setns(fd.fileno(), CLONE_NEWNET)
    except OSError:
        log.exception('Failed to enter network namespace of pid {}'.format(netns_pid))
        return

