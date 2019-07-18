from __future__ import print_function

import terranet.config
import argparse
import os
import sys
import json
import threading
import copy
import configparser
import select
import zmq
import time
import subprocess
import math

import ipmininet.ipnet
import ipmininet.iptopo
import ipmininet.cli
import ipmininet.link
import ipmininet.router.config as ipcfg
import ipmininet.utils

import networkx
import matplotlib.pyplot


class OpenrConfig(ipcfg.RouterConfig):
    """A simple config with only a OpenR daemon"""

    def __init__(self, node, *args, **kwargs):
        defaults = {
            "redistribute_ifaces": "lo",
            "iface_regex_include": ".*",
            "enable_v4": True
        }
        super(OpenrConfig, self).__init__(node,
                                          daemons=((ipcfg.Openr, defaults),),
                                          *args, **kwargs)


class FronthaulEmulator:
    def __init__(self, cfg_tuples, pub_port, starting_index=0):
        self.cfg_tuples = cfg_tuples
        self.current_tuple = cfg_tuples[starting_index]
        self.lock = threading.Lock()
        self.registered_dns = []
        self.pub_port = pub_port

        self.ctx = zmq.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind('tcp://127.0.0.1:{}'.format(self.pub_port))

    def register(self, dn):
        self.registered_dns.append(dn)
        self.apply_global_config(self.current_tuple)

    def apply_global_config(self, cfg_tuple):
        for dn in self.registered_dns:
            result_path = cfg_tuple[1]
            parser = configparser.ConfigParser()

            with open(result_path, 'r') as f:
                parser.read_file(f)

            for s in parser.sections():
                if s.startswith('Node_') and 'wlan' in parser[s] and parser[s]['wlan'] == dn.wlan:
                    rate = max(parser.getint(s, 'throughput'), 8)
                    delay = max(parser.getfloat(s, 'delay'), 0.001)
                    delay = 10.0  # FIXME I think delay is not what we think it is.
                    burst = 0.5 * rate  # TODO: is this the right thing to do?
                    burst = 32e3
                    cn_name = s.split('Node_')[1]
                    dn.limit(cn_name, rate, burst, delay)

        text = ''
        for ap in cfg_tuple[0].get_access_points():
            text += '<p>{name}: {min} -- {max} ({bw} MHz)</p>\n'.format(name=ap.short(),
                                                                        min=ap.min_channel_allowed,
                                                                        max=ap.max_channel_allowed,
                                                                        bw=20 * (int(ap.max_channel_allowed) - int(
                                                                            ap.min_channel_allowed) + 1))
            self.pub.send_multipart(['config', text])

    def change_global_config(self, dn_name, changes):
        with self.lock:
            new_cfg = copy.deepcopy(self.current_tuple[0])

            try:
                dn = iter(filter(lambda ap: ap.short() == dn_name, new_cfg.get_access_points())).next()
                stas = filter(lambda s: s.wlan_code == dn.wlan_code, new_cfg.get_stations())

                dn.min_channel_allowed = changes['min_channel_allowed']
                dn.max_channel_allowed = changes['max_channel_allowed']

                for sta in stas:
                    sta.min_channel_allowed = changes['min_channel_allowed']
                    sta.max_channel_allowed = changes['max_channel_allowed']

            except IndexError:
                print('Unable to find Distribution Node %s in current configuration!' % dn_name)
                return False

            # Search for equivalent config
            try:
                cfg_index = list(map(lambda t: t[0], self.cfg_tuples)).index(new_cfg)
            except ValueError:
                print('Unable to find equivalent configuration!')
                return False

            print('Changing to config {}'.format(cfg_index))
            sys.stdout.flush()

            self.current_tuple = self.cfg_tuples[cfg_index]
            self.apply_global_config(self.current_tuple)

            return True


class DistributionNode(ipmininet.router.Router):
    def __init__(self, name, fronthaul_emulator, wlan, pos=None, **params):
        self.fh_emulator = fronthaul_emulator
        self.pos = pos
        self.processes = []
        self.wlan = wlan
        self.ap_daemon_handler = threading.Thread(target=self.handle_ap_daemon)
        self.ap_daemon = None
        self.running = False

        super(DistributionNode, self).__init__(name, **params)

    def start(self):
        # TODO Maybe start Iperf client
        super(DistributionNode, self).start()
        self.running = True
        self.ap_daemon_handler.start()
        self.fh_emulator.register(self)

    def terminate(self):
        self.running = False
        for p in self.processes:
            try:
                if p != self.ap_daemon_handler:
                    os.kill(-1 * p.pid, 9)
            except OSError:
                pass
        self.ap_daemon_handler.join()
        super(DistributionNode, self).terminate()

    def popen(self, *args, **kwargs):
        p = super(DistributionNode, self).popen(*args, **kwargs)
        self.processes.append(p)
        return p

    def apply_local_config(self, cfg):
        if not self.fh_emulator.change_global_config(self.name, cfg):
            print('Could not apply new local config for DN %s' % self.name)
        else:
            print('Applied new config for DN %s' % self.name)

        sys.stdout.flush()

    def limit(self, cn_name, rate, burst, latency):
        print('LIMIT %s' % cn_name)
        if_name = None
        for i in self.intfList():
            if cn_name in [i.link.intf1.node.name, i.link.intf2.node.name]:
                if_name = i.name
                break

        if if_name is None:
            print('No interface found for ClientNode %s' % cn_name)
            return
        burst_kbit = burst // 1024
        cmd = 'tc qdisc add dev %s root tbf rate %dbit burst %dkbit latency %0.3fms' % (
            if_name, rate, burst_kbit, latency)
        cmd_replace = 'tc qdisc replace dev %s root tbf rate %dbit burst %dkbit latency %0.3fms' % (
            if_name, rate, burst_kbit, latency)
        self.cmdPrint(cmd_replace)  # Replace possibly existing previous rule
        self.cmdPrint(cmd)  # Just to make sure. This is lazy. I know.

    def handle_ap_daemon(self):
        self.ap_daemon = self.popen('python -m terranet.ap_daemon')
        out = self.ap_daemon.stdout
        err = self.ap_daemon.stderr
        print('Starting AP daemon ({pid})'.format(pid=self.ap_daemon.pid))
        while self.running:
            readfds, _, _ = select.select([out, err], [], [], 3.0)
            if err in readfds:
                print(err.readline().strip())
            if out not in readfds:
                continue
            line = out.readline()

            if line == '':
                break
            try:
                new_cfg = json.loads(line)
                self.apply_local_config(new_cfg)
            except ValueError as e:
                print('Ignoring invalid config: %s' % e)
                print('Line: {}'.format(line.strip()))

        os.kill(-1 * self.ap_daemon.pid, 9)
        print('AP daemon exited.')


class ClientNode(ipmininet.router.Router):
    def __init__(self, name, pos=None, **params):
        self.pos = pos
        super(ClientNode, self).__init__(name, **params)


class TerraNetClient(ipmininet.ipnet.Host):
    def __init__(self, name, pos=None, **params):
        self.processes = []
        self.pos = pos
        super(TerraNetClient, self).__init__(name, **params)

    def terminate(self):
        for p in self.processes:
            try:
                os.kill(-1 * p.pid, 9)
            except OSError:
                pass

        super(TerraNetClient, self).terminate()

    def popen(self, *args, **kwargs):
        p = super(TerraNetClient, self).popen(*args, **kwargs)
        self.processes.append(p)
        return p

    def start(self):
        self.popen('iperf -s -V')


class TerraNetGateway(ipmininet.router.Router):
    def __init__(self, name, dev, pos=None, **params):
        self.pos = pos
        super(TerraNetGateway, self).__init__(name, **params)
        # TODO: Make this work, without the disappearing intf afterwards
        # ipmininet.link.PhysicalInterface(dev, node=self) # Adds external interface to node


class TerraNetTopo(ipmininet.iptopo.IPTopo):
    @classmethod
    def from_komondor_config(cls, cfg, fh_emulator):
        topo = cls()
        prev = None
        for ap in cfg.get_access_points():
            topo.addRouter(ap.short(), cls=DistributionNode, fronthaul_emulator=fh_emulator, wlan=ap.wlan_code,
                           pos=(float(ap.x), float(ap.y)),
                           config=OpenrConfig, )#privateDirs=['/tmp', '/var/log'])

            if prev is not None:
                topo.addLink(prev.short(), ap.short())

            for sta in filter(lambda s: s.wlan_code == ap.wlan_code, cfg.get_stations()):
                topo.addRouter(sta.short(), cls=ClientNode, pos=(float(sta.x), float(sta.y)), config=OpenrConfig,
                               )#privateDirs=['/tmp', '/var/log'])
                topo.addLink(ap.short(), sta.short())

                num_clients = 1  # TODO  For now every station gets three clients, make this configurable
                for i in range(1, num_clients + 1):
                    client_name = sta.short() + '_C%d' % i
                    topo.addHost(client_name, cls=TerraNetClient,
                                 pos=(float(sta.x) + ((i - 1) * 8), float(sta.y) + 5 + ((i - 1) * 3)))
                    topo.addLink(sta.short(), client_name)

            prev = ap

        # TODO Gateway + Controller instance.
        # --> idea: take an external intf and drag it into gw namespace. Then make gw a NAT node
        # Problems: no IPv6 at TUB :_( + IPv4 Routing screwed up in OpenR
        topo.addRouter('gw', cls=TerraNetGateway, dev='enp0s3', config=OpenrConfig,
                       pos=(float(prev.x) + 20, float(prev.y)),
                       )#privateDirs=['/tmp', '/var/log'])  # Gateway -- Not a DN
        topo.addLink(prev.short(), 'gw')

        return topo


class TerraNet(ipmininet.ipnet.IPNet):
    def start(self):
        super(TerraNet, self).start()
        for client in filter(lambda h: isinstance(h, TerraNetClient), self.hosts):
            client.start()


def draw_network(net, path):
    g = net.topo.convertTo(networkx.MultiGraph)
    positions = {}
    color = {}
    for name in net:
        n = net[name]
        positions[n.name] = n.pos
        if isinstance(n, TerraNetClient):
            color[n.name] = 'g'
        elif isinstance(n, ClientNode):
            color[n.name] = 'orange'
        else:
            color[n.name] = 'r'

    nodelist = g.nodes()
    colorlist = list(map(lambda n: color[n], nodelist))

    networkx.draw(g, pos=positions, nodelist=nodelist, node_color=colorlist, node_size=1e3, with_labels=True)
    matplotlib.pyplot.savefig(path)


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


def main(args):
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

    limiter = FronthaulEmulator(cfg_tuples, args.config_port,starting_index=cfg_tuples.index(default))
    topo = TerraNetTopo.from_komondor_config(cfg_tuples[0][0], limiter)
    net = TerraNet(topo=topo)

    net.start()

    import functools
    key = functools.partial(config_metric, net=net)
    best = sorted(cfg_tuples, key=key, reverse=True)[0]

    # Should be built before drawing
    draw_network(net, '/tmp/topology.png')
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

    for client in filter(lambda h: isinstance(h, TerraNetClient), net.hosts):
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('cfg_path', help='Path to topology files for komondor simulation')
    parser.add_argument('out_path', help='Path to the simulation results')
    parser.add_argument('-t', '--topo-port',
                        help='Set port of web server serving the topology image. Defaults to 6666.',
                        type=int,
                        default=6666)
    parser.add_argument('-m', '--metering-port',
                        help='Set port for publishing flow metering info. Defaults to 5556',
                        type=int,
                        default=5556)
    parser.add_argument('-c', '--config-port',
                        help='Set port for publishing configuration changes. Defaults to 4568',
                        type=int,
                        default=4568)

    arguments = parser.parse_args()

    main(arguments)
