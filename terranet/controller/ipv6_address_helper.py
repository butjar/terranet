import ipaddress


class IPv6AddressHelper:
    @classmethod
    def parse_address(cls, ip):
        return ipaddress.IPv6Address(str(ip))

    @classmethod
    def prefix(cls, ip):
        ip_parts = cls.parse_address(ip).exploded.split(":")
        return "{}:{}:{}".format(ip_parts[0], ip_parts[1], ip_parts[2])

    @classmethod
    def subnet_id(cls, ip):
        ip_parts = cls.parse_address(ip).exploded.split(":")
        return ip_parts[3]

    @classmethod
    def subnet_prefix(cls, ip):
        return "{}:{}".format(cls.prefix(ip), cls.subnet_id(ip))

    @classmethod
    def interface_id(cls, ip):
        ip_parts = cls.parse_address(ip).exploded.split(":")
        return "{}:{}:{}:{}".format(ip_parts[4], ip_parts[5], ip_parts[6],
                                    ip_parts[7])

    @classmethod
    def distribution_id(cls, ip):
        subnet_id = cls.subnet_id(ip)
        distribution_id = int("0x{}".format(subnet_id[:2]), 16) - 0x80
        return distribution_id

    @classmethod
    def client_id(cls, ip):
        subnet_id = cls.subnet_id(ip)
        client_id = int("0x{}".format(subnet_id[2:]), 16)
        return client_id

    @classmethod
    def distribution_net(cls, ip):
        prefix = cls.prefix(ip)
        distribution_id = cls.distribution_id(ip)
        distribution_subnet = distribution_id + 0x80
        return ipaddress.ip_network(
                u"{}:{:x}00::0/56".format(prefix,
                                          distribution_subnet))

    @classmethod
    def client_net(cls, ip):
        subnet_prefix = cls.subnet_prefix(ip)
        return ipaddress.ip_network(u"{}::/64".format(subnet_prefix))

    @classmethod
    def customer_net(cls, ip):
        subnet_prefix = cls.subnet_prefix(ip)
        return ipaddress.ip_network(u"{}:8000::/65".format(subnet_prefix))

    @classmethod
    def is_customer_address(cls, ip):
        subnet_prefix = cls.subnet_prefix(ip)
        customer_net = cls.customer_net(ip)
        if cls.parse_address(ip) in customer_net:
            return True
        return False
