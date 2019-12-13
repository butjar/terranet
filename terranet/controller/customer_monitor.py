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
        self.influxclient.create_database(dbname)

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
            datapoint = {"tags": {}, "fields": {}}

            if stat.match.get("ipv6_src"):
                measurement = "ipv6_src_{}".format(stat.match["ipv6_src"])
                datapoint["measurement"] = measurement

            if stat.match.get("ipv6_dst"):
                measurement = "ipv6_dst_{}".format(stat.match["ipv6_dst"])
                datapoint["measurement"] = measurement

            datapoint["fields"].update({
                "packet_count": stat.packet_count,
                "byte_count": stat.byte_count
            })
            self.influxclient.write_points([datapoint])
            self.logger.info("CustomerMonitor: Received stats: "
                             "table_id {}, "
                             "match {}, "
                             "packet_count {}, "
                             "byte_count {}.".format(stat.table_id,
                                                     stat.match,
                                                     stat.packet_count,
                                                     stat.byte_count))
