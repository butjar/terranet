import threading
import terranet
import select
import json
import time
import logging
import zmq
import configparser
import math
import functools
import os
import subprocess
import multiprocessing
import sys


class PseudoMeterer(threading.Thread):

    def __init__(self, src, dst, socket, zmq_lock):
        super(PseudoMeterer, self).__init__()
        self.running = False
        self.dst = dst
        self.src = src
        self.socket = socket
        self.zmq_lock = zmq_lock

    def run(self):
        self.running = True
        log = logging.getLogger(__name__)
        log.debug('Entering Iperf thread for client {}.'.format(self.dst.name))

        topic = 'flows/{}'.format(self.dst.name)
        p = None
        ip6 = None
        while ip6 is None:
            _, ip6 = terranet.address_pair(self.dst)
            if ip6 is None:
                log.debug('Waiting for IPv6 address of client {}'.format(self.dst.name))
                time.sleep(3)
                continue

        while self.running:

            duration = 3000  # Make it very long to have stable flows.
            cmd = 'iperf -y c -V -t {} -i 5 -c {}'.format(duration, ip6)

            log.debug('Starting iperf for client {} with: {}'.format(self.dst.name, cmd))
            p = self.src.popen(cmd)
            log.info('Started iperf process for client {} ({}).'.format(self.dst.name, ip6))

            while self.running:
                rlist, _, _ = select.select([p.stdout, p.stderr], [], [], 7)

                if not rlist:
                    log.warning('Iperf process for client {} timed out.'.format(self.dst.name))
                    continue

                if p.stderr in rlist:
                    err = p.stderr.readline()

                    if err != "":
                        err_out = p.stderr.readline()
                        log.warn('Iperf for client {} encountered an error: {} '.format(self.dst.name, err_out))

                if p.poll() is not None:
                    log.warn('Iperf process for client {} exited unexpectedly.'.format(self.dst.name))
                    time.sleep(3)
                    break

                if p.stdout in rlist:
                    o = p.stdout.readline()

                    if o == "":
                        break

                    payload = "{}".format(int(o.split(',')[8]) / 1e6)
                    time_span = float(o.split(',')[6].split('-')[1]) - float(o.split(',')[6].split('-')[0])

                    if time_span > duration:
                        continue  # Skip summary line

                    log.debug('Payload for client {}({}): {}'.format(self.dst.name, ip6, payload))

                    with self.zmq_lock:
                        try:
                            # NOBLOCK necessary to prevent deadlock
                            self.socket.send(topic, flags=zmq.SNDMORE | zmq.NOBLOCK)
                            self.socket.send(payload, flags=zmq.NOBLOCK)
                        except zmq.ZMQError:
                            log.error('Dropping message due to full queue')

            log.info('Iperf process for client {} ({}) exited.'.format(self.dst.name, ip6))

        if p and p.poll() is None:
            log.info('Stopping iperf process with pid {}'.format(p.pid))
            p.kill()


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
                    self.fh_emulator.switch_config(self.fh_emulator.current_tuple)

        sub.close()


def config_metric(cfg_tuple, network):
    p = configparser.ConfigParser()
    log = logging.getLogger(__name__)
    with open(cfg_tuple[1], 'r') as f:
        p.read_file(f)

    metric = 0.0
    for sta in filter(lambda s: s.startswith('Node_'), p.sections()):
        name = sta.split('Node_')[1]
        tp = p.getfloat(sta, 'throughput')
        wlan = p.get(sta, 'wlan')

        clients = None
        for n in network['networks']:
            if n['wlan_code'] != wlan:
                continue
            sta_index = int(name.split('STA_{}'.format(wlan))[1]) - 1
            clients = n['stas'][sta_index]['clients']

        if clients is None:
            log.debug('No client number specified for {}. Defaulting to 1.'.format(name))
            clients = 1

        try:
            metric += math.log(tp / clients) * clients if clients > 0 else 0
        except ValueError as e:
            log.debug('{} for {}->tp = {} in {}'.format(e, name, tp, cfg_tuple[1]))

    return metric


def config_parse_proxy(file):
    return terranet.config.Config.from_file(file)  # This is necessary to allow pickling for pool.map()


def run(args):
    log = logging.getLogger(__name__)

    if os.geteuid() != 0:
        log.error('This program needs to be run as root!')
        sys.exit(-1)

    pool = multiprocessing.Pool()
    join_cfg_paths = functools.partial(os.path.join, args.cfg_path)
    cfg_files = pool.map(join_cfg_paths,
                         filter(lambda p: p.endswith('.cfg') and os.path.isfile(os.path.join(args.cfg_path, p)),
                                os.listdir(args.cfg_path)))
    cfg_files.sort()

    if len(cfg_files) < 1:
        log.error('No configuration files found. Exiting...')
        pool.close()
        sys.exit(-1)

    join_out_paths = functools.partial(os.path.join, args.out_path)
    out_files = pool.map(join_out_paths,
                         filter(lambda p: p.endswith('.cfg') and os.path.isfile(os.path.join(args.out_path, p)),
                                os.listdir(args.cfg_path)))  # Use the same files names to get corresponding outputs
    out_files.sort()

    if len(out_files) != len(cfg_files):
        log.error('Missing simulation results for given configurations!')
        pool.close()
        sys.exit(-1)

    log.info('Found {} configurations and corresponding simulation results.'.format(len(cfg_files)))
    log.info('Parsing...')
    tn_configs = pool.map(config_parse_proxy, cfg_files)
    cfg_tuples = zip(tn_configs, out_files)
    pool.close()

    log.info('Searching results for default configuration...')
    default = list(filter(lambda cfg_tup: False not in
                                          map(lambda ap: int(ap.max_channel_allowed) - int(ap.min_channel_allowed) == 7,
                                              cfg_tup[0].get_access_points()),
                          cfg_tuples))[0]

    limiter = terranet.FronthaulEmulator(cfg_tuples, args.config_port, starting_index=cfg_tuples.index(default))
    log.info('Generating ipmininet topology...')

    with open(args.network) as f:
        network_json = json.load(f)

    topo = terranet.TerraNetTopo.from_network_dict(network_json, limiter)
    net = terranet.TerraNet(topo=topo)

    log.info('Starting ipmininet...')
    net.start()

    key = functools.partial(config_metric, network=network_json)
    best = sorted(cfg_tuples, key=key, reverse=True)[0]

    # Should be built before drawing
    # terranet.draw_network(net, '/tmp/topology.png')
    net.draw('/tmp/topology.png')
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

    try:
        terranet.TerraNetCLI(net)
    except:
        log.exception('Exception in IPCLI')
    finally:
        log.info('Stopping...')

        log.info('Terminating Web server...')
        topo_server.terminate()
        log.info('Terminated Web server.')

        log.info('Stopping Iperf client processes...')

        for t in iperf_threads:
            t.running = False

        for t in iperf_threads:
            t.join()

        log.info('Stopping flipswitch...')

        flipswitch.running = False
        flipswitch.join()
        s.close()

        log.info('Stopping mininet...')
        net.stop()
        log.info('Mininet stopped.')






