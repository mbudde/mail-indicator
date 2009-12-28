#!/usr/bin/env python
#
# Name: Gmail Notifier
# Version: 1.5.2
# Copyright (C) 2009 Michael Tom-Wing, Michael Budde
# Author: Michael Tom-Wing <mtomwing@gmail.com>,
#         Michael Budde <mbudde@gmail.com>
# Date: November 29th, 2009
# URL: http://ahadiel.org/projects/gmail-notifier
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gtk

import Utils
import info
from Config import Config
from Notifier import Notifier

GCONF_PATH = '/apps/' + info.APPNAME

def main():
    conf = Config(GCONF_PATH)
    notifier = Notifier(conf)
    notifier.start_mail_checks()
    try:
        gtk.main()
    except KeyboardInterrupt:
        notifier.destroy()
