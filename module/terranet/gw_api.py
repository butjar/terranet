import multiprocessing
import threading
import select
import logging
import ctypes
import os

from flask import Flask, request, abort, jsonify

api = Flask(__name__)
child_pipe = None

CLONE_NEWNET = 0x40000000


class Gateway_API_handler(threading.Thread):
    def __init__(self, name, gw, port, netns_pid, *args, **kwargs):
        self.port = port
        self.gw = gw
        self.netns_pid = netns_pid
        self.proc = multiprocessing.Process()
        self.running = False
        super(Gateway_API_handler, self).__init__(name=name, *args, **kwargs)

    def run(self):
        log = logging.getLogger(__name__)
        log.info('Starting Gateway API for {}.'.format(self.name))
        self.running = True
        parent_conn, child_conn = multiprocessing.Pipe()
        proc = multiprocessing.Process(target=_run_server, args=(self.port, child_conn, self.netns_pid))
        proc.start()

        while self.running and proc.exitcode is None:
            rlist, _, _ = select.select([parent_conn], [], [], 3.0)

            if parent_conn in rlist:
                req = parent_conn.recv()
                log.info('{} received information request.'.format(self.name))

                resp = {'status': 'Ok'}
                if req == 'reports':
                    reports = self.gw.reports
                    resp['query'] = reports
                    parent_conn.send(resp)
                elif req == 'throughput':
                    throughput = self.gw.throughput
                    resp['query'] = throughput
                    parent_conn.send(resp)
                elif req == 'fairness':
                    fairness = self.gw.jains_fairness
                    resp['query'] = fairness
                    parent_conn.send(resp)
                else:
                    parent_conn.send({'status': 'Error'})

        log.info('Stopping Gateway API for {}'.format(self.name))

        if proc.exitcode is None:
            log.info('Stopping {} Gateway API process...'.format(self.name))
            proc.terminate()

        proc.join()


def _run_server(port, pipe, netns_pid):
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

    global child_pipe
    child_pipe = pipe
    api.run(host='::', debug=False, port=port)


@api.route('/info/<query>', methods=['GET'])
def _get_info(query):
    child_pipe.send(query)
    resp = child_pipe.recv()
    return jsonify(resp)
