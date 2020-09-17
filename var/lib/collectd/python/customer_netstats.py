#!/usr/bin/env python3
import glob, os
import collectd


PLUGIN_NAME = 'customer_netstats'
INTERVAL = 1 # seconds

def config(conf):
    pass

def parse_stats(path):
    netstats = []
    keys = ["iface",
            "rx_bytes", "rx_packets", "rx_errs", "rx_drop", "rx_fifo",
            "rx_frame", "rx_compressed", "rx_multicast",
            "tx_bytes", "tx_packets", "tx_errs", "tx_drop", "tx_fifo",
            "tx_colls", "tx_carrier", "tx_compressed"]

    with open(path) as f:
        while True:
            try:
                l = next(f).strip()
                items = l.split()
                # Parse lines with iface stats only
                if items[0][-1] != ":":
                    continue
                else:
                    iface = items[0][:-1]
                    values = [iface] + items[1:]
                    iface_stats = dict(zip(keys, values))
                    collectd.debug("Parsed iface stats {}.".format(iface_stats))
                    netstats.append(iface_stats)
            except StopIteration:
                break
    return netstats


def read(data={}):
    dir = "/tmp"
    g = os.path.join(dir, "*_netstat.log")
    for path in glob.glob(g):
        fname = os.path.basename(path)
        ipv6 = fname.split("_")[1]
        collectd.info("Parsing stats from {} @ {}".format(ipv6, path))
        try:
            data = parse_stats(path)
            collectd.info("Data {}".format(data))
        except Exception as err:
            pass
            collectd.error("Couldn't parse {}:\n{}".format(path, err))

        for iface_stats in data:
            collectd.info("Dispatching stats {}".format(data))
            if "tx_bytes" in iface_stats.keys():
                tx_bytes = iface_stats["tx_bytes"]
                collectd.Values(type='gauge',
                                plugin=PLUGIN_NAME,
                                type_instance="tx_bytes",
                                host=ipv6,
                                values=[tx_bytes]).dispatch()
            if "rx_bytes" in iface_stats.keys():
                rx_bytes = iface_stats["rx_bytes"]
                collectd.Values(type='gauge',
                                plugin=PLUGIN_NAME,
                                type_instance="rx_bytes",
                                host=ipv6,
                                values=[rx_bytes]).dispatch()

collectd.register_config(config)
collectd.register_read(read, INTERVAL)
