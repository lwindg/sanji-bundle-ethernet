#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import sh
import getopt
import json


IFACE_RES = "/network/ethernets"

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "-i:", ["link="])
    except getopt.GetoptError:
        exit(-1)

    data = {
        "code": 200,
        "method": "put",
        "data": {
            "type": "eth"
        }
    }

    for opt, arg in opts:
        if opt == "-i":
            data["data"]["name"] = arg
        elif opt == "--link":
                data["data"]["link"] = True if arg == "1" else False

    # send event to views
    data["resource"] = "{}?name={}".format(IFACE_RES, data["data"]["name"])
    sh.mosquitto_pub("-t", "/controller", "-m", json.dumps(data, indent=2))
