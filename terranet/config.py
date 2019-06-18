from __future__ import print_function
from future.utils import with_metaclass
from future.standard_library import install_aliases
install_aliases()

import sys
from abc import ABCMeta, abstractproperty
import itertools as it
from configparser import ConfigParser


class ConfigABC(with_metaclass(ABCMeta)):
    def getName(self):
        return self._name

    def setName(self, name):
        self._name = name

    name = abstractproperty(getName, setName)

    @classmethod
    def from_config(cls, name, cfg):
        return cls(name=name, **dict(cfg))


class System(ConfigABC):
    def __init__(self, name="System", num_channels=8,
            basic_channel_bandwidth=20, pdf_backoff=0, pdf_tx_time=1,
            packet_length=12000, num_packets_aggregated=64,
            path_loss_model_default=5, path_loss_model_indoor_indoor=5,
            path_loss_model_indoor_outdoor=8,
            path_loss_model_outdoor_outdoor=7, capture_effect=20,
            noise_level=-95, adjacent_channel_model=0, collisions_model=0,
            constant_per=0, traffic_model=99, backoff_type=1,
            cw_adaptation=False, pifs_activated=False, capture_effect_model=1):
        self._name = name
        self._num_channels = num_channels
        self._basic_channel_bandwidth = basic_channel_bandwidth
        self._pdf_backoff = pdf_backoff
        self._pdf_tx_time = pdf_tx_time
        self._packet_length = packet_length
        self._num_packets_aggregated = num_packets_aggregated
        self._path_loss_model_default = path_loss_model_default
        self._path_loss_model_indoor_indoor = path_loss_model_indoor_indoor
        self._path_loss_model_indoor_outdoor = path_loss_model_indoor_outdoor
        self._path_loss_model_outdoor_outdoor = path_loss_model_outdoor_outdoor
        self._capture_effect = capture_effect
        self._noise_level = noise_level
        self._adjacent_channel_model = adjacent_channel_model
        self._collisions_model = collisions_model
        self._constant_per = constant_per
        self._traffic_model = traffic_model
        self._backoff_type = backoff_type
        self._cw_adaptation = int(self.__class__ \
                                      .__parse_bool(cw_adaptation))
        self._pifs_activated = int(self.__class__ \
                                       .__parse_bool(pifs_activated))
        self._capture_effect_model = capture_effect_model

    @property
    def name(self):
        return super(System, self).name

    @name.setter
    def name(self, name):
        return super(System, self).name.fset(self, name)

    @property
    def num_channels(self):
        return self._num_channels

    @num_channels.setter
    def num_channels(self, num_channels):
        self._num_channels = int(num_channels)

    @property
    def basic_channel_bandwidth(self):
        return self._basic_channel_bandwidth

    @basic_channel_bandwidth.setter
    def basic_channel_bandwidth(self, basic_channel_bandwidth):
        self._basic_channel_bandwidth = int(basic_channel_bandwidth)

    @property
    def pdf_backoff(self):
        return self._pdf_backoff

    @pdf_backoff.setter
    def pdf_backoff(self, pdf_backoff):
        self._pdf_backoff = int(pdf_backoff)

    @property
    def pdf_tx_time(self):
        return self._pdf_tx_time

    @pdf_tx_time.setter
    def pdf_tx_time(self, pdf_tx_time):
        self._pdf_tx_time = int(pdf_tx_time)

    @property
    def packet_length(self):
        return self._packet_length

    @packet_length.setter
    def packet_length(self, packet_length):
        self._packet_length = int(packet_length)

    @property
    def num_packets_aggregated(self):
        return self._num_packets_aggregated

    @num_packets_aggregated.setter
    def num_packets_aggregated(self, num_packets_aggregated):
        self._num_packets_aggregated = int(num_packets_aggregated)

    @property
    def path_loss_model_default(self):
        return self._path_loss_model_default

    @path_loss_model_default.setter
    def path_loss_model_default(self, path_loss_model_default):
        self._path_loss_model_default = int(path_loss_model_default)

    @property
    def path_loss_model_indoor_indoor(self):
        return self._path_loss_model_indoor_indoor

    @path_loss_model_indoor_indoor.setter
    def path_loss_model_indoor_indoor(self, path_loss_model):
        self._path_loss_model_indoor_indoor = int(path_loss_model)

    @property
    def path_loss_model_indoor_outdoor(self):
        return self._path_loss_model_indoor_outdoor

    @path_loss_model_indoor_outdoor.setter
    def path_loss_model_indoor_outdoor(self, path_loss_model):
        self._path_loss_model_indoor_outdoor = int(path_loss_model)

    @property
    def path_loss_model_outdoor_outdoor(self):
        return self._path_loss_model_outdoor_outdoor

    @path_loss_model_outdoor_outdoor.setter
    def path_loss_model_outdoor_outdoor(self, path_loss_model):
        self._path_loss_model_outdoor_outdoor = int(path_loss_model)

    @property
    def capture_effect(self):
        return self._capture_effect

    @capture_effect.setter
    def capture_effect(self, capture_effect):
        self._capture_effect = int(capture_effect)

    @property
    def noise_level(self):
        return self._noise_level

    @noise_level.setter
    def noise_level(self, noise_level):
        self._noise_level = int(noise_level)

    @property
    def adjacent_channel_model(self):
        return self._adjacent_channel_model

    @adjacent_channel_model.setter
    def adjacent_channel_model(self, adjacent_channel_model):
        self._adjacent_channel_model = int(adjacent_channel_model)

    @property
    def collisions_model(self):
        return self._collisions_model

    @collisions_model.setter
    def collisions_model(self, collisions_model):
        self._collisions_model = int(collisions_model)

    @property
    def constant_per(self):
        return self._constant_per

    @constant_per.setter
    def constant_per(self, constant_per):
        self._constant_per = int(constant_per)

    @property
    def traffic_model(self):
        return self._traffic_model

    @traffic_model.setter
    def traffic_model(self, traffic_model):
        self._traffic_model = int(traffic_model)

    @property
    def backoff_type(self):
        return self._backoff_type

    @backoff_type.setter
    def backoff_type(self, backoff_type):
        self._backoff_type = int(backoff_type)

    @property
    def cw_adaptation(self):
        return self._cw_adaptation

    @cw_adaptation.setter
    def cw_adaptation(self, cw_adaptation):
        self._cw_adaptation = int(self.__class__ \
                                      .__parse_bool(cw_adaptation))

    @property
    def pifs_activated(self):
        return self._pifs_activated

    @pifs_activated.setter
    def pifs_activated(self, pifs_activated):
        self._pifs_activated = int(self.__class__ \
                                       .__parse_bool(pifs_activated))

    @property
    def capture_effect_model(self):
        return self._capture_effect_model

    @capture_effect_model.setter
    def capture_effect_model(self, capture_effect_model):
        self._capture_effect_model = int(capture_effect_model)

    @staticmethod
    def __parse_bool(arg):
        if isinstance(arg, bool):
            return arg
        if isinstance(arg, str) or \
           isinstance(arg, unicode) or \
           isinstance(arg, bytes):
            if arg.lower() in ["false", "f"]:
                return False
            if arg.lower() in ["true", "t"]:
                return True
        if arg.isnumeric():
            return bool(int(arg))
        raise ValueError("Can not parse boolen from arg {}".format(arg))


class Config(object):
    def __init__(self, configparser=ConfigParser(), system=System(), nodes=[]):
        self.configparser = configparser
        self.system = system
        self.nodes = nodes

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


class Node(ConfigABC):
    def __init__(self, name=None, type=0, wlan_code="A", destination_id=-1,
                 x=0, y=0, z=0, primary_channel=0, min_channel_allowed=0,
                 max_channel_allowed=7, cw=16, cw_stage=5, tpc_min=30,
                 tpc_default=30, tpc_max=30, cca_min=-82, cca_default=-82,
                 cca_max=-82, tx_antenna_gain=0, rx_antenna_gain=0,
                 channel_bonding_model=1, modulation_default=0, central_freq=5,
                 lam=10000, ieee_protocol=1, traffic_load=1000,
                 node_env="outdoor"):
        self._name = name
        self._type = type
        self._wlan_code = wlan_code
        self._destination_id = destination_id
        self._x = x
        self._y = y
        self._z = z
        self._primary_channel = primary_channel
        self._min_channel_allowed = min_channel_allowed
        self._max_channel_allowed = max_channel_allowed
        self._cw = cw
        self._cw_stage = cw_stage
        self._tpc_min = tpc_min
        self._tpc_default = tpc_default
        self._tpc_max = tpc_max
        self._cca_min = cca_min
        self._cca_default = cca_default
        self._cca_max = cca_max
        self._tx_antenna_gain = tx_antenna_gain
        self._rx_antenna_gain = rx_antenna_gain
        self._channel_bonding_model = channel_bonding_model
        self._modulation_default = modulation_default
        self._central_freq = central_freq
        self._lam = lam
        self._ieee_protocol = ieee_protocol
        self._traffic_load = traffic_load
        self._node_env = node_env

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

    @property
    def name(self):
        return super(Node, self).name

    @name.setter
    def name(self, name):
        return super(Node, self).name.fset(self, name)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, node_type):
        self._type = int(node_type)

    @property
    def wlan_code(self):
        return self._wlan_code

    @wlan_code.setter
    def wlan_code(self, wlan_code):
        self._wlan_code = str(wlan_code)

    @property
    def destination_id(self):
        return self._destination_id

    @destination_id.setter
    def destination_id(self, destination_id):
        self._destination_id = int(destination_id)

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y):
        self._y = y

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, z):
        self._z = z

    @property
    def primary_channel(self):
        return self._primary_channel

    @primary_channel.setter
    def primary_channel(self, primary_channel):
        self._primary_channel = primary_channel

    @property
    def min_channel_allowed(self):
        return self._min_channel_allowed

    @min_channel_allowed.setter
    def min_channel_allowed(self, min_channel_allowed):
        self._min_channel_allowed = min_channel_allowed

    @property
    def max_channel_allowed(self):
        return self._max_channel_allowed

    @max_channel_allowed.setter
    def max_channel_allowed(self, max_channel_allowed):
        self._max_channel_allowed = max_channel_allowed

    @property
    def cw(self):
        return self._cw

    @cw.setter
    def cw(self, cw):
        self._cw = cw

    @property
    def cw_stage(self):
        return self._cw_stage

    @cw_stage.setter
    def cw_stage(self, cw_stage):
        self._cw_stage = cw_stage

    @property
    def tpc_min(self):
        return self._tpc_min

    @tpc_min.setter
    def tpc_min(self, tpc_min):
        self._tpc_min = tpc_min

    @property
    def tpc_default(self):
        return self._tpc_default

    @tpc_default.setter
    def tpc_default(self, tpc_default):
        self._tpc_default = tpc_default

    @property
    def tpc_max(self):
        return self._tpc_max

    @tpc_max.setter
    def tpc_max(self, tpc_max):
        self._tpc_max = tpc_max

    @property
    def cca_min(self):
        return self._cca_min

    @cca_min.setter
    def cca_min(self, cca_min):
        self._cca_min = cca_min

    @property
    def cca_default(self):
        return self._cca_default

    @cca_default.setter
    def cca_default(self, cca_default):
        self._cca_default = cca_default

    @property
    def cca_max(self):
        return self._cca_max

    @cca_max.setter
    def cca_max(self, cca_max):
        self._cca_max = cca_max

    @property
    def tx_antenna_gain(self):
        return self._tx_antenna_gain

    @tx_antenna_gain.setter
    def tx_antenna_gain(self, tx_antenna_gain):
        self._tx_antenna_gain = tx_antenna_gain

    @property
    def rx_antenna_gain(self):
        return self._rx_antenna_gain

    @rx_antenna_gain.setter
    def rx_antenna_gain(self, rx_antenna_gain):
        self._rx_antenna_gain = rx_antenna_gain

    @property
    def channel_bonding_model(self):
        return self._channel_bonding_model

    @channel_bonding_model.setter
    def channel_bonding_model(self, channel_bonding_model):
        self._channel_bonding_model = channel_bonding_model

    @property
    def modulation_default(self):
        return self._modulation_default

    @modulation_default.setter
    def modulation_default(self, modulation_default):
        self._modulation_default = modulation_default

    @property
    def central_freq(self):
        return self._central_freq

    @central_freq.setter
    def central_freq(self, central_freq):
        self._central_freq = central_freq

    @property
    def lam(self):
        return self._lam

    @lam.setter
    def lam(self, lam):
        self._lam = lam

    @property
    def ieee_protocol(self):
        return self._ieee_protocol

    @ieee_protocol.setter
    def ieee_protocol(self, ieee_protocol):
        self._ieee_protocol = ieee_protocol

    @property
    def traffic_load(self):
        return self._traffic_load

    @traffic_load.setter
    def traffic_load(self, traffic_load):
        self._traffic_load = traffic_load

    @property
    def node_env(self):
        return self._node_env

    @node_env.setter
    def node_env(self, node_env):
        self._node_env = node_env

    def is_ap(self):
        return self.type == 0

    def is_sta(self):
        return self.type == 1

class AccessPoint(Node):
    def __init__(self, name=None, type=0, **kwargs):
        super(AccessPoint, self).__init__(name=name, type=type, **kwargs)

class Station(Node):
    def __init__(self, name=None, type=1, **kwargs):
        super(Station, self).__init__(name=name, type=type, **kwargs)
