#! /usr/bin/env python
# encoding: utf-8

import subprocess
import glob

from GmailNotifier.info import *

srcdir = '.'
blddir = 'build'

import Scripting
Scripting.g_gz = 'gz'

def set_options(opt):
    opt.tool_options('python')

def configure(conf):
    conf.check_tool('python')
    # Save destdir option to env
    import Options, Utils, os.path
    conf.env['destdir'] = os.path.expanduser(Options.options.destdir)

def build(bld):
    obj = bld.new_task_gen(
            features='py',
            install_path='${PREFIX}/share/gmail-notifier/GmailNotifier')
    obj.find_sources_in_dirs('GmailNotifier', exts=['.py'])

    # Retrive destdir option from env
    import Options
    Options.options.destdir = bld.env['destdir']

    bld.install_files('${PREFIX}/bin', 'gmail-notifier', chmod=0755)
    #bld.install_files('${PREFIX}/share/gmail-notifier/GmailNotifier', 'GmailNotifier/*.py')
    bld.install_files('${PREFIX}/share/gmail-notifier/data', 'data/*.ui')
    bld.install_files('${PREFIX}/share/applications', 'data/*.desktop')

def test(ctx):
    subprocess.call(['python', 'tests/TestAll.py'])
