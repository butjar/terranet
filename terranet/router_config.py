from ipmininet.router.config import OpenrRouterConfig
from ipmininet.node_description import OpenrRouterDescription


class TerranetRouterDescription(OpenrRouterDescription):
    def __new__(cls, value, *args, **kwargs):
        return super(TerranetRouterDescription, cls).__new__(cls, value,
                                                             *args, **kwargs)

    def __init__(self, o, topo):
        self.topo = topo
        super(TerranetRouterDescription, self).__init__(o, topo)

    def addDaemon(self, daemon, default_cfg_class=OpenrRouterConfig,
                  **daemon_params):
        self.topo.addDaemon(self, daemon, default_cfg_class=default_cfg_class,
                            **daemon_params)
