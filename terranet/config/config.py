import itertools as it
from configparser import ConfigParser

from terranet.config.node import Node, AccessPoint, Station
from terranet.config.system import System

class Config(object):

    def __init__(self, configparser=ConfigParser()):
        self.configparser = configparser
        self.system = None
        self.nodes = None

    @classmethod
    def from_file(cls, path):
        cfg = cls()
        with open(path) as file:
            cfg.configparser.read_file(file)
        cfg.build()
        return cfg

    def build(self):
        system_config = self.configparser["System"]
        self.system = System.from_config("System", system_config)

        node_sections = list(
            it.filterfalse(lambda x: x == "System",
                           self.configparser.sections())
        )

        self.nodes = list(
            map(lambda x: Node.factory(x, self.configparser[x]), 
                node_sections)
        )

    def get_access_points(self):
        return list(
            filter(lambda x: isinstance(x, AccessPoint), self.nodes)
        )

    def get_stations(self):
        return list(
            filter(lambda x: isinstance(x, Station), self.nodes)
        )

    def get_links(self):
        links = []

        for ap in self.get_access_points():
            wlan_code = ap.wlan_code
            stas = list(
                filter(lambda x: x.wlan_code == wlan_code,
                       self.get_stations())
            )
            l = list(map(lambda x: (ap, x), stas))
            links += l

        return links
