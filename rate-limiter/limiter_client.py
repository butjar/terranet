import requests
import configparser
import json
import subprocess
import sys

PORT = 5000

class Limiter():
    """Applies TC rate limiting to distribution nodes"""

    def __init__(self, apconfig_path, watch_path):
        self.apconfig_path = apconfig_path
        self.watch_path = watch_path

        with open(apconfig_path, 'r') as f:
            self.ip_info = json.load(f)

        with open(watch_path, 'r') as f:
            self.config_path = json.load(f)['path']

        with open(self.config_path, 'r') as f:
            self.cfg = configparser.ConfigParser()
            self.cfg.read_file(f)


    @staticmethod
    def ipv4_str_to_num(ip):
        octets = ip.split('.')
        num = 0
        for i in range(0, len(octets)):
            num += int(octets[i]) << (8 * (len(octets) - (i+1)))
        return num

    @staticmethod
    def num_to_ipv4_str(num):
        octets = []
        for i in range(0, 4):
            octets.append("%d" % ((num >> 8*(4 - (i+1))) & 0xFF))

        return '.'.join(octets)


    def switch_config(self, result_config_path):
        self.config_path = result_config_path
        self.cfg = configparser.ConfigParser().read_file(result_config_path)
        self.apply_limits()

    def apply_limits(self):
        for s in filter(lambda sec: sec.startswith('Node_STA_'), self.cfg.sections()):
            sname = s.split('Node_STA_')[1]
            ap_name = 'AP_' + sname.rstrip('0123456789')
            if_num = int(sname.split(ap_name)[1])

            addr = self.ip_info['Node_' + ap_name]
            if_name = "%s-eth%d" % (ap_name, if_num)

            endpoint = 'http://%s:%d/limit/%s/' % (addr, PORT, if_name)
            tp = max(self.cfg.getint(s,'throughput'), 8)
            delay = max(self.cfg.getfloat(s, 'delay'), 0.001)
            burst = tp // 2 # TODO What should the burst value be?
            data = {'rate': '%dbits' % tp,
                    'latency':  '%fms'% delay,
                    'burst': '%dbits' % burst}

            try:
                requests.put(endpoint, json=data, timeout=10)
            except requests.ConnectionError as e:
                print e

    def watch(self):
        while True:
            args = ['inotifywait', '-e', 'modify', self.watch_path]
            subprocess.call(args=args)

            with open(self.watch_path, 'r') as f:
                self.config_path = json.load(f)['path']

            self.apply_limits()

if __name__ == '__main__':
    apconf = sys.argv[1]
    watch_path = sys.argv[2]
    limiter = Limiter(apconf, watch_path)
    limiter.apply_limits()
    limiter.watch()
