from ipmininet.iptopo import IPTopo
from .router_config import OpenrConfig, TerranetRouterDescription

from .node import (ClientNode, DistributionNode60, DistributionNode5_60,
                   Gateway, IperfDownloadClient, IperfDownloadServer)
from .link import Wifi5GHzLink, Wifi60GHzLink


class Terratopo(IPTopo):
    def __init__(self, *args, **kwargs):
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

    def add_iperf_download_client(self, name, server_name=None, **opts):
        return self.addHost(name, cls=IperfDownloadClient,
                            server_name=server_name, **opts)

    def add_iperf_download_server(self, name, **opts):
        return self.addHost(name, cls=IperfDownloadServer, **opts)

    def is_client_node(self, node):
        return self.isNodeType(node, 'is_client_node')

    def is_distribution_node_5_60(self, node):
        return self.isNodeType(node, 'is_distribution_node_5_60')

    def is_distribution_node_60(self, node):
        return self.isNodeType(node, 'is_distribution_node_60')

    def client_nodes(self, sort=True):
        return filter(self.is_client_node, self.nodes(sort))

    def distribution_nodes(self, sort=True):
        return (self.distribution_nodes_5_60(sort=sort) +
                self.distribution_nodes_60(sort=sort))

    def distribution_nodes_5_60(self, sort=True):
        return filter(self.is_distribution_node_5_60, self.nodes(sort))

    def distribution_nodes_60(self, sort=True):
        return filter(self.is_distribution_node_60, self.nodes(sort))

    def terranodes(self, sort=True):
        return client_nodes(sort=sort) + distribution_nodes(sort=sort)
