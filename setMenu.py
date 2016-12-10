#!/usr/bin/env python

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
