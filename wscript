#! /usr/bin/env python
# encoding: utf-8

import os
import subprocess
import glob

from MailIndicator.info import *

srcdir = '.'
blddir = 'build'

import Scripting
Scripting.g_gz = 'gz'

def set_options(opt):
    opt.tool_options('python')

def configure(conf):
    conf.check_tool('python')
    conf.check_python_version((2,6,0))
    # Save destdir option to env
    import Options, Utils, os.path
    conf.env['destdir'] = os.path.expanduser(Options.options.destdir)

def build(bld):
    obj = bld.new_task_gen(
            features='py',
            install_path='${PREFIX}/share/mail-indicator/MailIndicator')
    obj.find_sources_in_dirs('MailIndicator', exts=['.py'])

    # Retrive destdir option from env
    import Options
    Options.options.destdir = bld.env['destdir']

    bld.install_files('${PREFIX}/bin', 'mail-indicator', chmod=0755)
    bld.install_files('${PREFIX}/share/mail-indicator/data', 'data/*.ui')
    bld.install_files('${PREFIX}/share/applications', 'data/*.desktop')

def test(ctx):
    subprocess.call(['python', 'tests/TestAll.py'])

def glade(ctx):
    with open(os.devnull) as devnull:
        cmd = ['glade']
        cmd.extend(glob.glob('data/*.ui'))
        subprocess.Popen(cmd, stdout=devnull, stderr=subprocess.STDOUT)
