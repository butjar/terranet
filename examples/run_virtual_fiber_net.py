import os

from mininet.log import setLogLevel, info, debug
from mininet.node import Ryu, RemoteController
from ipmininet.cli import IPCLI

import terranet
from terranet.topo import HybridTerragraphTopo
from terranet.net import Terranet


if __name__ == '__main__':
    setLogLevel('info')
    topo = HybridTerragraphTopo()
    net = Terranet(topo=topo)
    os.environ['HOME'] = os.path.dirname(terranet.__file__)
    modules = ['terranet.ryu.ryu.app.customer_flow_matching',
               'terranet.ryu.ryu.app.customer_monitor']
    ryu_manager = Ryu('ryu-manager', *modules, port=6633)
    net.addController(ryu_manager)
    #ctrlr = RemoteController('remote_ctrlr', port=6633)
    #net.addController(ctrlr)
    net.start()
    IPCLI(net)
    net.stop()
