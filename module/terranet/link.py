import logging

import ipmininet.link


class TerraNetIntf(ipmininet.link.IPIntf):
    kernel_HZ = 300  # TODO We should verify that that is somehow the HZ value of the current kernel

    def __init__(self, *args, **kwargs):
        self.bw_limited = False
        self.rate = None
        self.burst = None
        self.latency = None
        super(TerraNetIntf, self).__init__(*args, **kwargs)

    def set_tbf(self, rate, burst=None, latency=None):
        """
        Uses the linux tc command to apply a Token Bucket Filter to the interface.
        :param rate: Desired output rate in bits/s. Corresponds to the number of tokens generated.
        :param burst: The size of the token bucket in Bytes.
        :param latency: Maximum time a packet can wait for tokens in ms.
        :return:
        """

        log = logging.getLogger(__name__)
        if not burst:
            burst = int((rate * 1.01) // (self.kernel_HZ * 8))  # Allow minimal burstiness by default.

        if not latency:
            latency = 10  # ms --> High values do not hurt so much...

        if self.bw_limited:
            log.debug('Replacing existing bandwidth limit on intf {}.'.format(self.name))
            cmd = 'tc qdisc replace dev {} root'.format(self.name)
        else:
            cmd = 'tc qdisc add dev {} root'.format(self.name)

        if burst < int(rate // (self.kernel_HZ * 8)):
            log.warning('Burst parameter is smaller than rate/HZ! The desired rate might not be achieved!')

        cmd += ' tbf rate {:d}bit burst {:d}b latency {:.3f}ms'.format(rate, burst, latency)
        log.info('Setting Token Bucket Filter for {} ({:d} bit/s -- {:d} Bytes - {:.3f}ms)'.format(self.name,
                                                                                                  rate,
                                                                                                  burst,
                                                                                                  latency))
        out = self.node.cmd(cmd)
        log.debug('TC returned: {}'.format(out))

        # TODO: Check if tc was successful!
        self.bw_limited = True
        self.rate = rate
        self.burst = burst
        self.latency = latency

    def set_delay(self):
        pass


class TerraNetLink(ipmininet.link.IPLink):
    def __init__(self, node1, node2, intf=TerraNetIntf, *args, **kwargs):
        super(TerraNetLink, self).__init__(node1=node1, node2=node2,
                                           intf=intf, *args, **kwargs)
