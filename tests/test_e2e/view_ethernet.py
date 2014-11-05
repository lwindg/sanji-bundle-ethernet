#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
from time import sleep

from sanji.core import Sanji
from sanji.connection.mqtt import Mqtt


REQ_RESOURCE = "/network/ethernets"
MANUAL_TEST = 0


class View(Sanji):

    # This function will be executed after registered.
    def run(self):

        for count in xrange(0, 100, 1):
            # Normal CRUD Operation
            #   self.publish.[get, put, delete, post](...)
            # One-to-One Messaging
            #   self.publish.direct.[get, put, delete, post](...)
            #   (if block=True return Message, else return mqtt mid number)
            # Agruments
            #   (resource[, data=None, block=True, timeout=60])

            # case 1: test GET collection
            sleep(2)
            resource = REQ_RESOURCE
            print "GET %s" % resource
            res = self.publish.get(resource)
            if res.code != 200:
                print "GET collection is supported, should be code 200"
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 2: test GET with querying id
            sleep(2)
            resource = "%s?id=1" % REQ_RESOURCE
            print "GET %s" % resource
            res = self.publish.get(resource)
            if res.code != 200:
                print "GET by querying id is supported, should be code 200"
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 3: GET one interface
            sleep(2)
            resource = "%s/1" % REQ_RESOURCE
            print "GET %s" % resource
            res = self.publish.get(resource)
            if res.code != 200:
                print "GET is supported, should be code 200"
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 4: GET inexist interface
            sleep(2)
            resource = "%s/7" % REQ_RESOURCE
            print "GET %s" % resource
            res = self.publish.get(resource)
            if res.code != 404:
                print "Interface not found, should be code 404."
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 5: test PUT with no data attribute
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, None)
            if res.code != 400:
                print "data is required, code 400 is expected"
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 6: test PUT with empty data
            sleep(2)
            print "PUT %s" % REQ_RESOURCE
            res = self.publish.put(REQ_RESOURCE, data={})
            if res.code != 400:
                print "data.enable is required, code 400 is expected"
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 7: test PUT with enable=0 for eth1
            sleep(2)
            data = {"id": 2, "enable": 0}
            resource = "%s/2" % REQ_RESOURCE
            print "PUT %s" % resource
            res = self.publish.put(resource, data=data)
            if res.code != 200:
                print "data.enable=0 should reply code 200"
                print res.to_json()
                self.stop()
            print data
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 8: test PUT with enable=1 for eth1
            sleep(2)
            data = {"id": 2, "enable": 1,
                    "enableDhcp": 0,
                    "enableDefaultGW": 1,
                    "ip": "192.168.31.37",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.31.0",
                    "gateway": "192.168.31.254",
                    "dns": ["192.168.50.42"]}
            # data = {"id": 2, "enable": 1, "enableDhcp": 1}
            resource = "%s/2" % REQ_RESOURCE
            print "PUT %s" % resource
            res = self.publish.put(resource, data=data)
            if res.code != 200:
                print "data.enable=1 should reply code 200"
                print res.to_json()
                self.stop()
            print data
            if 1 == MANUAL_TEST:
                print var

            # stop the test view
            self.stop()


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("Ethernet")

    view = View(connection=Mqtt())
    view.start()
