from ipmininet.router import OpenrRouter
from ipmininet.router.config import OpenrRouterConfig

class TerranetRouter(OpenrRouter):
    def __init__(self, name,
                 config=OpenrRouterConfig,
                 lo_addresses=(),
                 *args, **kwargs):
        super().__init__(name,
                         config=config,
                         lo_addresses=lo_addresses,
                         *args, **kwargs)
