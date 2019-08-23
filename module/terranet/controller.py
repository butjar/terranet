import logging
import subprocess
import json
import threading
import os

from .ns import switch_namespace


class TerraNetController(threading.Thread):
    def __init__(self, nspid, gw_ip6, gw_api_port=6666, *args, **kwargs):
        self.gw_addr = gw_ip6
        self.gw_port = gw_api_port
        self.running = False

        self.nspid = nspid
        self.old_pid = os.getpid()

        super(TerraNetController, self).__init__(*args, **kwargs)

    def _enter_namespace(self):
        switch_namespace(self.nspid)

    def _exit_namespace(self):
        switch_namespace(self.old_pid)

    def _query_gw(self, query):
        log = logging.getLogger(__name__)
        p = subprocess.Popen('curl -g -6 http://[{}]:{}/info/{}'.format(self.gw_addr, self.gw_port, query).split(),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        if p.returncode != 0:
            log.error('Error executing query to gateway! Stderr: {} | Stdout: {}'.format(err, out))
            return None

        try:
            resp = json.loads(out.decode('utf-8'))
        except ValueError():
            log.exception('Received unexpected output from curl! --> "{}"'.format(out))
            return None

        if 'status' not in resp:
            log.error('Received unexpected output from curl! --> "{}"'.format(out))
            return None

        if resp['status'] == 'Error':
            log.warning('Query could not be executed by gateway!')
            return None

        if 'query' not in resp:
            log.error('Received unexpected output from curl! --> "{}"'.format(out))
            return None

        return resp['query']

    def get_fairness(self):
        return self._query_gw('fairness')

    def get_throughput(self):
        return self._query_gw('throughput')

    def get_flows(self):
        return self._query_gw('reports')

    def run(self):
        self.running = True
        self._enter_namespace()
        self.ctrl_loop()
        self._exit_namespace()

    def ctrl_loop(self):
        """Override me! NOTE: The method should exit when self.running is set to False."""
        pass

    def stop(self):
        """Call this method from the parent thread to stop the running method."""
        self.running = False
        self.join()
