import os
import functools

import requests

from ryu.controller.handler import set_ev_cls
from ryu.lib import hub

from terranet.wifi.komondor_config import KomondorConfig, \
                                          read_komondor_configs, \
                                          read_komondor_results

from .customer_flow_pipeline import EventCustomerFlowAdded, \
    EventCustomerFlowRemoved
from .customer_allocation_monitor import CustomerAllocationMonitor
from .ipv6_address_helper import IPv6AddressHelper

class ChannelAssignmentOracle(CustomerAllocationMonitor):
    def __init__(self, *args, **kwars):
        super().__init__(*args, **kwars)

        self.dn_config_dict = {
            1: {'ssid': 'A', 'proxy_proxy': 8199},
            2: {'ssid': 'B', 'proxy_proxy': 8299},
            3: {'ssid': 'C', 'proxy_proxy': 8399}
        }

        komondor_config_dir = '/vagrant/terranet/topo/.komondor/HybridVirtualFiberTopo/'
        self.komondor_config_dir = os.path.abspath(komondor_config_dir)
        self.komondor_input_dir = f'{self.komondor_config_dir}/input'
        self.komondor_output_dir = f'{self.komondor_config_dir}/output'
        self.komondor_configs, self.komondor_results = \
            self._read_komondor_cache()

    def _read_komondor_cache(self):
        configs = read_komondor_configs(self.komondor_input_dir)
        results = read_komondor_results(self.komondor_output_dir)
        return (configs, results)

    @set_ev_cls(EventCustomerFlowAdded)
    def _customer_flow_added_handler(self, ev):
        super()._customer_flow_added_handler(ev)
        channel_configs = self._channel_configurations()
        if channel_configs:
            self.assign_channels(channel_configs)
        return self.customer_allocation

    @set_ev_cls(EventCustomerFlowRemoved)
    def _customer_flow_removed_handler(self, ev):
        super()._customer_flow_removed_handler(ev)
        channel_configs = self._channel_configurations()
        if channel_configs:
            self.assign_channels(channel_configs)
        return self.customer_allocation

    def assign_channels(self, channel_configs):
        for dn_id, conf in channel_configs.items():
            channel = conf['channel']
            port = self.dn_config_dict[dn_id]['proxy_proxy']
            self._request_channel_switch(channel, port)

    def _request_channel_switch(self, channel, port,
                                host='http://localhost'):
        url = f'{host}:{port}/channel'
        payload = {'channel': channel}
        self.logger.info('ChannelAssignmentOracle: Posting channel switch '
                         'url {} payload {}.\n'.format(url, payload))
        r = requests.post(url, json=payload)
        self.logger.info('ChannelAssignmentOracle: Channel switch response code '
                         '{}, message {}.\n'.format(r.status_code, r.text))
        return r

    def _channel_configurations(self):
        oracle_dict = {}
        if len(self.dn_config_dict) > len(self.customer_allocation):
            self.logger.warn('ChannelAssignmentOracle: Not all DNs have been '
                             'added to the database yet. Skipping channel '
                             'assignment.\n')
            return None
        res = sorted(self._compute_oracle_dict(),
                     key=lambda x: x['jainXtpt'],
                     reverse=True)
        best = res[0]
        self.logger.info('ChannelAssignmentOracle: Best configuration {} for '
                         'current customer distribution {}.\n'
                         .format(best, self.customer_allocation))

        komondor_config = KomondorConfig(cfg_file=best['config_file'])
        dn_channel_configs = komondor_config.ap_channel_configurations()
        for config in dn_channel_configs:
            ssid = config['wlan_code']
            dn_id = self.get_dn_id_by_ssid(ssid)
            channel = config['channel']
            oracle_dict[dn_id] = {'channel': channel}
        return oracle_dict

    def _compute_oracle_dict(self):
        metrics_list = []
        for file, result in self.komondor_results.items():
            result_file = os.path.join(self.komondor_output_dir, file)
            config_file = os.path.join(self.komondor_input_dir, file)
            result_metrics = self._analyse_komondor_result(result)
            result_metrics['result_file'] = result_file
            result_metrics['config_file'] = config_file
            metrics_list.append(result_metrics)
        return metrics_list

    def _analyse_komondor_result(self, komondor_result):
        configured_ssids = sorted(
            [x['ssid'] for x in self.dn_config_dict.values()])
        ssids = komondor_result.wlans()
        assert configured_ssids == ssids

        total_throughput = komondor_result.total_throughput()
        wlan_throughputs = self._extract_wlan_throughputs(komondor_result)
        throughputs = functools.reduce(
            lambda x, y: [*x, *y['customer_throughputs']],
            wlan_throughputs.values(), [])
        fairness_index = self._calculate_jains_fairness_index(throughputs)

        metrics = {
            'total_throughput': total_throughput,
            'fairness_index': fairness_index,
            'jainXtpt': fairness_index * total_throughput,
            'wlan_throughputs': wlan_throughputs
        }

        return metrics

    def _extract_wlan_throughputs(self, komondor_result):
        ssids = komondor_result.wlans()
        throughputs = {}
        for ssid in ssids:
            throughputs[ssid] = {}
            throughput = komondor_result.wlan_throughput(ssid)
            throughputs[ssid]['throughput'] = throughput
            dn_id = self.get_dn_id_by_ssid(ssid)
            customer_count = self.dn_customer_count(dn_id)
            total_throughput = komondor_result.wlan_throughput(ssid)
            throughput_per_customer = (total_throughput / customer_count)
            customer_throughputs = \
                [throughput_per_customer for _ in range(0, customer_count)]
            throughputs[ssid]['customer_throughputs'] = customer_throughputs
        return throughputs

    def _calculate_jains_fairness_index(self, throughputs=[]):
        customer_count = len(throughputs)
        sum_throughputs_squared = pow(sum(throughputs), 2)
        squared_throughputs = [pow(x, 2) for x in throughputs]
        sum_squared_throughputs = sum(squared_throughputs)
        return (sum_throughputs_squared /
            (customer_count * sum_squared_throughputs))


    def get_dn_id_by_ssid(self, ssid):
        for dn_id in self.customer_allocation.keys():
            config = self.dn_config_dict[dn_id]
            if config.get('ssid') == ssid:
                return dn_id
        return None
