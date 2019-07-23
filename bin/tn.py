#!/usr/bin/env python2
from __future__ import print_function
import argparse
import os
import sys
import subprocess
import math
import configparser
import zmq
import threading
import select
import time

import ipmininet.utils
import terranet
import terranet.config

import multiprocessing
import functools
import progress.bar
import time

import json
import itertools
import jinja2

from terranet.komondor import Komondor


class PseudoMeterer(threading.Thread):
    def __init__(self, src, dst, socket, lock):
        super(PseudoMeterer, self).__init__()
        self.running = False
        self.dst = dst
        self.src = src
        self.socket = socket
        self.lock = lock

    def run(self):
        self.running = True

        topic = 'flows/{}'.format(self.dst.name)
        while self.running:
            _, ip6 = ipmininet.utils.address_pair(self.dst)
            if ip6 is None:
                time.sleep(3)
                continue
            # FIXME:
            # iperf always returns a summary of the whole run as last entry, which sometimes looks like a sudden
            # drop in throughput, if e.g. the config was changed during the run.
            p = self.src.popen('iperf -y c -V -t 3000 -i 5 -c %s' % ip6)

            while p.poll() is None and self.running:
                rlist, _, _ = select.select([p.stdout, p.stderr], [], [], 7)

                if p.stderr in rlist:
                    time.sleep(3)
                    continue

                if p.stdout in rlist:
                    o = p.stdout.readline()

                    if o == "":
                        break

                    payload = "{}".format(int(o.split(',')[8]) / 1e6)
                    with self.lock:
                        self.socket.send(topic, flags=zmq.SNDMORE)
                        self.socket.send(payload)


class FronthaulEmulatorSwitch(threading.Thread):
    def __init__(self, hostname, sub_port, fh_emulator, default, best):
        super(FronthaulEmulatorSwitch, self).__init__()
        self.sub_port = sub_port
        self.hostname = hostname
        self.running = False
        self.fh_emulator = fh_emulator
        self.default = default
        self.best = best

    def run(self):
        self.running = True
        ctx = zmq.Context()
        sub = ctx.socket(zmq.SUB)
        sub.setsockopt(zmq.SUBSCRIBE, 'controller')
        sub.connect('tcp://{}:{}'.format(self.hostname, self.sub_port))

        while self.running:
            rlist, _, _ = zmq.select([sub], [], [], 3.0)
            if sub in rlist:
                topic, content = sub.recv_multipart()
                with self.fh_emulator.lock:
                    index = self.best if content == 'true' else self.default
                    self.fh_emulator.current_tuple = self.fh_emulator.cfg_tuples[index]
                    self.fh_emulator.apply_global_config(self.fh_emulator.current_tuple)

        sub.close()


def config_metric(cfg_tuple, net):
    p = configparser.ConfigParser()

    with open(cfg_tuple[1], 'r') as f:
        p.read_file(f)

    metric = 0.0
    for sta in filter(lambda s: s.startswith('Node_'), p.sections()):
        name = sta.split('Node_')[1]
        tp = p.getfloat(sta, 'throughput')

        try:
            metric += math.log(tp)
        except ValueError as e:
            print('{} for {}->tp = {} in {}'.format(e, name, tp, cfg_tuple[1]))
        # TODO Factor in number of (active) clients

    return metric


def run(args):
    cfg_files = sorted(
        map(lambda p: os.path.join(args.cfg_path, p),
            filter(lambda p: p.endswith('.cfg') and os.path.isfile(os.path.join(args.cfg_path, p)),
                   os.listdir(args.cfg_path))))

    if len(cfg_files) < 1:
        print('No configuration files found. Exiting...')
        sys.exit(-1)

    out_files = sorted(
        map(lambda p: os.path.join(args.out_path, p),
            filter(lambda p: p.endswith('.cfg') and os.path.isfile(os.path.join(args.cfg_path, p)),
                   os.listdir(args.cfg_path))))  # Use the same files names to get corresponding outputs

    if len(out_files) != len(cfg_files):
        print('Missing simulation results for given configurations!')
        sys.exit(-1)

    cfg_tuples = list(
        map(lambda t: (terranet.config.Config.from_file(t[0]), t[1]),
            zip(cfg_files, out_files))
    )

    default = list(filter(lambda cfg_tup: False not in
                                          map(lambda ap: int(ap.max_channel_allowed) - int(ap.min_channel_allowed) == 7,
                                              cfg_tup[0].get_access_points()),
                          cfg_tuples))[0]

    limiter = terranet.FronthaulEmulator(cfg_tuples, args.config_port, starting_index=cfg_tuples.index(default))
    topo = terranet.TerraNetTopo.from_komondor_config(cfg_tuples[0][0], limiter)
    net = terranet.TerraNet(topo=topo)

    net.start()

    import functools
    key = functools.partial(config_metric, net=net)
    best = sorted(cfg_tuples, key=key, reverse=True)[0]

    # Should be built before drawing
    terranet.draw_network(net, '/tmp/topology.png')
    topo_server = subprocess.Popen(['python2', '-m', 'SimpleHTTPServer', '{}'.format(args.topo_port)],
                                   cwd='/tmp/',
                                   stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'),
                                   close_fds=True)

    iperf_threads = []
    gw = net['gw']

    zmq_lock = threading.Lock()
    ctx = zmq.Context()
    s = ctx.socket(zmq.PUB)
    s.bind('tcp://127.0.0.1:{}'.format(args.metering_port))

    for client in filter(lambda h: isinstance(h, terranet.TerraNetClient), net.hosts):
        p = PseudoMeterer(gw, client, s, zmq_lock)
        iperf_threads.append(p)
        p.start()

    flipswitch = FronthaulEmulatorSwitch('localhost', 4567, limiter, cfg_tuples.index(default), cfg_tuples.index(best))
    flipswitch.start()

    # ipmininet.cli.IPCLI(net)

    try:
        raw_input('Press any key to exit')
    finally:
        print('Stopping...')
        print('Terminating Web server...')
        topo_server.terminate()

        print('Stopping Iperf client processes...')

        for t in iperf_threads:
            t.running = False

        for t in iperf_threads:
            t.join()

        print('Stopping flipswitch...')

        flipswitch.running = False
        flipswitch.join()
        s.close()

        print('Stopping mininet...')
        net.stop()


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


def generator_worker((iteration, channels), network, max_digits):
        config = generate_config(network["networks"], channels)
        template = get_template(config=config)
        suffix = format(iteration, "0{}".format(max_digits))
        file_name = os.path.join(args.cfg_dir, 'terranet_{}.cfg'.format(suffix))
        with open(file_name, "w") as f:
            f.write(template)


def generate(args):

    with open(args.topology, 'r') as f:
        network = json.load(f)

    ap_combinations = list(itertools.product(channel_combinations(),
                                             repeat=len(network["networks"])))

    max_digits = int(math.log10(len(ap_combinations))) + 1

    pool = multiprocessing.Pool()
    worker_func = functools.partial(generator_worker, network=network, max_digits=max_digits)
    pool.map(worker_func, enumerate(ap_combinations))
    pool.close()

    print('Generated {} configurations.'.format(len(ap_combinations)))


def init(q):
    global queue
    queue = q


def simulate(args):
    if not os.path.isdir(args.cfg_dir):
        raise ValueError("--cfg_dir must be a valid directory.")
    if not os.path.isdir(args.out_dir):
        raise ValueError("--out_dir must be a valid directory.")

    dirs = {"cfg": args.cfg_dir, "out": args.out_dir}
    komondor_args = {"time": args.time, "seed": args.seed}

    cfg_files = list(filter(
        lambda x: x.endswith(".cfg"),
        os.listdir(dirs["cfg"])
    ))
    print('Found {} configurations to simulate.'.format(len(cfg_files)))
    q = multiprocessing.Queue()
    bar = progress.bar.Bar('Simulating combinations', max=len(cfg_files))
    pool = multiprocessing.Pool(args.processes, initializer=init, initargs=(q,))
    f = functools.partial(komondor_worker, dirs=dirs, komondor=args.komondor,
                          komondor_args=komondor_args)
    t1 = time.time()
    async_res = pool.map_async(f, cfg_files)

    while not async_res.ready():
        try:
            r = q.get(timeout=5.0)
            if isinstance(r, RuntimeError):
                print(e)
            bar.next()
        except Exception as e:
            # Race condition
            # async might not be ready yet
            # but queue is already empty
            print(e)
            pass

    while not q.empty():
        try:
            q.get(False)
            bar.next()
        except:
            print('Timeout while waiting.')
            pass

    t2 = time.time()
    pool.close()
    bar.finish()
    print('Completed {} simulations in {} seconds.'.format(len(cfg_files), t2 - t1))


def komondor_worker(cfg, dirs, komondor=None, komondor_args=None):
    global queue
    cfg_file = os.path.abspath(os.path.join(dirs["cfg"], cfg))
    result_file = os.path.abspath(os.path.join(dirs["out"], cfg))
    args = komondor_args.copy()
    args["stats"] = result_file
    k = Komondor(executable=komondor)

    try:
        (proc, stdout, stderr) = k.run(cfg_file, **args)
        queue.put(stderr + stdout)
    except RuntimeError as e:
        return e

    return stderr


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    gen_parser = subparsers.add_parser('generate',
                                       help='Generate a permutation of possible Komondor configurations based on simple topology.')
    gen_parser.set_defaults(func=generate)

    gen_parser.add_argument('topology', type=str, help='JSON file containing the basic network topology.')
    gen_parser.add_argument('--cfg_dir', default='cfg', type=str,
                            help='Output directory for generated configurations. Defaults to "cfg".')

    simulate_parser = subparsers.add_parser('simulate', help='start Komondor simulator with generated configurations')
    simulate_parser.set_defaults(func=simulate)
    simulate_parser.add_argument('--cfg_dir',
                                 nargs='?',
                                 default="cfg",
                                 type=str,
                                 help='Input directory of generated configurations. Defaults to "cfg".')
    simulate_parser.add_argument('--out_dir',
                                 nargs='?',
                                 default="out",
                                 type=str,
                                 help='Output directory for simulation results. Defaults to "out".')
    simulate_parser.add_argument('--time',
                                 nargs='?',
                                 default=100,
                                 type=int,
                                 help="Simulation duration in seconds. Defaults to 100 seconds.")
    simulate_parser.add_argument('--seed',
                                 nargs='?',
                                 default=1000,
                                 type=int,
                                 help='')
    simulate_parser.add_argument('--processes',
                                 nargs='?',
                                 default=None,
                                 type=int,
                                 help='Number of parallel running simulations. Defaults to os.cpu_count().')
    simulate_parser.add_argument('--komondor',
                                 nargs='?',
                                 type=str,
                                 default='komondor',
                                 help='Path to Komondor executable. Defaults to "komondor".')

    run_parser = subparsers.add_parser('run', help='Run emulated Terranet in Mininet.')
    run_parser.set_defaults(func=run)
    run_parser.add_argument('cfg_path', help='Path to topology files for komondor simulation')
    run_parser.add_argument('out_path', help='Path to the simulation results')
    run_parser.add_argument('-t', '--topo-port',
                            help='Set port of web server serving the topology image. Defaults to 6666.',
                            type=int,
                            default=6666)
    run_parser.add_argument('-m', '--metering-port',
                            help='Set port for publishing flow metering info. Defaults to 5556.',
                            type=int,
                            default=5556)
    run_parser.add_argument('-c', '--config-port',
                            help='Set port for publishing configuration changes. Defaults to 4568.',
                            type=int,
                            default=4568)

    args = parser.parse_args()
    args.func(args)
