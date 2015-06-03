#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
# import subprocess
import sh
import getopt
import json
# from random import randint


DHCP_RES = "/network/interfaces/dhcp"
IFACE_RES = "/network/interfaces"

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "-i:",
            ["ip=", "netmask=", "subnet=", "gateway=", "dns="])
    except getopt.GetoptError:
        exit(-1)

    data = {
        "code": 200,
        "method": "put",
        "resource": DHCP_RES,
        "data": {
        }
    }

    for opt, arg in opts:
        if opt == "-i":
            data["data"]["name"] = arg
        elif opt == "--ip":
            data["data"]["ip"] = arg
        elif opt == "--netmask":
            data["data"]["netmask"] = arg
        elif opt == "--subnet":
            data["data"]["subnet"] = arg
        elif opt == "--gateway":
            data["data"]["gateway"] = arg
        elif opt == "--dns":
            data["data"]["dns"] = arg.split()

    # send event to ethernet
    data["resource"] = DHCP_RES
    sh.mosquitto_pub("-t", "/controller", "-m", json.dumps(data, indent=2))
    '''
    subprocess.Popen(
        ["mosquitto_pub",
         "-t", "/controller",
         "-m", "%s" % json.dumps(data, indent=2)],
        stdout=subprocess.PIPE)
    '''

    # send event to views
    data["resource"] = IFACE_RES
    sh.mosquitto_pub("-t", "/controller", "-m", json.dumps(data, indent=2))
    '''
    subprocess.Popen(
        ["mosquitto_pub",
         "-t", "/controller",
         "-m", "%s" % json.dumps(data, indent=2)],
        stdout=subprocess.PIPE)
    '''
