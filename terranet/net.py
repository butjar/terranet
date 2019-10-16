import time

from mininet.link import TCLink, TCIntf
from mininet.node import OVSSwitch
from ipmininet.ipnet import IPNet
from .link import Terralink
from .node import (Terranode, ClientNode, DistributionNode60,
                   DistributionNode5_60, IperfDownloadClient,
                   IperfDownloadServer, WifiNode,
                   WifiAccessPoint, WifiStation)
from .router_config import OpenrConfig

from .wifi.fronthaulemulator import FronthaulEmulator
from .wifi.komondor_config import KomondorSystemConfig


class Terranet(IPNet):
    def __init__(self,
                 komondor_system_cfg=None,
                 fronthaulemulator=None,
                 komondor_config_dir=None,
                 router=DistributionNode60,
                 config=OpenrConfig,
                 link=Terralink,
                 intf=TCIntf,
                 switch=OVSSwitch,
                 *args, **kwargs):
        if not fronthaulemulator:
            fronthaulemulator = FronthaulEmulator(
                net=self,
                komondor_config_dir=komondor_config_dir)
        self.fronthaulemulator = fronthaulemulator
        super(Terranet, self).__init__(router=router,
                                       config=config,
                                       link=link,
                                       intf=intf,
                                       switch=switch,
                                       *args, **kwargs)

    def build(self):
        super(Terranet, self).build()
        for node in self.wifi_nodes():
            node.register_fronthaulemulator(self.fronthaulemulator)
        self.fronthaulemulator.build_komondor()
        self.fronthaulemulator.apply_wifi_config()

    def start(self):
        super(Terranet, self).start()
        for server in self.get_iperf_download_servers():
            server.run_iperf_server()
        for client in self.get_iperf_download_clients():
            if client.server_name:
                client.host = self[client.server_name]
            if client.host:
                client.run_iperf_client()

    def terranodes(self):
        return filter(lambda x: isinstance(x, Terranode),
                      self.routers)

    def client_nodes(self):
        return filter(lambda x: isinstance(x, ClientNode),
                      self.terranodes())

    def distribution_nodes(self):
        return distribution_nodes_60 + distribution_nodes_5_60

    def distribution_nodes_60(self):
        return filter(lambda x: isinstance(x, DistributionNode60),
                      self.terranodes())

    def distribution_nodes_5_60(self):
        return filter(lambda x: isinstance(x, DistributionNode5_60),
                      self.terranodes())

    def wifi_nodes(self):
        return filter(lambda x: isinstance(x, WifiNode),
                      self.terranodes())

    def access_points(self):
        return filter(lambda x: isinstance(x, WifiAccessPoint),
                      self.terranodes())

    def stations(self):
        return filter(lambda x: isinstance(x, WifiStation),
                      self.terranodes())

    def get_nodes_by_komondor_setting(self, key, value):
        return filter(lambda x: x.komondor_config[key] == value,
                      self.terranodes())

    def connected_wifi_nodes(self, distribution_node_5_60):
        connectionsTo()
        wlan_code = distribution_node_5_60.komondor_config["wlan_code"]
        nodes_with_wlan_code = self.get_nodes_by_komondor_setting(
                                        "wlan_code", wlan_code)
        return filter(lambda x: isinstance(x, ClientNode),
                      nodes_with_wlan_code)

    def get_iperf_download_clients(self):
        return filter(lambda x: isinstance(x, IperfDownloadClient),
                      self.hosts)

    def get_iperf_download_servers(self):
        return filter(lambda x: isinstance(x, IperfDownloadServer),
                      self.hosts)
