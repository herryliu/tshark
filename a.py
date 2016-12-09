#!/usr/bin/env python
import cmd

import argparse
import getpass
import textwrap

import sys
import os
import re

from configs import add, clone_host, swap
from users import vlan, route, host, vrf, compare
from netaddr import IPNetwork, IPAddress, IPSet, AddrFormatError
SYSTEMSLIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib/python"))
sys.path.append(SYSTEMSLIB)
from systemslib.net import ipam
from systemslib.net.ipam import ipamException

WORKING_AUTH = False
ADDR_REGEX = re.compile(r'(?P<addr>\d+\.\d+\.\d+\.\d+)$')


class userMode(cmd.Cmd):
    SHOW_CMDS = ['host', 'vlan']

    def __init__(self, server, username, password, addr_vrf, route_vrf, vc_domain):
        cmd.Cmd.__init__(self)
        self.prompt = 'ecnConsole# '
        self.ipm = ipam.nocProject(server, username, password)
        self.addr_vrf = addr_vrf
        self.route_vrf = route_vrf
        self.vc_domain = vc_domain

    def emptyline(self):
        """Called when an empty line is entered in response to the prompt.

        If this method is not overridden, it repeats the last nonempty
        command entered.
        http://stackoverflow.com/questions/16479029/python-cmd-execute-last-command-while-prompt-and-empty-line
        """
        if self.lastcmd:
            self.lastcmd = ""
            return self.onecmd('\n')

    def postloop(self):
        print

    def do_EOF(self, line):
        return True

    def do_exit(self, line):
        return True

    def do_compare(self, args):
        tokens = args.split()
        if len(tokens) == 0 or tokens[0] == "?":
            print "compare"
            print "\thosts - compare the vlans assigned to a pair of hosts"
        else:
            compare(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("compare %s" % " ".join(tokens))

    def do_config(self, args):
        '''
        config
        Enter configuration mode
        '''
        configMode(self.ipm, self.addr_vrf, self.route_vrf, self.vc_domain).cmdloop()

    def do_set(self, args):
        '''
        Set the current working VRF
        '''
        tokens = args.split()
        if len(tokens) == 0 or tokens[0] == "?":
            print "set [vrf] - Set the current working VRF"
        elif tokens[0] == "vrf" and len(tokens) == 1:
            print "set [vrf] - Set the current working VRF"
        elif tokens[0] == 'vrf' and len(tokens) > 1:
            tmp_vrf = " ".join(tokens[1:])
            if "%s ECN Addresses" % tmp_vrf in self.ipm.vrfs:
                self.addr_vrf = "%s ECN Addresses" % tmp_vrf
                self.route_vrf = "%s ECN Routes" % tmp_vrf
                self.vc_domain = "%s ECN Vlans" % tmp_vrf
            else:
                print "Unknown VRF, remember to remove Addresses or Routes from the VRF"

    def do_show(self, args):
        tokens = args.split()
        if len(tokens) == 0 or tokens[0] == "?":
            print "show"
            print "\thost - show host configuration"
            print "\troute - show routes"
            print "\tvlan - show vlan configuration"
            print "\tvrf - show all the VRFs in the ecnConsole, add current to show which one we are configuring here"
        elif tokens[0] == "vlan":
            vlan(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("show_vlan %s" % " ".join(tokens))
        elif tokens[0] == "route":
            route(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("show_route %s" % " ".join(tokens))
        elif tokens[0] == "host":
            host(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("show_host %s" % " ".join(tokens))
        elif tokens[0] == "vrf":
            vrf(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("show_vrf %s" % " ".join(tokens))


class configMode(cmd.Cmd):
    def __init__(self, ipm, addr_vrf, route_vrf, vc_domain):
        cmd.Cmd.__init__(self)
        self.prompt = 'ecnConsole(config)# '
        self.ipm = ipm
        self.addr_vrf = addr_vrf
        self.route_vrf = route_vrf
        self.vc_domain = vc_domain

    def emptyline(self):
        """Called when an empty line is entered in response to the prompt.

        If this method is not overridden, it repeats the last nonempty
        command entered.
        http://stackoverflow.com/questions/16479029/python-cmd-execute-last-command-while-prompt-and-empty-line
        """
        if self.lastcmd:
            self.lastcmd = ""
            return self.onecmd('\n')

    def postloop(self):
        print

    def do_EOF(self, args):
        return True

    def do_exit(self, args):
        return True

    def do_add(self, args):
        '''
        add host [hostname] vlan [number] ip [address]
        add host [hostname] vlan [number] next-available
        add vlan [vlan ID] name [vlan name] [primary [primary gateway]] [secondary [secondary gateway]] [tag [tag name]]
        add subnet [ip subnet] vlan [vlan ID] [colo [colo]]
        add route [ip prefix] tag [tag1,tag2,...] [gateway-exception [router gateway]]
        '''
        tokens = args.split()
        if len(tokens) == 0 or tokens[0] == "?":
            print "\thostname - Add host ECN interface"
            print "\tvlan     - Add ECN vlan"
            print "\tsubnet   - Add ECN IP subnet"
            print "\troute    - Add ECN route"
        else:
            if tokens[0] in ('vlan','subnet','route'):
                add(
                    self.ipm,
                    self.addr_vrf,
                    self.route_vrf,
                    self.vc_domain
                ).onecmd("%s" % args)
            else:
                add(
                    self.ipm,
                    self.addr_vrf,
                    self.route_vrf,
                    self.vc_domain
                ).onecmd("host %s" % args)

    def do_clone(self, args):
        '''
        clone [host] [clone]
        clone [host] [clone] dry-run
        Take one host and copy all the VLAN interfaces it has to the clone host using the next available ips
        '''
        tokens = args.split()
        if len(tokens) == 0 or tokens[0] == "?":
            print "[old-host] \thost to be cloned"
        else:
            clone_host(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("clone %s" % args)

    def do_delete(self, args):
        '''
        host - give a hostname to delete all IP addresses from
        ip - delete a single IP address
        '''
        tokens = args.split()
        if len(tokens) == 0 or tokens[0] == "?":
            print self.do_delete.__doc__
        elif len(tokens) == 1:
            if tokens[0] == "host":
                print "\t<hostname> - select the hostname to delete"
            elif tokens[0] == "ip":
                print "\t<address> - ip address"
            else:
                print "Unknown command"
        elif len(tokens) >= 2:
            if tokens[0] == "host":
                if tokens[1] == "?":
                    print "\t<hostname> - select the hostname to delete"
                else:
                    if len(tokens) == 2:
                        self.ipm.delete_host_addresses(tokens[1], ECN_ONLY=True)
                    else:
                        print "Too many args"
            elif tokens[0] == "ip":
                if tokens[1] == "?":
                    print "\t<address> - ip address"
                else:
                    ip = tokens[1]
                    try:
                        self.ipm.delete_address(ip, self.addr_vrf)
                        print "Deleting %s" % ip
                    except ipam.ipamException as ie:
                        print ie

    def do_swap(self, args):
        '''
        swap [old-host] [new-host]
        swap [old-host] [new-host] dry-run
        swap [old-host] [new-host] ip A.B.C.D
        swap [old-host] [new-host] ip A.B.C.D dry-run
        Take an old host and replace the old hosts vlan interfaces with a given new host
        By default we do all interfaces, but at the IP address at the end and it will swap only
        that IP address
        '''

        tokens = args.split()
        if len(tokens) == 0 or tokens[0] == "?":
            print "\t[old-host] - specifiy the name of the old host"
        elif len(tokens) == 1 or tokens[1] == "?":
            print "\t[new-host] - specifiy the name of the new host"
        elif len(tokens) == 3 and tokens[2] == "?":
            print "\tip - select an IP address to swap"
            print "\tdry-run - show the changes but don't make them"
            print "\t<cr>"
        elif len(tokens) == 3 and tokens[2] == "ip":
            print "\tA.B.C.D - ip address to switch from the old host to the new host"
        elif len(tokens) == 4:
            ip = None
            if tokens[3] == "?":
                print "\t<cr>"
                return
            try:
                ip = IPAddress(tokens[3])
            except AddrFormatError:
                print "Invalid IP Address: %s" % tokens[3]
                return
            swap(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("swap_ip %s" % " ".join(tokens))
        elif len(tokens) == 5:
            print "\t<cr>"
            return
        else:
            swap(
                self.ipm,
                self.addr_vrf,
                self.route_vrf,
                self.vc_domain
            ).onecmd("swap_host %s" % " ".join(tokens))




if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
        DESCRIPTION:
        This is a tool is an interactive tool for viewing and changing ECN interfaces.
        '''),
        epilog=textwrap.dedent('''\
        EXAMPLE
        ''')
    )
    noc_connectivity = parser.add_argument_group(
        'NOC Connectivity Option',
        description="Define how to connect to the noc project server"
    )
    noc_connectivity.add_argument("--server", dest="server", help="Address of the noc server", default='shanoc1')
    noc_connectivity.add_argument("--username", dest="username", help="Username to connect to the noc server, otherwise defaults to current user")
    noc_connectivity.add_argument("--password", dest="password", help="Password to connect to the noc server")
    parser.add_argument("--vrf", dest="vrf", choices=['Americas', 'Europe', 'Asia'], default="Americas", help="Specify the VRF Region")
    args = parser.parse_args()
    if args.username is None:
        args.username = getpass.getuser()
        if not WORKING_AUTH:
            args.password = args.username
    if args.password is None:
        args.password = getpass.getpass()
    if args.vrf == "Americas":
        args.vrf = "Americas'"
    elif args.vrf == "Europe":
        args.vrf = "Europe's"
    elif args.vrf == "Asia":
        args.vrf = "Asia's"
    userMode(
        args.server,
        args.username,
        args.password,
        "%s ECN Addresses" % args.vrf,
        "%s ECN Routes" % args.vrf,
        "%s ECN Vlans" % args.vrf,

    ).cmdloop()
