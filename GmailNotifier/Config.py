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

import info
from Account import Account
from Keyring import Keyring
from PreferenceDialog import PreferenceDialog
from Utils import debug, debug_method


class Config(gobject.GObject):

    __gproperties__ = {
        'notifications': (
            gobject.TYPE_BOOLEAN,
            'Show notifications?', '',
            True,
            gobject.PARAM_READWRITE
        ),
        'notification-mode': (
            gobject.TYPE_STRING,
            'What notifications to show', '',
            'count', # 'count' or 'email'
            gobject.PARAM_READWRITE
        ),
        'run-on-startup': (
            gobject.TYPE_BOOLEAN,
            'Program is run on startup', '',
            False,
            gobject.PARAM_READWRITE
        ),
        'mail-application': (
            gobject.TYPE_STRING,
            'Application to open when an inbox is clicked', '',
            'browser', # 'browser', 'custom' or 'none'
            gobject.PARAM_READWRITE
        ),
        'custom-app-name': (
            gobject.TYPE_STRING,
            'Custom application name', '',
            '',
            gobject.PARAM_READWRITE
        ),
        'custom-app-icon': (
            gobject.TYPE_STRING,
            'Custom application icon', '',
            '',
            gobject.PARAM_READWRITE
        ),
        'custom-app-exec': (
            gobject.TYPE_STRING,
            'Custom application command', '',
            '',
            gobject.PARAM_READWRITE
        ),
        'custom-app-terminal': (
            gobject.TYPE_BOOLEAN,
            'Run custom application in a terminal', '',
            False,
            gobject.PARAM_READWRITE
        ),
    }

    def __init__(self, path):
        gobject.GObject.__init__(self)
        self.gconf = gconf.client_get_default()
        self.path = path
        self._init_properties_from_gconf()
        self.keyring = Keyring("Gmail Notifier", "A simple Gmail Notifier")
        self._accounts = None
        self._pref_dlg = PreferenceDialog(self)

    @debug_method
    def do_get_property(self, pspec):
        try:
            return getattr(self, '_'+pspec.name)
        except AttributeError:
            return pspec.default_value

    @debug_method
    def do_set_property(self, pspec, value):
        if (pspec.name == 'notification-mode' and value not in ('count', 'email')) or \
           (pspec.name == 'mail-application' and value not in ('browser', 'custom', 'none')):
            raise ValueError, 'invalid value `%s\' or property %s' % (value, pspec.name)
        setattr(self, '_'+pspec.name, value)
        self.gconf.set_value('%s/%s' % (self.path, pspec.name), value)

    def _init_properties_from_gconf(self):
        for pspec in self.props:
            path = '%s/%s' % (self.path, pspec.name)
            try:
                val = self.gconf.get_value(path)
            except ValueError:
                val = pspec.default_value
                self.gconf.set_value(path, val)
            setattr(self, '_'+pspec.name, val)

    def _init_account_from_gconf(self, path):
        account = Account()
        for pspec in account.props:
            if pspec.name == 'password':
                auth_token = self.gconf.get_value('%s/auth_token' % path)
                account.props.password = self.keyring.get_password(auth_token)
            else:
                setattr(account.props, pspec.name,
                        self.gconf.get_value('%s/%s' % (path, pspec.name)))
        account.connect('notify', self._prop_changed)
        return account

    def get_accounts(self):
        if self._accounts == None:
            paths = self.gconf.all_dirs('%s/accounts' % self.path)
            self._accounts = []
            for path in paths:
                self._accounts.append(self._init_account_from_gconf(path))
        return self._accounts

    def save_account(self, account):
        path = "%s/accounts/%s" % (self.path, account.props.email)
        for pspec in account.props:
            if pspec.name == 'password':
                auth_token = self.keyring.save_password(account.props.email, account.props.password)
                self.gconf.set_value('%s/auth_token' % path, auth_token)
            self.gconf.set_value('%s/%s' % (path, pspec-name),
                                 getattr(account.props, pspec.name))
        account.connect('notify', self._prop_changed)
        self._accounts.append(account)

    def remove_account(self, account):
        path = os.path.join(self.path, "accounts", account.props.email)
        self.gconf.recursive_unset(path, 0)
        # disconnect from notify signal
        self._accounts.remove(account)

    @debug_method
    def _prop_changed(self, acc, pspec):
        debug('prop changed in %s' % acc._email)
        if pspec.name == 'password':
            self.keyring.save_password(acc.props.email, acc.props.password)
        else:
            # Can't use get_property because of libindicate bug (LP#499490)
            self.gconf.set_value('%s/accounts/%s/%s' % (self.path, acc.props.email, pspec.name),
                                 getattr(acc.props, pspec.name))
                

    def open_pref_window(self):
        self._pref_dlg.show()

