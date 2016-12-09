#!/usr/bin/env python

import cmd
import subprocess
import re
import os

class TSSetMenu(cmd.Cmd):
    def __init__(self, parent):
        cmd.Cmd.__init__(self)
        self.parentMenu = parent
        self.prompt = parent.prompt + 'set>'

    def do_prompt(self, args):
        if args == '':
            print "Nothing to be set!"
            return
        newPrompt = args if args[-1] == '>' else args + '>'
        self.parentMenu.prompt = newPrompt
        return

    def do_file(self, args):
        if args == '':
            print "No file name!!"
            return
        self.parentMenu.tsharkOpt['file'] = args
        return

    def emptyline(self):
        # print out the current configuration
        for k in self.parentMenu.tsharkOpt:
            print "%s --> %s" % (k, self.parentMenu.tsharkOpt[k])
        return

    def do_default(self, args):
        # add whatever name provided and add to configuration
        if args == '':
            print "Nothing to add"
            return
        self.parentMenu.tsharkOpt['file'] = args
        return

class TSMainMenu(cmd.Cmd):
    def __init__(self, prompt="tshark>"):
        print "create cmd object"
        cmd.Cmd.__init__(self)
        self.prompt = prompt
        # create set menu instance
        self.setMenu = TSSetMenu(self)
        self.tsharkOpt =  { 'prompt':prompt}

    def do_exit(self, args):
        print "bye"
        return True

    def emptyline(self):
        return

    '''
    def do_set(self, args):
        self.setMenu.onecmd(args)
    '''

    def do_set(self, args):
        if args == '':
            #print out the current setting
            for k in self.tsharkOpt:
                print "%s --> %s" % (k, self.tsharkOpt[k])
            return
        argsList = args.split()
        field = argsList[0]
        value = ' '.join(argsList[1:])
        if field == '' or value == '':
            print "Re-entry setting please!"
        self.tsharkOpt[field] = value
        return

    def do_show(self, args):
        actions = ('stat', 'endpoints', 'tcp', 'udp', 'icmp')
        if args == '' or args.split()[0] not in actions:
            print " show %s" % "|".join(actions)
            return

        argsList = args.split()
        # just do a quick show stat
        if argsList[0] == "stat":
            #self.show_stat(argsList[1:])
            self.show_stat_easy()
        return

    def show_stat_easy(self):
        #subprocess.check_call(["ls", "-al"])
        #subprocess.check_output(["tshark", "-z" "conv", "-q", "-n", "-r ~/git/pcapfile/tcp_ports.pcap"])
        #subprocess.check_call("tshark -z conv,tcp -q -n -r ~/git/pcapfile/tcp_ports.pcap", shell = True)
        self.tsharkOpt['tshark']  = r'tshark'
        self.tsharkOpt['stat']    = r'-z'
        self.tsharkOpt['stat-val'] = r'conv,tcp'
        self.tsharkOpt['quit']    = r'-q'
        self.tsharkOpt['numerical'] = r'-n'
        self.tsharkOpt['file']     = r'-r'
        self.tsharkOpt['file-value'] = r'/home/admin/git/pcapfile/tcp_ports.pcap'

        #command = [self.tsharkOpt['tshark']] + [self.tsharkOpt['stat']] +  [self.tsharkOpt['display']] + [self.tsharkOpt['file']] 
        #subprocess.check_call(['tshark', '-z', 'conv,tcp', '-q', '-n', '-r', '/home/admin/git/pcapfile/tcp_ports.pcap'])
        command =[self.tsharkOpt['tshark']] +\
                 [self.tsharkOpt['stat']]   +\
                 [self.tsharkOpt['stat-val']] + \
                 [self.tsharkOpt['quit']]    + \
                 [self.tsharkOpt['numerical']] +\
                 [self.tsharkOpt['file']]     +\
                 [self.tsharkOpt['file-value']]


        output = subprocess.check_output(command)
        print output
        for l in output.split('\n'):
            if re.match(r'(\d{1,3}\.){3}\d{1,3}',l):
                pass
        return

    def show_stat(self, argsList):
        self.tsharkOpt['tshark']  = r'tshark'
        self.tsharkOpt['stat']    = r'-z'
        self.tsharkOpt['stat-opt'] = r'conv,tcp'
        self.tsharkOpt['display'] = r'-q -n'
        self.tsharkOpt['file']    = r'-r'
        self.tsharkOpt['file-opt'] = r'~/git/pcapfile/tcp_ports.pcap'

        command = [self.tsharkOpt['tshark']] + [self.tsharkOpt['stat']] + [self.tsharkOpt['stat-opt']] + [self.tsharkOpt['display']] + [self.tsharkOpt['file']] + [self.tsharkOpt['file-opt']]
        try:
            output = subprocess.check_output(command)
        except subprocess.CalledProcessError as e:
            print e
            return
        ip-port-Pattern = r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):(\d.*)'

        print output

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
