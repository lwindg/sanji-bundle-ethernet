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
                "link": True,
                "inet": [{
                    "broadcast": "192.168.31.255",
                    "ip": "192.168.31.36",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.31.0"}]}
    elif "eth1" == arg:
        return {"mac": "78:ac:c0:c1:a8:ff",
                "link": False,
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

        self.name = "ethernet"
        self.bundle = Ethernet(connection=Mockup())

    def tearDown(self):
        self.bundle.stop()
        self.bundle = None
        try:
            os.remove("%s/data/%s.json" % (dirpath, self.name))
        except OSError:
            pass

        try:
            os.remove("%s/data/%s.json.backup" % (dirpath, self.name))
        except OSError:
            pass

    @patch("ethernet.ip.interfaces")
    def test__init__no_iface(self, mock_interfaces):
        """
        init: no interface
        """
        mock_interfaces.return_value = []

        with self.assertRaises(ValueError):
            self.bundle.init()

    @patch("ethernet.ip.interfaces")
    def test__init__no_conf(self, mock_interfaces):
        """
        init: no configuration file
        """
        mock_interfaces.return_value = ["eth0"]

        with self.assertRaises(IOError):
            with patch("ethernet.ModelInitiator") as mock_modelinit:
                mock_modelinit.side_effect = IOError
                self.bundle.init()

    @patch("ethernet.ip.ifaddresses")
    def test__load__current_conf(self, mock_ifaddresses):
        """
        load: current configuration file
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses

        ifaces = ["eth0", "eth1"]
        self.bundle.load(dirpath, ifaces)
        self.assertEqual(2, len(self.bundle.model.db))
        for iface in self.bundle.model.db:
            ifname = "eth%d" % (iface["id"]-1)
            self.assertTrue(ifname in ifaces)

    @patch("ethernet.ip.ifaddresses")
    def test__load__backup_conf(self, mock_ifaddresses):
        """
        load: backup configuration file
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses
        os.remove("%s/data/%s.json" % (dirpath, self.name))

        ifaces = ["eth0", "eth1"]
        self.bundle.load(dirpath, ifaces)
        self.assertEqual(2, len(self.bundle.model.db))

    def test__load__no_conf(self):
        """
        load: no configuration file
        """
        # case: cannot load any configuration
        with self.assertRaises(Exception):
            self.bundle.load("%s/mock" % dirpath, [])

    def test__save(self):
        """
        save: tested in init()
        """
        # Already tested in init()
        pass

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    def test__apply__iface_down(self, mock_ifconfig, mock_ifupdown):
        """
        apply: set the interface to "down"
        """
        # TODO: how to determine if setting success
        data = {
            "id": 1,
            "enable": False
        }
        self.bundle.apply(data)

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    def test__apply__iface_up_static(self, mock_ifconfig, mock_ifupdown):
        """
        apply: set the interface to "up" with static IP
        """
        # TODO: how to determine if setting success
        data = {
            "id": 1,
            "enable": True,
            "enableDhcp": False,
            "ip": "192.168.31.39",
            "netmask": "255.255.255.0",
            "gateway": "192.168.31.254"
        }
        self.bundle.apply(data)

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    def test__apply__iface_up_dhcp(self, mock_ifconfig, mock_ifupdown):
        """
        apply: set the interface to "up" with dhcp enabled
        """
        # TODO: how to determine if setting success
        data = {
            "id": 1,
            "enable": True,
            "enableDhcp": True
        }
        self.bundle.apply(data)

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    def test__apply__iface_unknown(self, mock_ifconfig, mock_ifupdown):
        """
        apply: set an unknown interface
        """
        data = {
            "id": 0,
            "enable": True
        }
        with self.assertRaises(ValueError):
            mock_ifupdown.side_effect = ValueError
            mock_ifconfig.side_effect = ValueError
            self.bundle.apply(data)

    @patch("ethernet.ip.ifaddresses")
    def test__read(self, mock_ifaddresses):
        """
        read: read current status and mac
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses

        data = self.bundle.read(1)
        self.assertEqual(True, data["status"])
        self.assertEqual("78:ac:c0:c1:a8:fe", data["mac"])

    @patch("ethernet.ip.ifaddresses")
    def test__read__unknown_iface(self, mock_ifaddresses):
        """
        read: no such interface
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses

        data = self.bundle.read(3)
        self.assertEqual(None, data)
        data = self.bundle.read(0)
        self.assertEqual(None, data)

    @patch("ethernet.ip.ifaddresses")
    def test__get__collection(self, mock_ifaddresses):
        """
        get (/network/ethernets): collection
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses
        message = Message({"data": {}, "query": {}, "param": {}})

        # case: collection
        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, len(data))
        self.bundle.get(message=message, response=resp, test=True)

    @patch("ethernet.ip.ifaddresses")
    def test__get__by_id(self, mock_ifaddresses):
        """
        get (/network/ethernets?id=2)
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses
        message = Message({"data": {}, "query": {}, "param": {}})

        # case: by id
        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, data["id"])
            self.assertEqual(False, data["status"])
            self.assertEqual("78:ac:c0:c1:a8:ff", data["mac"])
        message.query["id"] = 2
        self.bundle.get(message=message, response=resp, test=True)

    @patch("ethernet.ip.ifaddresses")
    def test__get_by_id(self, mock_ifaddresses):
        """
        get_by_id (/network/ethernets/1)
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses
        message = Message({"data": {}, "query": {}, "param": {}})

        # case: get an interface successfully
        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(1, data["id"])
            self.assertEqual(True, data["status"])
            self.assertEqual("78:ac:c0:c1:a8:fe", data["mac"])
        message.param["id"] = 1
        self.bundle.get_by_id(message=message, response=resp, test=True)

    @patch("ethernet.ip.ifaddresses")
    def test__get_by_id__unknown_iface(self, mock_ifaddresses):
        """
        get_by_id (/network/ethernets/3): unknown interface
        """
        mock_ifaddresses.side_effect = mock_ip_ifaddresses
        message = Message({"data": {}, "query": {}, "param": {}})

        # case: get an interface successfully
        def resp(code=200, data=None):
            self.assertEqual(404, code)
            self.assertEqual(data, {"message": "No such device."})
        message.param["id"] = 3
        self.bundle.get_by_id(message=message, response=resp, test=True)

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put__no_data(self, mock_ifaddresses, mock_ifconfig,
                           mock_ifupdown):
        """
        put (/network/ethernets): no data attribute
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

        # case: no data attribute
        def resp(code=200, data=None):
            self.assertEqual(400, code)
        self.bundle.put(message, response=resp, test=True)

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put__invalid_json(self, mock_ifaddresses, mock_ifconfig,
                                mock_ifupdown):
        """
        put (/network/ethernets): invalid json schema
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
        # case: invalid json schema

        def resp(code=200, data=None):
            self.assertEqual(400, code)
        message = Message({"data": {}, "query": {}, "param": {}})
        self.bundle.put(message, response=resp, test=True)

        message = Message({"data": [], "query": {}, "param": {}})
        self.bundle.put(message, response=resp, test=True)

        message.data.append({"id": 0, "enable": True})
        self.bundle.put(message, response=resp, test=True)

    # @patch("ethernet.time.sleep")
    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put__partial_success(self, mock_ifaddresses, mock_ifconfig,
                                   mock_ifupdown):
        """
        put (/network/ethernets): one interface is not exist
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
        def mock_put(resource, data):
            pass
        self.bundle.publish.put = mock_put
        self.bundle.publish.event.put = mock_put

        # case: one interface is not exist (bulk); exist one will be updated
        message = Message({"data": [], "query": {}, "param": {}})

        # always true for response reply before apply the settings
        def resp(code=200, data=None):
            self.assertEqual(200, code)
        message.data.append(
            {"id": 1,
             "enable": True,
             "enableDhcp": False,
             "ip": u"192.168.31.36"})
        message.data.append({"id": 3, "enable": True, "enableDhcp": False})
        self.bundle.put(message, response=resp, test=True)
        data = self.bundle.read(1, config=True)
        self.assertEqual("192.168.31.36", data["ip"])

    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put__unknown_ifaces(self, mock_ifaddresses, mock_ifconfig,
                                  mock_ifupdown):
        """
        put (/network/ethernets): all interfaces are not exist
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
        message = Message({"data": [], "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(400, code)
        message.data.append({"id": 0, "enable": True})
        message.data.append({"id": 3, "enable": True})
        self.bundle.put(message, response=resp, test=True)

    # @patch("ethernet.time.sleep")
    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put(self, mock_ifaddresses, mock_ifconfig, mock_ifupdown):
        """
        put (/network/ethernets)
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
        message = Message({"data": [], "query": {}, "param": {}})

        def mock_put(resource, data):
            pass
        self.bundle.publish.put = mock_put

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, len(data))
        message.data.append(
            {"id": 1,
             "enable": True,
             "enableDhcp": False,
             "ip": u"192.168.31.37"})
        message.data.append(
            {"id": 2,
             "enable": True,
             "enableDhcp": False,
             "ip": u"192.168.41.37"})

        def mock_event_put(resource, data):
            pass
        self.bundle.publish.event.put = mock_event_put
        self.bundle.put(message, response=resp, test=True)

        data = self.bundle.read(1, config=True)
        self.assertEqual("192.168.31.37", data["ip"])
        data = self.bundle.read(2, config=True)
        self.assertEqual("192.168.41.37", data["ip"])

    # @patch("ethernet.time.sleep")
    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put__by_id(self, mock_ifaddresses, mock_ifconfig, mock_ifupdown):
        """
        put (/network/ethernets): by id
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
        message = Message({"data": [], "query": {}, "param": {}})

        def mock_put(resource, data):
            pass
        self.bundle.publish.put = mock_put

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(True, data["enable"])
            self.assertEqual("192.168.31.39", data["ip"])
        message = Message({"data": {}, "query": {}, "param": {}})
        message.param["id"] = 1
        message.data["id"] = 1
        message.data["enable"] = True
        message.data["enableDhcp"] = False
        message.data["ip"] = u"192.168.31.39"

        def mock_event_put(resource, data):
            pass
        self.bundle.publish.event.put = mock_event_put
        self.bundle.put(message, response=resp, test=True)

    # @patch("ethernet.time.sleep")
    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put_by_id__invalid_json(self, mock_ifaddresses, mock_ifconfig,
                                      mock_ifupdown):
        """
        put_by_id (/network/ethernets/1): invalid json schema
        "data": {
            "id": 1,
            ...
        }
        """
        message = Message({"query": {}, "param": {}})

        # no data attribute, other case already tested in "test_put()"
        def resp(code=200, data=None):
            self.assertEqual(400, code)
        self.bundle.put_by_id(message, response=resp, test=True)

    # @patch("ethernet.time.sleep")
    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put_by_id__unknown_iface(self, mock_ifaddresses, mock_ifconfig,
                                       mock_ifupdown):
        """
        put_by_id (/network/ethernets/3): unknown interface
        "data": {
            "id": 1,
            ...
        }
        """
        message = Message({"data": {}, "query": {}, "param": {}})

        def mock_put(resource, data):
            pass
        self.bundle.publish.put = mock_put

        def resp(code=200, data=None):
            self.assertEqual(404, code)
        message.data["id"] = 3
        message.data["enable"] = False
        message.data["enableDhcp"] = False
        message.data["ip"] = u"192.168.31.37"
        self.bundle.put_by_id(message, response=resp, test=True)

    # @patch("ethernet.time.sleep")
    @patch("ethernet.ip.ifupdown")
    @patch("ethernet.ip.ifconfig")
    @patch("ethernet.ip.ifaddresses")
    def test__put_by_id(self, mock_ifaddresses, mock_ifconfig, mock_ifupdown):
        """
        put_by_id (/network/ethernets/1)
        "data": {
            "id": 1,
            ...
        }
        """
        message = Message({"data": {}, "query": {}, "param": {}})

        def mock_put(resource, data):
            pass
        self.bundle.publish.put = mock_put

        def resp(code=200, data=None):
            self.assertEqual(404, code)
        message.data["id"] = 1
        message.data["enable"] = False
        message.data["enableDhcp"] = False
        message.data["ip"] = u"192.168.31.40"
        self.bundle.put_by_id(message, response=resp, test=True)
        data = self.bundle.read(1, config=True)
        self.assertEqual("192.168.31.40", data["ip"])

    def test__put_dhcp_info__invalid_json(self):
        """
        put_dhcp_info (/network/interface/dhcp): invalid json schema
        "data": {
            "name": "",
            "ip": "",
            "netmask": "",
            "subnet": "",
            "dns": [],
            "gateway": ""
        }
        """
        message = Message({"query": {}, "param": {}})

        with self.assertRaises(ValueError):
            self.bundle.put_dhcp_info(message, test=True)

    def test__put_dhcp_info__unknown_iface(self):
        """
        put_dhcp_info (/network/interface/dhcp): unknown interface
        "data": {
            "name": "",
            "ip": "",
            "netmask": "",
            "subnet": "",
            "dns": [],
            "gateway": ""
        }
        """
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["name"] = "eth2"
        message.data["ip"] = "192.168.41.3"
        message.data["netmask"] = "255.255.255.0"
        message.data["gateway"] = "192.168.41.254"
        message.data["dns"] = ["8.8.8.8"]
        with self.assertRaises(ValueError):
            self.bundle.put_dhcp_info(message, test=True)

    @patch("ethernet.ip.ifaddresses")
    def test__put_dhcp_info(self, mock_ifaddresses):
        """
        put_dhcp_info (/network/interface/dhcp)
        "data": {
            "name": "",
            "ip": "",
            "netmask": "",
            "subnet": "",
            "dns": [],
            "gateway": ""
        }
        """
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["name"] = "eth1"
        message.data["ip"] = "192.168.41.3"
        message.data["netmask"] = "255.255.255.0"
        message.data["gateway"] = "192.168.41.254"
        message.data["dns"] = ["8.8.8.8"]
        self.bundle.put_dhcp_info(message, test=True)

        data = self.bundle.read(2, config=True)
        self.assertEqual("192.168.41.3", data["ip"])
        self.assertEqual("255.255.255.0", data["netmask"])
        self.assertEqual("192.168.41.254", data["gateway"])
        self.assertEqual(["8.8.8.8"], data["dns"])


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger('Ethernet Test')
    unittest.main()
