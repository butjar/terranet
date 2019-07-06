from ipmininet.ipnet import IPNet
from fronthaulemulator import FronthaulEmulator
from link import Terralink
from node import Terranode, CN, DN60, DN5_60

class Terranet(IPNet):
    def __init__(self,
                 fronthaulemulator=FronthaulEmulator(),
                 link=Terralink,
                 system_config={},
                 *args, **kwargs):
        fronthaulemulator.net=self
        fronthaulemulator.system_config=system_config
        self.fronthaulemulator = fronthaulemulator
        super(Terranet, self).__init__(link=link,
                                       *args, **kwargs)

    def build(self):
        super(Terranet, self).build()
        for node in self.terranodes():
            node.register_fronthaulemulator(self.fronthaulemulator)
        self.fronthaulemulator.apply_network_config()


    def terranodes(self):
        return filter(lambda x: isinstance(x, Terranode),
                      self.routers)

    def cns(self):
        return filter(lambda x: isinstance(x, CN),
                      self.terranodes())

    def dns(self):
        return dn60s + dn5_60s

    def dn60s(self):
        return filter(lambda x: isinstance(x, DN60),
                      self.terranodes())

    def dn5_60s(self):
        return filter(lambda x: isinstance(x, DN5_60),
                      self.terranodes())

    def get_nodes_by_komondor_setting(self, key, value):
        return filter(lambda x: x.komondor_config[key] == value,
                      self.terranodes())

    def get_connected_cns(self, dn5_60):
        wlan_code = dn5_60.komondor_config["wlan_code"]
        nodes_with_wlan_code = self.get_nodes_by_komondor_setting("wlan_code",
                                                                  wlan_code)
        return filter(lambda x: isinstance(x, CN), nodes_with_wlan_code)

