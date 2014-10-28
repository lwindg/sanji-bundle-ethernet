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
from voluptuous import Optional, Extra
# from voluptuous import Required
# from voluptuous import All
from voluptuous import In, Range
# from voluptuous import Length, In, Range
import ip


# TODO: logger should be defined in sanji package?
logger = logging.getLogger()


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

        path_root = os.path.abspath(os.path.dirname(__file__))
        if bundle_env == "debug":  # pragma: no cover
            path_root = "%s/tests" % path_root

        # Find all ethernet interfaces and load the configuration
        ifaces = ip.interfaces()
        ifaces = [x for x in ifaces if x.startswith("eth")]
        if 0 == len(ifaces):
            logger.info("No interfaces to be configured.")
            self.stop()
            raise ValueError("No interfaces to be configured.")

        try:
            self.load(path_root, ifaces)
        except:
            self.stop()
            raise IOError("Cannot load any configuration.")

        # Apply the configuration
        for iface in self.model.db:
            self.apply(iface)

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
        # TODO: 1. type is always "WAN" for CS
        #       2. 1st iface's type is "LAN" with dhcp server; another is "WAN"
        if 1 == len(self.model.db) and "id" not in self.model.db[0]:
            print "factory install"
            default_db = self.model.db.pop()
            ip_3_def = int(default_db["ip"].split(".")[2]) - 1
            for iface in ifaces:
                ifaddr = ip.ifaddresses(iface)
                db = copy.deepcopy(default_db)
                db["id"] = int(iface.replace("eth", "")) + 1

                ip_3 = ip_3_def + db["id"]
                db["ip"] = "192.168.%d.127" % ip_3
                db["subnet"] = "192.168.%d.0" % ip_3
                db["gateway"] = "192.168.%d.254" % ip_3

                db["currentStatus"] = ifaddr["link"]
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
            ip.ifconfig(iface, True)
        else:
            ip.ifconfig(iface, False, data["ip"], data["netmask"],
                        data["gateway"])

    def read(self, id):
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

        iface = "eth%d" % (data["id"]-1)
        ifaddr = ip.ifaddresses(iface)
        data["currentStatus"] = ifaddr["link"]
        data["mac"] = ifaddr["mac"]

        """Use configuration data instead of realtime retrieving
        data["ip"] = ifaddr["inet"][0]["ip"]
        data["netmask"] = ifaddr["inet"][0]["netmask"]
        if "subnet" in ifaddr["inet"][0]:
            data["subnet"] = ifaddr["inet"][0]["subnet"]
        else:
            data.pop("subnet")
        if "broadcast" in ifaddr["inet"][0]:
            data["broadcast"] = ifaddr["inet"][0]["broadcast"]
        else:
            data.pop("broadcast")
        """
        return data

    @staticmethod
    def schema_validate(message):
        """
        Validate the received data, ensure the schema is correct.
        """
        # TODO: ip validation
        schema = Schema({
            "id": Range(min=1),
            "enable": In(frozenset([0, 1])),
            Optional("type"): In(frozenset([0, 1])),
            Optional("enableDhcp"): In(frozenset([0, 1])),
            Optional("enableDefaultGW"): In(frozenset([0, 1])),
            Optional("ip"): str,
            Optional("netmask"): str,
            Optional("subnet"): str,
            Optional("gateway"): str,
            Optional("dns"): list,
            Extra: object
        }, required=True)

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

    @Route(methods="get", resource="/network/ethernet")
    def get(self, message, response):
        """
        capability: /network/ethernet
        collection: /network/ethernet?collection=true
        """
        if "collection" in message.query:
            collection = []
            for iface in self.model.db:
                data = self.read(iface["id"])
                if data:
                    collection.append(data)
            return response(data={"collection": collection})

        if "id" in message.param:
            return self.get_by_id(message=message)

        capability = []
        for iface in self.model.db:
            capability.append(iface["id"])
        return response(data=capability)

    @Route(methods="get", resource="/network/ethernet/:id")
    def get_by_id(self, message, response):
        """
        /network/ethernet/1
        """
        ifinfo = self.read(message.param["id"])
        if ifinfo:
            return response(data=ifinfo)
        return response(code=404, data={"message": "No such device."})

    def merge_info(self, iface):
        """
        Merge the given interface information into database.
        """
        for item in self.model.db:
            if item["id"] == iface["id"]:
                return merge(item, iface)
        else:
            raise ValueError("No such device.")

    @Route(methods="put", resource="/network/ethernet")
    def put(self, message, response):
        """
        bulk put: /network/ethernet
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
            return response(code=400,
                            data={"message": "Invalid input: %s." % e})

        if "id" in message.param:
            return self.put_by_id(message)

        error = None
        for iface in message.data:
            try:
                info = self.merge_info(iface)
                self.apply(info)
                self.model.save_db()
            except Exception, e:
                error = "%s" % e
        self.model.backup_db()
        if error:
            return response(code=400, data={"message": error})
        return response(data=self.model.db)

    @Route(methods="put", resource="/network/ethernet/:id")
    def put_by_id(self, message, response):
        """
        /network/ethernet/1
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
            return response(code=400,
                            data={"message": "Invalid input: %s." % e})

        try:
            info = self.merge_info(message.data)
            self.apply(info)
            self.model.save_db()
            self.model.backup_db()
            return response(data=info)
        except Exception, e:
            return response(code=404, data={"message": "%s" % e})

    put_dhcp_schema = Schema({
        "ip": str,
        "netmask": str,
        Optional("subnet"): str,
        "gateway": str,
        "dns": list,
        Extra: object
    }, required=True)

    @Route(methods="put", resource="/network/ethernet/:id/dhcp",
           schema=put_dhcp_schema)
    def put_dhcp_info(self, message, response):
        """
        /network/ethernet/1/dhcp
        "data": {
            "ip": "",
            "netmask": "",
            "subnet": "",
            "dns": [],
            "gateway": ""
        }
        """
        if not hasattr(message, "data"):
            return response(code=400,
                            data={"message": "Invalid input."})

        message.data["id"] = message.param["id"]
        try:
            info = self.merge_info(message.data)
            self.model.save_db()
            return response(data=info)
        except Exception, e:
            return response(code=404, data={"message": "%s" % e})


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Ethernet")

    ethernet = Ethernet(connection=Mqtt())
    ethernet.start()
