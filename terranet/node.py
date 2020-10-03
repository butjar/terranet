import os
import signal
from threading import Thread, Event
import subprocess

from mininet.log import info, warn
from mininet.node import OVSBridge

from ipmininet.host import IPHost
from ipmininet.router import ProcessHelper
from ipmininet.router import OpenrRouter

from .router_config import OpenrConfig
from .config_api import ConfigAPI
from .link import WifiLink

from .wifi.komondor_config import KomondorNodeConfig
from .wifi.channel import Channel

import netns


class TerranetRouter(OpenrRouter):
    def __init__(self, name,
                 config=OpenrConfig,
                 lo_addresses=(),
                 privateDirs=['/tmp'],
                 *args, **kwargs):
        self.has_changed = False
        super().__init__(name,
                         config=config,
                         lo_addresses=lo_addresses,
                         privateDirs=privateDirs,
                         *args, **kwargs)


class WifiNode(TerranetRouter):
    def __init__(self, name,
                 komondor_args={'x': 0, 'y': 0, 'z': 0},
                 coordinates={},
                 *args, **kwargs):
        komondor_args = self._insert_coorinates(coordinates,
                                                komondor_args)
        self._komondor_config = KomondorNodeConfig(name, **komondor_args)
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
    def __init__(self, name, ssid,
                 available_channels=[Channel(32)],
                 primary_channel=None,
                 fronthaulemulator=None,
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
        self.fronthaulemulator = fronthaulemulator
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

    def run_config_api_thread(self):
        nspid = self.pid
        with netns.NetNS(nspid=nspid):
            api = ConfigAPI(self.name, self)
            kwargs = {"host": "::",
                      "port": 80}
            api_thread = Thread(target=api.run, kwargs=kwargs)
            api_thread.daemon = True
            api_thread.start()


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

class WifiStation(WifiNode):
    def __init__(self,
                 name,
                 komondor_args={},
                 *args, **kwargs):
        komondor_args.update({"type": 1})
        super().__init__(name,
                         komondor_args=komondor_args,
                         *args, **kwargs)


class ClientNode(WifiStation):
    def __init__(self, name,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)


class DistributionNode60(TerranetRouter):
    def __init__(self, name,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)


class DistributionNode5_60(ConfigurableWifiAccessPoint):
    def __init__(self, name, ssid,
                 *args, **kwargs):
        super().__init__(name, ssid,
                         *args, **kwargs)


class Gateway(OVSBridge):
    def __init__(self, name,
                 **params):
        super().__init__(name,
                         **params)


class IperfHost(IPHost):
    def __init__(self, name,
                 autostart=True,
                 autostart_params=None,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)
        if "logfile" in kwargs:
            self.logfile = params["logfile"]
        else:
            self.logfile = "/var/log/iperf_{}.log".format(self.name)
        self.pids = {}
        self.bind_address = None
        self.autostart = autostart
        self.autostart_params = autostart_params

    def run(self,
            bin="iperf3",
            iperf_args="",
            bind_address=None,
            *args, **kwargs):

        iface = self.intfList()[0]
        if not bind_address:
            self.bind_address = iface.ip6

        # Kill current processes
        self.stop()
        # Implement iperf command in subclass
        pass

    def stop(self):
        for process, pid in self.pids.items():
            try:
                os.killpg(pid, signal.SIGHUP)
                info("Stopped process {} with PID {}.". format(process,
                                                              pid))
            except Exception as e:
                warn("""Could not stop process {} with PID: {}\n
                        {}""".format(process,
                                     pid,
                                     e))
        self.pids = {}

    def terminate(self):
        self.stop()
        super().terminate()


class IperfClient(IperfHost):
    def __init__(self, name,
                 host=None,
                 netstats_log=None,
                 *args, **kwargs):
        self.host = host
        self.netstats_log = netstats_log
        super().__init__(name,
                         *args, **kwargs)

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        if isinstance(host, IperfServer):
            self._host = host.intfList()[0].ip6
        else:
            self._host = host

    def run(self,
            bin="iperf3",
            iperf_args="-6 -t0 -i10 -u -b0 -l1400 -Z",
            *args, **kwargs):
        super().run(bin=bin,
                    iperf_args=iperf_args,
                    *args, **kwargs)

        if not self.host:
            raise ValueError("""Host attribute must be set before running
                                iperf client.""")

        iface = self.intfList()[0]
        if not self.netstats_log:
            self.netstats_log = "/var/log/{}_{}_netstats.log".format(iface.name,
                                                                   iface.ip6)
        netstats_cmd = ("(while :; do "
                       "cat /proc/net/dev | grep {intf} > {logfile} 2>&1; "
                       "sleep {interval}; done) &").format(intf=iface.name,
                                                           logfile=self.netstats_log,
                                                           interval=2)
        p_netstats = self.popen(netstats_cmd, shell=True)
        self.pids.update({"netstats_logger": p_netstats.pid})

        # --logfile option requires iperf3 >= 3.1
        cmd = ("until ping6 -c1 {host} >/dev/null 2>&1; do :; done; "
               "{bin} {iperf_args} "
               "-c {host} "
               "-B {bind} "
               "--logfile {log}").format(bin=bin,
                                         iperf_args=iperf_args,
                                         host=self.host,
                                         bind=self.bind_address,
                                         log=self.logfile)
        p = self.popen(cmd, shell=True)
        self.pids.update({"iperf": p.pid})
        return p


class IperfReverseClient(IperfClient):
    def __init__(self, name,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)

    def run(self,
            bin="iperf3",
            iperf_args="-6 -R -t0 -i10 -u -b0 -l1400 -Z",
            *args, **kwargs):
        super().run(bin=bin,
                    iperf_args=iperf_args,
                    *args, **kwargs)


class IperfServer(IperfHost):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)

    def run(self,
            bin="iperf3",
            iperf_args="-s",
            *args, **kwargs):
        super().run(bin=bin,
                    iperf_args=iperf_args,
                    *args, **kwargs)

        # --logfile option requires iperf3 >= 3.1
        cmd = ("{bin} {iperf_args} "
               "-B {bind} "
               "--logfile {log}").format(bin=bin,
                                         iperf_args=iperf_args,
                                         bind=self.bind_address,
                                         log=self.logfile)
        p = self.popen(cmd, shell=True)
        self.pids.update({"iperf": p.pid})
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
