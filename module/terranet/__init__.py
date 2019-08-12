# coding=utf-8

import ipmininet.ipnet
import ipmininet.iptopo
import ipmininet.router.config as ipcfg
import ipmininet.utils

from .node import TerraNetClient, TerraNetGateway, DistributionNode, ClientNode, FronthaulEmulator, g_subprocess_lock
from .link import TerraNetLink, TerraNetIntf
from ipmininet.cli import IPCLI

import networkx
import matplotlib.pyplot


class OpenrConfig(ipcfg.RouterConfig):
    """A simple config with only a OpenR daemon"""

    def __init__(self, node, *args, **kwargs):
        defaults = {
            "redistribute_ifaces": "lo",
            "iface_regex_include": ".*",
            "enable_v4": True
        }
        super(OpenrConfig, self).__init__(node,
                                          daemons=((ipcfg.Openr, defaults),),
                                          *args, **kwargs)


class TerraNetTopo(ipmininet.iptopo.IPTopo):
    @classmethod
    def from_network_dict(cls, network, fh_emulator):
        topo = cls()
        for n in network['networks']:
            ap_name = 'AP_{}'.format(n['wlan_code'])
            topo.addRouter(ap_name, cls=DistributionNode, fronthaul_emulator=fh_emulator, wlan=n['wlan_code'],
                           pos=(float(n['ap']['x']), float(n['ap']['y'])),
                           config=OpenrConfig, privateDirs=['/tmp', '/var/log'])

            for i, sta in enumerate(n['stas']):
                sta_name = 'STA_{}{}'.format(n['wlan_code'], i + 1)
                topo.addRouter(sta_name, cls=ClientNode, pos=(float(sta['x']), float(sta['y'])), config=OpenrConfig,
                               privateDirs=['/tmp', '/var/log'])

                topo.addLink(ap_name, sta_name, cls=TerraNetLink, intf=TerraNetIntf)

                if 'clients' in sta:
                    for i in range(1, sta['clients'] + 1):
                        client_name = sta_name + '_C%d' % i
                        topo.addHost(client_name, cls=TerraNetClient,
                                     pos=(float(sta['x']) + ((i - 1) * 8), float(sta['y']) + 5 + ((i - 1) * 3)))
                        topo.addLink(sta_name, client_name, cls=TerraNetLink, intf=TerraNetIntf)

        if 'gateway' in network:  # aka. MysteryBox™
            gw = network['gateway']
            topo.addRouter('gw', cls=TerraNetGateway, dev='enp0s3', config=OpenrConfig,
                           pos=(float(gw['x']), float(gw['y'])),
                           privateDirs=['/tmp', '/var/log'])  # Gateway -- Not a DN

        if 'backhaul_links' in network:
            for l in network['backhaul_links']:
                src = 'AP_{}'.format(l[0]) if l[0] != 'gw' else 'gw'
                dst = 'AP_{}'.format(l[1]) if l[1] != 'gw' else 'gw'
                topo.addLink(src, dst, cls=TerraNetLink, intf=TerraNetIntf)  # Link to gateway should be unlimited
        else:
            raise ValueError('No backhaul links set in network!!')

        return topo


class TerraNet(ipmininet.ipnet.IPNet):

    def start(self):
        super(TerraNet, self).start()
        for client in filter(lambda h: isinstance(h, TerraNetClient), self.hosts):
            client.start()

    def to_multigraph(self):
        g = networkx.MultiGraph()

        g.add_nodes_from(filter(lambda h: isinstance(h, DistributionNode), [self[name] for name in self]), color='r')
        g.add_nodes_from(filter(lambda h: isinstance(h, ClientNode), [self[name] for name in self]), color='orange')
        g.add_nodes_from(filter(lambda h: isinstance(h, TerraNetClient), [self[name] for name in self]), color='g')

        g.add_edges_from([(l.intf1.node, l.intf2.node) for l in self.links])
        return g

    def draw(self, path):
        g = self.to_multigraph()
        matplotlib.pyplot.switch_backend('agg')

        nodelist = g.nodes

        positions = {}
        for n in g.nodes:
            positions[n] = n.pos

        colorlist = map(lambda n: n[1]['color'] if 'color' in n[1] else 'b', g.nodes(data=True))

        networkx.draw(g, pos=positions, nodelist=nodelist, node_color=colorlist, node_size=1e3, with_labels=True)
        matplotlib.pyplot.savefig(path)

import threading
ip_lock = threading.Lock()
def address_pair(node):
    with ip_lock:
        '''
        Some explanation for this nonsense:
        address_pair() calls subprocess under the hood, which is not thread-safe under 2.7.
        We **should** secure it with the g_subprocess_lock but due to some unknown dependency
        this causes a deadlock. So we will just use a local lock and hope for the best for now.
        '''
        return ipmininet.utils.address_pair(node)

