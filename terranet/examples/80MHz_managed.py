#!/usr/bin/env python
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


class ManagedBandTopo(Terratopo):
    """
           cpe_a1      cpe_b1      cpe_b2  (CPEs)
             |           |           |
       |  +-----+     +-----+     +-----+
    20 |  |cn_a1|     |cn_b1|     |cn_b2|  (STAs/ CNs)
       |  +-----+     +-----+     +-----+
       |     |           |       /
       |     |           |      /
    10 |     |           |     /
       |     |           |    /
       |     |           |   /
       |  +------+    +------+
     0 |  | dn_a |    | dn_b |             (APs/ DNs)
       |  +------+    +------+
       ---------------------------------->
     -10     0    15    20    25    30
    """

    def build(self, *args, **kwargs):
        channel_list = [Channel(32), Channel(34), Channel(36), Channel(38),
                        Channel(40), Channel(42), Channel(44), Channel(46),
                        Channel(48)]

        # Segment A
        dn_a = self.add_distribution_node_5_60(
            "dn_a",
            ssid="A",
            available_channels=channel_list,
            coordinates={"x": 0, "y": 0, "z": 0})

        cn_a1 = self.add_client_node("cn_a1",
                                     coordinates={"x": 0, "y": 20, "z": 0})
        self.add_wifi_link(dn_a, cn_a1)

        cpe_a1 = self.add_iperf_client("cpe_a1", server_name="server_a1")
        lcna1cpea1 = self.addLink(cn_a1, cpe_a1)
        lcna1cpea1[cn_a1].addParams(ip=("10.128.0.1/16",
                                        "fd00:0:0:100::1/56"))
        lcna1cpea1[cpe_a1].addParams(ip=("10.128.1.1/16",
                                         "fd00:0:0:1101::1/56"))

        # Segment B
        dn_b = self.add_distribution_node_5_60(
            "dn_b",
            ssid="B",
            available_channels=channel_list,
            coordinates={"x": 20, "y": 0, "z": 0})

        cn_b1 = self.add_client_node("cn_b1",
                                     coordinates={"x": 20, "y": 20, "z": 0})
        self.add_wifi_link(dn_b, cn_b1)

        cpe_b1 = self.add_iperf_client("cpe_b1", server_name="server_b1")
        lcnb1cpeb1 = self.addLink(cn_b1, cpe_b1)
        lcnb1cpeb1[cn_b1].addParams(ip=("10.129.0.1/16",
                                        "fd00:0:0:200::1/56"))
        lcnb1cpeb1[cpe_b1].addParams(ip=("10.129.2.1/16",
                                         "fd00:0:0:1201::1/56"))

        cn_b2 = self.add_client_node("cn_b2",
                                     coordinates={"x": 30, "y": 20, "z": 0})
        self.add_wifi_link(dn_b, cn_b2)

        cpe_b2 = self.add_iperf_client("cpe_b2", server_name="server_b2")
        lcnb2cpeb2 = self.addLink(cn_b2, cpe_b2)
        lcnb2cpeb2[cn_b2].addParams(ip=("10.129.0.2/16",
                                        "fd00:0:0:200::2/56"))
        lcnb2cpeb2[cpe_b2].addParams(ip=("10.129.3.1/16",
                                         "fd00:0:0:1202::1/56"))

        # Add WiFi 60GHz Links between DN_A and DN_B
        self.add_terragraph_link(dn_a, dn_b)

        # Add GW switch behind DN_A
        gw = self.addSwitch("s1", cls=OVSSwitch)
        self.add_ip_link(gw, dn_a)

        # Add iperf servers behind the gateway
        server_a1 = self.add_iperf_server("server_a1")
        self.addLink(gw, server_a1)

        server_b1 = self.add_iperf_server("server_b1")
        self.addLink(gw, server_b1)

        server_b2 = self.add_iperf_server("server_b2")
        self.addLink(gw, server_b2)

        # Build topo
        super(ManagedBandTopo, self).build(*args, **kwargs)


if __name__ == '__main__':
    setLogLevel('info')
    topo = ManagedBandTopo()
    komondor_config_dir = os.path.join(
        os.path.abspath("./.komondor"),
        os.path.basename(os.path.splitext(__file__)[0]))
    net = Terranet(topo=topo,
                   komondor_config_dir=komondor_config_dir,
                   ipBase=u"10.0.0.0/16",
                   ip6Base=u"fd00:0:0:0::/56",
                   max_v6_prefixlen=64)
    ctrlr = RemoteController("flow_ctrlr", port=6633)
    net.addController(ctrlr)
    net.start()
    IPCLI(net)
    net.stop()
