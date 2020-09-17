import uuid
import itertools
from ipaddress import IPv4Network, IPv6Network

from ipmininet.link import IPLink
from ipmininet.iptopo import IPTopo
from .router_config import OpenrConfig, TerranetRouterDescription

from .node import (ClientNode, DistributionNode60, DistributionNode5_60,
                   Gateway, IperfReverseClient, IperfServer)
from .link import WifiLink, TerragraphLink
from .wifi.komondor_config import KomondorSystemConfig


class Terratopo(IPTopo):
    def __init__(self,
                 komondor_system_config=None,
                 *args, **kwargs):
        if not komondor_system_config:
            self.komondor_system_config = KomondorSystemConfig()
        super(Terratopo, self).__init__(*args, **kwargs)

    def addDaemon(self, router, daemon, default_cfg_class=OpenrConfig,
                  cfg_daemon_list="daemons", **daemon_params):
        super(Terratopo, self).addDaemon(router, daemon,
                                         default_cfg_class=default_cfg_class,
                                         cfg_daemon_list=cfg_daemon_list,
                                         **daemon_params)

    def addRouter(self, name, **kwargs):
        router = self.addNode(name, isRouter=True, **kwargs)
        return TerranetRouterDescription(router, self)

    def add_client_node(self, name, **opts):
        return self.addRouter(name, is_client_node=True, cls=ClientNode,
                              **opts)

    def add_distribution_node_60(self, name, **opts):
        return self.addRouter(name, is_distribution_node60=True,
                              cls=DistributionNode60, **opts)

    def add_distribution_node_5_60(self, name, **opts):
        return self.addRouter(name, is_distribution_node_5_60=True,
                              cls=DistributionNode5_60, **opts)

    def add_gateway(self, name, **opts):
        return self.addSwitch(name, cls=Gateway, **opts)

    def add_iperf_reverse_client(self, name, host=None, **opts):
        return self.addHost(name, cls=IperfReverseClient,
                            host=host, **opts)

    def add_iperf_server(self, name, **opts):
        return self.addHost(name, cls=IperfServer, **opts)

    def add_ip_link(self, node1, node2, *args, **kwargs):
        return self.addLink(node1, node2, cls=IPLink)

    def add_wifi_link(self, node1, node2, *args, **kwargs):
        return self.addLink(node1, node2, cls=WifiLink)

    def add_terragraph_link(self, node1, node2):
        return self.addLink(node1, node2, cls=TerragraphLink)

    def is_client_node(self, node):
        return self.isNodeType(node, 'is_client_node')

    def is_distribution_node_5_60(self, node):
        return self.isNodeType(node, 'is_distribution_node_5_60')

    def is_distribution_node_60(self, node):
        return self.isNodeType(node, 'is_distribution_node_60')

    def client_nodes(self, sort=True):
        return list(filter(self.is_client_node,
                           self.nodes(sort)))

    def distribution_nodes(self, sort=True):
        return (self.distribution_nodes_5_60(sort=sort) +
                self.distribution_nodes_60(sort=sort))

    def distribution_nodes_5_60(self, sort=True):
        return list(filter(self.is_distribution_node_5_60,
                           self.nodes(sort)))

    def distribution_nodes_60(self, sort=True):
        return list(filter(self.is_distribution_node_60,
                           self.nodes(sort)))

    def terranodes(self, sort=True):
        return client_nodes(sort=sort) + distribution_nodes(sort=sort)

    def _get_customer_ip(self, ip):
        cn_v4_net = IPv4Network(ip[0].decode('utf-8'), strict=False)
        customer_v4_net = next(
            itertools.islice(cn_v4_net.subnets(), 1, None))
        customer_v4_ip = "{netaddr}/{prefix}".format(
                netaddr=str(customer_v4_net.network_address),
                prefix=cn_v4_net.prefixlen)

        cn_v6_net = IPv6Network(ip[1].decode('utf-8'), strict=False)
        customer_v6_net = next(
            itertools.islice(cn_v6_net.subnets(), 1, None))
        customer_v6_ip = "{netaddr}/{prefix}".format(
                netaddr=str(customer_v6_net.network_address),
                prefix=cn_v6_net.prefixlen)
        return (customer_v4_ip, customer_v6_ip)

    def _get_ip(self, network,
                 cn_prefix4=24,
                 cpe_prefix4=16,
                 cn_prefix6=80,
                 cpe_prefix6=64):
        net4 = IPv4Network(network[0])
        cn4 =  "{}/{}".format(net4[1], cn_prefix4)
        cpe4 = "{}/{}".format(net4[2], cpe_prefix4)

        net6 = IPv6Network(network[1])
        cn6 = "{}/{}".format(net6[1], cn_prefix6)
        cpe6 = "{}/{}".format(net6[2], cpe_prefix6)
        return ((cn4, cn6), (cpe4, cpe6))

    def add_customer_flow(self,
                          cn,
                          gateway,
                          suffix=None,
                          client_prefix="h",
                          server_prefix="s",
                          network=("10.0.0.0/24",
                                   "fd00:0:0:8000:8000::0/80"),
                          autostart_client=False,
                          autostart_server=True,
                          *args, **kwargs):
        if not suffix:
            suffix_len = 10 - max(len(client_prefix), len(server_prefix))
            suffix = uuid.uuid4().hex[:suffix_len]
        cpe_name = "{}{}".format(client_prefix, suffix)
        server_name = "{}{}".format(server_prefix, suffix)
        cpe = self.add_iperf_reverse_client(cpe_name,
                                            server_name,
                                            autostart=autostart_client)
        link = self.add_wifi_link(cn, cpe)
        (cn_ip, cpe_ip) = self._get_ip(network)
        link[cn].addParams(ip=cn_ip)
        link[cpe].addParams(ip=cpe_ip)

        server = self.add_iperf_server(server_name,
                                       autostart=True)
        self.add_ip_link(gateway, server)
        return (cpe, server)
