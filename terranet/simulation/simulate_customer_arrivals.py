import time
import random
import numpy as np

from mininet.log import info

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
    seed = 2000
    rng = random.Random(seed)
    arrivals = 10
    customers = [f'h{x}{y}' for x in range(2,6) for y in ('a1','b1','c1')]
    customer_events = rng.choices(customers, k=arrivals)
    np.random.seed(seed)
    lam = 90
    waits = np.random.poisson(lam, arrivals)
    topo = HybridVirtualFiberTopo()
    net = Terranet(topo=topo,
                   build=False)
    module_path = 'terranet.ryu.app'
    apps = ('customer_flow_pipeline',
            'customer_stats_monitor',
            'customer_allocation_monitor')
    modules = [ '.'.join([module_path, x]) for x in apps ]
    ryu_manager = RyuManager('ryu-manager', modules=modules)
    net.addController(ryu_manager)
    with TerranetSimulator('customer_arrivals_simulation', net, clean_after=False) as net:
        for i in range(0, arrivals):
            toogle_customer_arrival(net, waits[i], customer_events[i])
        time.sleep(90)
