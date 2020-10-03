#! python
import os
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.node import OVSSwitch
from mininet.node import RemoteController

from ipmininet.cli import IPCLI

from terranet.net import Terranet
from terranet.topo import Terratopo

from terranet.wifi.komondor_config import KomondorConfig
from terranet.wifi.channel import Channel


class HybridHandoverTopo(Terratopo):
    def build(self, *args, **kwargs):
        # Segment A
        channel_list_a = [
            Channel(42), # 80MHz
            Channel(38), Channel(46), # 40MHz
            Channel(36), Channel(40), Channel(44), Channel(48) # 20MHz
        ]
        dn_a = self.add_distribution_node_60('dn_a')
        ap_a = self.add_smart_access_point('ap_a',
                                           ssid='A',
                                           available_channels=channel_list_a,
                                           coordinates={'x': 0, 'y': 0})
        self.add_ip_link(dn_a, ap_a)
        cn_a1 = self.add_client_node('cn_a1',
                                     coordinates={'x': 0, 'y': 20})
        self.add_terragraph_link(dn_a, cn_a1)
        self.add_wifi_link(ap_a, cn_a1)


        # Segment B
        channel_list_b = [
            Channel(58), # 80MHz
            Channel(54), Channel(62), # 40MHz
            Channel(52), Channel(56), Channel(60), Channel(64) # 20MHz
        ]
        dn_b = self.add_distribution_node_60('dn_b')
        ap_b = self.add_smart_access_point('ap_b',
                                           ssid='B',
                                           available_channels=channel_list_b,
                                           coordinates={'x': 20, 'y': 0})
        self.add_ip_link(dn_b, ap_b)
        cn_b1 = self.add_client_node('cn_b1',
                                     coordinates={'x': 20, 'y': 20})
        self.add_terragraph_link(dn_b, cn_b1)
        self.add_wifi_link(ap_b, cn_b1)


        # Add WiFi 60GHz Links between DN_A and DN_B
        self.add_terragraph_link(dn_a, dn_b)

        # Add GW switch behind DN_A
        gw = self.addSwitch('s1', cls=OVSSwitch)
        self.add_ip_link(gw, dn_a)

        # cn_a1 customer flows
        h1a1, s1a1 = self.add_customer_flow(cn_a1, gw,
                                            suffix='1a1',
                                            network=('10.145.128.0/24',
                                                     'fd00:0:0:8101:8001::0/80'),
                                            autostart_client=True)
        h2a1, s2a1 = self.add_customer_flow(cn_a1, gw,
                                            suffix='2a1',
                                            network=('10.145.129.0/24',
                                                     'fd00:0:0:8101:8002::0/80'),
                                            autostart_client=False)

        # cn_b1 customer flows
        h1b1, s1b1 = self.add_customer_flow(cn_b1, gw,
                                            suffix='1b1',
                                            network=('10.161.128.0/24',
                                                     'fd00:0:0:8201:8001::0/80'),
                                            autostart_client=True)
        h2b1, s2b1 = self.add_customer_flow(cn_b1, gw,
                                            suffix='2b1',
                                            network=('10.161.129.0/24',
                                                     'fd00:0:0:8201:8002::0/80'),
                                            autostart_client=False)

        # Build topo
        super().build(*args, **kwargs)


if __name__ == '__main__':
    setLogLevel('info')
    topo = HybridHandoverTopo()
    komondor_config_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '.komondor',
        os.path.basename(os.path.splitext(__file__)[0]))
    net = Terranet(topo=topo,
                   komondor_config_dir=komondor_config_dir,
                   ipBase=u'10.0.0.0/9',
                   ip6Base=u'fd00:0:0::0/49',
                   max_v6_prefixlen=96)
    ctrlr = RemoteController('flow_ctrlr', port=6633)
    net.addController(ctrlr)
    net.start()
    IPCLI(net)
    net.stop()
