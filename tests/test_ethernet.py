#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest
from mock import patch

from sanji.connection.mockup import Mockup
from sanji.message import Message

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from ethernet import Ethernet
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + '/../'
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


def mock_ip_ifaddresses(arg):
    if "eth0" == arg:
        return {"mac": "78:ac:c0:c1:a8:fe",
                "link": 1,
                "inet": [{
                    "broadcast": "192.168.31.255",
                    "ip": "192.168.31.36",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.31.0"}]}
    elif "eth1" == arg:
        return {"mac": "78:ac:c0:c1:a8:ff",
                "link": 0,
                "inet": [{
                    "broadcast": "192.168.31.255",
                    "ip": "192.168.31.37",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.31.0"}]}
    else:
        raise ValueError


class TestEthernetClass(unittest.TestCase):

    @patch("ethernet.ip.interfaces")
    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def setUp(self, mock_ifaddresses, mock_ifconfig, mock_ifupdown,
              mock_interfaces):
        # Setup the mock
        mock_interfaces.return_value = ["eth0", "eth1"]
        mock_ifaddresses.side_effect = mock_ip_ifaddresses

        self.ethernet = Ethernet(connection=Mockup())

        # case 1: test init() function to load the default configuration
        self.assertTrue(os.path.isfile("%s/data/ethernet.json" % dirpath))
        self.assertTrue(os.path.isfile("%s/data/ethernet.backup.json" %
                                       dirpath))

        os.remove("%s/data/ethernet.json" % dirpath)
        os.remove("%s/data/ethernet.backup.json" % dirpath)

    def tearDown(self):
        self.ethernet.stop()
        self.ethernet = None

    @patch("ethernet.ip.interfaces")
    def test_init(self, mock_interfaces):
        # case 1: no interfaces
        mock_interfaces.return_value = []
        with self.assertRaises(ValueError):
            self.ethernet.init()

        # case 2: cannot load any configuration
        mock_interfaces.return_value = ["eth0", "eth1"]
        with self.assertRaises(IOError):
            with patch("ethernet.ModelInitiator") as mock_modelinit:
                mock_modelinit.side_effect = IOError
                self.ethernet.init()

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test_load(self, mock_ifaddresses, mock_ifconfig, mock_ifupdown):
        # Setup the mock
        ifaces = ["eth0", "eth1"]
        mock_ifaddresses.side_effect = mock_ip_ifaddresses

        # case 1: load current configuration
        self.ethernet.load(dirpath, ifaces)
        self.assertEqual(2, len(self.ethernet.model.db))
        for iface in self.ethernet.model.db:
            ifname = "eth%d" % (iface["id"]-1)
            self.assertTrue(ifname in ifaces)

        os.remove("%s/data/ethernet.json" % dirpath)

        # case 2: load backup configuration
        self.ethernet.load(dirpath, ifaces)
        self.assertEqual(2, len(self.ethernet.model.db))

        os.remove("%s/data/ethernet.json" % dirpath)
        os.remove("%s/data/ethernet.backup.json" % dirpath)

        # case 3: cannot load any configuration
        with self.assertRaises(IOError):
            self.ethernet.load("%s/mock" % dirpath, ifaces)

    def test_save(self):
        # Already tested in init()
        pass

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    def test_apply(self, mock_ifconfig, mock_ifupdown):
        # TODO: how to determine if setting success
        # case 1: set the interface to "down"
        data = {
            "id": 1,
            "enable": 0
        }
        self.ethernet.apply(data)

        data["enable"] = 1

        # case 2: set the interface to "up" with dhcp enabled
        data["enableDhcp"] = 1
        self.ethernet.apply(data)

        # case 3: set the interface to "up" with static IP
        data["enableDhcp"] = 0
        data["ip"] = "192.168.31.39"
        data["netmask"] = "255.255.255.0"
        data["gateway"] = "192.168.31.254"
        self.ethernet.apply(data)

        # case 4: set an unknown interface
        data["id"] = 0
        with self.assertRaises(ValueError):
            mock_ifupdown.side_effect = ValueError
            mock_ifconfig.side_effect = ValueError
            self.ethernet.apply(data)

    @patch("ethernet.ip.ifaddresses")
    def test_read(self, mock_ifaddresses):
        mock_ifaddresses.side_effect = mock_ip_ifaddresses

        # case 1: read current status and mac
        data = self.ethernet.read(1)
        self.assertEqual(1, data["currentStatus"])
        self.assertEqual("78:ac:c0:c1:a8:fe", data["mac"])

        # case 2: no such interface
        data = self.ethernet.read(3)
        self.assertEqual(None, data)
        data = self.ethernet.read(0)
        self.assertEqual(None, data)

    @patch("ethernet.ip.ifaddresses")
    def test_get(self, mock_ifaddresses):
        """
        collection: /network/ethernets
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses
        message = Message({"data": {}, "query": {}, "param": {}})

        '''remove capability function
        # case 1: capability
        def resp1(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(data, [1, 2])
        self.ethernet.get(message=message, response=resp1, test=True)
        '''

        # case 2: collection
        def resp2(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, len(data))
        self.ethernet.get(message=message, response=resp2, test=True)

        # case 3: id
        def resp3(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, data["id"])
            self.assertEqual(0, data["currentStatus"])
            self.assertEqual("78:ac:c0:c1:a8:ff", data["mac"])
        message.query["id"] = 2
        self.ethernet.get(message=message, response=resp3, test=True)

    @patch("ethernet.ip.ifaddresses")
    def test_get_by_id(self, mock_ifaddresses):
        """
        /network/ethernets/1
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses
        message = Message({"data": {}, "query": {}, "param": {}})

        # case 1: get an interface successfully
        def resp1(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(1, data["id"])
            self.assertEqual(1, data["currentStatus"])
            self.assertEqual("78:ac:c0:c1:a8:fe", data["mac"])
        message.param["id"] = 1
        self.ethernet.get_by_id(message=message, response=resp1, test=True)

        # case 2: no such interface
        def resp2(code=200, data=None):
            self.assertEqual(404, code)
            self.assertEqual(data, {"message": "No such device."})
        message.param["id"] = 3
        self.ethernet.get_by_id(message=message, response=resp2, test=True)

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test_put(self, mock_ifaddresses, mock_ifconfig, mock_ifupdown):
        """
        bulk put: /network/ethernets
        "data": [
            {
                "id": 1,
                ...
            },
            {
                "id": 2,
                ...
            }
        ]
        """
        message = Message({"query": {}, "param": {}})

        # case 1: no data attribute
        def resp1(code=200, data=None):
            self.assertEqual(400, code)
        self.ethernet.put(message, response=resp1, test=True)

        # case 1: invalid json schema
        message = Message({"data": {}, "query": {}, "param": {}})
        self.ethernet.put(message, response=resp1, test=True)

        message = Message({"data": [], "query": {}, "param": {}})
        self.ethernet.put(message, response=resp1, test=True)

        message.data.append({"id": 0, "enable": 1})
        self.ethernet.put(message, response=resp1, test=True)

        # case 2: one interface is not exist (bulk); exist one will be updated
        message = Message({"data": [], "query": {}, "param": {}})

        def resp2(code=200, data=None):
            self.assertEqual(400, code)
        message.data.append({"id": 1, "enable": 1, "ip": u"192.168.31.36"})
        message.data.append({"id": 3, "enable": 1})
        self.ethernet.put(message, response=resp2, test=True)
        data = self.ethernet.read(1)
        self.assertEqual("192.168.31.36", data["ip"])

        # case 3: all interfaces are not exist (bulk)
        message = Message({"data": [], "query": {}, "param": {}})

        def resp3(code=200, data=None):
            self.assertEqual(400, code)
        message.data.append({"id": 0, "enable": 1})
        message.data.append({"id": 3, "enable": 1})
        self.ethernet.put(message, response=resp3, test=True)

        # case 4: put successfully (bulk)
        message = Message({"data": [], "query": {}, "param": {}})

        def resp4(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, len(data))
        message.data.append({"id": 1, "enable": 1, "ip": u"192.168.31.37"})
        message.data.append({"id": 2, "enable": 1, "ip": u"192.168.41.37"})
        self.ethernet.put(message, response=resp4, test=True)
        data = self.ethernet.read(1)
        self.assertEqual("192.168.31.37", data["ip"])
        data = self.ethernet.read(2)
        self.assertEqual("192.168.41.37", data["ip"])

        # case 5: put by id (fully test in test_put_by_id())
        def resp5(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(1, data["enable"])
            self.assertEqual("192.168.31.39", data["ip"])
        message = Message({"data": {}, "query": {}, "param": {}})
        message.param["id"] = 1
        message.data["id"] = 1
        message.data["enable"] = 1
        message.data["ip"] = u"192.168.31.39"
        self.ethernet.put(message, response=resp5, test=True)

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    def test_put_by_id(self, mock_ifconfig, mock_ifupdown):
        """
        /network/ethernets/1
        "data": {
            "id": 1,
            ...
        }
        """
        # case 1: invalid json schema
        message = Message({"query": {}, "param": {}})

        # no data attribute, other case already tested in "test_put()"
        def resp1(code=200, data=None):
            self.assertEqual(400, code)
        self.ethernet.put_by_id(message, response=resp1, test=True)

        # case 2: no such interface
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp2(code=200, data=None):
            self.assertEqual(404, code)
        message.data["id"] = 3
        message.data["enable"] = 0
        message.data["ip"] = u"192.168.31.37"
        self.ethernet.put_by_id(message, response=resp2, test=True)

        # case 3: put successfully
        def resp3(code=200, data=None):
            self.assertEqual(404, code)
        message.data["id"] = 1
        message.data["enable"] = 0
        message.data["ip"] = u"192.168.31.40"
        self.ethernet.put_by_id(message, response=resp3, test=True)
        data = self.ethernet.read(1)
        self.assertEqual("192.168.31.40", data["ip"])

    def test_put_dhcp_info(self):
        """
        /network/ethernets/1/dhcp
        "data": {
            "ip": "",
            "netmask": "",
            "subnet": "",
            "dns": [],
            "gateway": ""
        }
        """
        message = Message({"query": {}, "param": {}})

        # case 1: invalid json schema
        def resp1(code=200, data=None):
            self.assertEqual(400, code)
        self.ethernet.put_dhcp_info(message, response=resp1, test=True)

        # case 2: no such interface
        def resp2(code=200, data=None):
            self.assertEqual(404, code)

        message = Message({"data": {}, "query": {}, "param": {}})
        message.param["id"] = 3
        message.data["ip"] = "192.168.41.3"
        message.data["netmask"] = "255.255.255.0"
        message.data["gateway"] = "192.168.41.254"
        message.data["dns"] = ["8.8.8.8"]
        self.ethernet.put_dhcp_info(message, response=resp2, test=True)

        # case 3: put successfully
        def resp3(code=200, data=None):
            self.assertEqual(200, code)

        message = Message({"data": {}, "query": {}, "param": {}})
        message.param["id"] = 1
        message.data["ip"] = "192.168.41.3"
        message.data["netmask"] = "255.255.255.0"
        message.data["gateway"] = "192.168.41.254"
        message.data["dns"] = ["8.8.8.8"]
        self.ethernet.put_dhcp_info(message, response=resp3, test=True)


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger('Ethernet Test')
    unittest.main()
