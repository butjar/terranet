from mininet.link import TCIntf, TCLink

class Terralink(TCLink):
    def __init__(self,
                 node1,
                 node2,
                 intf=TCIntf,
                 *args, **kwargs):
        super(Terralink, self).__init__(node1=node1, node2=node2,
                                        intf=intf, *args, **kwargs)


class Wifi60GHzLink(Terralink):
    def __init__(self,
                 node1,
                 node2,
                 intf=TCIntf,
                 *args, **kwargs):
        super(Wifi60GHzLink, self).__init__(node1=node1, node2=node2,
                                            intf=intf, *args, **kwargs)


class Wifi5GHzLink(Terralink):
    def __init__(self,
                 node1,
                 node2,
                 intf=TCIntf,
                 *args, **kwargs):
        super(Wifi5GHzLink, self).__init__(node1=node1, node2=node2,
                                           intf=intf, *args, **kwargs)

