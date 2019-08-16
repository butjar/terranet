import threading
import logging
import os
import sys
import functools
import time
import select

import copy
import configparser
import zmq

import ipmininet.router
import ipmininet.ipnet

from .link import TerraNetIntf
from .channel_api import API_handler

g_subprocess_lock = threading.Lock()


class FronthaulEmulator:
    def __init__(self, cfg_tuples, pub_port, starting_index=0):
        self.cfg_tuples = cfg_tuples
        self.current_tuple = cfg_tuples[starting_index]
        self.lock = threading.Lock()
        self.registered_dns = []
        self.pub_port = pub_port
        self._lock = threading.Lock()
        self.ctx = zmq.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind('tcp://127.0.0.1:{}'.format(self.pub_port))

    def register(self, dn):
        self.registered_dns.append(dn)
        self.switch_config(self.current_tuple)

    def switch_config(self, cfg_tuple):
        log = logging.getLogger(__name__)
        with self._lock:
            for dn in self.registered_dns:
                result_path = cfg_tuple[1]
                parser = configparser.ConfigParser()

                with open(result_path, 'r') as f:
                    parser.read_file(f)

                for cn in dn.client_nodes():
                    section = 'Node_{}'.format(cn.name)

                    try:
                        rate = max(parser.getint(section, 'throughput'), 8)
                    except configparser.Error:
                        log.exception('Could not find throughput for Client Node {}'.format(cn.name))
                        continue

                    fh_intf = dn.get_tn_intf(cn.name)

                    if fh_intf is None:
                        log.error('No interface found for ClientNode %s' % cn.name)
                        continue

                    fh_intf.set_tbf(rate)

                    clients = list(filter(lambda c: c.active, cn.clients()))
                    for c in clients:
                        c_intf = cn.get_tn_intf(c.name)

                        if c_intf is None:
                            log.error('No interface found for client {}'.format(c.name))
                            continue

                        c_intf.set_tbf(rate // max(1, len(clients)))

            text = ''
            for ap in cfg_tuple[0].get_access_points():
                text += '<p>{name}: {min} -- {max} ({bw} MHz)</p>\n'.format(name=ap.short(),
                                                                            min=ap.min_channel_allowed,
                                                                            max=ap.max_channel_allowed,
                                                                            bw=20 * (int(ap.max_channel_allowed) - int(
                                                                                ap.min_channel_allowed) + 1))
                self.pub.send_multipart(['config', text])

    def clients_changed(self):
        self.switch_config(self.current_tuple)

    def channel_configuration_change(self, dn_name, changes):
        log = logging.getLogger(__name__)
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
                log.error('Unable to find Distribution Node %s in current configuration!' % dn_name)
                return False

            # Search for equivalent config
            try:
                cfg_index = list(map(lambda t: t[0], self.cfg_tuples)).index(new_cfg)
            except ValueError:
                log.error('Unable to find equivalent configuration!')
                return False

            log.info('Changing to config {}'.format(cfg_index))
            sys.stdout.flush()

            self.current_tuple = self.cfg_tuples[cfg_index]
            self.switch_config(self.current_tuple)

            return True


class TerraNetRouter(ipmininet.router.Router):
    def __init__(self, name, pos=None, net=None, **params):
        self.pos = pos
        self.processes = []
        self.net = net
        super(TerraNetRouter, self).__init__(name, **params)

    def popen(self, *args, **kwargs):
        with g_subprocess_lock:
            p = super(TerraNetRouter, self).popen(*args, **kwargs)
        self.processes.append(p)
        return p

    def cmd(self, *args, **kwargs):
        """
        Overwriting cmd including the global subprocess lock. This will block ALL nodes from running commands in the
        meantime. DO NOT USE IF YOUR CMD IS A LONG RUNNING PROCESS! In this case use popen() instead.
        """
        with g_subprocess_lock:
            return super(TerraNetRouter, self).cmd(*args, **kwargs)

    def get_tn_intf(self, neighbor_name):
        intf = None
        for i in filter(lambda i: isinstance(i, TerraNetIntf), self.intfList()):
            if neighbor_name in [i.link.intf1.node.name, i.link.intf2.node.name]:
                intf = i
                break
        return intf

    def terminate(self):
        for p in self.processes:
            try:
                os.kill(-1 * p.pid, 9)
            except OSError:
                pass

        super(TerraNetRouter, self).terminate()

    def route_exists_v6(self, ip6):
        proc = self.popen('ip -6 route get {}'.format(ip6))
        proc.communicate()
        return proc.returncode == 0

    def neighbours(self):
        for i in filter(lambda i: isinstance(i, TerraNetIntf), self.intfList()):
            link = i.link
            node1, node2 = link.intf1.node, link.intf2.node
            if node1 == self:
                yield node2
            elif node2 == self:
                yield node1

    def connected_nodes(self):
        visited = {self}
        node_queue = list(self.neighbours())
        horizon = set(node_queue)

        while node_queue:
            n = node_queue.pop()

            if isinstance(n, TerraNetRouter):
                for neighbour in filter(lambda x: x not in visited and x not in horizon, n.neighbours()):
                    node_queue.append(neighbour)
                    horizon.add(neighbour)

            visited.add(n)

        visited.remove(self)
        return visited


class DistributionNode(TerraNetRouter):
    def __init__(self, name, fronthaul_emulator, wlan, api_port=6000, *args, **params):
        self.fh_emulator = fronthaul_emulator
        self.wlan = wlan
        self.running = False
        self.api_port = api_port

        super(DistributionNode, self).__init__(name, *args, **params)

        f = functools.partial(self.fh_emulator.channel_configuration_change, self.name)
        self.api_handler = API_handler(self.name, self.api_port, f, self.pid)

    def start(self):
        super(DistributionNode, self).start()
        self.fh_emulator.register(self)

        self.api_handler.start()

    def terminate(self):
        self.api_handler.running = False
        self.api_handler.join()
        super(DistributionNode, self).terminate()

    def client_nodes(self):
        return filter(lambda n: isinstance(n, ClientNode), self.neighbours())


class ClientNode(TerraNetRouter):
    def __init__(self, name, **params):
        super(ClientNode, self).__init__(name, **params)

    def clients(self):
        return filter(lambda n: isinstance(n, TerraNetClient), self.neighbours())


class TerraNetClient(ipmininet.ipnet.Host):
    def __init__(self, name, pos=None, net=None, **params):
        self.processes = []
        self.pos = pos
        self.net = net
        self._active = False
        super(TerraNetClient, self).__init__(name, **params)

    def terminate(self):
        for p in self.processes:
            try:
                os.kill(-1 * p.pid, 9)
            except OSError:
                pass

        super(TerraNetClient, self).terminate()

    def popen(self, *args, **kwargs):
        with g_subprocess_lock:
            p = super(TerraNetClient, self).popen(*args, **kwargs)
        self.processes.append(p)
        return p

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        prev = self._active
        self._active = value

        if value != prev:
            if self.net:
                self.net.fh_emulator.clients_changed()
                self.net.draw()

    def start(self):
        self.popen('iperf -s -V')


class TerraNetGateway(TerraNetRouter):
    def __init__(self, name, dev, iperf_report_cb=None, **params):
        self.connected_clients = set()
        self.iperf_threads = {}
        self.iperf_report_cb = iperf_report_cb
        super(TerraNetGateway, self).__init__(name, **params)
        # TODO: Make this work, without the disappearing intf afterwards
        # ipmininet.link.PhysicalInterface(dev, node=self) # Adds external interface to node

    def start_all_iperfs(self):
        for c in self.connected_clients:
            self.start_iperf(c)

    def stop_all_iperfs(self):
        for dst in self.iperf_threads.keys():
            self.iperf_threads[dst][1] = False

        for dst in self.iperf_threads.keys():
            self.iperf_threads[dst][0].join()

    def start_iperf(self, dst):
        log = logging.getLogger(__name__)
        if dst not in self.iperf_threads:
            t = threading.Thread(target=self._run_iperf, args=(dst,))
            self.iperf_threads[dst] = [t, True]

            if isinstance(dst, TerraNetClient):
                dst.active = True

            t.start()

        else:
            log.error('Iperf from {} to {} is already running!'.format(self.name, dst.name))

    def stop_iperf(self, dst):
        log = logging.getLogger(__name__)
        if dst not in self.iperf_threads:
            log.error('No iperf running from {} to {}!'.format(self.name, dst.name))
            return

        log.info('Stopping iperf from {} to {}...'.format(self.name, dst.name))
        self.iperf_threads[dst][1] = False
        self.iperf_threads[dst][0].join()

        if isinstance(dst, TerraNetClient):
            dst.active = False

        log.info('Iperf from {} to {} stopped.'.format(self.name, dst.name))
        del self.iperf_threads[dst]

    def terminate(self):
        self.stop_all_iperfs()
        super(TerraNetGateway, self).terminate()

    def _iperf_alive(self, dst):
        return dst in self.iperf_threads and self.iperf_threads[dst][1]

    def _run_iperf(self, dst):
        log = logging.getLogger(__name__)
        log.debug('Starting Iperf for client {}.'.format(dst.name))

        p = None

        while dst.intf().ip6 is None and self._iperf_alive(dst):
            log.debug('Waiting for IPv6 address of client {}'.format(dst.name))
            time.sleep(3)

        ip6 = dst.intf().ip6

        while not self.route_exists_v6(ip6) and self._iperf_alive(dst):
            log.debug('Waiting for route from {} to {}'.format(self.name, dst.name))
            time.sleep(3)


        while self._iperf_alive(dst):
            duration = 3000  # Make it very long to have stable flows.
            cmd = 'iperf -y c -V -t {} -i 5 -c {}'.format(duration, ip6)

            log.debug('Starting iperf for client {} with: {}'.format(dst.name, cmd))
            p = self.popen(cmd)
            log.info('Started iperf process for client {} ({}).'.format(dst.name, ip6))

            while self._iperf_alive(dst):
                rlist, _, _ = select.select([p.stdout, p.stderr], [], [], 7)

                if not rlist:
                    log.warning('Iperf process for client {} timed out.'.format(dst.name))
                    continue

                if p.stderr in rlist:
                    err = p.stderr.readline()

                    if err != "":
                        err_out = p.stderr.readline()
                        log.warn('Iperf for client {} encountered an error: {} '.format(dst.name, err_out))

                if p.stdout in rlist:
                    o = p.stdout.readline()

                    if o == "":
                        break

                    log.debug("Iperf stdout ({}): {}".format(dst.name, o))

                    payload = "{}".format(int(o.split(',')[8]) / 1e6)
                    time_span = float(o.split(',')[6].split('-')[1]) - float(o.split(',')[6].split('-')[0])

                    if time_span > duration:
                        continue  # Skip summary line

                    log.debug('Payload for client {}({}): {}'.format(dst.name, ip6, payload))
                    if hasattr(self.iperf_report_cb, '__call__'):
                        self.iperf_report_cb(self, dst, payload)

                if p.poll() is not None:
                    log.warn('Iperf process for client {} exited unexpectedly.'.format(dst.name))
                    time.sleep(3)
                    break


            log.info('Iperf process for client {} ({}) exited.'.format(dst.name, ip6))


        if p and p.poll() is None:
            log.info('Stopping iperf process with pid {}'.format(p.pid))
            p.kill()

    def start(self):
        super(TerraNetRouter, self).start()
        log = logging.getLogger(__name__)
        log.debug('Started Terranet gateway "{}"'.format(self.name))
        for n in filter(lambda h: isinstance(h, TerraNetClient), self.connected_nodes()):
            self.connected_clients.add(n)
