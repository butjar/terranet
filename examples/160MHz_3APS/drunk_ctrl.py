import terranet
from terranet.util import valid_5ghz_outdoor_channels
import time
import random
import logging


class DrunkCtrl(terranet.TerraNetController):
    def ctrl_loop(self):
        while self.running:
            log = logging.getLogger(__name__)

            flows = self.get_flows()
            aps = set()

            for ip in flows:
                aps.add(self.get_dn_ip6(ip))

            ap = random.sample(aps, 1)[0]

            # All or Nothing! Or Half! Whatever!
            chan = random.choice(list(valid_5ghz_outdoor_channels()))
            log.info('Setting Channel to {} -- {}'.format(chan[0], chan[1]))
            self.set_channel(ap, chan[0], chan[1])

            time.sleep(1 + (random.random() * 10))

