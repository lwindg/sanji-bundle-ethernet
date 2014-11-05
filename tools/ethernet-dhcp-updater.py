#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import subprocess
import getopt
import json
from random import randint


DHCP_RES = "/network/ethernets/:iface/dhcp"
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "-i:",
            ["ip=", "netmask=", "subnet=", "gateway=", "dns="])
    except getopt.GetoptError:
        exit(-1)

    data = {
        "method": "put",
        "resource": DHCP_RES,
        "data": {
        }
    }

    for opt, arg in opts:
        if opt == "-i":
            iface = int(arg.replace("eth", "")) + 1
            data["resource"] = DHCP_RES.replace(":iface", str(iface))
        elif opt == "--ip":
            data["data"]["ip"] = arg
        elif opt == "--netmask":
            data["data"]["netmask"] = arg
        elif opt == "--subnet":
            data["data"]["subnet"] = arg
        elif opt == "--gateway":
            data["data"]["gateway"] = arg
        elif opt == "--dns":
            data["data"]["dns"] = arg

    # send event to view
    subprocess.Popen(
        ["mosquitto_pub",
         "-t", "/controller",
         "-m", "%s" % json.dumps(data, indent=2)],
        stdout=subprocess.PIPE)

    # send request to model
    data["id"] = randint(10000, 99999999)
    data["tunnel"] = "ethernet-dhcp-updater"
    subprocess.Popen(
        ["mosquitto_pub",
         "-t", "/controller",
         "-m", "%s" % json.dumps(data, indent=2)],
        stdout=subprocess.PIPE)
