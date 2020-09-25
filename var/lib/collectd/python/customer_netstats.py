#!/usr/bin/env python3
import glob, os
import collectd


# Plugin vars
PLUGIN_NAME = 'customer_netstats'
IS_READ_REGISTERED = False
KEYS = ['iface',
        'rx_bytes', 'rx_packets', 'rx_errs', 'rx_drop', 'rx_fifo',
        'rx_frame', 'rx_compressed', 'rx_multicast',
        'tx_bytes', 'tx_packets', 'tx_errs', 'tx_drop', 'tx_fifo',
        'tx_colls', 'tx_carrier', 'tx_compressed']

# Default config
NETSTAT_LOG_DIR = '/var/log'
INTERVAL = 1
FILE_GLOB = '*_netstat.log'
DISPATCH_KEYS = ('rx_bytes', 'tx_bytes')


def config(conf):
    global NETSTAT_LOG_DIR, INTERVAL, DISPATCH_KEYS, FILE_GLOB
    for node in conf.children:
        if node.key == 'NetstatLogDir' and node.values:
            val = node.values[0]
            collectd.info('Setting NetstatLogDir: {}'.format(val))
            NETSTAT_LOG_DIR = val
        if node.key == 'Interval' and node.values:
            try:
                val = int(node.values[0])
                collectd.info('Setting Interval: {}'.format(val))
                INTERVAL = val
            except ValueError as e:
                collectd.error('Could not parse integer from Interval setting.')
                collectd.error('Error message: {}'.format(e))
        if node.key == 'FileGlob' and node.values:
            val = node.values[0]
            collectd.info('Setting FileGlob: {}'.format(val))
            FILE_GLOB = val
        if node.key == 'DispatchKeys' and node.values:
            val = node.values
            collectd.info('Setting DispatchKeys: {}'.format(val))
            DISPATCH_KEYS = val

    global IS_READ_REGISTERED
    if not IS_READ_REGISTERED:
        collectd.debug('Registering callback function {}' \
                       ' at Interval {}s'.format(read,
                                                 INTERVAL))
        collectd.register_read(read, INTERVAL)
        IS_READ_REGISTERED = True
        collectd.info('Read callback registered.')


def _parse_stats(path):
    netstats = []
    with open(path) as f:
        while True:
            try:
                l = next(f).strip()
                items = l.split()
                # Parse lines with iface stats only
                if items[0][-1] != ':':
                    continue
                else:
                    iface = items[0][:-1]
                    values = [iface] + items[1:]
                    iface_stats = dict(zip(KEYS, values))
                    collectd.debug('Parsed iface stats from file {}:\n' \
                                   '{}'.format(path, iface_stats))
                    netstats.append(iface_stats)
            except StopIteration:
                break
    return netstats


def _dispatch_values(values,
                     type_instance,
                     host,
                     type='gauge',
                     plugin=PLUGIN_NAME):
    collectd.info('Dispatching {}@{} {}'.format(type_instance, host, values))
    collectd.Values(values=values, type_instance=type_instance, host=host,
                    type=type, plugin=plugin).dispatch()


def read(data={}):
    g = os.path.join(NETSTAT_LOG_DIR, FILE_GLOB)
    collectd.debug('Looking for files that match {}'.format(g))
    for path in glob.glob(g):
        fname = os.path.basename(path)
        ipv6 = fname.split('_')[1]
        collectd.debug('Parsing stats from {} @ {}'.format(ipv6, path))
        try:
            data = _parse_stats(path)
            collectd.debug('Data {}'.format(data))
        except Exception as err:
            collectd.error('Could not parse {}.'.format(path))
            collectd.error('{}'.format(err))

        for iface_stats in data:
            for dispatch_key in DISPATCH_KEYS:
                if dispatch_key in iface_stats.keys():
                    values = [iface_stats[dispatch_key]]
                    _dispatch_values(values, dispatch_key, ipv6)


collectd.register_config(config)
