import netns
from threading import Thread

from mininet.log import info, warn

from ..wifi.komondor_config import KomondorNodeConfig
from ..wifi.channel import Channel
from ..link import WifiLink
from ..config_api import ConfigAPI
from ..proxy import NamespaceProxy
from ..event import KomondorConfigChangeEvent, ChannelSwitchEvent, \
        Sub6GhzEmulatorRegistrationEvent, \
        Sub6GhzEmulatorCancelRegistrationEvent

from .router import TerranetRouter

class WifiNode(TerranetRouter):
    def __init__(self, name,
                 komondor_args={'x': 0, 'y': 0, 'z': 0},
                 coordinates={},
                 *args, **kwargs):
        komondor_args = self._insert_coorinates(coordinates,
                                                komondor_args)
        self._komondor_config = KomondorNodeConfig(name, **komondor_args)
        self.has_changed = False
        super().__init__(name,
                         *args, **kwargs)

    @property
    def komondor_config(self):
        return self._komondor_config

    def _insert_coorinates(self, coord, d={}):
        coord = { k: v for k, v in coord.items() if k in ('x', 'y', 'z') }
        d.update(coord)
        return d

    def channel_config(self):
        kcfg = self.komondor_config
        return {"primary_channel": kcfg["primary_channel"],
                "min_channel_allowed": kcfg["min_channel_allowed"],
                "max_channel_allowed": kcfg["max_channel_allowed"],
                "central_freq": kcfg["central_freq"]}

    def update_komondor_config(self, config_dict):
        self._komondor_config.update(config_dict)
        evt = KomondorConfigChangeEvent(self, config_dict)
        self.notify_sub6ghz_emulator(evt)
        return (evt.result, evt.message)

    def register_sub6ghz_emulator(self, emulator):
        self.sub6ghz_emulator = emulator
        evt = Sub6GhzEmulatorRegistrationEvent(self)
        self.notify_sub6ghz_emulator(evt)
        return (evt.result, evt.message)

    def unregister_sub6ghz_emulator(self):
        self.sub6ghz_emulator = None
        evt = Sub6GhzEmulatorCancelRegistrationEvent(self)
        self.notify_sub6ghz_emulator(evt)
        return (evt.result, evt.message)

    def clear_changed(self):
        self.has_changed = False

    def notify_sub6ghz_emulator(self, evt, wait=True):
        self.has_changed = True
        if self.sub6ghz_emulator:
            self.sub6ghz_emulator.update(evt)
        if wait:
            evt.wait()
        self.clear_changed()


class WifiAccessPoint(WifiNode):
    def __init__(self, name, ssid,
                 available_channels=[Channel(32)],
                 primary_channel=None,
                 sub6ghz_emulator=None,
                 komondor_args={},
                 *args, **kwargs):
        komondor_args.update({"type": 0})
        self.available_channels = available_channels
        channel_config = available_channels[0].komondor_channel_params
        if not primary_channel:
            primary_channel = channel_config["min_channel_allowed"]
        komondor_args.update({"wlan_code": ssid,
                              "primary_channel": primary_channel})
        komondor_args.update(channel_config)
        self.sub6ghz_emulator = sub6ghz_emulator
        super().__init__(name,
                         komondor_args=komondor_args,
                         *args, **kwargs)

    def connected_stations(self):
        stations = []
        for intf in self.intfList():
            link = intf.link
            if link and isinstance(link, WifiLink):
                node1, node2 = link.intf1.node, link.intf2.node
                if node1 == self and isinstance(node2, WifiStation):
                    stations.append(node2)
                elif node2 == self and isinstance(node1, WifiStation):
                    stations.append(node1)
        return stations

    def get_channel_config(self):
        return self.channel_config()


class ConfigurableWifiAccessPoint(WifiAccessPoint):
    def __init__(self, name, ssid,
                 proxy_port=None,
                 *args, **kwargs):
        super().__init__(name, ssid,
                         *args, **kwargs)
        self.run_config_api_thread()
        self.proxy = None
        self.proxy_port = proxy_port
        if proxy_port:
            self.proxy = self.run_namespace_proxy()

    def run_config_api_thread(self):
        nspid = self.pid
        with netns.NetNS(nspid=nspid):
            api = ConfigAPI(self.name, self)
            kwargs = {"host": "::",
                      "port": 80}
            api_thread = Thread(target=api.run, kwargs=kwargs)
            api_thread.daemon = True
            api_thread.start()

    def run_namespace_proxy(self):
        nspid = self.pid
        proxy = NamespaceProxy(nspid, self.proxy_port)
        info('Starting Namespace proxy for node {}'
             'with NSPID {} on port {}.\n'.format(self.name,
                                                  proxy.nspid,
                                                  proxy.port))
        proxy.start_proxy_process()
        info('Proxy started at process {}.\n'.format(proxy.process.pid))
        return proxy

    def switch_channel(self, channel, primary_channel=None):
        channel_params = channel.komondor_channel_params
        if not primary_channel:
            primary_channel = channel_params["min_channel_allowed"]
        min_channel_allowed = channel_params["min_channel_allowed"]
        max_channel_allowed = channel_params["max_channel_allowed"]
        central_freq = channel_params["central_freq"]
        old_channel_cfg = self.get_channel_config()
        new_channel_cfg = {"primary_channel": primary_channel,
                           "min_channel_allowed": min_channel_allowed,
                           "max_channel_allowed": max_channel_allowed,
                           "central_freq": central_freq}
        self.update_komondor_config(new_channel_cfg)
        evt = ChannelSwitchEvent(self,
                                 old_channel_cfg,
                                 new_channel_cfg)
        self.notify_sub6ghz_emulator(evt)
        return (evt.result, evt.message)

    def terminate(self):
        if self.proxy and self.proxy.process:
            try:
                pid = self.proxy.process.pid
                info('Terminating proxy process with pid {}.\n'.format(pid))
                self.proxy.process.terminate()
            except Exception as e:
                warn('Could not kill proxy process: \n'
                     '{}\n'.format(e))
        super().terminate()


class WifiStation(WifiNode):
    def __init__(self,
                 name,
                 komondor_args={},
                 *args, **kwargs):
        komondor_args.update({"type": 1})
        super().__init__(name,
                         komondor_args=komondor_args,
                         *args, **kwargs)
