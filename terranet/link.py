from mininet.link import TCIntf, TCLink
from ipmininet.link import IPIntf


class TerraIntf(TCIntf):
    def __init__(self, bwParamMax=10000, *args, **kwargs):
        self.bwParamMax = bwParamMax
        super(TerraIntf, self).__init__(*args, **kwargs)


class TerraLink(TCLink):
    def __init__(self,
                 node1,
                 node2,
                 intf=TerraIntf,
                 cls1=TerraIntf,
                 cls2=TerraIntf,
                 *args, **kwargs):
        super(TerraLink, self).__init__(node1, node2,
                                        intf=intf,
                                        cls1=cls1,
                                        cls2=cls2,
                                        *args, **kwargs)


class TerragraphLink(TerraLink):
    def __init__(self,
                 node1,
                 node2,
                 bw=3600,
                 params1={},
                 params2={},
                 *args, **kwargs):
        params1.update({"bw": bw, "use_tbf": True})
        params2.update({"bw": bw, "use_tbf": True})
        super(TerragraphLink, self).__init__(node1, node2,
                                             params1=params1,
                                             params2=params2,
                                             *args, **kwargs)


class WifiLink(TerraLink):
    def __init__(self,
                 node1,
                 node2,
                 *args, **kwargs):
        super(WifiLink, self).__init__(node1, node2,
                                       *args, **kwargs)
