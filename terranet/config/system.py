from terranet.config.configabc import ConfigABC

class System(ConfigABC):
    def __init__(self, name="System"):
        self._name = name
        self._num_channels = 8
        self._basic_channel_bandwidth = 20
        self._pdf_backoff = 0
        self._pdf_tx_time = 1
        self._packet_length = 12000
        self._num_packets_aggregated = 64
        self._path_loss_model_default = 5
        self._path_loss_model_indoor_indoor = 5
        self._path_loss_model_indoor_outdoor = 8
        self._path_loss_model_outdoor_outdoor = 7
        self._capture_effect = 20
        self._noise_level = -95
        self._adjacent_channel_model = 0
        self._collisions_model = 0
        self._constant_PER = 0
        self._traffic_model = 99
        self._backoff_type = 1
        self._cw_adaptation = False
        self._pifs_activated = False
        self._capture_effect_model = 1

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
    def constant_PER(self):
        return self._constant_PER

    @constant_PER.setter
    def constant_PER(self, constant_PER):
        self._constant_PER = int(constant_PER)

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
        self._cw_adaptation = self.__class__ \
                                  .__parse_bool(cw_adaptation)

    @property
    def pifs_activated(self):
        return self._pifs_activated

    @pifs_activated.setter
    def pifs_activated(self, pifs_activated):
        self._pifs_activated = self.__class__ \
                                   .__parse_bool(pifs_activated)

    @property
    def capture_effect_model(self):
        return self._capture_effect_model

    @capture_effect_model.setter
    def capture_effect_model(self, capture_effect_model):
        self._capture_effect_model = int(capture_effect_model)

    @staticmethod
    def __parse_bool(arg):
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
