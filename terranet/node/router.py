from ipmininet.router import OpenrRouter
from ipmininet.router.config import OpenrConfig

class TerranetRouter(OpenrRouter):
    def __init__(self, name,
                 config=OpenrConfig,
                 lo_addresses=(),
                 *args, **kwargs):
        super().__init__(name,
                         config=config,
                         lo_addresses=lo_addresses,
                         *args, **kwargs)
