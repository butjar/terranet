import requests
import configparser

BASE_ADDR = "10.0.0.0"
PORT = 5000

class Limiter():
    """Applies TC rate limiting to distribution nodes"""
    def __init__(self, result_config_path):
        self.config_path = result_config_path
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

    def ap_name_to_ipv4(self, ap_name):
        offset = 0
        for c in ap_name:
            offset += ord(c) - ord('A') + 1

        return self.num_to_ipv4_str(self.ipv4_str_to_num(BASE_ADDR) + offset)

    def switch_config(self, result_config_path):
        self.config_path = result_config_path
        self.cfg = configparser.ConfigParser().read_file(result_config_path)
        self.apply_limits()

    def apply_limits(self):
        for s in filter(lambda sec: sec.startswith('Node_STA_'), self.cfg.sections()):
            sname = s.split('Node_STA_')[1]
            ap_name = sname.rstrip('0123456789')
            if_num = int(sname.split(ap_name)[1])

            addr = self.ap_name_to_ipv4(ap_name)
            if_name = "AP_%s-eth%d" % (ap_name, if_num)

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


if __name__ == '__main__':
    lim = Limiter('/home/sebastian/Dokumente/terranet/examples/160MHz/out/terranet_000.cfg')
    lim.apply_limits()




