#!/usr/bin/env python

from __future__ import print_function

import fileinput
import math
import itertools
import collections
from terranet.config import KomondorConfig


def channel_combinations():
    return list(filter(lambda t: t[1] - t[0] in [0, 1, 3, 7],
                       itertools.product(range(8), repeat=2)))


def system_config():
    return collections.OrderedDict({
        "num_channels": 8,
        "basic_channel_bandwidth": 20,
        "pdf_backoff": 0,
        "pdf_tx_time": 1,
        "packet_length": 12000,
        "num_packets_aggregated": 64,
        "path_loss_model_default": 5,
        "path_loss_model_indoor_indoor": 5,
        "path_loss_model_indoor_outdoor": 8,
        "path_loss_model_outdoor_outdoor": 7,
        "capture_effect": 20,
        "noise_level": -95,
        "adjacent_channel_model": 0,
        "collisions_model": 0,
        "constant_PER": 0,
        "traffic_model": 99,
        "backoff_type": 1,
        "cw_adaptation": 0,
        "pifs_activated": 0,
        "capture_effect_model": 1})


def node_config(type, wlan_code, coordinates, channels):
    return collections.OrderedDict({
        "type": type,
        "wlan_code": wlan_code,
        "destination_id": -1,
        "x": coordinates["x"],
        "y": coordinates["y"],
        "z": coordinates["z"],
        "primary_channel": channels["primary_channel"],
        "min_channel_allowed": channels["min_channel_allowed"],
        "max_channel_allowed": channels["max_channel_allowed"],
        "cw": 16,
        "cw_stage": 5,
        "tpc_min": 30,
        "tpc_default": 30,
        "tpc_max": 30,
        "cca_min": -82,
        "cca_default": -82,
        "cca_max": -82,
        "tx_antenna_gain": 0,
        "rx_antenna_gain": 0,
        "channel_bonding_model": 1,
        "modulation_default": 0,
        "central_freq": 5,
        "lambda": 10000,
        "ieee_protocol": 1,
        "traffic_load": 1000,
        "node_env": "outdoor"})


def generate_config(networks, channels):
    config = collections.OrderedDict()
    config["System"] = system_config()

    for ap_idx, net in enumerate(networks):
        wlan_code = net["wlan_code"]
        name = "Node_AP_{}".format(wlan_code)
        coordinates = {"x": net["ap"]["x"],
                       "y": net["ap"]["y"],
                       "z": net["ap"]["z"]}
        (min_ch, max_ch) = channels[ap_idx]
        channels_cfg = {"primary_channel": min_ch,
                        "min_channel_allowed": min_ch,
                        "max_channel_allowed": max_ch}
        config[name] = node_config(0, wlan_code, coordinates, channels_cfg)

        num_stas = len(net["stas"])
        for sta_idx, sta in enumerate(range(num_stas)):
            name = "Node_STA_{}{}".format(wlan_code, sta_idx + 1)
            coordinates = {"x": net["stas"][sta_idx]["x"],
                           "y": net["stas"][sta_idx]["y"],
                           "z": net["stas"][sta_idx]["z"]}
            config[name] = node_config(1, wlan_code, coordinates, channels_cfg)

    return config


if __name__ == '__main__':
    network = {
        "networks": [
            {"wlan_code": "A",
             "ap": {"x": 30, "y": 0, "z": 0},
             "stas": [
                 {"x": 10, "y": 20, "z": 0},
                 {"x": 30, "y": 20, "z": 0}]},
            {"wlan_code": "B",
             "ap": {"x": 70, "y": 0, "z": 0},
             "stas": [
                 {"x": 50, "y": 20, "z": 0},
                 {"x": 70, "y": 20, "z": 0},
                 {"x": 90, "y": 20, "z": 0}]}
            ]
        }

    ap_combinations = list(itertools.product(channel_combinations(),
                                             repeat=len(network["networks"])))

    max_digits = int(math.log10(len(ap_combinations))) + 1

    for iteration, channels in enumerate(ap_combinations):
        config = generate_config(network["networks"], channels)
        komondor_config = KomondorConfig()
        komondor_config.read_dict(config)
        suffix = format(iteration, "0{}".format(max_digits))
        file_name = "./cfg/terranet_{}.cfg".format(suffix)
        with open(file_name, "w+") as f:
            komondor_config.write(f)

        # Dirty fix for constant_PER. The ConfigParser uses lower case keys,
        # but the komondor config is case sensitive
        for line in fileinput.input(file_name, inplace=True):
            print(line.replace('constant_per', 'constant_PER'),
                  end='')
