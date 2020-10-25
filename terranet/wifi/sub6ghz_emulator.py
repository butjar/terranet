import os
import collections
import math
import itertools
import multiprocessing
from functools import partial
from configparser import ConfigParser

from mininet.log import info, warn

from ..event import KomondorConfigChangeEvent, ChannelSwitchEvent, \
    Sub6GhzEmulatorRegistrationEvent, \
    Sub6GhzEmulatorCancelRegistrationEvent
from .komondor import run_komondor_worker
from .komondor_config import KomondorConfig, KomondorSystemConfig, \
                             read_komondor_configs, read_komondor_results


class Sub6GhzEmulator(object):
    def __init__(self,
                 net=None,
                 komondor_executable=None,
                 komondor_config_dir=None,
                 komondor_system_cfg=None,
                 komondor_configs=None,
                 komondor_results=None,
                 current_komondor_file=None,
                 current_komondor_config=None,
                 current_komondor_result=None):
        self.net = net
        self.komondor_executable = komondor_executable
        self.komondor_config_dir = os.path.abspath(komondor_config_dir)
        self.komondor_input_dir = f'{self.komondor_config_dir}/input'
        self.komondor_output_dir = f'{self.komondor_config_dir}/output'
        if not komondor_system_cfg:
            komondor_system_cfg = KomondorSystemConfig()
        self.komondor_system_cfg = komondor_system_cfg
        self.komondor_configs = komondor_configs
        self.komondor_results = komondor_results
        self.current_komondor_file = current_komondor_file
        self.current_komondor_config = current_komondor_config
        self.current_komondor_result = current_komondor_result

    def update(self, evt):
        if isinstance(evt, KomondorConfigChangeEvent):
            self.handle_komondor_config_change(evt)
        elif isinstance(evt, ChannelSwitchEvent):
            self.handle_channel_switch(evt)
        elif isinstance(evt, Sub6GhzEmulatorRegistrationEvent):
            self.handle_registration(evt)
        elif isinstance(evt, Sub6GhzEmulatorCancelRegistrationEvent):
            self.handle_cancel_registration(evt)

    def handle_komondor_config_change(self, evt):
        info("Sub6GhzEmulator: Changing config of node {}.\n"
             .format(evt.node.name))
        info("Sub6GhzEmulator: New config {}\n".format(evt.update))
        evt.result = True
        evt.message = "OK\n"
        evt.set()

    def handle_channel_switch(self, evt):
        info("Sub6GhzEmulator: Node {} triggered channel switch.\n"
             .format(evt.node.name))
        ap = evt.node
        client_nodes = ap.connected_stations()
        try:
            self.adjust_station_wifi_config(ap)
            self.apply_wifi_config()
            evt.result = True
            evt.message = "New config file: {}\n"\
                          .format(self.current_komondor_file)
            evt.set()
        except RuntimeError as err:
            error_message = """Sub6GhzEmulator: Error {}
                               Rolling back to previos config: {}.\n"""\
                            .format(err, self.current_komondor_file)
            warn(error_message)
            for node in (client_nodes + [ap]):
                node.update_komondor_config(evt.old_channel_config)
            self.apply_wifi_config()
            evt.result = False
            evt.message = error_message
            evt.set()

    def handle_registration(self, evt):
        info("Sub6GhzEmulator: Registering node {}\n".format(evt.node.name))
        evt.result = True
        evt.message = "OK\n"
        evt.set()

    def handle_cancel_registration(self, evt):
        info("Sub6GhzEmulator: Unregistering node {}\n"
             .format(evt.node.name))
        evt.result = True
        evt.message = "OK\n"
        evt.set()

    def apply_wifi_config(self):
        info("Sub6GhzEmulator: Trying to apply new network config.\n")
        new_config = self.wifi_config()
        config_tuple = self.find_kommondor_config(new_config)
        if not config_tuple:
            warn("No config found for new network configs.\n")
            raise RuntimeError("Current config not found.")
        else:
            file_name = config_tuple[0]
            config = config_tuple[1]

        self.current_komondor_file = file_name
        self.current_komondor_config = self.komondor_configs[file_name]
        self.current_komondor_result = self.komondor_results[file_name]
        info('Sub6GhzEmulator: Trying to apply new config file {}.\n'
             .format(file_name))
        self.apply_results()
        info("Sub6GhzEmulator: Network config {} successfully applied.\n"
             .format(config.cfg_file))

    def apply_results(self):
        for ap in self.net.access_points():
            stas = ap.connected_stations()
            for sta in stas:
                komondor_name = sta.komondor_config.name
                result = self.current_komondor_result[komondor_name]
                links = self.net.linksBetween(ap, sta)
                for link in links:
                    bw = int(result.getint("throughput") / 1000000)
                    # Dirty fix for ZeroDivisionError in mininet
                    if bw == 0:
                        bw = 1
                    delay_value = result.get('delay')
                    if delay_value in ['nan', '-nan']:
                        delay_value = '0'
                    delay = '{}ms'.format(round(float(delay_value)))
                    link.intf1.config(bw=bw, delay=delay, use_tbf=True)
                    link.intf2.config(bw=bw, delay=delay, use_tbf=True)

    def wifi_config(self):
        config = KomondorConfig()
        config_dict = collections.OrderedDict()
        config_dict["System"] = collections.OrderedDict(
            **self.komondor_system_cfg)
        node_configs = [node.komondor_config for node in self.net.wifi_nodes()]

        for cfg in node_configs:
            config_dict[cfg.name] = collections.OrderedDict(**cfg)

        config.read_dict(config_dict)
        return config

    def adjust_station_wifi_config(self, ap):
        wlan_code = ap.komondor_config["wlan_code"]
        channel_params = ap.channel_config()
        for sta in ap.connected_stations():
            sta.komondor_config.update({"wlan_code": wlan_code})
            sta.komondor_config.update(channel_params)
        return channel_params

    def build_komondor(self, use_cache=True):
        configs = []
        access_points = self.net.access_points()

        # No simulation needed
        if not access_points:
            return None

        for ap in access_points:
            self.adjust_station_wifi_config(ap)

        channels = sorted([ ap.available_channels for ap in access_points ])
        channel_combinations = list(itertools.product(*channels))

        for channels in channel_combinations:
            config = self.__build_channel_config(channels)
            configs.append(config)

        cached_config_dict = read_komondor_configs(self.komondor_input_dir)
        cached_configs = list(cached_config_dict.values())
        if not use_cache or configs != cached_configs:
            info("Not using cached komondor config.\n")
            self.delete_cache()
            self.write_komondor_configs(configs)
            self.komondor_configs = read_komondor_configs(
                self.komondor_input_dir)
            info("Simulating komondor configurations. "
                 "This might take a while.\n")
            import time
            start = time.time()
            self.presimulate()
            end = time.time()
            time_elapsed = end - start
            info("Simulations finished."
                 "Time elapsed: {} seconds.\n".format(time_elapsed))
        else:
            info("Using cached komondor config.\n")
            self.komondor_configs = cached_config_dict
        self.komondor_results = read_komondor_results(
            self.komondor_output_dir)
        return self

    def __build_channel_config(self, channels):
        config_dict = collections.OrderedDict()
        config_dict["System"] = collections.OrderedDict(
            **self.komondor_system_cfg)
        for i, ap in enumerate(self.net.access_points()):
            channel = channels[i]
            cfg = self.__build_bss_config(ap, channel)
            config_dict.update(cfg)
        config = KomondorConfig()
        config.read_dict(config_dict)
        return config

    def __build_bss_config(self, ap, channel):
        config = collections.OrderedDict()
        channel_cfg = channel.komondor_channel_params
        primary_channel = channel_cfg["min_channel_allowed"]
        ap_cfg = collections.OrderedDict(**ap.komondor_config)
        ap_cfg.update(channel_cfg)
        ap_cfg.update({"primary_channel": primary_channel})
        ap_name = ap.komondor_config.name
        config[ap_name] = collections.OrderedDict(ap_cfg)
        for sta in ap.connected_stations():
            cfg = collections.OrderedDict(**sta.komondor_config)
            cfg.update({"wlan_code": ap_cfg["wlan_code"],
                        "primary_channel": primary_channel})
            cfg.update(channel_cfg)
            sta_name = sta.komondor_config.name
            config[sta_name] = collections.OrderedDict(cfg)
        return config

    def write_komondor_configs(self, configs):
        config_map = []
        max_digits = int(math.log10(len(configs))) + 1
        for i, config in enumerate(configs):
            suffix = format(i, "0{}".format(max_digits))
            fname = "{}.cfg".format(suffix)
            fpath = os.path.join(self.komondor_input_dir, fname)
            with open(fpath, 'w') as f:
                config.write(f)
            config_map.append((fname, config))
        return config_map

    def presimulate(self):
        cfg_files = [os.path.join(self.komondor_input_dir, f)
                     for f in os.listdir(self.komondor_input_dir)
                     if f.endswith(".cfg")]
        pool = multiprocessing.Pool()

        f = partial(run_komondor_worker,
                    output_dir=self.komondor_output_dir)
        pool.map(f, cfg_files)

    def delete_cache(self):
        for d in [self.komondor_input_dir, self.komondor_output_dir]:
            for f in os.listdir(d):
                if f.endswith(".cfg"):
                    os.remove(os.path.join(d, f))

    def find_kommondor_config(self, config):
        for fname, cfg in self.komondor_configs.items():
            if cfg == config:
                return (fname, cfg)
        return None
