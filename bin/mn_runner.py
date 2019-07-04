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

import ipmininet.ipnet
import ipmininet.iptopo
import ipmininet.cli
import ipmininet.link
import ipmininet.router.config as ipcfg
import ipmininet.utils


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
    def __init__(self, cfg_tuples, starting_index=0):
        self.cfg_tuples = cfg_tuples
        self.current_tuple = cfg_tuples[starting_index]
        self.lock = threading.Lock()
        self.registered_dns = []

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
                    delay = 10.0 # FIXME I think delay is not what we think it is.
                    burst = 0.5*rate  # TODO: is this the right thing to do?
                    burst = 32e3
                    cn_name = s.split('Node_')[1]
                    dn.limit(cn_name, rate, burst, delay)

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
    def __init__(self, name, fronthaul_emulator, wlan, **params):
        self.fh_emulator = fronthaul_emulator
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
        cmd = 'tc qdisc add dev %s root tbf rate %dbit burst %dkbit latency %0.3fms' % (if_name, rate, burst_kbit, latency)
        cmd_replace = 'tc qdisc replace dev %s root tbf rate %dbit burst %dkbit latency %0.3fms' % (if_name, rate, burst_kbit, latency)
        self.cmdPrint(cmd_replace)  # Replace possibly existing previous rule
        self.cmdPrint(cmd) # Just to make sure. This is lazy. I know.

    def handle_ap_daemon(self):
        self.ap_daemon = self.popen('python ap_daemon.py')
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
    def __init__(self, name, **params):
        super(ClientNode, self).__init__(name, **params)


class TerraNetClient(ipmininet.ipnet.Host):
    def __init__(self, name, **params):
        self.processes = []
        super(TerraNetClient, self).__init__(name, **params)

    def terminate(self):
        for p in self.processes:
            try:
                os.kill(-1*p.pid, 9)
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
    def __init__(self, name, dev, **params):
        super(TerraNetGateway, self).__init__(name, **params)
        # TODO: Make this work, without the disappearing intf afterwards
        # ipmininet.link.PhysicalInterface(dev, node=self) # Adds external interface to node


class TerraNetTopo(ipmininet.iptopo.IPTopo):
    @classmethod
    def from_komondor_config(cls, cfg, fh_emulator):
        topo = cls()
        prev = None
        for ap in cfg.get_access_points():
            topo.addRouter(ap.short(), cls=DistributionNode, fronthaul_emulator=fh_emulator, wlan=ap.wlan_code, config=OpenrConfig, privateDirs=['/tmp', '/var/log'])

            if prev is not None:
                topo.addLink(prev.short(), ap.short())

            for sta in filter(lambda s: s.wlan_code == ap.wlan_code, cfg.get_stations()):
                topo.addRouter(sta.short(), cls=ClientNode, config=OpenrConfig, privateDirs=['/tmp', '/var/log'])
                topo.addLink(ap.short(), sta.short())

                num_clients = 1 # TODO  For now every station gets three clients, make this configurable
                for i in range(1, num_clients+1):
                    client_name = sta.short() + '_C%d' % i
                    topo.addHost(client_name, cls=TerraNetClient)
                    topo.addLink(sta.short(), client_name)

            prev = ap

        # TODO Gateway + Controller instance.
        # --> idea: take an external intf and drag it into gw namespace. Then make gw a NAT node
        # Problems: no IPv6 at TUB :_( + IPv4 Routing screwed up in OpenR
        topo.addRouter('gw', cls=TerraNetGateway, dev='enp0s3', config=OpenrConfig, privateDirs=['/tmp', '/var/log'])  # Gateway -- Not a DN
        topo.addLink(prev.short(), 'gw')

        return topo


class TerraNet(ipmininet.ipnet.IPNet):
    def start(self):
        super(TerraNet, self).start()
        for client in filter(lambda h: isinstance(h, TerraNetClient), self.hosts):
            client.start()


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

    limiter = FronthaulEmulator(cfg_tuples)
    topo = TerraNetTopo.from_komondor_config(cfg_tuples[0][0], limiter)
    net = TerraNet(topo=topo)

    net.start()

    iperf_threads = []
    gw = net['gw']

    zmq_lock = threading.Lock()
    ctx = zmq.Context()
    s = ctx.socket(zmq.PUB)
    s.bind('tcp://127.0.0.1:5556')

    for client in filter(lambda h: isinstance(h, TerraNetClient), net.hosts):
        p = PseudoMeterer(gw, client, s, zmq_lock)
        iperf_threads.append(p)
        p.start()

    #ipmininet.cli.IPCLI(net)
    raw_input('Press any key to exit')

    for t in iperf_threads:
        t.running = False

    for t in iperf_threads:
        t.join()

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
                time.sleep(5)
                continue
            p = self.src.popen('iperf -y c -V -t 10 -c %s' % ip6)
            o, e = p.communicate()

            if e != '':
                time.sleep(5)
                continue
            payload = "{}".format(int(o.split(',')[8]) / 1e6)
            with self.lock:
                msg = '{topic},{payload}'.format(topic=topic, payload=payload)
                #print(msg)
                self.socket.send(topic, flags=zmq.SNDMORE)
                self.socket.send(payload)




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('cfg_path', help='Path to topology files for komondor simulation')
    parser.add_argument('out_path', help='Path to the simulation results')
    arguments = parser.parse_args()
    main(arguments)
