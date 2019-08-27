import logging
import subprocess
import json
import threading
import os
import shlex
import ipaddress

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

    @staticmethod
    def get_dn_ip6(flow_ip):
        f = ipaddress.IPv6Interface(u'{}/72'.format(flow_ip))

        ap_prefix = f.network.supernet(prefixlen_diff=16)

        # The first IP in the first subnet must be the Access Point
        dn_ip = next(next(ap_prefix.subnets(prefixlen_diff=16)).hosts())
        return str(dn_ip)

    def set_channel(self, ap_addr, chan_min, chan_max, api_port=6000):
        log = logging.getLogger(__name__)
        cmd = 'curl -g -6 -XPUT -H "Content-type: application/json" -d '
        cmd += '\'{{ "config": {{"min_channel_allowed": "{}", "max_channel_allowed": "{}"}}}}\' '.format(chan_min,
                                                                                                         chan_max)
        cmd += 'http://[{}]:{}/cfg/'.format(ap_addr, api_port)

        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        out, err = p.communicate()
        if p.returncode != 0:
            log.error('Failed to execute query to access point! Stderr: {} | Stdout: {}'.format(err, out))
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
            log.warning('Query could not be executed by access point!')
            return None

        return resp

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
