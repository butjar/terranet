import terranet
import time
import logging

class DummyCtrl(terranet.TerraNetController):
    def ctrl_loop(self):
        while self.running:
            log = logging.getLogger(__name__)
            log.info('Beep Boop Beep Boop!')
            log.info('My Gateway: {}'.format(self.gw_addr))
            log.info('My Gateway Port: {}'.format(self.gw_port))
            log.info('Current fairness: {}'.format(self.get_fairness()))
            log.info('Current throughput: {}'.format(self.get_throughput()))

            log.info('Current Flows')
            flows = self.get_flows()
            for ip in flows:
                log.info('IPv6: {} -- {} Mbit/s -- DN: {}'.format(ip, flows[ip]/1e6, self.get_dn_ip6(ip)))
            time.sleep(5)

