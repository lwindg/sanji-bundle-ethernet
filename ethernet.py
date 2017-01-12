#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import copy
import logging
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator
from voluptuous import Schema
from voluptuous import Required, Optional, Extra, Range, Any, REMOVE_EXTRA
import ipcalc
import ip.addr as ip


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger("sanji.ethernet")


def merge(dest, src, path=None):
    """Merges src into desc."""
    if path is None:
        path = []
    for key in src:
        if key in dest:
            if isinstance(dest[key], dict) and \
               isinstance(src[key], dict):
                merge(dest[key], src[key], path + [str(key)])
            elif dest[key] == src[key]:
                pass  # same leaf value
            else:
                dest[key] = src[key]
        else:
            dest[key] = src[key]
    return dest


class Ethernet(Sanji):
    """
    A model to handle Ethernet interfaces' configuration.

    Attributes:
        model: Ethernet interfaces' database with json format.
    """
    def init(self, *args, **kwargs):
        try:  # pragma: no cover
            bundle_env = kwargs["bundle_env"]
        except KeyError:
            bundle_env = os.getenv("BUNDLE_ENV", "debug")

        self.path_root = os.path.abspath(os.path.dirname(__file__))
        if bundle_env == "debug":  # pragma: no cover
            self.path_root = "%s/tests" % self.path_root

        # Find all ethernet interfaces and load the configuration
        ifaces = ip.interfaces()
        ifaces = [x for x in ifaces if x.startswith("eth")]
        if 0 == len(ifaces):
            _logger.info("No interfaces to be configured.")
            self.stop()
            raise ValueError("No interfaces to be configured.")

        try:
            self.load(self.path_root, ifaces)
        except:
            self.stop()
            raise IOError("Cannot load any configuration.")

        # Apply the configuration
        for iface in self.model.db:
            self.apply(iface)

    def run(self):
        for iface in self.model.db:
            iface["type"] = "eth"
            iface["mode"] = "dhcp" if iface["enableDhcp"] else "static"
            self.publish.event.put(
                "/network/interfaces/{}".format(iface["name"]), data=iface)

    def load(self, path, ifaces):
        """
        Load the configuration. If configuration is not installed yet,
        initialise them with the given interfaces and install them.

        Args:
            path: Path for the bundle, the configuration should be located
                under "data" directory.
            ifaces: A list of interfaces name.
        """
        self.model = ModelInitiator("ethernet", path, backup_interval=-1)
        if not self.model.db:
            raise IOError("Cannot load any configuration.")

        # Initialise the interfaces
        # TODO: 2nd iface's type is "LAN"; another is "WAN"
        if 1 == len(self.model.db) and "id" not in self.model.db[0]:
            _logger.debug("factory install")
            default_db = self.model.db.pop()
            ip_3_def = int(default_db["ip"].split(".")[2]) - 1
            for iface in ifaces:
                ifaddr = ip.ifaddresses(iface)
                db = copy.deepcopy(default_db)
                db["name"] = iface
                db["id"] = int(iface.replace("eth", "")) + 1

                ip_3 = ip_3_def + db["id"]
                db["ip"] = "192.168.%d.127" % ip_3
                db["subnet"] = "192.168.%d.0" % ip_3
                db["gateway"] = "192.168.%d.254" % ip_3

                db["status"] = True if ifaddr["link"] == 1 else False
                db["mac"] = ifaddr["mac"]
                self.model.db.append(db)
            self.save()

    def save(self):
        """
        Save and backup the configuration.
        """
        self.model.save_db()
        self.model.backup_db()

    def apply(self, data):
        """
        Apply the configuration to an interface.

        Args:
            data: Information for the interface to be applied (with dictionary
                format)
        """
        iface = "eth%d" % (data["id"]-1)

        ip.ifupdown(iface, True if data["enable"] else False)
        if not data["enable"]:
            return

        if data["enableDhcp"]:
            ip.ifconfig(iface, True, script="%s/hooks/dhclient-script" %
                        self.path_root)
        else:
            ip.ifconfig(iface, False, data["ip"], data["netmask"],
                        data["gateway"])

    def read(self, id, restart=False, config=True):
        """
        Read the setting for an interface.

        Args:
            id: Interface id, interface name will be eth(id+1).
        """
        for data in self.model.db:
            if data["id"] == id:
                break
        else:
            return None

        # deepcopy to prevent settings be modified
        data = copy.deepcopy(data)

        if not restart and "restart" in data:
            data.pop("restart")

        iface = "eth%d" % (data["id"]-1)
        ifaddr = ip.ifaddresses(iface)
        data["status"] = True if ifaddr["link"] == 1 else False
        data["mac"] = ifaddr["mac"]

        # """Use configuration data instead of realtime retrieving
        if True is config:
            return data

        data["ip"] = ""
        data["netmask"] = ""
        data["subnet"] = ""
        data["broadcast"] = ""
        # data["gateway"] = ""
        if ifaddr["inet"] and len(ifaddr["inet"]):
            data["ip"] = ifaddr["inet"][0]["ip"]
            data["netmask"] = ifaddr["inet"][0]["netmask"]
            if "subnet" in ifaddr["inet"][0]:
                data["subnet"] = ifaddr["inet"][0]["subnet"]
            else:
                data.pop("subnet")
            if "broadcast" in ifaddr["inet"][0]:
                data["broadcast"] = ifaddr["inet"][0]["broadcast"]
            elif "broadcast" in data:
                data.pop("broadcast")
        # """
        return data

    @staticmethod
    def schema_validate(message):
        """
        Validate the received data, ensure the schema is correct.
        """
        # TODO: ip validation
        schema = Schema({
            Required("id"): Range(min=1),
            Required("enable"): bool,
            Required("enableDhcp"): bool,
            Optional("wan"): bool,
            Optional("ip"): Any(str, unicode),
            Optional("netmask"): Any(str, unicode),
            Optional("gateway"): Any(str, unicode),
            Optional("dns"): [Any(str, unicode)],
            Extra: object
        }, extra=REMOVE_EXTRA)

        if not hasattr(message, "data"):
            raise KeyError("Invalid input: \"data\" attribute is required.")

        if type(message.data) is list:
            if 0 == len(message.data):
                raise KeyError("Invalid input: empty \"data\".")
            for item in message.data:
                try:
                    schema(item)
                except Exception, e:
                    raise KeyError("Invalid input: %s." % e)

        if type(message.data) is dict:
            try:
                schema(message.data)
            except Exception, e:
                raise KeyError("Invalid input: %s." % e)

    def _get_by_id(self, message, response):
        """
        /network/ethernets
        with id=#
        """
        ifinfo = self.read(int(message.param["id"]))
        if ifinfo:
            return response(data=ifinfo)
        return response(code=404, data={"message": "No such device."})

    @Route(methods="get", resource="/network/ethernets")
    def get(self, message, response):
        """
        collection: /network/ethernets
        id: /network/ethernets?id=#
        """
        collection = []

        if "id" in message.query:
            for id in message.query["id"].split(","):
                data = self.read(int(id))
                if data:
                    collection.append(data)
            collection = sorted(collection, key=lambda k: k["id"])
            return response(data=collection)

        for iface in self.model.db:
            data = self.read(iface["id"])
            if data:
                collection.append(data)
        collection = sorted(collection, key=lambda k: k["id"])
        return response(data=collection)

    @Route(methods="get", resource="/network/ethernets/:id")
    def get_by_id(self, message, response):
        """
        /network/ethernets/1
        """
        return self._get_by_id(message=message, response=response)

    def merge_info(self, iface):
        """
        Merge the given interface information into database.
        """
        for item in self.model.db:
            if item["id"] == iface["id"]:
                return merge(item, iface)
        else:
            raise ValueError("No such device.")

    def _put_by_id(self, message, response):
        """
        /network/ethernets/1
        "data": {
            "id": 1,
            ...
        }
        """
        # TODO: status code should be added into error message
        # 1. no "data"
        # 2. data is dict() and no "enable"
        try:
            self.schema_validate(message)
        except Exception, e:
            _logger.debug(e, exc_info=True)
            return response(code=400,
                            data={"message": e.message})

        try:
            info = self.merge_info(message.data)
            if info["enableDhcp"] is False and \
                    ("ip" in info and "netmask" in info):
                net = ipcalc.Network("%s/%s" % (info["ip"], info["netmask"]))
                info["subnet"] = str(net.network())
                info["broadcast"] = str(net.broadcast())
            resp = copy.deepcopy(info)

            restart = False
            if "restart" in info:
                restart = info["restart"]

            current = self.read(info["id"], config=False)
            if restart is True and current["ip"] != info["ip"]:
                resp["restart"] = True
            else:
                resp["restart"] = False

            if resp["restart"] is True:
                response(data=resp)

            self.apply(info)
            self.save()
            info["type"] = "eth"
            info["mode"] = "dhcp" if info["enableDhcp"] else "static"
            self.publish.event.put(
                "/network/interfaces/{}".format(info["name"]), data=info)

            if resp["restart"] is False:
                # time.sleep(2)
                return response(data=resp)
        except Exception, e:
            return response(code=404, data={"message": e.message})

    @Route(methods="put", resource="/network/ethernets")
    def put(self, message, response):
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
        # TODO: status code should be added into error message
        # 1. no "data"
        # 2. data is dict() and no "enable"
        # 3. data is list() and len(data) > 0 and each element has no "enable"
        try:
            self.schema_validate(message)
        except Exception, e:
            _logger.debug(e, exc_info=True)
            return response(code=400,
                            data={"message": e.message})

        if "id" in message.param:
            return self._put_by_id(message=message, response=response)

        response(data=message.data)

        # error = None
        for iface in message.data:
            try:
                info = self.merge_info(iface)
                self.apply(info)
                self.model.save_db()
                info["type"] = "eth"
                info["mode"] = "dhcp" if iface["enableDhcp"] else "static"
                self.publish.event.put(
                    "/network/interfaces/{}".format(info["name"]), data=info)
            except Exception, e:
                # error = e.message
                pass
        self.model.backup_db()

    @Route(methods="put", resource="/network/ethernets/:id")
    def put_by_id(self, message, response):
        """
        /network/ethernets/1
        "data": {
            "id": 1,
            ...
        }
        """
        if hasattr(message, "data"):
            message.data["id"] = int(message.param["id"])
        return self._put_by_id(message=message, response=response)

    put_dhcp_schema = Schema({
        Optional("name"): Any(str, unicode),
        Optional("type"): Any(str, unicode),
        Required("ip"): Any(str, unicode),
        Required("netmask"): Any(str, unicode),
        Optional("subnet"): Any(str, unicode),
        Required("gateway"): Any(str, unicode),
        Optional("dns"): [Any(str, unicode)],
        Extra: object
    }, extra=REMOVE_EXTRA)

    @Route(methods="put", resource="/network/interfaces/:iface",
           schema=put_dhcp_schema)
    def put_dhcp_info(self, message):
        """
        /network/interfaces/:iface
        "data": {
            "ip": "",
            "netmask": "",
            "subnet": "",
            "dns": [],
            "gateway": ""
        }
        """
        # TODO: should be removed when schema worked for unittest
        if not hasattr(message, "data"):
            raise ValueError("Invalid input.")

        message.data["name"] = message.param["iface"]
        if message.data["type"] != "eth":
            return

        message.data["id"] = int(message.data["name"].replace("eth", "")) + 1
        message.pop("type")

        try:
            net = ipcalc.Network(
                "%s/%s" % (message.data["ip"], message.data["netmask"]))
            message.data["broadcast"] = str(net.broadcast())
        except Exception as e:
            raise ValueError("Cannot calculate broadcast: {}.".format(e))

        try:

            self.merge_info(message.data)
            _logger.debug(self.model.db)
            self.model.save_db()
        except Exception, e:
            raise ValueError("Invalid input: %s.", str(e))


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.ethernet")

    ethernet = Ethernet(connection=Mqtt())
    ethernet.start()
