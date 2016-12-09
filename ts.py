#!/usr/bin/env python

import cmd

class TSMainMenu(cmd.Cmd):
    def __init__(self, prompt):
        print "create cmd object"
        cmd.Cmd.__init__(self)
        self.prompt = prompt
        # create set menu instance
        self.setMenu = TSSetMenu()

    def do_exit(self, args):
        print "bye"
        return True

    def emptyline(self):
        return

    def do_set(self, args):
        print "in set command"
        argsList = args.split()
        if args[0] == "prompt":
            self.setMenu.docmd(argList[1])

class TSSetMenu(cmd.Cmd):
    def do_prompt(self, args):
        print "args %s" % args
        self.prompt = args
        
mainMenu = TSMainMenu("tshark>")

mainMenu.cmdloop()
