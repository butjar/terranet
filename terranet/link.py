from mininet.link import TCIntf, TCLink


class Terralink(TCLink):
    def __init__(self,
                 node1,
                 node2,
                 intf=TCIntf,
                 *args, **kwargs):
        super(Terralink, self).__init__(node1=node1, node2=node2,
                                        intf=intf, *args, **kwargs)


class TerragraphLink(Terralink):
    def __init__(self,
                 node1,
                 node2,
                 intf=TCIntf,
                 *args, **kwargs):
        super(TerragraphLink, self).__init__(node1=node1, node2=node2,
                                             intf=intf, *args, **kwargs)


class WifiLink(Terralink):
    def __init__(self,
                 node1,
                 node2,
                 intf=TCIntf,
                 *args, **kwargs):
        super(WifiLink, self).__init__(node1=node1, node2=node2,
                                       intf=intf, *args, **kwargs)
