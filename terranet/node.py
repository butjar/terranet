import threading
from threading import Thread
from ipmininet.router import Router, ProcessHelper

from mininet.node import Host, OVSBridge

from .router_config import OpenrConfig
from .config_api import ConfigAPI

import netns

class Terranode(Router):
    def __init__(self,
                 name,
                 config=OpenrConfig,
                 komondor_config=None,
                 cwd='/tmp',
                 process_manager=ProcessHelper,
                 use_v4=True,
                 use_v6=True,
                 password=None,
                 *args, **kwargs):
        self._komondor_config = komondor_config
        self.has_changed = False
        super(Terranode, self).__init__(name,
                                        config=config,
                                        cwd=cwd,
                                        process_manager=process_manager,
                                        use_v4=use_v4,
                                        use_v6=use_v6,
                                        password=password,
                                        *args, **kwargs)

    @property
    def komondor_config(self):
        return self._komondor_config

    def update_komondor_config(self, config_dict):
        self._komondor_config.update(config_dict)
        evt = KomondorConfigChangeEvent(self, config_dict)
        self.notify_fronthaulemulator(evt)
        return (evt.result, evt.message)

    def register_fronthaulemulator(self, fronthaulemulator):
        self.fronthaulemulator = fronthaulemulator
        evt = FronthaulEmulatorRegistrationEvent(self)
        self.notify_fronthaulemulator(evt)
        return (evt.result, evt.message)

    def unregister_fronthaulemulator(self):
        self.fronthaulemulator = None
        evt = FronthaulEmulatorCancelRegistrationEvent(self)
        self.notify_fronthaulemulator(evt)
        return (evt.result, evt.message)

    def clear_changed(self):
        self.has_changed = False

    def notify_fronthaulemulator(self, evt, wait=True):
        self.has_changed = True
        if self.fronthaulemulator:
            self.fronthaulemulator.update(evt)
        if wait:
            evt.wait()
        self.clear_changed()


class CN(Terranode):
    def __init__(self,
                 name,
                 config=OpenrConfig,
                 komondor_config=None,
                 *args, **kwargs):
        super(CN, self).__init__(name,
                                   config=config,
                                   komondor_config=komondor_config,
                                   *args, **kwargs)


class DN60(Terranode):
    def __init__(self,
                 name,
                 config=OpenrConfig,
                 komondor_config=None,
                 *args, **kwargs):
        super(DN60, self).__init__(name,
                                   config=config,
                                   komondor_config=komondor_config,
                                   *args, **kwargs)


class DN5_60(Terranode):
    def __init__(self,
                 name,
                 config=OpenrConfig,
                 komondor_config=None,
                 fronthaulemulator=None,
                 *args, **kwargs):
        self.fronthaulemulator = fronthaulemulator
        super(DN5_60, self).__init__(name,
                                     config=config,
                                     komondor_config=komondor_config,
                                     *args, **kwargs)
        self.run_config_api_thread()

    def run_config_api_thread(self):
        nspid = self.pid
        with netns.NetNS(nspid=nspid):
            api = ConfigAPI(self.name, self)
            kwargs = { "host": "::",
                       "port": 80 }
            api_thread = Thread(target=api.run, kwargs=kwargs)
            api_thread.daemon=True
            api_thread.start()

    def get_channel_config(self):
        channel_cfg = None
        if self.komondor_config:
            primary_channel = self.komondor_config["primary_channel"]
            min_channel_allowed = self.komondor_config["min_channel_allowed"]
            max_channel_allowed = self.komondor_config["max_channel_allowed"]
            channel_cfg = { "primary_channel": primary_channel,
                            "min_channel_allowed": min_channel_allowed,
                            "max_channel_allowed": max_channel_allowed }
        return channel_cfg

    def switch_channel(self,
                       primary_channel,
                       min_channel_allowed,
                       max_channel_allowed):
        old_channel_cfg = self.get_channel_config()
        new_channel_cfg = {"primary_channel": primary_channel,
                           "min_channel_allowed": min_channel_allowed,
                           "max_channel_allowed": max_channel_allowed}
        self.update_komondor_config(new_channel_cfg)
        evt = ChannelSwitchEvent(self,
                                 old_channel_cfg,
                                 new_channel_cfg)
        self.notify_fronthaulemulator(evt)
        return (evt.result, evt.message)


class Gateway(OVSBridge):
    def __init__(self, name, **params):
        super(Gateway, self).__init__(name, **params)


class TerranetEvent(object):
    def __init__(self, cls=threading.Event):
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
    def __init__(self,
                 node,
                 update):
        self.node = node
        self.update = update
        super(KomondorConfigChangeEvent, self).__init__()


class ChannelSwitchEvent(TerranetEvent):
    def __init__(self,
                 node,
                 old_channel_config,
                 new_channel_config):
        self.node = node
        self.old_channel_config = old_channel_config
        self.new_channel_config = new_channel_config
        super(ChannelSwitchEvent, self).__init__()


class FronthaulEmulatorRegistrationEvent(TerranetEvent):
    def __init__(self,
                 node):
        self.node = node
        super(FronthaulEmulatorRegistrationEvent, self).__init__()


class FronthaulEmulatorCancelRegistrationEvent(TerranetEvent):
    def __init__(self,
                 node):
        self.node = node
        super(FronthaulEmulatorCancelRegistrationEvent, self).__init__()

