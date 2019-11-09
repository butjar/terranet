import time
import terranet
import itertools
from terranet.util import valid_5ghz_outdoor_channels
import logging


class Option:
    def __init__(self, cfg, controller):
        self.cfg = cfg
        self.share = self.calc_share(cfg)
        self.controller = controller

    def overlap(self):
        overlap = 0
        for n in self.count_channel_users(self.cfg):
            if n > 1:
                overlap += n-1
        return overlap

    def unused(self):
        loss = 0
        for n in self.count_channel_users(self.cfg):
            if n < 1:
                loss += 1
        return loss

    def metric(self):
        dist_squared = 0.0

        for share_ap, ap in zip(self.share, self.controller.aps):
            dist_squared += (ap.relative_load - share_ap)**2

        return dist_squared + self.overlap() + self.unused()

    @staticmethod
    def calc_share(cfg_option):
        aps_total = len(cfg_option)
        ap_share = [0.0] * aps_total
        aps_per_channel = Option.count_channel_users(cfg_option)

        for chan, num_aps in enumerate(aps_per_channel):
            for ap, ap_chan in enumerate(cfg_option):
                if ap_chan[0] <= chan <= ap_chan[1]:
                    ap_share[ap] += (1.0 / 8.0) / float(num_aps)

        # TODO We should factor in channel overlap
        return ap_share

    @staticmethod
    def count_channel_users(cfg_option):
        chan_users = [0] * 8
        for i in range(0, 8):
            num_user = 0
            for min, max in cfg_option:
                if min <= i <= max:
                    num_user += 1

            chan_users[i] = num_user
        return chan_users


class AP:
    def __init__(self, ipv6, controller):
        self.controller = controller
        self.ipv6 = ipv6
        self.absolute_load = 0.0
        self.relative_load = 0.0

    def update_load(self):
        flows = self.controller.get_flows()
        for ip in flows:
            if terranet.TerraNetController.get_dn_ip6(ip) == self.ipv6:
                self.absolute_load += 1.0
        self.relative_load = self.absolute_load / len(flows)


class HeuristicController(terranet.TerraNetController):
    def __init__(self, *args, **kwargs):
        super(HeuristicController, self).__init__(*args, **kwargs)
        self.aps = []
        self.options = []

    def compute_options(self):
        if not self.aps:
            return

        num_aps = len(self.aps)

        cfg_options = list(itertools.product(valid_5ghz_outdoor_channels(), repeat=num_aps))
        self.options = []
        for c in cfg_options:
            self.options.append(Option(c, self))

    def compute_load_per_ap(self):
        flows = self.get_flows()

        flow_ap = set()
        for ip in flows:
            ap = self.get_dn_ip6(ip)
            flow_ap.add(ap)

        self.aps = []
        for ap in flow_ap:
            a = AP(ap, self)
            a.update_load()
            self.aps.append(a)

        self.aps.sort(key=lambda x: x.ipv6)

    def ctrl_loop(self):
        log = logging.getLogger(__name__)

        while self.running:
            self.compute_load_per_ap()
            self.compute_options()

            distances = map(lambda o: o.metric(), self.options)
            min_index = min(xrange(len(distances)), key=distances.__getitem__)

            log.info(min_index)
            best_cfg = self.options[min_index].cfg
            log.info(best_cfg)

            for i, chan in enumerate(best_cfg):
                log.info("IP:{} Chan ({},{}), Load: {}".format(self.aps[i].ipv6, chan[0], chan[1], self.aps[i].relative_load))
                self.set_channel(self.aps[i].ipv6, chan[0], chan[1])

            time.sleep(10)


