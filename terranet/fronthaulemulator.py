import os
from mininet.log import info, warn
from configparser import ConfigParser
from .config import KomondorConfig, KomondorResult
from .node import (KomondorConfigChangeEvent,
                   ChannelSwitchEvent,
                   FronthaulEmulatorRegistrationEvent,
                   FronthaulEmulatorCancelRegistrationEvent)


class FronthaulEmulator(object):
    def __init__(self,
                 net=None,
                 cfg_dir="./cfg/",
                 out_dir="./out/",
                 system_config=None,
                 current_file=None,
                 current_config=None,
                 current_result=None):
        self.net = net
        self.cfg_dir = os.path.abspath(cfg_dir)
        self.out_dir = os.path.abspath(out_dir)
        self.system_config = system_config
        self.current_file = current_file
        self.current_config = current_config
        self.current_result = current_result
        self.read_komondor_configs()
        self.read_komondor_results()

    def update(self, evt):
        if isinstance(evt, KomondorConfigChangeEvent):
            self.handle_komondor_config_change(evt)
        elif isinstance(evt, ChannelSwitchEvent):
            self.handle_channel_switch(evt)
        elif isinstance(evt, FronthaulEmulatorRegistrationEvent):
            self.handle_registration(evt)
        elif isinstance(evt, FronthaulEmulatorCancelRegistrationEvent):
            self.handle_cancel_registration(evt)

    def handle_komondor_config_change(self, evt):
        info("FronthaulEmulator: Changing config of node {}.\n"
             .format(evt.node.name))
        info("FronthaulEmulator: New config {}\n".format(evt.update))
        evt.result = True
        evt.message = "OK\n"
        evt.set()

    def handle_channel_switch(self, evt):
        info("FronthaulEmulator: Node {} triggered channel switch.\n"
             .format(evt.node.name))
        try:
            distribution_node = evt.node
            client_nodes = self.net.connected_client_nodes(distribution_node)
            for client_node in client_nodes:
                client_node.update_komondor_config(evt.new_channel_config)
            self.apply_network_config()
            evt.result = True
            evt.message = "New config file: {}\n".format(self.current_file)
            evt.set()
        except RuntimeError as err:
            error_message = """FronthaulEmulator: Error {}
                               Rolling back to previos config: {}.\n"""\
                            .format(err, self.current_file)
            warn(error_message)
            for node in (connected_client_nodes + [distribution_node]):
                node.update_komondor_config(evt.old_channel_config)
            self.apply_network_config()
            evt.result = False
            evt.message = error_message
            evt.set()

    def handle_registration(self, evt):
        info("FronthaulEmulator: Registering node {}\n".format(evt.node.name))
        evt.result = True
        evt.message = "OK\n"
        evt.set()

    def handle_cancel_registration(self, evt):
        info("FronthaulEmulator: Unregistering node {}\n"
             .format(evt.node.name))
        evt.result = True
        evt.message = "OK\n"
        evt.set()

    def read_configs(self, cfg_dir, cls=KomondorConfig):
        configs = dict()
        for cfg_file in os.listdir(cfg_dir):
            path = os.path.join(cfg_dir, cfg_file)
            komondor_config = cls(cfg_file=path)
            configs[cfg_file] = komondor_config
        return configs

    def read_komondor_configs(self):
        self.komondor_configs = self.read_configs(self.cfg_dir)

    def read_komondor_results(self):
        self.komondor_results = self.read_configs(self.out_dir,
                                                  cls=KomondorResult)

    def apply_network_config(self):
        info("FronthaulEmulator: Trying to apply new network config.\n")
        new_config = self.build_terranet_config()
        config_tuple = self.find_kommondor_config(new_config)
        if not config_tuple:
            warn("No config found for new network configs.\n")
            raise RuntimeError("Current config not found.")
        else:
            (file_name, config) = config_tuple

        self.current_file = file_name
        self.current_config = config
        self.current_result = self.komondor_results[file_name]
        self.apply_results()
        info("FronthaulEmulator: Network config {} successfully applied.\n"
             .format(config.cfg_file))

    def apply_results(self):
        for distribution_node in self.net.distribution_nodes_5_60():
            client_nodes = self.net.connected_client_nodes(distribution_node)
            for client_node in client_nodes:
                for (intf, _) in distribution_node.connectionsTo(client_node):
                    result = self.read_result(client_node)
                    bw = int(result.getint("throughput") / 1000000)
                    delay = "{}ms".format(int(result.getfloat("delay")))
                    intf.config(bw=bw, delay=delay, use_tbf=True)

    def build_terranet_config(self):
        config_dict = {"System": self.system_config}

        def insert_config(dict, node):
            dict["Node_{}".format(node.name)] = node.komondor_config
            return dict

        node_configs = reduce(lambda x, y: insert_config(x, y),
                              self.net.terranodes(), {})
        config_dict.update(node_configs)
        config = KomondorConfig()
        config.read_dict(config_dict)
        return config

    def find_kommondor_config(self, config):
        for name, cfg in self.komondor_configs.items():
            if cfg == config:
                return (name, cfg)
        return None

    def read_result(self, node):
        section_name = "Node_{}".format(node.name)
        return self.current_result[section_name]

    def read_result(self, node):
        section_name = "Node_{}".format(node.name)
        return self.current_result[section_name]
