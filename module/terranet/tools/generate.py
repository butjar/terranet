import multiprocessing
import jinja2
import terranet.config
import itertools
import functools
import logging
import os
import math
import json


def channel_combinations():
    return list(filter(lambda t: t[1] - t[0] in [0, 1, 3, 7],
                       itertools.product(range(8), repeat=2)))


def get_template(*args, **kwargs):
    env = jinja2.Environment(
        loader=jinja2.PackageLoader('terranet', 'templates'),
    )
    template = env.get_template('config.j2')
    return template.render(*args, **kwargs)


def generate_config(networks, channels):
    system = terranet.config.System()
    nodes = []

    for ap_idx, net in enumerate(networks):
        wlan_code = net["wlan_code"]
        name = "Node_AP_{}".format(wlan_code)
        (min_ch, max_ch) = channels[ap_idx]

        args = {"wlan_code": wlan_code,
                "primary_channel": min_ch,
                "min_channel_allowed": min_ch,
                "max_channel_allowed": max_ch,
                "x": net["ap"]["x"],
                "y": net["ap"]["y"],
                "z": net["ap"]["z"]
                }

        ap = terranet.config.AccessPoint(name=name, **args)
        nodes.append(ap)

        num_stas = len(net["stas"])
        for sta_idx, sta in enumerate(range(num_stas)):
            name = "Node_STA_{}{}".format(wlan_code, sta_idx + 1)
            args = {"wlan_code": wlan_code,
                    "primary_channel": min_ch,
                    "min_channel_allowed": min_ch,
                    "max_channel_allowed": max_ch,
                    "x": net["stas"][sta_idx]["x"],
                    "y": net["stas"][sta_idx]["y"],
                    "z": net["stas"][sta_idx]["z"]
                    }
            sta = terranet.config.Station(name=name, **args)
            nodes.append(sta)

    return terranet.config.Config(system=system, nodes=nodes)


def generator_worker((iteration, channels), network, max_digits, cfg_dir):
        config = generate_config(network["networks"], channels)
        template = get_template(config=config)
        suffix = format(iteration, "0{}".format(max_digits))
        file_name = os.path.join(cfg_dir, 'terranet_{}.cfg'.format(suffix))
        with open(file_name, "w") as f:
            f.write(template)

def generate(args):
    log = logging.getLogger(__name__)

    try:
        with open(args.topology, 'r') as f:
            network = json.load(f)
    except OSError as e:
        log.exception('Unable to open network description!')

    ap_combinations = list(itertools.product(channel_combinations(),
                                             repeat=len(network["networks"])))

    max_digits = int(math.log10(len(ap_combinations))) + 1

    pool = multiprocessing.Pool()
    worker_func = functools.partial(generator_worker, network=network, max_digits=max_digits, cfg_dir=args.cfg_dir)
    pool.map(worker_func, enumerate(ap_combinations))
    pool.close()

    log.info('Generated {} configurations.'.format(len(ap_combinations)))