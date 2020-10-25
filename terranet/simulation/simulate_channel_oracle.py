import os
import time
import random
import numpy as np

from mininet.log import info

import terranet.ryu.app as ryu_app_module
from terranet.topo import HybridVirtualFiberTopo
from terranet.net import Terranet
from terranet.controller import RyuManager
from terranet.simulator import TerranetSimulator

def toogle_customer_arrival(net, wait, customer):
    info(f'Next arrival after {wait} seconds.\n')
    time.sleep(wait)
    info(f'Toggling iperf of customer {customer}.\n')
    net[customer].toggle_iperf()


if __name__ == '__main__':
    arrivals = 10
    rng = random.Random(2000)
    customers = [f'h{x}{y}' for x in range(2,6) for y in ('a1','b1','c1')]
    customer_events = rng.choices(customers, k=arrivals)
    lam = 90
    waits = np.random.poisson(lam, arrivals)
    topo = HybridVirtualFiberTopo()
    net = Terranet(topo=topo,
                   build=False)
    apps = ('customer_flow_pipeline',
            'customer_stats_monitor',
            'channel_assignment_oracle')
    modules = [ '.'.join(['terranet.ryu.app', x]) for x in apps ]
    config_file =  os.path.join(os.path.dirname(ryu_app_module.__file__),
                                'cfg/channel_oracle.conf')
    ryuArgs = (f'--config-file {config_file}')
    ryu_manager = RyuManager('ryu-manager', ryuArgs, modules=modules)
    net.addController(ryu_manager)
    with TerranetSimulator('channel_oracle_simulation', net, clean_after=False) as net:
        for i in range(0, arrivals):
            toogle_customer_arrival(net, waits[i], customer_events[i])
