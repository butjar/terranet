import requests
import configparser
import json
import subprocess
import sys
import logging
import logging.handlers

LOG_FILENAME = '/tmp/limiter_client.log'

# Set up a specific logger with our desired output level
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(
    LOG_FILENAME)

my_logger.addHandler(handler)

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
        try:
            with open(self.config_path, 'r') as f:
                self.cfg = configparser.ConfigParser()
                self.cfg.read_file(f)
                self.apply_limits()
        except IOError as e:
            my_logger.exception(e)

    def apply_limits(self):
        for s in filter(lambda sec: sec.startswith('Node_STA_'), self.cfg.sections()):
            my_logger.debug('Applying filter for %s', s)
            sname = s.split('Node_STA_')[1]
            my_logger.debug('sname: %s', sname)
            ap_name = 'AP_' + sname.rstrip('0123456789')

            my_logger.debug('apname: %s', ap_name)
            if_num = int(sname.split(ap_name.split('AP_')[1])[1])

            addr = self.ip_info['Node_' + ap_name]
            if_name = "%s-eth%d" % (ap_name, if_num)

            endpoint = 'http://%s:%d/limit/%s/' % (addr, PORT, if_name)
            tp = max(self.cfg.getint(s,'throughput'), 8)
            delay = max(self.cfg.getfloat(s, 'delay') * 1000, 0.001)
            burst = 32  # tp // 2 # TODO What should the burst value be?
            data = {'rate': '%dbit' % tp,
                    'latency':  '%fms'% delay,
                    'burst': '%dkbit' % burst}

            try:
                my_logger.info('Endpoint: %s', endpoint)
                r = requests.put(endpoint, json=data)
                my_logger.info('Response: %s', r.text)
                my_logger.info('Done')
            except requests.ConnectionError as e:
                my_logger.error("Could not apply limits: %s", e)

    def watch(self):
        while True:
            args = ['inotifywait', '-e', 'modify', self.watch_path]
            subprocess.call(args=args)
            my_logger.info('Reading from %s', self.watch_path)
            with open(self.watch_path, 'r') as f:
                try:
                    p = json.load(f)['path']
                    my_logger.info('New config: %s', p)
                    self.switch_config(p)
                except ValueError as e:
                    my_logger.exception(e)


my_logger.debug('This is a test.')
if __name__ == '__main__':
    try:
        if len(sys.argv) < 3:
            my_logger.error('Not enough args!')
            sys.exit(-1)
        apconf = sys.argv[1]
        watch_path = sys.argv[2]

        my_logger.info('Starting with "%s" and "%s"', apconf, watch_path)
        limiter = Limiter(apconf, watch_path)
        limiter.apply_limits()
        limiter.watch()
    except Exception as e:
        my_logger.exception('Uncaught exception %s', e)
