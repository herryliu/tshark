#!/usr/bin/env python

import cmd
import subprocess
import re
import os


class TSMainMenu(cmd.Cmd):
    def __init__(self, prompt="tshark>"):
        cmd.Cmd.__init__(self)
        self.prompt = prompt
        self.conf =  {'prompt'  : prompt,
                      'file'    : '/home/admin/git/pcapfile/tcp_ports.pcap',
                      'statCmd' : 'tshark -z conv,tcp -q -n ',
                      'fileloaded' : False,
                      'filter'  : {},
                      }

        self.connList = []

    def do_exit(self, args):
        print "bye"
        return True

    def emptyline(self):
        return

    def do_set(self, args):
        if args == '':
            #print out the current setting
            for k in self.conf:
                print "%s\t\t --> %s" % (k, self.conf[k])
            return
        argsList = args.split()
        field = argsList[0]
        value = ' '.join(argsList[1:])
        if field == '' or value == '':
            print "Re-entry setting please!"

        # set file
        if field == 'file':
            # find out if the file exists or reset the file back to None
            if not os.path.exists(os.path.expanduser(value)):
                    print "The file %s doesn't exist" % value
                    self.conf[field] = None
            else:
                self.conf[field] = os.path.expanduser(value)
                # mark the file as new file
                self.conf['fileloaded'] = False
                return

        # set packet filter
        if field == 'filter':
            print "Save connection detail into a fileter for easier of use in the future"
            if len(value.split()) != 3:
                print "set filter [filter_name] connection [connection ID]"
            (filter_name, c, connID) = value.split()
            if int(connID) > len(self.connList):
                print "There is no connection %s. Please show connection to find out!" % connID
                return
            print "Filter will be built based on %s" % self.connList[int(connID) - 1]
            c = self.connList[int(connID) - 1]
            print c[1:]
            d_filter = " ip.src == %s and tcp.srcport == %s and ip.dst == %s and tcp.dstport == %s "  % tuple(c[1:])
            #% ( x for x in c[1:])
            print d_filter
            self.conf['filter'][filter_name] = d_filter
            return

        # set the as detail action if there nother special need to be done
        self.conf[field] = value

        return

    def do_show(self, args):
        actions = ('connection', 'endpoints', 'tcp', 'udp', 'icmp')
        if args == '' or args.split()[0] not in actions:
            print " show %s" % "|".join(actions)
            return

        argsList = args.split()
        # show tcp connection info 
        if argsList[0] == "connection":
            if len(argsList) <2:
                self.show_conn(None)
            else:
                self.show_conn(argsList[1:])
        return

    def show_conn(self, args):
        if not self.conf['fileloaded']:
            print "Need to load the file before show the connection"
            return

        if not self.connList:
            print "No connection exists. Make sure the file contains tcp connections!"
            return

        if not args: 
            # print out all connections
            for conn in self.connList:
                print conn
            return

        if int(args[0]) > len(self.connList):
            print "Out of range"
        else:
            print self.connList[int(args[0]) -1]
        return

    def do_load(self, args):
        if self.conf['fileloaded']:
            print "Not a new file. Statistics is ready!"
            return
        self.connList = []

        if self.conf['file'] == None:
            print "Capture file is not set!!"
            return
        # construct the command for "tshark -z conv,tcp"
        command_string = self.conf['statCmd'] + r'-r ' + self.conf['file'] 
        # split the command into a list
        command = command_string.split()
        # execute the command
        output = subprocess.check_output(command)

        # match the connection related lines and break each line for tcp connection detail
        r = re.compile(r'<->')
        connection_id = 1

        for line in output.split("\n"):
            # each line in format of " src_ip:src_port <-> dst_ip:dst_port "
            if r.search(line):
                fields = re.split(r'\s+',line,4) 
                src = re.search(r'(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d*$)', fields[0])
                dst = re.search(r'(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d*$)', fields[2])
                if src and dst: 
                    print "from %s port %s to %s port %s" % (src.group(1), src.group(2),
                                                             dst.group(1), dst.group(2))
                    self.connList = self.connList + [ [ connection_id, src.group(1), 
                            src.group(2), dst.group(1), dst.group(2) ] ]
                    connection_id += 1
        # mark the file as old file
        self.conf['fileloaded'] = True
        return

    def do_apply(self, args):
        # check if filter provided
        if not args:
            print "Please provide saved filter name"
            return
        # check if filter is defined
        if args not in self.conf['filter']:
            print "Filter %s is not defined!" % args
            return

        self.connList = []

        if self.conf['file'] == None:
            print "Capture file is not set!!"
            return
        # construct the command for "tshark -z conv,tcp"
        command_string = self.conf['statCmd'] + r'-r ' + self.conf['file']
        # split the command into a list and adding '-2' and '-R' for input filter
        command = command_string.split() + ['-2'] + ['-R'] + [self.conf['filter'][args]]
        # execute the command
        output = subprocess.check_output(command)

        # match the connection related lines and break each line for tcp connection detail
        r = re.compile(r'<->')
        connection_id = 1

        for line in output.split("\n"):
            # each line in format of " src_ip:src_port <-> dst_ip:dst_port "
            if r.search(line):
                fields = re.split(r'\s+',line,4) 
                src = re.search(r'(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d*$)', fields[0])
                dst = re.search(r'(^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d*$)', fields[2])
                if src and dst: 
                    print "from %s port %s to %s port %s" % (src.group(1), src.group(2),
                                                             dst.group(1), dst.group(2))
                    self.connList = self.connList + [ [ connection_id, src.group(1), 
                            src.group(2), dst.group(1), dst.group(2) ] ]
                    connection_id += 1
        # mark the file as old file
        self.conf['fileloaded'] = True
        return



if __name__ == "__main__":
    # Create the main menu and start the menu loop
    mainMenu = TSMainMenu("tshark>")
    mainMenu.cmdloop()

'''
>>> p_ip_port = r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):(\d*)'
>>> p_ip_s_d = r'(' + p_ip_port + r')' + r' *' + r'<->' + r' *' + r'(' + p_ip_port + r')'
>>> print p_ip_s_d
((\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):(\d*)) *<-> *((\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):(\d*))
>>> r = re.compile(p_ip_s_d)
>>> m = r.search(r'172.16.16.128:2832   <-> 67.228.110.120:80')
>>> m.groups()
('172.16.16.128:2832', '172', '16', '16', '128', '2832', '67.228.110.120:80', '67', '228', '110', '120', '80')
'''
'''
a* --> any number of a (>= 0)
a+ --> at least one a (>= 1)
a? --> no more than one 1 (<= 1)
'''
'''
tshark -z option detail

- list the conversations
    -z conv,type[,filter]
    tshark -r tcp_ports.pcap -n -q -z conv,tcp
    
- expert analysis
    -z expert,[error,warm,note,chat],[filter]
    the servity servity level order is error>warm>note>chat ( note = error + warm + note )
    tshark -r tcp_ports.pcap -n -q -z expert,chat,'tcpport == 2828'

- flow analysis
    -z follow,[tcp,udp],[ascii,hex],[filter]
    if the pcap file contains multiple session, filter must be applied to get right pair of conversation
    the filter format can be "ip:port,ip:port" [ it will be translated into correct filter statement.
    stream index (index number eg. 1, 2, 3) can be used as filter as well
    tshark -r tcp_ports.pcap -n -q -z follow,tcp,hex,172.16.16.128:2828,67.228.110.120:80

tshark -r tcp_ports.pcap -n -q -z io,stat,0.1
tshark -r tcp_ports.pcap -n -q -z io,phs
-z io,stat,interval,"[COUNT|SUM|MIN|MAX|AVG|LOAD](field)filter"
'''
