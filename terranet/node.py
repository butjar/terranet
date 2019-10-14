import os
import signal
from threading import Thread, Event
import subprocess

from mininet.log import warn
from mininet.node import Host, OVSBridge

from ipmininet.router import Router, ProcessHelper

from .router_config import OpenrConfig
from .config_api import ConfigAPI
from .link import WifiLink

from .wifi.komondor_config import KomondorNodeConfig
from .wifi.channel import Channel

import netns


class Terranode(Router):
    def __init__(self,
                 name,
                 config=OpenrConfig,
                 cwd='/tmp',
                 process_manager=ProcessHelper,
                 use_v4=True,
                 use_v6=True,
                 password=None,
                 *args, **kwargs):
        self.has_changed = False
        super(Terranode, self).__init__(name,
                                        config=config,
                                        cwd=cwd,
                                        process_manager=process_manager,
                                        use_v4=use_v4,
                                        use_v6=use_v6,
                                        password=password,
                                        *args, **kwargs)


class WifiNode(Terranode):
    def __init__(self,
                 name,
                 komondor_args={},
                 *args, **kwargs):
        self._komondor_config = KomondorNodeConfig(name, **komondor_args)
        super(WifiNode, self).__init__(name,
                                       *args, **kwargs)

    @property
    def komondor_config(self):
        return self._komondor_config

    def channel_config(self):
        kcfg = self.komondor_config
        return {"primary_channel": kcfg["primary_channel"],
                "min_channel_allowed": kcfg["min_channel_allowed"],
                "max_channel_allowed": kcfg["max_channel_allowed"],
                "central_freq": kcfg["central_freq"]}

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


class WifiAccessPoint(WifiNode):
    def __init__(self,
                 name,
                 komondor_args={},
                 *args, **kwargs):
        komondor_args.update({"type": 0})
        super(WifiAccessPoint, self).__init__(name,
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


class WifiStation(WifiNode):
    def __init__(self,
                 name,
                 komondor_args={},
                 *args, **kwargs):
        komondor_args.update({"type": 1})
        super(WifiStation, self).__init__(name,
                                          komondor_args=komondor_args,
                                          *args, **kwargs)


class ClientNode(WifiStation):
    def __init__(self,
                 name,
                 coordinates={"x": 0, "y": 0, "z": 0},
                 komondor_args={},
                 *args, **kwargs):
        komondor_args.update(coordinates)
        super(ClientNode, self).__init__(name,
                                         komondor_args=komondor_args,
                                         *args, **kwargs)


class DistributionNode60(Terranode):
    def __init__(self,
                 name,
                 *args, **kwargs):
        super(DistributionNode60, self).__init__(name, *args, **kwargs)


class DistributionNode5_60(WifiAccessPoint):
    def __init__(self,
                 name,
                 ssid,
                 available_channels=[Channel(32)],
                 primary_channel=None,
                 coordinates={"x": 0, "y": 0, "z": 0},
                 komondor_args={},
                 fronthaulemulator=None,
                 *args, **kwargs):
        self.available_channels = available_channels
        channel_config = available_channels[0].komondor_channel_params
        if not primary_channel:
            primary_channel = channel_config["min_channel_allowed"]
        komondor_args.update({"wlan_code": ssid,
                              "primary_channel": primary_channel})
        komondor_args.update(coordinates)
        komondor_args.update(channel_config)
        self.fronthaulemulator = fronthaulemulator
        super(DistributionNode5_60, self).__init__(name,
                                                   komondor_args=komondor_args,
                                                   *args, **kwargs)
        self.run_config_api_thread()

    def run_config_api_thread(self):
        nspid = self.pid
        with netns.NetNS(nspid=nspid):
            api = ConfigAPI(self.name, self)
            kwargs = {"host": "::",
                      "port": 80}
            api_thread = Thread(target=api.run, kwargs=kwargs)
            api_thread.daemon = True
            api_thread.start()

    def get_channel_config(self):
        return self.channel_config()

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
        self.notify_fronthaulemulator(evt)
        return (evt.result, evt.message)


class Gateway(OVSBridge):
    def __init__(self, name, **params):
        super(Gateway, self).__init__(name, **params)


class IperfHost(Host):
    def __init__(self, name, **params):
        super(IperfHost, self).__init__(name, **params)
        if "logfile" in params:
            self.logfile = params["logfile"]
        else:
            self.logfile = "/tmp/iperf_{}.log".format(self.name)
        self.iperf_pid = None

    def terminate(self):
        if self.iperf_pid:
            try:
                os.killpg(self.iperf_pid, signal.SIGHUP)
            except Exception as e:
                warn("""Could not kill iperf process with PID: {}\n
                        {}""".format(self.iperf_pid, e))
        super(IperfHost, self).terminate()


class IperfDownloadClient(IperfHost):
    def __init__(self, name, host=None, server_name=None, **params):
        self._host = host
        self.server_name = server_name
        super(IperfDownloadClient, self).__init__(name, **params)

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        if isinstance(host, IperfDownloadServer):
            self._host = host.intfList()[0].ip6
        else:
            self._host = host

    def run_iperf_client(self,
                         bin="iperf3",
                         args="-6 -R -t 0 -i 10",
                         bind_address=None):
        if not self.host:
            raise ValueError("""Host attribute must be set before running
                                iperf client.""")
        if not bind_address:
            bind_address = self.intfList()[0].ip6
        # --logfile option requires iperf3 >= 3.1
        cmd = """until ping6 -c1 {host} >/dev/null 2>&1; do :; done;
                 {bin} {args} -c {host} -B {bind} --logfile {log}""".format(
                      bin=bin, args=args, host=self.host, bind=bind_address,
                      log=self.logfile)
        p = self.popen(cmd, shell=True)
        self.iperf_pid = p.pid
        return p


class IperfDownloadServer(IperfHost):
    def __init__(self, name, **params):
        super(IperfDownloadServer, self).__init__(name, **params)

    def run_iperf_server(self,
                         bin="iperf3",
                         args="",
                         bind_address=None):
        if not bind_address:
            bind_address = self.intfList()[0].ip6
        # --logfile option requires iperf3 >= 3.1
        cmd = """while true; do
                 {bin} -s {args} -B {bind} --logfile {log};
                 done""".format(bin=bin, args=args, bind=bind_address,
                                log=self.logfile)
        p = self.popen(cmd, shell=True)
        self.iperf_pid = p.pid
        return p


class TerranetEvent(object):
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
