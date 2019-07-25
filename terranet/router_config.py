from ipmininet.router.config.base import RouterConfig
from ipmininet.router.config.openr import Openr
from ipmininet.iptopo import RouterDescription


class OpenrConfig(RouterConfig):
    """A simple config with only a OpenR daemon"""
    def __init__(self, node, *args, **kwargs):
        defaults = {
                     "redistribute_ifaces": "lo",
                     "iface_regex_include": ".*",
                     "enable_v4": True
                   }
        super(OpenrConfig, self).__init__(node,
                                          daemons=((Openr, defaults),),
                                          *args, **kwargs)


class TerranetRouterDescription(RouterDescription):
    def __new__(cls, value, *args, **kwargs):
        return super(TerranetRouterDescription, cls).__new__(cls, value,
                                                             *args, **kwargs)

    def __init__(self, o, topo):
        self.topo = topo
        super(TerranetRouterDescription, self).__init__(o, topo)

    def addDaemon(self, daemon, default_cfg_class=OpenrConfig,
                  **daemon_params):
        self.topo.addDaemon(self, daemon, default_cfg_class=default_cfg_class,
                            **daemon_params)
