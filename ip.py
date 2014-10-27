#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import sys
import ipcalc

# add customized library path
root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(root + "/../ezshell")
import ezshell


# Used shell commands:
#   echo, grep, awk, sed, sort, ip, iw
# https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-net

# Used python modules:
# setuptools
#   https://pypi.python.org/pypi/setuptools
#
# ipcalc.py
#   https://github.com/tehmaze/ipcalc/
#
# ezshell
#   customized


def interfaces():
    # ifaces=$(ip a show | grep -Eo "[0-9]: wlan[0-9]" | sed "s/.*wlan//g")
    # ifaces=$(ip a show | grep -Eo '[0-9]: eth[0-9]' | awk '{print $2}')
    try:
        ifaces = os.listdir("/sys/class/net")
        ifaces = [x for x in ifaces if not x.startswith("lo")]
        return ifaces
    except Exception, e:
        print "Cannot get interfaces: %s" % e
        raise e


def ifaddresses(iface):
    """
    return {
        "mac": "",
        "link": 1,
        "inet": [
            {
                "ip": "",
                "netmask": "",
                "subnet": "",
                "broadcast": ""
            }
        ]
    }

    """
    info = dict()
    try:
        info["mac"] = open("/sys/class/net/%s/address" % iface).read()
        info["mac"] = info["mac"][:-1]  # remove '\n'
    except:
        info["mac"] = None

    try:
        info["link"] = open("/sys/class/net/%s/operstate" % iface).read()
        if "down" == info["link"][:-1]:
            info["link"] = 0
        else:
            info["link"] = open("/sys/class/net/%s/carrier" % iface).read()
            info["link"] = int(info["link"][:-1])  # convert to int
    except:
        info["link"] = 0

    #    "ip addr show %s | grep inet | grep -v inet6 | awk '{print $2}'"
    ret = ezshell.run(
        "ip addr show %s | grep inet | awk '{print $2}'"
        % iface, 0)
    if ret.returncode() != 0:
        raise ValueError("Device \"%s\" does not exist." % iface)

    info["inet"] = list()
    for ip in ret.output().split():
        net = ipcalc.Network(ip)
        item = dict()
        item["ip"] = ip.split("/")[0]
        item["netmask"] = net.netmask()
        if 4 == net.version():
            item["subnet"] = net.network()
            item["broadcast"] = net.broadcast()
        info["inet"].append(item)

    return info


def ifupdown(iface, up):
    try:
        if not up:
            ret = ezshell.run(
                "ps aux | grep %s | grep -v grep | \
                awk '{print $2}'" % iface)
            dhclients = ret.output().split()
            for dhclient in dhclients:
                ezshell.run("kill %s" % dhclient)
        cmd = "ip link set %s %s" % (iface, "up" if up else "down")
        ret = ezshell.run(cmd, 0)
        if ret.returncode() != 0:
            raise ValueError("Cannot update the link status for \"%s\"."
                             % iface)
    except Exception, e:
        print "Cannot update the link status: %s" % e
        raise e


def ifconfig(iface, dhcpc, ip="", netmask="24", gateway=""):
    # TODO(aeluin) catch the exception?
    # Check if interface exist
    ret = ezshell.run("ip a show %s" % iface, 0)
    if ret.returncode() != 0:
        raise ValueError("Device \"%s\" does not exist." % iface)

    # Disable the dhcp client and flush interface
    dhclients = ezshell.run(
        "ps aux | grep 'dhclient %s' | grep -v grep" % iface)
    dhclients = dhclients.output().split()
    if 1 == len(dhclients):
        ezshell.run("dhclient -x %s", 0)
    elif len(dhclients) > 1:
        for dhclient in dhclients:
            ezshell.run("kill %s" % dhclient)
    ezshell.run("ip -4 addr flush label %s" % iface, 0)

    if dhcpc:
        ezshell.run("dhclient %s" % iface)
    else:
        if ip:
            net = ipcalc.Network("%s/%s" % (ip, netmask))
            cmd = "ip a add %s/%s broadcast %s dev %s" % \
                (ip, net.netmask(), net.broadcast(), iface)
            ezshell.run(cmd, 0)


if __name__ == "__main__":
    print interfaces()

    # ifconfig("eth0", True)
    # time.sleep(10)
    # ifconfig("eth1", False, "192.168.31.36")
    eth0 = ifaddresses("eth0")
    print eth0
    print "link: %d" % eth0["link"]
    for ip in eth0["inet"]:
        print "ip: %s" % ip["ip"]
        print "netmask: %s" % ip["netmask"]
        if "subnet" in ip:
            print "subnet: %s" % ip["subnet"]

    '''
    ifupdown("eth1", True)
    # ifconfig("eth1", True)
    ifconfig("eth1", False, "192.168.31.39")

    eth1 = ifaddresses("eth1")
    print "link: %d" % eth1["link"]
    for ip in eth1["inet"]:
        print "ip: %s" % ip["ip"]
        print "netmask: %s" % ip["netmask"]
        if "subnet" in ip:
            print "subnet: %s" % ip["subnet"]
    '''
