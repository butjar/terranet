import threading
import logging
import os
import sys
import select
import json

import copy
import configparser
import zmq

import ipmininet.router
import ipmininet.ipnet


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
        log = logging.getLogger(__name__)
        if not self.fh_emulator.change_global_config(self.name, cfg):
            log.error('Could not apply new local config for DN %s' % self.name)
        else:
            log.info('Applied new config for DN %s' % self.name)

        sys.stdout.flush()

    def limit(self, cn_name, rate, burst, latency):
        log = logging.getLogger(__name__)
        log.debug('LIMIT %s' % cn_name)
        if_name = None
        for i in self.intfList():
            if cn_name in [i.link.intf1.node.name, i.link.intf2.node.name]:
                if_name = i.name
                break

        if if_name is None:
            log.error('No interface found for ClientNode %s' % cn_name)
            return

        burst_kbit = burst // 1024
        cmd = 'tc qdisc add dev %s root tbf rate %dbit burst %dkbit latency %0.3fms' % (
            if_name, rate, burst_kbit, latency)
        cmd_replace = 'tc qdisc replace dev %s root tbf rate %dbit burst %dkbit latency %0.3fms' % (
            if_name, rate, burst_kbit, latency)
        self.cmdPrint(cmd_replace)  # Replace possibly existing previous rule
        self.cmdPrint(cmd)  # Just to make sure. This is lazy. I know.

    def handle_ap_daemon(self):
        log = logging.getLogger(__name__)
        # Make sure we are starting the current interpreter, with all the required modules.
        python_path = sys.executable
        if not python_path:
            python_path = 'python'

        self.ap_daemon = self.popen('{} -m terranet.ap_daemon'.format(python_path))
        out = self.ap_daemon.stdout
        err = self.ap_daemon.stderr
        log.info('Starting AP daemon ({pid})'.format(pid=self.ap_daemon.pid))
        while self.running:
            readfds, _, _ = select.select([out, err], [], [], 3.0)
            if err in readfds:
                log.debug(err.readline().strip())
            if out not in readfds:
                continue
            line = out.readline()

            if line == '':
                break
            try:
                new_cfg = json.loads(line)
                self.apply_local_config(new_cfg)
            except ValueError as e:
                log.debug('Ignoring invalid config: %s' % e)
                log.debug('Line: {}'.format(line.strip()))

        os.kill(-1 * self.ap_daemon.pid, 9)
        log.info('AP daemon exited.')


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
