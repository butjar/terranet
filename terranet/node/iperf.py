import os
import signal

from mininet.log import info, warn
from ipmininet.host import IPHost

class IperfHost(IPHost):
    def __init__(self, name,
                 autostart=True,
                 autostart_params=None,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)
        if "logfile" in kwargs:
            self.logfile = params["logfile"]
        else:
            self.logfile = "/var/log/iperf_{}.log".format(self.name)
        self.pids = {}
        self.bind_address = None
        self.autostart = autostart
        self.autostart_params = autostart_params

    def run_iperf(self,
                  bin="iperf3",
                  iperf_args="",
                  bind_address=None,
                  *args, **kwargs):
        iface = self.intfList()[0]
        if not bind_address:
            self.bind_address = iface.ip6

        # Kill current processes
        self.stop_iperf()
        # Implement iperf command in subclass
        pass

    def stop_iperf(self):
        for process, pid in self.pids.items():
            try:
                os.killpg(pid, signal.SIGHUP)
                info("Stopped process {} with PID {}.". format(process,
                                                              pid))
            except Exception as e:
                warn("""Could not stop process {} with PID: {}\n
                        {}""".format(process,
                                     pid,
                                     e))
        self.pids = {}

    def terminate(self):
        self.stop_iperf()
        super().terminate()


class IperfClient(IperfHost):
    def __init__(self, name,
                 host=None,
                 netstats_log=None,
                 *args, **kwargs):
        self.host = host
        self.netstats_log = netstats_log
        super().__init__(name,
                         *args, **kwargs)

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, host):
        if isinstance(host, IperfServer):
            self._host = host.intfList()[0].ip6
        else:
            self._host = host

    def run_iperf(self,
                  bin="iperf3",
                  iperf_args="-6 -t0 -i10 -u -b0 -l1400 -Z",
                  *args, **kwargs):
        super().run_iperf(bin=bin,
                          iperf_args=iperf_args,
                          *args, **kwargs)

        if not self.host:
            raise ValueError("""Host attribute must be set before running
                                iperf client.""")

        iface = self.intfList()[0]
        if not self.netstats_log:
            self.netstats_log = "/var/log/{}_{}_netstats.log".format(iface.name,
                                                                   iface.ip6)
        netstats_cmd = ("(while :; do "
                       "cat /proc/net/dev | grep {intf} > {logfile} 2>&1; "
                       "sleep {interval}; done) &").format(intf=iface.name,
                                                           logfile=self.netstats_log,
                                                           interval=2)
        p_netstats = self.popen(netstats_cmd, shell=True)
        self.pids.update({"netstats_logger": p_netstats.pid})

        # --logfile option requires iperf3 >= 3.1
        cmd = ("until ping6 -c1 {host} >/dev/null 2>&1; do :; done; "
               "{bin} {iperf_args} "
               "-c {host} "
               "-B {bind} "
               "--logfile {log}").format(bin=bin,
                                         iperf_args=iperf_args,
                                         host=self.host,
                                         bind=self.bind_address,
                                         log=self.logfile)
        p = self.popen(cmd, shell=True)
        self.pids.update({"iperf": p.pid})
        return p

    def stop_iperf(self):
        super().stop_iperf()
        if self.netstats_log:
            os.remove(self.netstats_log)
            self.netstats_log = None


class IperfReverseClient(IperfClient):
    def __init__(self, name,
                 *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)

    def run_iperf(self,
                  bin="iperf3",
                  iperf_args="-6 -R -t0 -i10 -u -b0 -l1400 -Z",
                  *args, **kwargs):
        super().run_iperf(bin=bin,
                          iperf_args=iperf_args,
                          *args, **kwargs)


class IperfServer(IperfHost):
    def __init__(self, name, *args, **kwargs):
        super().__init__(name,
                         *args, **kwargs)

    def run_iperf(self,
                  bin="iperf3",
                  iperf_args="-s",
                  *args, **kwargs):
        super().run_iperf(bin=bin,
                          iperf_args=iperf_args,
                          *args, **kwargs)

        # --logfile option requires iperf3 >= 3.1
        cmd = ("{bin} {iperf_args} "
               "-B {bind} "
               "--logfile {log}").format(bin=bin,
                                         iperf_args=iperf_args,
                                         bind=self.bind_address,
                                         log=self.logfile)
        p = self.popen(cmd, shell=True)
        self.pids.update({"iperf": p.pid})
        return p
