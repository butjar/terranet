#!/usr/bin/env python

from __future__ import print_function

import math
import itertools
import pkgutil
from jinja2 import Environment, PackageLoader
from terranet.config import Config, System, AccessPoint, Station


def channel_combinations():
    return list(itertools.ifilter(lambda (x,y): y - x in [0,1,3,7],
                list(itertools.combinations(tuple(range(8)), 2))
           ))

def get_template(*args,**kwargs):
    env = Environment(
        loader=PackageLoader('terranet', 'templates'),
    )
    template = env.get_template('config.j2')
    return template.render(*args, **kwargs)
    
def generate_config(networks, channels):
    system = System()
    nodes = []

    for ap_idx, net in enumerate(networks):
        wlan_code = net["wlan_code"]
        name = "Node_AP_{}".format(wlan_code)
        (min_ch, max_ch) = channels[ap_idx]

        args = { "wlan_code": wlan_code,
                 "primary_channel": min_ch,
                 "min_channel_allowed": min_ch,
                 "max_channel_allowed": max_ch,
                 "x": net["ap"]["x"],
                 "y": net["ap"]["y"],
                 "z": net["ap"]["z"]
               }

        ap = AccessPoint(name=name, **args)
        nodes.append(ap)
    
        num_stas = len(net["stas"])
        for sta_idx, sta in enumerate(range(num_stas)):
            name = "Node_STA_{}{}".format(wlan_code, sta_idx + 1)
            args = { "wlan_code": wlan_code,
                     "x": net["stas"][sta_idx]["x"],
                     "y": net["stas"][sta_idx]["y"],
                     "z": net["stas"][sta_idx]["z"]
                   }
            sta = Station(name=name, **args)
            nodes.append(sta)
    
    return Config(system=system, nodes=nodes)


if __name__ == '__main__':
    network = { "networks": 
                [ { "wlan_code": "A", 
                    "ap": { "x": 20, "y": 0, "z": 0 },
                    "stas": [ { "x": 10, "y": 20, "z": 0},
                              { "x": 20, "y": 20, "z": 0} ]
                  },
                  { "wlan_code": "B", 
                    "ap": { "x": 40, "y": 0, "z": 0 },
                    "stas": [ { "x": 30, "y": 20, "z": 0},
                              { "x": 40, "y": 20, "z": 0},
                              { "x": 50, "y": 20, "z": 0} ]
                } ]
              }

    ap_combinations = list(itertools.product(channel_combinations(), 
                                             repeat=len(network["networks"])))

    max_digits = int(math.log10(len(ap_combinations))) + 1

    for iteration, channels in enumerate(ap_combinations):
        config = generate_config(network["networks"], channels)
        template = get_template(config=config)
        suffix = format(iteration, "0{}".format(max_digits))
        file_name = "./cfg/terranet_{}.cfg".format(suffix)
        with open(file_name, "w") as f:
            print(template, file=f)
