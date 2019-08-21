import threading
import terranet
import json
import logging
import zmq
import configparser
import math
import functools
import os
import subprocess
import multiprocessing
import sys


# TODO: Unify switches into one zmq interface with command handlers for different tasks
# That way we could use one port to connect to.
class FronthaulEmulatorSwitch(threading.Thread):
    def __init__(self, port, fh_emulator, default, best):
        super(FronthaulEmulatorSwitch, self).__init__()
        self.port =  port
        self.running = False
        self.fh_emulator = fh_emulator
        self.default = default
        self.best = best

    def run(self):
        self.running = True
        log = logging.getLogger(__name__)
        ctx = zmq.Context()
        rep = ctx.socket(zmq.REP)
        rep.bind('tcp://*:{}'.format(self.port))

        while self.running:
            rlist, _, _ = zmq.select([rep], [], [], 3.0)
            if rep in rlist:
                try:
                    topic, content = rep.recv_multipart()
                except ValueError:
                    log.exception('Received illegal message!')
                    rep.send_multipart(['Error', 'Error'])
                    continue
                except zmq.ZMQError as e:
                    log.exception('ZMQ Error: {}'.format(e))
                    continue

                with self.fh_emulator.lock:
                    index = self.best if content == 'true' else self.default
                    self.fh_emulator.current_tuple = self.fh_emulator.cfg_tuples[index]
                    self.fh_emulator.switch_config(self.fh_emulator.current_tuple)

                rep.send_multipart(['Ok', 'Ok'])

        rep.close()


class ClientSwitch(threading.Thread):
    def __init__(self, port, gw, net):
        super(ClientSwitch, self).__init__()
        self.port = port
        self.gw = gw
        self.net = net
        self.running = False

    def run(self):
        self.running = True
        log = logging.getLogger(__name__)

        ctx = zmq.Context()
        rep = ctx.socket(zmq.REP)
        rep.bind('tcp://*:{}'.format(self.port))

        log.info('Started client switch on port {}'.format(self.port))
        while self.running:

            rlist, _, _ = zmq.select([rep], [], [], 3.0)

            if rep not in rlist:
                continue

            try:
                name, state = rep.recv_multipart()
            except ValueError:
                log.exception('Exception while decoding message!')
                rep.send_multipart(['Error', 'Error'])
                continue
            except zmq.ZMQError:
                log.exception('ZMQ Error!')

            log.info('Received Request for Client {} --> {}'.format(name, state))

            if name in self.net:
                if state == 'on':
                    self.gw.start_iperf(self.net[name])
                    rep.send_multipart(['Ok', 'Ok'])
                    continue
                elif state == 'off':
                    self.gw.stop_iperf(self.net[name])
                    rep.send_multipart(['Ok', 'Ok'])
                    continue
                else:
                    log.warning('Received unknown command: {}'.format(state))

            rep.send_multipart(['Error', 'Error'])


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
    net = terranet.TerraNet(limiter, topo=topo, figure_path='/tmp/topology.png')

    log.info('Starting ipmininet...')
    net.start()

    key = functools.partial(config_metric, network=network_json)
    best = sorted(cfg_tuples, key=key, reverse=True)[0]

    topo_server = subprocess.Popen(['python2', '-m', 'SimpleHTTPServer', '{}'.format(args.topo_port)],
                                   cwd='/tmp/',
                                   stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'),
                                   close_fds=True)

    gw = net['gw']

    zmq_lock = threading.Lock()
    ctx = zmq.Context()
    s = ctx.socket(zmq.PUB)
    s.bind('tcp://127.0.0.1:{}'.format(args.metering_port))

    def report_iperf(src, dst, payload):
        with zmq_lock:
            try:
                # NOBLOCK necessary to prevent deadlock
                topic = 'flows'
                reports = json.dumps(src.reports)
                s.send_multipart([topic, reports], flags=zmq.NOBLOCK)

                topic = 'throughput'
                t = "{}".format(src.throughput)
                s.send_multipart([topic, t], flags=zmq.NOBLOCK)

                topic = 'fairness'
                fn = "{}".format(src.jains_fairness)
                s.send_multipart([topic, fn], flags=zmq.NOBLOCK)
            except zmq.ZMQError as e:
                log.error('Dropping message due to full queue')

    gw.iperf_report_cb = report_iperf
    gw.start_all_iperfs()

    flipswitch = FronthaulEmulatorSwitch(4567, limiter, cfg_tuples.index(default), cfg_tuples.index(best))
    flipswitch.start()

    cswitch = ClientSwitch(8888, gw, net)
    cswitch.start()

    try:
        terranet.TerraNetCLI(net)
    except:
        log.exception('Exception in IPCLI')
    finally:
        log.info('Stopping...')

        log.info('Terminating Web server...')
        topo_server.terminate()
        log.info('Terminated Web server.')

        log.info('Stopping flipswitch...')
        flipswitch.running = False
        flipswitch.join()

        log.info('Stopping cswitch...')
        cswitch.running = False
        cswitch.join()

        log.info('Stopping mininet...')
        net.stop()
        log.info('Mininet stopped.')
        s.close()


