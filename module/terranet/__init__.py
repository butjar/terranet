# coding=utf-8

import ipmininet.ipnet
import ipmininet.iptopo
import ipmininet.router.config as ipcfg
import ipmininet.utils

from .node import TerraNetClient, TerraNetGateway, DistributionNode, ClientNode, FronthaulEmulator

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

                topo.addLink(ap_name, sta_name)  # TODO: Add Link cls

                if 'clients' in sta:
                    for i in range(1, sta['clients'] + 1):
                        client_name = sta_name + '_C%d' % i
                        topo.addHost(client_name, cls=TerraNetClient,
                                     pos=(float(sta['x']) + ((i - 1) * 8), float(sta['y']) + 5 + ((i - 1) * 3)))
                        topo.addLink(sta_name, client_name)  # Unlimited link

        if 'gateway' in network:  # aka. MysteryBox™
            gw = network['gateway']
            topo.addRouter('gw', cls=TerraNetGateway, dev='enp0s3', config=OpenrConfig,
                           pos=(float(gw['x']), float(gw['y'])),
                           privateDirs=['/tmp', '/var/log'])  # Gateway -- Not a DN

        if 'backhaul_links' in network:
            for l in network['backhaul_links']:
                src = 'AP_{}'.format(l[0]) if l[0] != 'gw' else 'gw'
                dst = 'AP_{}'.format(l[1]) if l[1] != 'gw' else 'gw'
                topo.addLink(src, dst)  # TODO: Add Link cls ---> Make link to gateway unlimited
        else:
            raise ValueError('No backhaul links set in network!!')

        return topo

    @classmethod
    def from_komondor_config(cls, cfg, fh_emulator):
        topo = cls()
        prev = None
        for ap in cfg.get_access_points():
            topo.addRouter(ap.short(), cls=DistributionNode, fronthaul_emulator=fh_emulator, wlan=ap.wlan_code,
                           pos=(float(ap.x), float(ap.y)),
                           config=OpenrConfig, privateDirs=['/tmp', '/var/log'])

            if prev is not None:
                topo.addLink(prev.short(), ap.short())

            for sta in filter(lambda s: s.wlan_code == ap.wlan_code, cfg.get_stations()):
                topo.addRouter(sta.short(), cls=ClientNode, pos=(float(sta.x), float(sta.y)), config=OpenrConfig,
                               privateDirs=['/tmp', '/var/log'])
                topo.addLink(ap.short(), sta.short())

                num_clients = 1  # TODO  For now every station gets three clients, make this configurable
                for i in range(1, num_clients + 1):
                    client_name = sta.short() + '_C%d' % i
                    topo.addHost(client_name, cls=TerraNetClient,
                                 pos=(float(sta.x) + ((i - 1) * 8), float(sta.y) + 5 + ((i - 1) * 3)))
                    topo.addLink(sta.short(), client_name)

            prev = ap

        # TODO Gateway + Controller instance.
        # --> idea: take an external intf and drag it into gw namespace. Then make gw a NAT node
        # Problems: no IPv6 at TUB :_( + IPv4 Routing screwed up in OpenR
        topo.addRouter('gw', cls=TerraNetGateway, dev='enp0s3', config=OpenrConfig,
                       pos=(float(prev.x) + 20, float(prev.y)),
                       privateDirs=['/tmp', '/var/log'])  # Gateway -- Not a DN
        topo.addLink(prev.short(), 'gw')

        return topo


class TerraNet(ipmininet.ipnet.IPNet):
    def start(self):
        super(TerraNet, self).start()
        for client in filter(lambda h: isinstance(h, TerraNetClient), self.hosts):
            client.start()


def draw_network(net, path):
    g = net.topo.convertTo(networkx.MultiGraph)
    positions = {}
    color = {}
    matplotlib.pyplot.switch_backend('agg')
    for name in net:
        n = net[name]
        positions[n.name] = n.pos
        if isinstance(n, TerraNetClient):
            color[n.name] = 'g'
        elif isinstance(n, ClientNode):
            color[n.name] = 'orange'
        else:
            color[n.name] = 'r'

    nodelist = g.nodes()
    colorlist = list(map(lambda n: color[n], nodelist))

    networkx.draw(g, pos=positions, nodelist=nodelist, node_color=colorlist, node_size=1e3, with_labels=True)
    matplotlib.pyplot.savefig(path)
