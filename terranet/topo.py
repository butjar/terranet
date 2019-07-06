from ipmininet.iptopo import IPTopo

from node import CN, DN60, DN5_60
from link import Wifi5GHzLink, Wifi60GHzLink

class Terratopo(IPTopo):
    def __init__(self, *args, **kwargs):
        super(Terratopo, self).__init__(*args, **kwargs)

    def addCN(self, name, **opts):
        return super(Terratopo, self).addRouter(name, isCN=True, cls=CN,
                                                **opts)

    def addDN60(self, name, **opts):
        return super(Terratopo, self).addRouter(name, isDN60=True, cls=DN60,
                                                **opts)

    def addDN5_60(self, name, **opts):
        return super(Terratopo, self).addRouter(name, isDN5_60=True,
                                                cls=DN5_60, **opts)

    def isCN(self, node):
        return self.isNodeType(node, 'isCN')

    def isDN5_60(self, node):
        return self.isNodeType(node, 'isDN5_60')

    def isDN5_60(self, node):
        return self.isNodeType(node, 'isDN60')

    def cns(self, sort=True):
        return filter(self.isCN, self.nodes(sort))

    def dns(self, sort=True):
        return self.dn5_60s(sort=sort) + self.dn60s(sort=sort)

    def dn5_60s(self, sort=True):
        return filter(self.isDN5_60, self.nodes(sort))

    def dn60s(self, sort=True):
        return filter(self.isDN60, self.nodes(sort))

    def terranodes(self, sort=True):
        return cns(sort=sort) + dns(sort=sort)

