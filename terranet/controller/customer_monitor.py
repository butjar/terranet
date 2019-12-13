from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

from influxdb import InfluxDBClient

import customer_flow_matching


class CustomerMonitor(customer_flow_matching.CustomerFlowMatching):
    """
    https://osrg.github.io/ryu-book/en/html/traffic_monitor.html
    """

    INTERVAL = 10
    DB_NAME = "customerflows"

    def __init__(self, *args, **kwargs):
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)
        self._init_influxdb()
        super(CustomerMonitor, self).__init__(*args, **kwargs)

    def _init_influxdb(self):
        dbname = self.__class__.DB_NAME
        self.influxclient = InfluxDBClient(username="admin",
                                           password="admin",
                                           database=dbname)
        self.influxclient.drop_database(dbname)
        self.influxclient.create_database(dbname)

        # Create continous query to sample throughputs
        interval = self.__class__.INTERVAL
        throughputs_select = '''SELECT non_negative_derivative(max("value"), 1s) * 8
                                AS "value"
                                INTO "throughputs"
                                FROM "byte_count_in"
                                WHERE time > now() -{}s
                                GROUP BY time({}s), "ipv6"'''.format(interval,
                                                                     interval)
        self.influxclient.create_continuous_query('throughputs',
                                                  throughputs_select,
                                                  database='customerflows')

        # Create continous query for total net throughput
        net_throughput_select = '''SELECT sum("value")
                                   AS "value"
                                   INTO "net_throughput"
                                   FROM "throughputs"
                                   GROUP BY time({}s)'''.format(interval)
        self.influxclient.create_continuous_query('net_throughput',
                                                  net_throughput_select,
                                                  database='customerflows')

        net_throughput_squared_select = '''
            SELECT pow(last("value"), 2)
            AS "net_throughput_squared"
            INTO "janes_data"
            FROM "net_throughput"
            GROUP BY time({}s)'''.format(interval)
        self.influxclient.create_continuous_query(
            'net_throughput_squared', net_throughput_squared_select,
            database='customerflows')

        # Create continous query for customer count
        customer_count_select = '''SELECT count("last")
                                   AS "customer_count"
                                   INTO "janes_data"
                                   FROM (SELECT last("value")
                                         FROM "throughputs"
                                         GROUP BY "ipv6")
                                   GROUP BY time({}s)'''.format(interval)
        self.influxclient.create_continuous_query('customer_count',
                                                  customer_count_select,
                                                  database='customerflows')

        sum_squared_throughputs_select = '''
            SELECT sum("squares")
            AS "sum_squared_throughputs"
            INTO "janes_data"
            FROM (SELECT pow(last("value"), 2)
                  AS "squares"
                  FROM "throughputs"
                  GROUP BY "ipv6")
            GROUP BY time({}s)'''.format(interval)
        self.influxclient.create_continuous_query(
            'sum_squared_throughputs', sum_squared_throughputs_select,
            database='customerflows')

        # Create continous query for Jane's fairness index
        fairness_index_select = '''SELECT last("fairness_index")
                                   AS "value"
                                   INTO "janes_fairness_index"
                                   FROM (SELECT "net_throughput_squared"
                                                / "customer_count"
                                                / "sum_squared_throughputs"
                                         AS "fairness_index"
                                         FROM "janes_data")
                                   GROUP BY time({}s)'''.format(interval)
        self.influxclient.create_continuous_query('fairness_index',
                                                  fairness_index_select,
                                                  database='customerflows')

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.debug("CustomerMonitor: Register "
                                  "datapath {}.".format(datapath.id))
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug("CustomerMonitor: Unregister "
                                  "datapath {}.".format(datapath.id))
                del self.datapaths[datapath.id]

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                self._request_customer_stats(dp)
            hub.sleep(self.__class__.INTERVAL)

    def _request_customer_stats(self, datapath):
        self.logger.debug("CustomerMonitor: Sending stats request to "
                          "datapath {}.".format(datapath.id))
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.debug("{}".format(self.customer_table_allocation))
        for dn_id, values in self.customer_table_allocation.items():
            table_id = values["table_id"]
            req = parser.OFPFlowStatsRequest(datapath, table_id=table_id)
            datapath.send_msg(req)
            self.logger.info("CustomerMonitor: "
                             "Requested table stats for DN {} "
                             "at table_id {}.".format(dn_id,
                                                      table_id))

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body

        for stat in [flow for flow in body if flow.priority > 1]:
            if stat.match.get("ipv6_src"):
                ipv6 = stat.match["ipv6_src"]
                measurements = ("packet_count_out", "byte_count_out")

            if stat.match.get("ipv6_dst"):
                ipv6 = stat.match["ipv6_dst"]
                measurements = ("packet_count_in", "byte_count_in")

            datapoints = [
                {
                    "measurement": measurements[0],
                    "tags": {
                        "ipv6": ipv6
                    },
                    "fields": {
                        "value": stat.packet_count
                    }
                },
                {
                    "measurement": measurements[1],
                    "tags": {
                        "ipv6": ipv6
                    },
                    "fields": {
                        "value": stat.byte_count
                    }
                }
            ]

            self.influxclient.write_points(datapoints)
            self.logger.info("CustomerMonitor: Received stats: "
                             "table_id {}, "
                             "match {}, "
                             "packet_count {}, "
                             "byte_count {}.".format(stat.table_id,
                                                     stat.match,
                                                     stat.packet_count,
                                                     stat.byte_count))
