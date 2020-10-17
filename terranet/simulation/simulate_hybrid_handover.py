import time

from mininet.log import info

from terranet.topo import HybridBackupTerragraphTopo
from terranet.net import Terranet
from terranet.controller import RyuManager
from terranet.simulator import TerranetSimulator


if __name__ == '__main__':
    topo = HybridBackupTerragraphTopo()
    net = Terranet(topo=topo,
                   build=False)
    module_path = 'terranet.ryu.app'
    apps = ('customer_flow_pipeline',
            'customer_stats_monitor')
    modules = [ '.'.join([module_path, x]) for x in apps ]
    ryu_manager = RyuManager('ryu-manager', modules=modules)
    net.addController(ryu_manager)
    with TerranetSimulator('handover_simulation', net, clean_after=False) as net:
        # DN_A <-> CN_A1
        dn_a = net['dn_a']
        cn_a1 = net['cn_a1']
        link_dn_a_cn_a1 = net.linksBetween(dn_a, cn_a1)[0]
        # DN_B <-> DN_B1
        dn_b = net['dn_b']
        cn_b1 = net['cn_b1']
        cn_b2 = net['cn_b2']
        link_dn_b_cn_b1 = net.linksBetween(dn_b, cn_b1)[0]
        link_dn_b_cn_b2 = net.linksBetween(dn_b, cn_b2)[0]
        time.sleep(30)

        info('{}: Simulating link failure DN_A <=>
                CN_A1\n'
                .format(TerranetSimulator.time_ns()))
        link_dn_a_cn_a1.intf2.ifconfig('down')
        time.sleep(60)

        info('{}: Simulating link failure DN_B <=> CN_B1 '
             'and DN_B <=> CN_B2\n'
             .format(TerranetSimulator.time_ns()))
        link_dn_b_cn_b1.intf2.ifconfig('down')
        link_dn_b_cn_b2.intf2.ifconfig('down')
        time.sleep(60)

        info('{}: Simulating link failure recovery DN_A <=> CN_A1\n'
             .format(TerranetSimulator.time_ns()))
        link_dn_a_cn_a1.intf2.ifconfig('up')
        time.sleep(30)
