from __future__ import print_function
from future.utils import with_metaclass
from future.standard_library import install_aliases
install_aliases()

from abc import ABCMeta
import itertools as it
import copy
from configparser import ConfigParser


'''
FIXME: If constructed by us, all attributes have the right types but if we read a config from file
all attributes are suddenly strings because configparser does not know the types.
Could be fixed by casting in the constructor.
'''
class ConfigABC(with_metaclass(ABCMeta)):
    @classmethod
    def from_config(cls, name, cfg):
        return cls(name=name, **dict(cfg))


    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v))
        return result


class System(ConfigABC):
    def __init__(self, name="System", num_channels=8,
                 basic_channel_bandwidth=20, pdf_backoff=0, pdf_tx_time=1,
                 packet_length=12000, num_packets_aggregated=64,
                 path_loss_model_default=5, path_loss_model_indoor_indoor=5,
                 path_loss_model_indoor_outdoor=8,
                 path_loss_model_outdoor_outdoor=7, capture_effect=20,
                 noise_level=-95, adjacent_channel_model=0, collisions_model=0,
                 constant_per=0, traffic_model=99, backoff_type=0,
                 cw_adaptation=1, pifs_activated=0, capture_effect_model=1):
        self.name = name
        self.num_channels = num_channels
        self.basic_channel_bandwidth = basic_channel_bandwidth
        self.pdf_backoff = pdf_backoff
        self.pdf_tx_time = pdf_tx_time
        self.packet_length = packet_length
        self.num_packets_aggregated = num_packets_aggregated
        self.path_loss_model_default = path_loss_model_default
        self.path_loss_model_indoor_indoor = path_loss_model_indoor_indoor
        self.path_loss_model_indoor_outdoor = path_loss_model_indoor_outdoor
        self.path_loss_model_outdoor_outdoor = path_loss_model_outdoor_outdoor
        self.capture_effect = capture_effect
        self.noise_level = noise_level
        self.adjacent_channel_model = adjacent_channel_model
        self.collisions_model = collisions_model
        self.constant_per = constant_per
        self.traffic_model = traffic_model
        self.backoff_type = backoff_type
        self.cw_adaptation = cw_adaptation
        self.pifs_activated = pifs_activated
        self.capture_effect_model = capture_effect_model

    def __eq__(self, other):
        # NOTE: This should really be done explicitly. But I'm lazy...
        # TODO: One should implement __hash__ if he overrides __eq__
        for a in self.__dict__:
            if a not in other.__dict__:
                return False
            if self.__dict__[a] != other.__dict__[a]:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v))
        return result


class Config(object):
    def __init__(self, configparser=None, system=None, nodes=None):
        self.configparser = configparser if configparser is not None else ConfigParser()
        self.system = system if system is not None else System()
        self.nodes = nodes if nodes is not None else []

    @classmethod
    def from_file(cls, filenames):
        cfg = cls()
        cfg.configparser.read(filenames)
        cfg.build()
        cfg.configparser = None
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

    def __eq__(self, other):
        if not self.system == other.system:
            return False

        my_nodes = sorted(self.nodes, key=lambda n: n.name)
        other_nodes = sorted(other.nodes, key=lambda n: n.name)

        if len(my_nodes) != len(other_nodes):
            return False

        comp_vec = map(lambda n: n[0] == n[1], zip(my_nodes, other_nodes))
        return not False in comp_vec

    def __ne__(self, other):
        return not self.__eq__(other)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            if k == 'configparser':
                setattr(result, k, None)
                continue
            setattr(result, k, copy.deepcopy(v))
        return result



class Node(ConfigABC):
    def __init__(self, name=None, type=0, wlan_code="A", destination_id=-1,
                 x=0, y=0, z=0, primary_channel=0, min_channel_allowed=0,
                 max_channel_allowed=7, cw=16, cw_stage=5, tpc_min=30,
                 tpc_default=30, tpc_max=30, cca_min=-82, cca_default=-82,
                 cca_max=-82, tx_antenna_gain=0, rx_antenna_gain=0,
                 channel_bonding_model=1, modulation_default=0, central_freq=5,
                 lam=10000, ieee_protocol=1, traffic_load=1000,
                 node_env="outdoor"):
        self.name = name
        self.type = type
        self.wlan_code = wlan_code
        self.destination_id = destination_id
        self.x = x
        self.y = y
        self.z = z
        self.primary_channel = primary_channel
        self.min_channel_allowed = min_channel_allowed
        self.max_channel_allowed = max_channel_allowed
        self.cw = cw
        self.cw_stage = cw_stage
        self.tpc_min = tpc_min
        self.tpc_default = tpc_default
        self.tpc_max = tpc_max
        self.cca_min = cca_min
        self.cca_default = cca_default
        self.cca_max = cca_max
        self.tx_antenna_gain = tx_antenna_gain
        self.rx_antenna_gain = rx_antenna_gain
        self.channel_bonding_model = channel_bonding_model
        self.modulation_default = modulation_default
        self.central_freq = central_freq
        self.lam = lam
        self.ieee_protocol = ieee_protocol
        self.traffic_load = traffic_load
        self.node_env = node_env

    def short(self):
        return self.name.split('Node_')[1] if self.name.startswith('Node_') else self.name

    @classmethod
    def factory(cls, name, cfg):
        if cfg["type"] == "0":
            return AccessPoint.from_config(name, cfg)
        elif cfg["type"] == "1":
            return Station.from_config(name, cfg)
        else:
            raise ValueError("Unknown node type {}".format(cfg["type"]))

    @classmethod
    def from_config(cls, name, cfg):
        if "lambda" in cfg:
            cfg["lam"] = cfg.pop("lambda")
        return super(Node, cls).from_config(name, cfg)

    def is_ap(self):
        return self.type == 0

    def is_sta(self):
        return self.type == 1

    def __eq__(self, other):
        # NOTE: This should really be done explicitly. But I'm lazy...
        # TODO: One should implement __hash__ if he overrides __eq__
       #NOTE: Simple hack for now
        if (int(self.min_channel_allowed) == int(other.min_channel_allowed) and int(self.max_channel_allowed) == int(other.max_channel_allowed)):
            return True
        else:
            return False


        for a in self.__dict__.keys():
            if a not in other.__dict__:
                return False
            if self.__dict__[a] != other.__dict__[a]:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v))
        return result


class AccessPoint(Node):
    def __init__(self, name=None, type=0, **kwargs):
        super(AccessPoint, self).__init__(name=name, type=type, **kwargs)

class Station(Node):
    def __init__(self, name=None, type=1, num_clients=3, throughput=None,
                 delay=None, wlan=0, **kwargs):
        self.num_clients = num_clients
        self.throughput = throughput
        self.delay = delay
        self.wlan = wlan
        super(Station, self).__init__(name=name, type=type, **kwargs)