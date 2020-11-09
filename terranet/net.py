from mininet.node import OVSSwitch
from ipmininet.ipnet import IPNet
from ipmininet.ipnet import IPLink, IPIntf
from ipmininet.router.config import OpenrRouterConfig
from .link import TerraLink, TerraIntf
from .node import TerranetRouter, ClientNode, DistributionNode, \
                  DistributionNode60, DistributionNode5_60, \
                  IperfHost, IperfClient, IperfServer, \
                  WifiNode, WifiAccessPoint, WifiStation
from .wifi.sub6ghz_emulator import Sub6GhzEmulator
from .wifi.komondor_config import KomondorSystemConfig
from .influx.customerstats import CustomerstatsContinuousQueries
from .influx.switchstats import SwitchstatsContinuousQueries


class Terranet(IPNet):
    def __init__(self,
                 topo=None,
                 komondor_system_cfg=None,
                 sub6ghz_emulator=None,
                 komondor_config_dir=None,
                 router=DistributionNode60,
                 config=OpenrRouterConfig,
                 link=IPLink,
                 intf=IPIntf,
                 switch=OVSSwitch,
                 ipBase=u'10.0.0.0/9',
                 ip6Base=u'fd00:0:0::0/49',
                 max_v6_prefixlen=96,
                 *args, **kwargs):
        if not komondor_config_dir:
            if topo:
                komondor_config_dir = topo.komondor_config_dir()
        if not sub6ghz_emulator:
            sub6ghz_emulator = Sub6GhzEmulator(
                net=self,
                komondor_config_dir=komondor_config_dir)
        self.sub6ghz_emulator = sub6ghz_emulator
        super().__init__(topo=topo,
                         router=router,
                         config=config,
                         link=link,
                         intf=intf,
                         switch=switch,
                         *args, **kwargs)

    def build(self):
        super().build()
        for node in self.wifi_nodes():
            node.register_sub6ghz_emulator(self.sub6ghz_emulator)
        if not self.sub6ghz_emulator.build_komondor():
            self.sub6ghz_emulator = None

        if self.sub6ghz_emulator:
            self.sub6ghz_emulator.apply_wifi_config()

        CustomerstatsContinuousQueries.drop_cqs()
        SwitchstatsContinuousQueries.drop_cqs()
        CustomerstatsContinuousQueries.create_cqs()
        SwitchstatsContinuousQueries.create_cqs()

    def start(self):
        super().start()
        self.start_iperf_hosts()

    def stop(self):
        super().stop()
        CustomerstatsContinuousQueries.drop_cqs()
        SwitchstatsContinuousQueries.drop_cqs()

    def start_iperf_hosts(self):
        # resolve iperf server addresses
        iperf_server_names = [x.name for x in self.get_iperf_servers()]
        for iperf_client in self.get_iperf_clients():
            if iperf_client.host in iperf_server_names:
                iperf_server = self[iperf_client.host]
                iperf_server_ip = iperf_server.intfList()[0].ip6
                iperf_client.host = iperf_server_ip

        # autostart iperf host if enabled
        for iperf_host in self.get_iperf_hosts():
            if iperf_host.autostart:
                if iperf_host.autostart_params:
                    iperf_host.run_iperf(iperf_host.autostart_params)
                else:
                    iperf_host.run_iperf()

    def terranet_routers(self):
        return list(filter(lambda x: isinstance(x, TerranetRouter),
                           self.routers))

    def client_nodes(self):
        return list(filter(lambda x: isinstance(x, ClientNode),
                           self.terranet_routers()))

    def distribution_nodes(self):
        return [x for x in self.terranet_routers()
                    if isinstance(x, DistributionNode)]

    def distribution_nodes_60(self):
        return list(filter(lambda x: isinstance(x, DistributionNode60),
                           self.terranet_routers()))

    def distribution_nodes_5_60(self):
        return list(filter(lambda x: isinstance(x, DistributionNode5_60),
                           self.terranet_routers()))

    def wifi_nodes(self):
        return list(filter(lambda x: isinstance(x, WifiNode),
                           self.terranet_routers()))

    def access_points(self):
        return list(filter(lambda x: isinstance(x, WifiAccessPoint),
                           self.terranet_routers()))

    def stations(self):
        return list(filter(lambda x: isinstance(x, WifiStation),
                           self.terranet_routers()))

    def get_nodes_by_komondor_setting(self, key, value):
        return list(filter(lambda x: x.komondor_config[key] == value,
                           self.terranet_routers()))

    def connected_wifi_nodes(self, distribution_node_5_60):
        connectionsTo()
        wlan_code = distribution_node_5_60.komondor_config["wlan_code"]
        nodes_with_wlan_code = self.get_nodes_by_komondor_setting(
                                        "wlan_code", wlan_code)
        return list(filter(lambda x: isinstance(x, ClientNode),
                           nodes_with_wlan_code))

    def get_iperf_hosts(self):
        return list(filter(lambda x: isinstance(x, IperfHost),
                           self.hosts))

    def get_iperf_clients(self):
        return list(filter(lambda x: isinstance(x, IperfClient),
                           self.hosts))

    def get_iperf_servers(self):
        return list(filter(lambda x: isinstance(x, IperfServer),
                           self.hosts))
