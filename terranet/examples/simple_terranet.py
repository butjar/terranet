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


class SimpleTerranetTopo(Terratopo):
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
        channel_list = [Channel(42), Channel(36), Channel(38), Channel(40),
                        Channel(44), Channel(46), Channel(48)]

        # Segment A
        dn_a = self.add_distribution_node_5_60(
            "dn_a",
            ssid="A",
            available_channels=channel_list,
            coordinates={"x": 0, "y": 0, "z": 0},
            proxy_port=8199)

        cn_a1 = self.add_client_node("cn_a1",
                                     coordinates={"x": 0, "y": 20, "z": 0})
        self.add_wifi_link(dn_a, cn_a1)


        # Segment B
        dn_b = self.add_distribution_node_5_60(
            "dn_b",
            ssid="B",
            available_channels=channel_list,
            coordinates={"x": 20, "y": 0, "z": 0},
            proxy_port=8299)

        cn_b1 = self.add_client_node("cn_b1",
                                     coordinates={"x": 20, "y": 20, "z": 0})
        self.add_wifi_link(dn_b, cn_b1)


        # Segment C
        dn_c = self.add_distribution_node_5_60(
            "dn_c",
            ssid="C",
            available_channels=channel_list,
            coordinates={"x": 40, "y": 0, "z": 0},
            proxy_port=8399)

        cn_c1 = self.add_client_node("cn_c1",
                                     coordinates={"x": 40, "y": 20, "z": 0})
        self.add_wifi_link(dn_c, cn_c1)


        # Add WiFi 60GHz Links between DN_A and DN_B
        self.add_terragraph_link(dn_a, dn_b)

        # Add WiFi 60GHz Links between DN_B and DN_C
        self.add_terragraph_link(dn_b, dn_c)

        # Add GW switch behind DN_A
        gw = self.addSwitch("s1", cls=OVSSwitch)
        self.add_ip_link(gw, dn_a)

        # cn_a1 customer flows
        h1a1, s1a1 = self.add_customer_flow(cn_a1, gw,
                                            suffix="1a1",
                                            network=("10.145.128.0/24",
                                                     "fd00:0:0:8101:8001::0/80"),
                                            autostart_client=True)
        h2a1, s2a1 = self.add_customer_flow(cn_a1, gw,
                                            suffix="2a1",
                                            network=("10.145.129.0/24",
                                                     "fd00:0:0:8101:8002::0/80"),
                                            autostart_client=True)
        h3a1, s3a1 = self.add_customer_flow(cn_a1, gw,
                                            suffix="3a1",
                                            network=("10.145.130.0/24",
                                                     "fd00:0:0:8101:8003::0/80"),
                                            autostart_client=True)

        # cn_b1 customer flows
        h1b1, s1b1 = self.add_customer_flow(cn_b1, gw,
                                            suffix="1b1",
                                            network=("10.161.128.0/24",
                                                     "fd00:0:0:8201:8001::0/80"),
                                            autostart_client=True)
        h2b1, s2b1 = self.add_customer_flow(cn_b1, gw,
                                            suffix="2b1",
                                            network=("10.161.129.0/24",
                                                     "fd00:0:0:8201:8002::0/80"),
                                            autostart_client=False)
        h3b1, s3b1 = self.add_customer_flow(cn_b1, gw,
                                            suffix="3b1",
                                            network=("10.161.130.0/24",
                                                     "fd00:0:0:8201:8003::0/80"),
                                            autostart_client=False)

        # cn_c1 customer flows
        h1c1, s1c1 = self.add_customer_flow(cn_c1, gw,
                                            suffix="1c1",
                                            network=("10.177.128.0/24",
                                                     "fd00:0:0:8301:8001::0/80"),
                                            autostart_client=True)
        h2c1, s2c1 = self.add_customer_flow(cn_c1, gw,
                                            suffix="2c1",
                                            network=("10.177.129.0/24",
                                                     "fd00:0:0:8301:8002::0/80"),
                                            autostart_client=False)
        h3c1, s3c1 = self.add_customer_flow(cn_c1, gw,
                                            suffix="3c1",
                                            network=("10.177.130.0/24",
                                                     "fd00:0:0:8301:8003::0/80"),
                                            autostart_client=False)


        # Build topo
        super(SimpleTerranetTopo, self).build(*args, **kwargs)


if __name__ == '__main__':
    setLogLevel('info')
    topo = SimpleTerranetTopo()
    komondor_config_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        ".komondor",
        os.path.basename(os.path.splitext(__file__)[0]))
    net = Terranet(topo=topo,
                   komondor_config_dir=komondor_config_dir,
                   ipBase=u"10.0.0.0/9",
                   ip6Base=u"fd00:0:0::0/49",
                   max_v6_prefixlen=96)
    ctrlr = RemoteController("flow_ctrlr", port=6633)
    net.addController(ctrlr)
    net.start()
    IPCLI(net)
    net.stop()
