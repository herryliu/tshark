import re
from collections import OrderedDict
from ipam_base import ipam_base
from netaddr import IPAddress, IPSet, IPNetwork, AddrFormatError
import socket

# pylib
import sys
sys.path.append("/obin/")
from pylib import base

from tabulate import tabulate

class vlan(ipam_base):
    vlan_regex = "^\S+-(\w\w\w)-vl\d+$"

    def __do_show_vlan_free_used__(self, tokens):
        all_ecn_vlans = set(range(400, 599))
        vl_numbers = set()
        vl_numbers_by_colo = dict()
        for vlan in self.ipm.get_all_vlans():
            if vlan['vc_domain__label'] == self.vc_domain:
                vl_numbers.add(int(vlan['l1']))
                m = re.match(self.vlan_regex, vlan['name'])
                if m:
                    site = m.group(1)
                    if site in vl_numbers_by_colo:
                        vl_numbers_by_colo[site].add(int(vlan['l1']))
                    else:
                        vl_numbers_by_colo[site] = set([int(vlan['l1'])])

        if len(tokens) == 2 and tokens[1] == 'used':
            # For some reason the set isn't being sorted, so make sure it is sorted
            # -unfortunately sets are unordered as i think in python it's backed up only by the __hash__ function&sparse backend with collision resolution. maintaining as a binary tree with implicit sorting would obviously be great, but then you loose O(1) insertion/membership checkign
            for v in sorted(vl_numbers):
                print "  %s" % v

        elif len(tokens) == 2 and tokens[1] == 'free':
            print "First 10 free vlan numbers for %s" % self.vc_domain
            for i in sorted(all_ecn_vlans.difference(vl_numbers))[:10]:
                print "  %s" % i

        elif len(tokens) == 3 and tokens[2] == '?':
            if tokens[1] in ["free", "used"]:
                print "show vlan %s" % tokens[1]
                print "\t WORD - 3 letter code for site"
                print "\t <cr>"
            else:
                print "Invalid input"

        elif len(tokens) == 3 and tokens[1] == 'free':
            print "First 10 free vlan numbers for %s" % tokens[2]
            if tokens[2] in vl_numbers_by_colo:
                set_diff = sorted(all_ecn_vlans.difference(vl_numbers_by_colo[tokens[2]]))
                for i in set_diff[:10]:
                    print "  %s" % i
            else:
                print "%s not a valid 3 letter colo code" % (tokens[2])
                print " " + "\n ".join(vl_numbers_by_colo.keys())
        elif len(tokens) == 3 and tokens[1] == 'used':
            print "Used vlan numbers for %s" % tokens[2]
            if tokens[2] in vl_numbers_by_colo:
                for v in vl_numbers_by_colo[tokens[2]]:
                    print v
            else:
                print "No Site found: use one of the following 3 letter codes"
                print " " + "\n ".join(vl_numbers_by_colo.keys())
        elif len(tokens) == 2 and tokens[1] == 'used':
            for v in sorted(vl_numbers):
                print "  %s" % v
        elif len(tokens) == 2 and tokens[1] == 'free':
            print "First 10 free vlan numbers for %s" % self.vc_domain
            set_diff = sorted(all_ecn_vlans.difference(vl_numbers))
            for i in set_diff[:10]:
                print "  %s" % i
        else:
            return False
        return True

    def do_show_vlan(self, args):
        tokens = args.split()

        if len(tokens) == 1 or tokens[1] == "?":
            print "show vlan"
            print "\tfree - show first 10 free vlans"
            print "\tused - show used vlans"
            print "\t<vlan numbers> - show hosts configured for vlan and the routes for the vlan"
            return

        if tokens[1] in ["free", "used"]:
            if self.__do_show_vlan_free_used__(tokens):
                return

        elif not re.match(r'\d+', tokens[1]):
            print "need to specify an number for the vlan"
            return

        colo = None
        if len(tokens) == 2:
            vlans = self.ipm.get_vlans(tokens[1], vdomain=self.vc_domain)
            if len(vlans) == 0:
                print "No Vlans found"
                return
            elif len(vlans) > 1:
                print "More than 1 vlan found, use command show vlan NUMBER colo 3-LETTER-CODE"
                print "Vlan %s exists at the following sites" % tokens[1]
                for v in vlans:
                    m = re.match(self.vlan_regex, v['name'])
                    if m:
                        print m.group(1)
                    else:
                        print "%s INVALID VLAN NAME" % tokens[1]
                return
        elif len(tokens) == 3 and tokens[2] == "?":
            print "colo - Specify the colo for this vlan"
            return
        elif len(tokens) == 3 and tokens[2] != "colo":
            print "Unknown command"
            print "colo - Specify the colo for this vlan"
            return
        elif len(tokens) == 3 and tokens[2] == "colo":
            print "incomplete command"
            print "<3 letter code> - The 3 letter colo code for the vlan"
            return
        elif len(tokens) == 4 and tokens[3] == "?":
            print "<3 letter code> - The 3 letter colo code for the vlan"
            return
        elif len(tokens) == 4 and len(tokens[3]) != 3:
            print "Uknown 3 letter code"
            print "<3 letter code> - The 3 letter colo code for the vlan"
            return
        elif len(tokens) == 5 and tokens[4] == "?":
            print "<cr>"
            return
        else:
            colo = tokens[3]

        if colo:
            try:
                host_data = self.ipm.get_all_host_data_from_vlan(tokens[1], "%s" % self.vc_domain, colo_code=colo)
            except Exception as e:
                print e
                return
        else:
            host_data = self.ipm.get_all_host_data_from_vlan(tokens[1], "%s" % self.vc_domain)
        print "-" * 20
        print "Hosts in vlan %s" % (tokens[1])
        print "-" * 20
        sorted_addrs = host_data['addresses'].keys()
        sorted_addrs.sort()
        for addr in sorted_addrs:
            print "Host %s ip %s Primary switch: %s Vlan: %s" % (
                host_data['addresses'][addr]['host'],
                addr,
                host_data['addresses'][addr]['switch'],
                tokens[1]
            )
        print "-" * 20
        print "Free addresses for vlan %s - Limited to first 10" % (tokens[1])
        print "-" * 20
        used = IPSet(host_data['addresses'].keys())
        prefix = IPNetwork(host_data['prefix'])
        count = 0
        for ip in prefix:
            if ip != prefix.network and ip != prefix.broadcast and ip not in used and count < 10:
                print "%s" % ip
                count += 1

        print "-" * 20
        print "Routes for vlan %s" % (tokens[1])
        print "-" * 20
        print "%s" % self.route_vrf
        for route in self.ipm.get_vlan_routes(tokens[1], vrf=self.route_vrf, vc_domain=self.vc_domain, colo_code=colo):
            print "Route: %s Vlan: %s Route: %s via %s on switch %s" % (
                route['tag'],
                route['vlan'],
                route['prefix']['prefix'],
                route['gw'],
                route['switch']
            )


class route(ipam_base):
    def __do_show_route_functional_args__(self, t):
        cases = OrderedDict([
            (lambda: len(t) == 1 or t[1] == "?",
                "show route\n\t\
A.B.C.D/E - Match this IP Prefix and show the tags and vlans \
associated with the prefix\n\t\
tag - Show all routes and vlans  associated with a route tag\n\t\
to - Specify a market to display the available routes to that market"),
            # route tag <cr>
            (lambda: len(t) == 2 and t[1] == "tag",
                "show route tag\n\tTAG - specify the tag to look for routes to"),
            # route tag ?
            (lambda: len(t) == 3 and t[1] == "tag" and t[2] == "?",
                "show route tag\n\tTAG - specify the tag to look for routes to"),

            # route to <cr>
            (lambda: len(t) == 2 and t[1] == "to",
                "show route to\n\tMARKET - Specify the market you wish to lookup routes to"),
            # route to ? <cr>
            (lambda: len(t) == 3 and t[1] == "to" and t[2] == "?",
                "show route to\n\tMARKET - Specify the market you wish to lookup routes to"),
            # route to MARKET ?
            (lambda: len(t) == 4 and t[1] == "to" and t[3] == "?",
                "show route to MARKET colo\n\tcolo - filter results by colo"),
            # route to MARKET !colo
            (lambda: len(t) == 4 and t[1] == "to" and t[3] != "colo",
                "invalid command\nshow route to MARKET\n\t colo - filter results by colo"),
            # rouet to MARKET colo <cr>
            (lambda: len(t) == 4 and t[1] == "to" and t[3] == "colo",
                "incomplete command\nshow route to MARKET colo\n\tCOLO_CODE - 3 letter colo code"),
            # route to MARKET colo ?
            (lambda: len(t) == 5 and t[1] == "to" and t[3] == "colo" and t[4] == "?",
                "show route to MARKET colo\n\tCOLO_CODE - 3 letter colo code"),
            # route to MARKET colo COLO_CODE ?
            (lambda: len(t) == 6 and t[1] == "to" and t[3] == "colo" and t[5] == "?",
                "<cr>"),
        ])
        for f, m in cases.iteritems():
            if f():
                print m
                return True
        return False

    def __get_ips_to_market(self, market):
        ips = dict()
        for driver in base.getBase().tripView.getDriversByMarket(market.upper()):
            if driver.Address:
                dest, port = driver.Address.split(":")
                try:
                    ips["%s" % IPAddress(dest)] = driver.Name
                except AddrFormateError:
                    try:
                        ips[socket.gethostbyname(dest)] = driver.Name
                    except socket.gaierror:
                        print "Unable to lookup Driver destination - Market %s driver \"address\": %s" % (market, driver.Address)
        return ips

    def __get_vlan_route_to(self, dest, vrf, colo):
        tags = list()
        for _, t in self.ipm.get_possible_routes_tags(dest, vrf).items():
            tags += t
        vlans = [v['name'] for v in self.ipm.search_tagged_vlans(tags, colo=colo)]
        return vlans

    def do_show_route(self, args):
        tokens = args.split()
        if self.__do_show_route_functional_args__(tokens):
            return

        if tokens[1] == "tag" and len(tokens) > 2:
            print "-" * 20
            print "Routes with tag(s): %s" % (", ".join(tokens[2:]))
            print "-" * 20
            for prefix in self.ipm.search_tagged_prefixes(tokens[2:]):
                print "%s - %s" % (",".join(prefix['tags']), prefix['prefix'])
            print "-" * 20
            print "Vlans with tags: %s" % (", ".join(tokens[2:]))
            print "-" * 20
            for t in tokens[2:]:
                for v in self.ipm.find_vlans_tagged_with(t, self.vc_domain):
                    print "%s - %s" % (v['l1'], v['name'])
        elif tokens[1] == "to":
            market = tokens[2]
            colo = None
            if len(tokens) == 5:
                colo = tokens[4]
            ips = self.__get_ips_to_market(market)
            if len(ips) == 0:
                print "Unable to find any trip drivers to market %s" % market
                print "Make sure you are putting in the market name as it appears in tripdrivers.py"
                return
            needed_vlans = set()
            for ip in ips:
                needed_vlans.update(self.__get_vlan_route_to(ip, self.route_vrf, colo))
            if len(needed_vlans) == 0:
                if colo:
                    print "Unable to find any vlans in %s to %s" % (colo, market)
                    return
                else:
                    print "Unable to find vlans to %s" % market
                    return
            print "Vlans to Market %s" % market
            for nv in needed_vlans:
                print nv
        else:
            PREFIX_REGEX = "(?P<prefix>\d+\.\d+\.\d+\.\d+)\/(?P<mask>\d+)"
            m = re.match(PREFIX_REGEX, tokens[1])
            if m:
                print "-" * 20
                print "Routes"
                print "-" * 20
                tags = set()
                for p in self.ipm.get_prefixes("%s/%s" % (m.groupdict()['prefix'], m.groupdict()['mask']), vrf=self.route_vrf):
                    print "%s - %s" % (p['prefix'], p['tags'])
                    for t in p['tags']:
                        tags.add(t)
                print "-" * 20
                print "Vlans tagged with %s" % (",".join(tags))
                print "-" * 20
                for t in tags:
                    for v in self.ipm.find_vlans_tagged_with(t, self.vc_domain):
                        print "%s - %s" % (v['l1'], v['name'])
            else:
                print "None found for %s" % tokens[1]


class compare(ipam_base):
    def __do_show_compare_functional_args__(self, t):
        cases = OrderedDict([
            # compare host
            (lambda: len(t) == 1 and t[0] not in ["hosts"],
                "invalid command\ncompare\n\thost - compare the vlans assigned to a pair of hosts"),
            (lambda: (len(t) == 1 and t[0] == "hosts") or (len(t) == 2 and t[1] == "?"),
                "compare hosts\n\tHOST_1 - specify the first host to compare"),
            (lambda: (len(t) == 2 or (len(t) == 3 and t[2] == "?")),
                "compare hosts HOST_1\n\tHOST_2 - specify the second host to compare")
        ])
        for f, m in cases.iteritems():
            if f():
                print m
                return True
        return False

    def __host_compare(self, tokens):
        host1 = tokens[1]
        host2 = tokens[2]
        host1_vlans = {v['l1']: v for v in self.ipm.get_host_vlans(host1)}
        host2_vlans = {v['l1']: v for v in self.ipm.get_host_vlans(host2)}
        sym_diff = set(host1_vlans.keys()).symmetric_difference(
            set(host2_vlans.keys()))
        headers = [host1, "", host2]
        table = list()
        for v in sym_diff:
            row = None
            if v in host1_vlans:
                row = [host1_vlans[v]['name'], "<", " "]
            else:
                row = [" ", ">", host2_vlans[v]['name']]
            table.append(row)
        print tabulate(table, headers=headers)

    def do_compare(self, args):
        tokens = args.split()
        if self.__do_show_compare_functional_args__(tokens):
            return
        # After checking all the syntax of the commands select what type of
        # compare we want to do
        # Right now we only have host compare but this gives us the ability to
        # add more later
        if tokens[0] == "host":
            self.__host_compare(tokens)


class host(ipam_base):
    def do_show_host(self, args):
        tokens = args.split()
        if len(tokens) == 1 or tokens[1] == "?":
            print "show host"
            print "\t<hostname> - show hostname interfaces and routes"
            return

        print "-" * 20
        print "%s Interfaces" % tokens[1]
        print "-" * 20
        for interface in sorted(self.ipm.get_host_interfaces(tokens[1]), key=lambda intf: intf['vlan']):
            print "Host: %s IP: %s/%s Primary Switch: %s Vlan: %s" % (
                interface['host'], interface['addr'], interface['mask'], interface['switch'], interface['vlan']
            )
        print "-" * 20
        print "%s Routes" % tokens[1]
        print "-" * 20
        routes = self.ipm.get_host_routes(tokens[1], vrf=self.route_vrf)
        for route in sorted(routes, key=lambda r: r['vlan']):
            print "Route: %s Vlan: %s Route: %s via %s on switch %s" % (
                route['tag'], route['vlan'], route['prefix'], route['gw'], route['switch']
            )


class vrf(ipam_base):
    def __do_show_vrf_functional_check_args__(self, t):
        cases = OrderedDict([
            (lambda: len(t) > 1 and t[1] == "current", #case 1
                "Address VRF: %s Route VRF: %s Vlan Domain: %s" % (self.addr_vrf, self.route_vrf, self.vc_domain)),
            (lambda: len(t) > 1 and t[1] == "?", #case 2
                "show vrf\n\tcurrent - shows the vrf we are currently looking at\n\t<cr>"),
            (lambda: len(t) > 2 and t[1] != "current", #case 3
                "unknown command")
            ])
        for f, m in cases.iteritems():
            if f():
                print m
                return True
        return False

    def do_show_vrf(self, args):
        tokens = args.split()
        if self.__do_show_vrf_functional_check_args__(tokens):
            return
        print "-" * 20
        for v in self.ipm.vrfs:
            print v
        print "-" * 20
