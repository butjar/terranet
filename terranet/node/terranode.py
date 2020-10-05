from mininet.log import info, warn
from mininet.node import OVSSwitch

from .router import TerranetRouter
from .wifi import WifiStation, ConfigurableWifiAccessPoint

class ClientNode(WifiStation):
    def __init__(self, name,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)


class DistributionNode60(TerranetRouter):
    def __init__(self, name,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)


class DistributionNode5_60(ConfigurableWifiAccessPoint):
    def __init__(self, name, ssid,
                 *args, **kwargs):
        super().__init__(name, ssid,
                         *args, **kwargs)


class Gateway(OVSSwitch):
    def __init__(self, name,
                 **params):
        super().__init__(name,
                         **params)
