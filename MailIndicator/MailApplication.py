#
# Copyright (C) 2009  Michael Budde <mbudde@gmail.com>
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

import gobject
import gconf
import subprocess


class MailApplication(gobject.GObject):

    @classmethod
    def get_command(cls):
        raise NotImplemented

    @staticmethod
    def insert_link(link, command):
        for i, v in enumerate(command):
            if v.startswith('%'):
                command[i] = link
        return command

    @classmethod
    def open(cls, link=''):
        command = cls.get_command()
        subprocess.Popen(cls.insert_link(link, command))

    @classmethod
    def compose(cls):
        raise NotImplemented


class DefaultMailApplication(MailApplication):

    @classmethod
    def get_command(cls):
        gconf = gconf.client_get_default()
        path = '/desktop/gnome/url-handlers/mailto'
        command = gconf.get_string(path + '/command').split()
        term = gconf.get_bool(path + '/needs_terminal')
        if term:
            path = '/desktop/gnome/applications/terminal'
            term_cmd = gconf.get_string(path + '/exec')
            term_arg = gconf.get_string(path + '/exec_arg')
            command = [term_cmd, term_arg] + command
        return command


class CustomMailApplication(MailApplication):

    @classmethod
    def get_command(cls):
        raise NotImplemented

