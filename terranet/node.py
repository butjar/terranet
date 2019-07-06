import threading
from ipmininet.router import Router, ProcessHelper
from ipmininet.router.config.base import RouterConfig
from .config_api import ConfigAPI

import netns

class OpenrConfig(RouterConfig):
    """A simple config with only a OpenR daemon"""
    def __init__(self, node, *args, **kwargs):
        defaults = {
                     "redistribute_ifaces": "lo",
                     "iface_regex_include": ".*",
                     "enable_v4": True
                   }

        super(OpenrConfig, self).__init__(node,
                                          daemons=((Openr, defaults),),
                                          *args, **kwargs)


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

    def register_fronthaulemulator(self, fronthaulemulator):
        self.fronthaulemulator = fronthaulemulator
        evt = FronthaulEmulatorRegistrationEvent(self)
        self.notify_fronthaulemulator(evt)

    def unregister_fronthaulemulator(self):
        self.fronthaulemulator = None
        evt = FronthaulEmulatorCancelRegistrationEvent(self)

    def clear_changed(self):
        self.has_changed = False

    def notify_fronthaulemulator(self, evt):
        self.has_changed = True
        if self.fronthaulemulator:
            self.fronthaulemulator.update(evt)
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
            api_thread = threading.Thread(target=api.run, kwargs=kwargs)
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


class KomondorConfigChangeEvent(object):
    def __init__(self,
                 node,
                 update):
        self.node = node
        self.update = update


class ChannelSwitchEvent(object):
    def __init__(self,
                 node,
                 old_channel_config,
                 new_channel_config):
        self.node = node
        self.old_channel_config = old_channel_config
        self.new_channel_config = new_channel_config


class FronthaulEmulatorRegistrationEvent(object):
    def __init__(self,
                 node):
        self.node = node


class FronthaulEmulatorCancelRegistrationEvent(object):
    def __init__(self,
                 node):
        self.node = node

