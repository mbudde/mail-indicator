#! /usr/bin/env python
# encoding: utf-8

from GmailNotifier.info import *

srcdir = '.'
blddir = 'build'

import Scripting
Scripting.g_gz = 'gz'

def set_options(opt):
    pass

def configure(conf):
    # Save destdir option to env
    import Options, Utils, os.path
    conf.env['destdir'] = os.path.expanduser(Options.options.destdir)

def build(bld):
    # Retrive destdir option from env
    import Options
    Options.options.destdir = bld.env['destdir']

    bld.install_files('${PREFIX}/bin', 'gmail-notifier', chmod=0755)
    bld.install_files('${PREFIX}/share/gmail-notifier/GmailNotifier', 'GmailNotifier/*.py')
    bld.install_files('${PREFIX}/share/gmail-notifier/data', 'data/*.ui')
