from terranet.config.configabc import ConfigABC

class Node(ConfigABC):
    def __init__(self, name=None):
        self._name = name
        self._type = 0
        self._wlan_code = "A"
        self._destination_id = -1
        self._x = 0
        self._y = 0
        self._z = 0
        self._primary_channel = 0
        self._min_channel_allowed = 0
        self._max_channel_allowed = 7
        self._cw = 16
        self._cw_stage = 5
        self._tpc_min = 30
        self._tpc_default = 30
        self._tpc_max = 30
        self._cca_min = -82
        self._cca_default = -82
        self._cca_max = -82
        self._tx_antenna_gain = 0
        self._rx_antenna_gain = 0
        self._channel_bonding_model = 1
        self._modulation_default = 0
        self._central_freq = 5
        self._lam = 10000
        self._ieee_protocol = 1
        self._traffic_load = 1000
        self._node_env = "outdoor"

    @classmethod
    def factory(cls, name, cfg):
        if cfg["type"] == "0":
            return AccessPoint.from_config(name, cfg)
        elif cfg["type"] == "1":
            return Station.from_config(name, cfg)
        else:
            raise ValueError("Unknown node type {}".format(cfg["type"]))

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
    def __init__(self, name=None):
        super(AccessPoint, self).__init__(name=name)

class Station(Node):
    def __init__(self, name=None):
        super(Station, self).__init__(name=name)
