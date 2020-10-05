from threading import Event


class TerranetEvent:
    def __init__(self, cls=Event):
        self._event = cls()
        self.result = None
        self.message = None

    @property
    def event(self):
        return self._event

    def is_set(self):
        return self._event.is_set()

    isSet = is_set

    def set(self):
        self._event.set()

    def clear(self):
        self._event.clear()

    def wait(self, timeout=None):
        self._event.wait(timeout=timeout)


class KomondorConfigChangeEvent(TerranetEvent):
    def __init__(self, node, update):
        self.node = node
        self.update = update
        super().__init__()


class ChannelSwitchEvent(TerranetEvent):
    def __init__(self, node,
                 old_channel_config,
                 new_channel_config):
        self.node = node
        self.old_channel_config = old_channel_config
        self.new_channel_config = new_channel_config
        super().__init__()


class FronthaulEmulatorRegistrationEvent(TerranetEvent):
    def __init__(self, node):
        self.node = node
        super().__init__()


class FronthaulEmulatorCancelRegistrationEvent(TerranetEvent):
    def __init__(self, node):
        self.node = node
        super().__init__()
