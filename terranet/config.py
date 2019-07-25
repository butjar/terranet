import itertools
from configparser import ConfigParser


class KomondorBaseConfig(ConfigParser):
    def __init__(self,
                 cfg_file=None,
                 **kwargs):
        super(KomondorBaseConfig, self).__init__(**kwargs)
        self.cfg_file = cfg_file
        if self.cfg_file:
            self.read(cfg_file)

    def filter_sections_by_value(self, key, value):
        sections = filter(lambda x: key in self[x] and self[x][key] == value,
                          self.sections())
        return map(lambda x: self[x], sections)

    def nodes(self):
        sections = filter(lambda x: not x == "System", self.sections())


class KomondorConfig(KomondorBaseConfig):
    def __init__(self, cfg_file=None):
        super(KomondorConfig, self).__init__(cfg_file=cfg_file)

    def system(self):
        return self["System"]

    def access_points(self):
        return self.filter_sections_by_value("type", "0")

    def stations(self):
        return self.filter_sections_by_value("type", "1")

    def nodes_by_wlan_code(self, wlan_code):
        return self.filter_sections_by_value("wlan_code", wlan_code)

    def get_stations_by_access_point(self, ap):
        return filter(lambda x: x["type"] == "1",
                      self.nodes_by_wlan_code(ap["wlan_code"]))

    def wifi5_links_for_access_point(self, ap):
        return [(ap.name, sta.name)
                for sta in self.get_stations_by_access_point(ap)]

    def wifi5GHz_links(self):
        return reduce(lambda x, y: x + self.wifi5_links_for_access_point(y),
                      self.access_points(), [])

    def wifi60GHz_links(self):
        aps = map(lambda x: x.name,
                  self.sort_west_to_east(self.access_points()))
        return [(aps[i], aps[i+1]) for i, _ in enumerate(aps)
                if i+1 < len(aps)]

    def sort_west_to_east(self, nodes):
        return sorted(nodes, key=lambda x: x["x"])


class KomondorResult(KomondorBaseConfig):
    def __init__(self, cfg_file=None):
        super(KomondorResult, self).__init__(cfg_file=cfg_file)
