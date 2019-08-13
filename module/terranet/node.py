import threading
import logging
import os
import sys
import functools

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

        self.ctx = zmq.Context()
        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.bind('tcp://127.0.0.1:{}'.format(self.pub_port))

    def register(self, dn):
        self.registered_dns.append(dn)
        self.switch_config(self.current_tuple)

    def switch_config(self, cfg_tuple):
        log = logging.getLogger(__name__)
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

                clients = list(cn.clients())
                for c in clients:
                    c_intf = cn.get_tn_intf(c.name)

                    if c_intf is None:
                        log.error('No interface found for client {}'.format(c.name))
                        continue

                    c_intf.set_tbf(rate // len(clients))

        text = ''
        for ap in cfg_tuple[0].get_access_points():
            text += '<p>{name}: {min} -- {max} ({bw} MHz)</p>\n'.format(name=ap.short(),
                                                                        min=ap.min_channel_allowed,
                                                                        max=ap.max_channel_allowed,
                                                                        bw=20 * (int(ap.max_channel_allowed) - int(
                                                                            ap.min_channel_allowed) + 1))
            self.pub.send_multipart(['config', text])

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
    def __init__(self, name, pos=None, **params):
        self.pos = pos
        self.processes = []
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

    def connected_nodes(self):
        for i in filter(lambda i: isinstance(i, TerraNetIntf), self.intfList()):
            link = i.link
            node1, node2 = link.intf1.node, link.intf2.node
            if node1 == self:
                yield node2
            elif node2 == self:
                yield node1


class DistributionNode(TerraNetRouter):
    def __init__(self, name, fronthaul_emulator, wlan, *args, **params):
        self.fh_emulator = fronthaul_emulator
        self.wlan = wlan
        self.running = False

        super(DistributionNode, self).__init__(name, *args, **params)

        f = functools.partial(self.fh_emulator.channel_configuration_change, self.name)
        self.api_handler = API_handler(self.name, 6000, f, self.pid)

    def start(self):
        super(DistributionNode, self).start()
        self.fh_emulator.register(self)

        self.api_handler.start()

    def terminate(self):
        self.api_handler.running = False
        self.api_handler.join()
        super(DistributionNode, self).terminate()

    def client_nodes(self):
        return filter(lambda n: isinstance(n, ClientNode), self.connected_nodes())


class ClientNode(TerraNetRouter):
    def __init__(self, name, **params):
        super(ClientNode, self).__init__(name, **params)

    def clients(self):
        return filter(lambda n: isinstance(n, TerraNetClient), self.connected_nodes())


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
        with g_subprocess_lock:
            p = super(TerraNetClient, self).popen(*args, **kwargs)
        self.processes.append(p)
        return p

    def start(self):
        self.popen('iperf -s -V')


class TerraNetGateway(TerraNetRouter):
    def __init__(self, name, dev,  **params):
        super(TerraNetGateway, self).__init__(name, **params)
        # TODO: Make this work, without the disappearing intf afterwards
        # ipmininet.link.PhysicalInterface(dev, node=self) # Adds external interface to node

