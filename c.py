from collections import OrderedDict
import re
from ipam_base import ipam_base
from netaddr import IPNetwork, IPAddress, AddrFormatError

import sys
sys.path.append("/systems/lib/python")
from systemslib.net.ipam import ipamException


class add(ipam_base):
    def __caseError__(self, args):
        return

    def __do_host_functional_check_args__(self, t):
        """All we need is a list of error conditions to check -
        we can keep those in a dictionary and automatically give the user
        the appropriate message"""
        cases = OrderedDict([
            (lambda: len(t) == 1 or t[1] == "?",  # case 1,2
                "add host\n\t[hostname] - name of host"),
            (lambda: len(t) == 2 or t[2] == "?",  # case 3,4
                "\tvlan - vlan"),
            (lambda: t[2] not in ['vlan'],  # case 5
                "invalid input"),
            (lambda: len(t) == 3 or t[3] == "?",  # case 6,7
                "\t[number] - vlan number"),
            (lambda: not t[3].isdigit(),  # case 8
                "invalid input, not a number"),
            (lambda: t[4] == "?" or t[4] not in ['ip', 'next-available', 'colo'],  # case 9, 10 could be combined to one case
                "\tip - set ip address\n\tnext-available - available - pick next available ip address\n\tcolo - set the vlan for a certain colo"),
            (lambda: t[4] == "colo" and (len(t) == 5 or t[5] == "?"),  # case 11
                "\t[3char] - 3 letter code for colo"),
            (lambda: t[4] == "ip" and (len(t) == 5 or t[5] == "?"),  # case 12
                "\A.B.C.D - ip address"),
            (lambda: t[4] == "colo" and (len(t) == 6 or t[5] == "?"),  # case 13
                "\t[3char] - 3 letter code for colo"),
            (lambda: t[4] == "colo" and (t[6] == "?"),  # case 14
                "\tA.B.C.D - ip address\n\tnext-available - pick next available ip address")
        ])

        for f, m in cases.iteritems():
            if f():
                print m
                return True
        return False

    def __do_host_get_vlans__(self, tokens):
        '''Extract specified vlan, w/ respect to colo code'''
        # case 19-22
        colo_code = tokens[5] if tokens[4] == 'colo' else None
        vlans = self.ipm.get_vlans(tokens[3], vdomain=self.vc_domain, colo_code=colo_code)
        return vlans

    def __do_host_get_ip__(self, tokens):
        '''Extract specified IP'''
        if tokens[4] == 'colo' and tokens[6] == 'ip':  # case 21-22
            ip = tokens[7]
        elif tokens[4] == 'ip':  # case 15-16
            ip = tokens[5]
        else:
            ip = ''
        return ip

    def __do_host_check_ip__(self, ip):
        '''Check that an IP address is valid'''
        str_ip = ip.strip()
        try:  # verify that it is an actual ip address
            ip = IPAddress(str_ip)
            if str_ip != str(ip):  # check that 10.10 -> 10.0.0.10 didnt happen
                print "Invalid IP Address"
                return False
        except AddrFormatError as e:
            print e
            return False
        return True

    def do_host(self, args):
        '''
        add host [hostname] vlan [number] ip [address]
        add host [hostname] vlan [number] ip [address] dry-run
        add host [hostname] vlan [number] next-available
        add host [hostname] vlan [number] next-available dry-run
        add host [hostname] vlan [number] colo [3char] next-available
        add host [hostname] vlan [number] colo [3char] next-available dry-run
        add host [hostname] vlan [number] colo [3char] ip [address]
        add host [hostname] vlan [number] colo [3char] ip [address] dry-run
        '''

        """
        Each case implicitly depends on the last in that we know it did not satisfy it
        To add new cases, they should be as close to the bottom of the list as possible

        _ = junk

        Case      0       1       2      3          4              5             6               7           8
         1   add  _
         2   add host     ?
         3   add host [hostname]
         4   add host [hostname]  ?
         5   add host [hostname]  _
         6   add host [hostname] vlan
         7   add host [hostname] vlan    ?
         8   add host [hostname] vlan    _
         9   add host [hostname] vlan [number]      ?          [address]
         10  add host [hostname] vlan [number]      _          [address]
         11  add host [hostname] vlan [number] colo               (?)?
         12  add host [hostname] vlan [number] ip                 (?)?
         13  add host [hostname] vlan [number] colo            [address]|(?)?
         14  add host [hostname] vlan [number] colo            [address]         ?


         15  add host [hostname] vlan [number] ip              [address]
         16  add host [hostname] vlan [number] ip              [address]      dry-run
         17  add host [hostname] vlan [number] next-available
         18  add host [hostname] vlan [number] next-available  dry-run
         19  add host [hostname] vlan [number] colo            [3char]        next-available
         20  add host [hostname] vlan [number] colo            [3char]        next-available  dry-run
         21  add host [hostname] vlan [number] colo            [3char]        ip              [address]
         22  add host [hostname] vlan [number] colo            [3char]        ip              [address]    dry-run
        Case      0       1       2      3          4              5             6               7           8
        """
        tokens = args.split()

        if self.__do_host_functional_check_args__(tokens):
            return
        vlans = self.__do_host_get_vlans__(tokens)

        # case 19-22, figure out vlan
        if tokens[4] == "colo":
            colo = tokens[5]
            colo_vlans = [v for v in vlans if colo in v['name']]  # filter
            if len(colo_vlans) > 1:
                print "Multiple vlans objects found in colo %s for vlan %s" % (colo, tokens[3])
                return
            elif len(colo_vlans) == 1:
                vlan = colo_vlans[0]
            else:
                print "Vlan: %s not found for colo %s" % (tokens[3], colo)
                return
        # case 15-18, figure out vlan
        elif tokens[4] in ["ip", "next-available"]:
            if len(vlans) > 1:
                print 'Multiple Vlan objects found, try using command "add host carfakehostname vlan 123 colo car next-available"'
                return
            elif len(vlans) == 0:
                print 'No Vlan objects found'
                return
            else:
                vlan = vlans[0]

        fqdn = "%s.%s.hudson-trading.com" % (tokens[1], vlan['name'])
        if self.ipm.get_fqdn(fqdn):  # check fqdn
            print "Host already exists in this vlan"
            return
        ip = self.__do_host_get_ip__(tokens)

        # case 17-20, ip not specified, find next-available.
        if "next-available" in tokens:
            prefix = self.ipm.get_vlans_prefix(vlan['id'])
            ip = self.ipm.find_next_available_address(prefix['prefix'], vrf=self.addr_vrf)
            # Finally check that the given IP is in the correct prefix
            if ip not in IPNetwork(prefix['prefix']):
                print "IP address out of range of vlan: %s" % prefix['prefix']
                return False
        elif not ip:
            print "Invalid input \n" + self.do_host.__doc__
            return
        elif not self.__do_host_check_ip__(ip):  # case 15-16, 21-22, ip is specified by user, must check the formatting
            return

        print "Add IP: Host: %s IP: %s Vl %s" % (fqdn, ip, vlan['l1'])
        if 'dry-run' not in tokens:
            try:
                self.ipm.add_address(str(ip), self.addr_vrf, fqdn=fqdn)
            except ipamException as ie:
                print "IP Address already in use: %s" % ie
        return
    
    def do_vlan(self, args):
        ''' 
        add vlan [vlan ID] name [vlan name] [primary [primary gateway]] [secondary [secondary gateway]] [tag [tag name]]
        '''
        usage = "add vlan [vlan ID] name [vlan name] [primary [primary gateway]] [secondary [secondary gateway]] [tag [tag name]]"
        # check args number
        argsLen = len(args.split())
        if "?" in args or argsLen % 2 == 0 or argsLen < 3:
            print usage
            return

        # pasrse the vlan configuration args and put info into a dictionary
        # it will override the default values
        argsList = ("vlan_id "+args).split()
        argsConf = dict([ argsList[x:x+2] for x in range(0, len(argsList), 2) ])
        vlanConf = {'vlan_id':None,
                    'name':None,
                    'primary':None,
                    'secondary':None,
                    'tag':None}
        for k in argsConf:
            if not k in vlanConf.keys():
                print "%s is not a valid field" % k
                print usage
                return
            else:
                vlanConf[k] = argsConf[k]

        # check if vlan id is 3 or 4-digit
        if not re.match(r'^\d\d\d\d?$',vlanConf['vlan_id']):
            print "VLAN id must be 3 or 4-digit number!!"
            return

        # find out which colo has the same vlan id
        # in EU/NA vlan id is unique only to colo not whole region
        vlanInColo = []
        vlanList = self.ipm.get_vlans(vlanConf['vlan_id'], vdomain=self.vc_domain)
        for vlan in vlanList:
            vname = vlan['name']
            colo = re.search(r'.*-(\w\w\w)-vl\d\d\d\d?$', vname).group(1)
            vlanInColo = vlanInColo + [colo]

        # check if vlan name with right format .*-xxx-vlyyy xxx --> colo and yyy --> 3 or 4-digit vlan number
        m = re.search(r'.*-(?P<colo>\w\w\w)-vl(?P<vlan_id>\d\d\d\d?$)', str(vlanConf['name']))
        if not m:
            # the format  is wrong
            print "VLAN name should be in form .*-xxx-vlyyy[y] xxx --> colo and yyy[y] --> 3 or 4-digit vlan number"
            return
        else:
            # check if vlan id matches the vlan name
            if m.groupdict()['vlan_id'] != vlanConf['vlan_id']:
                print "VLAN ID: %s doesn't match vlan id %s in vlan name: %s" % (vlanConf['vlan_id'], m.groupdict()['vlan_id'], 
                                                                                 vlanConf['name'])
                return
            # check if the vlan id added to colo has same id defined before 
            if m.groupdict()['colo'] in vlanInColo:
                print "VLAN ID %s exists in Colo: %s! Can't be added!!" % (vlanConf['vlan_id'], m.groupdict()['colo'])
                return

        # if vlan doesn't exist go ahead and add the vlan into database
        descr = ""
        if vlanConf['primary'] != None:
            descr = descr + "Primary: %s" % vlanConf['primary']
        if vlanConf['secondary'] != None:
            descr = descr + " Secondary: %s" % vlanConf['secondary']

        try:
            self.ipm.add_vlan(vlanConf['vlan_id'],
                            vlanConf['name'],
                            vdomain=self.vc_domain,
                            tags=vlanConf['tag'],
                            description=descr)
        except ipamException:
            print "Error adding VLAN %s - %s" % (vlanConf['vlan_id'], vlanConf['name'])
            return

        print "VLAN %s - %s is added" % (vlanConf['vlan_id'], vlanConf['name'])
        return

    def do_subnet(self, args):
        '''
        add subnet [ip subnet] vlan [vlan ID] [colo [colo]]
        '''
        usage = "add subnet [ip subnet] vlan [vlan ID] [colo [colo]]"
        #check args and default subnet config values
        argsLen = len(args.split())
        if args == "?" or argsLen % 2 == 0 or argsLen < 3:
            print usage
            return
        argsList = ("subnet "+args).split()
        argsConf = dict([ argsList[x:x+2] for x in range(0, len(argsList), 2) ])
        subnetConf = {'subnet':None,
                      'vlan' :None,
                      'colo' :None,}
        for k in argsConf:
            if not k in subnetConf.keys():
                print "%s is not a valid field" % k
                print usage
                return
            else:
                subnetConf[k] = argsConf[k]

        #check subnet with correct format
        try:
            ip = IPNetwork(subnetConf['subnet'])
        except AddrFormatError as e:
            print e
            return
        subnetConf['subnet'] = str(ip)

        #check subnet is on network boundary
        if ip[0] != ip.ip:
            print "The IP subnet %s is not on network boundary %s. Please check!" \
                    % (subnetConf['subnet'], ip[0])
            return

        # check if vlan id is 3 or 4-digit
        if not re.match(r'^\d\d\d\d?$',subnetConf['vlan']):
            print "VLAN id must be 3 or 4-digit number!!"
            return

        # find the vlan and determin if colo code is reqruied
        vlanList = self.ipm.get_vlans(subnetConf['vlan'], vdomain=self.vc_domain)
        if not vlanList:
            print "VLAN %s is not found!!" % subnetConf['vlan']
            return
        if len(vlanList) == 1:
            # only one vlan matched and no colo code is required
            vid = vlanList[0]['id']
        else:
            # more than one colo matches. Need colo code
            vlanInColo = []
            for vlan in vlanList:
                vname = vlan['name']
                colo = re.search(r'.*-(\w\w\w)-vl\d\d\d\d?$', vname).group(1)
                vlanInColo = vlanInColo + [colo]

            # if colo can't be found
            if subnetConf['colo'] not in vlanInColo:
                print "Can't find vlan %s in colo %s" % (subnetConf['vlan'], subnetConf['colo'])
                print "Colo is either not given or wrong"
                return
            # find the colo and get the vid 
            index = vlanInColo.index(subnetConf['colo'])
            vid = vlanList[index]['id']

        # add the subnet to db
        try:
            self.ipm.add_prefix(subnetConf['subnet'], self.addr_vrf, vc=vid)
        except ipamException as e:
            print e
            return
        print "subnet %s is added" % subnetConf['subnet']
        return

    def do_route(self, args):
        '''
        add route [ip prefix] tag [tag1,tag2,...] [gateway-exception [router gateway]]
        '''
        usage = "add route [ip prefix] tag [tag1,tag2,...] [gateway-exception [router gateway]]"
        # check args
        argsLen = len(args.split())
        if args == "?" or argsLen % 2 == 0 or argsLen < 2:
            print usage
            return
        argsList = ("route "+args).split()
        argsConf = dict([ argsList[x:x+2] for x in range(0, len(argsList), 2) ])
        routeConf = {'route':None,
                      'tag' :None,
                     'gateway-exception' :None,}
        for k in argsConf:
            if not k in routeConf.keys():
                print "%s is not a valid field" % k
                print usage
                return
            else:
                routeConf[k] = argsConf[k]

        #check route with correct format
        try:
            ip = IPNetwork(routeConf['route'])
        except AddrFormatError as e:
            print e
            return
        routeConf['route'] = str(ip)

        #check route is on network boundary
        if ip[0] != ip.ip:
            print "The IP router %s is not on network boundary %s. Please check!" \
                    % (routeConf['route'], ip[0])
            return
        # check tags
        if routeConf['tag'] == None:
            print "Tag is not assigned"
            print usage
            return
        else:
            routeConf['tag'] = routeConf['tag'].split(',')

        # check gateway
        if routeConf['gateway-exception'] != None:
            try:
                ip = IPAddress(routeConf['gateway-exception'])
            except AddrFormatError as e:
                print e
                return
            routeConf['gateway-exception'] = "Gateway: %s" % ip 
            
        # add routes to route vrf
        try:
            self.ipm.add_prefix(routeConf['route'], self.route_vrf, 
                                tags=routeConf['tag'], description=routeConf['gateway-exception'])
        except ipamException as e:
            print e
            return
        print "route %s is added" % routeConf['route']
        return


class clone_host(ipam_base):
    def __do_clone_functional_check_args(self, t):
        cases = OrderedDict([
            (lambda: len(t) == 1 or t[1] == "?",  # case 1, 2
                "[new-host] - hostname of new machine"),
            (lambda: len(t) == 3 and (t[2] == "?" or t[2] != "dry-run"),  # case 3
                "dry-run - test run command, no changes made\n<cr>"),
            (lambda: len(t) == 4 and t[3] == "?",  # case 4
                "<cr>"),
            (lambda: len(t) == 4 and t[3] != "?",  # case 5
                "%invalid input")
        ])

        for f, m in cases.iteritems():
            if f():
                print m
                return True
        return False

    def do_clone(self, args):
        '''
        Case           0       1       2       3
         1    clone    _
         2    clone    _       ?
         3    clone  [host] [clone]    ?
         4    clone                            ?
         5    clone                            _

         6    clone  [host] [clone]
         7    clone  [host] [clone]  dry-run
        '''

        tokens = args.split()
        if self.__do_clone_functional_check_args(tokens):
            return

        host = tokens[0]  # cases 6,7
        clone = tokens[1]
        # Check if host exists or has interfaces
        if len(self.ipm.get_host_interfaces(host)) > 0:
            # Clone that host
            if "dry-run" in args:  # case 7
                self.ipm.clone_host_ecn_interfaces(host, clone, dryRun=True)
            else:
                try:  # case 6
                    self.ipm.clone_host_ecn_interfaces(host, clone)
                except ipamException as ie:
                    print ie


class swap(ipam_base):

    def do_swap_host(self, args):
        tokens = args.split()
        old_host, new_host = tokens[:2]
        dry_run = "dry-run" in tokens

        if self.ipm.get_host_addresses(new_host, ecnOnly=True):
            print "Host already has entries, must add all entries in manually"
            return

        for addr in self.ipm.get_host_addresses(old_host, ecnOnly=True):
            # Let's only swap ECN Addresses
            if "ECN Addresses" in addr['vrf__label']:
                if self.ipm.get_fqdn(addr['fqdn'].replace(old_host, new_host)):
                    print "New Host already has entry for %s" % addr['address']
                    return

                usr_msg = "Swap IP: %s from %s to %s" % (addr['address'], addr['fqdn'], addr['fqdn'].replace(old_host, new_host))
                try:
                    if dry_run:
                        print usr_msg
                    else:
                        self.ipm.update_address(addr['address'], addr['vrf__label'], preserveTags=True, fqdn=addr['fqdn'].replace(old_host, new_host))
                except ipamException as e:
                    print "Unable to swap addresses: %s" % e

    def do_swap_ip(self, args):
        tokens = args.split()
        old_host, new_host, _, ip = tokens[:4]
        addrs = self.ipm.get_address(ip, vrf=self.addr_vrf)

        if not addrs:
            print "Address not found %s" % ip
            return
        if len(addrs) > 1:
            print "Multiple addresses found, %s" % (str(addrs))
            return
        addr = addrs[0]
        regex = "(\S+)\.\S+-\w\w\w-vl\d\d\d.hudson-trading.com"
        m = re.match(regex, addr['fqdn'])  # don't need to compile for this use case, should be quicker
        if not m:
            print "Hostname format not valid for IP: %s FQDN: %s" % (ip, addr['fqdn'])
            return
        if m.group(1) != old_host:
            print "Host: %s doesn't control IP: %s" % (old_host, ip)
            return
        if new_host in addr['fqdn']:
            print "Host is already in the subnet! %s" % (addr['fqdn'])
            return

        try:
            self.ipm.update_address(addr['address'], addr['vrf__label'], preserveTags=True, fqdn=addr['fqdn'].replace(old_host, new_host))
        except ipamException as e:
            print "Unable to swap addresses: %s" % e
            print "Swap IP: %s From: %s to %s" % (addr['address'], addr['fqdn'], addr['fqdn'].replace(old_host, new_host))
            return
