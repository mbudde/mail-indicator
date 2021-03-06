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
from Debug import debug


class Config(gobject.GObject):
    """Class containing program preferences.

    Config automatically saves and loads its properties to/from GConf.
    Config also takes care of loading Accounts from GConf and saving
    their properties when they change.
    """

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
        self.keyring = Keyring('Gmail Notifier', 'A simple Gmail Notifier')
        self._accounts = None
        self._account_hid = {}

    def do_get_property(self, pspec):
        try:
            return getattr(self, '_'+pspec.name)
        except AttributeError:
            return pspec.default_value

    def do_set_property(self, pspec, value):
        if (pspec.name == 'notification-mode' and value not in ('count', 'email')) or \
           (pspec.name == 'mail-application' and value not in ('browser', 'custom', 'none')):
            raise ValueError('invalid value `{0}\' for property {1}'.format(value, pspec.name))
        setattr(self, '_'+pspec.name, value)
        self.gconf.set_value('{0}/{1}'.format(self.path, pspec.name), value)

    def open_pref_window(self):
        PreferenceDialog.open(self)

    def get_accounts(self):
        if self._accounts == None:
            paths = self.gconf.all_dirs('{0}/accounts'.format(self.path))
            self._accounts = []
            for path in paths:
                self._init_account_from_gconf(path)
        return self._accounts

    def save_account(self, account):
        for acc in self._accounts:
            if acc.props.email == account.props.email:
                return False
        path = '{0}/accounts/{1}'.format(self.path, account.props.email)
        for pspec in account.props:
            if pspec.name == 'password':
                auth_token = self.keyring.save_password(account.props.email, account.props.password)
                self.gconf.set_int('{0}/auth_token'.format(path), auth_token)
            else:
                self.gconf.set_value('{0}/{1}'.format(path, pspec.name),
                                     getattr(account.props, pspec.name))
        self._account_hid[account.props.email] = \
                account.connect('notify', self._account_prop_changed)
        self._accounts.append(account)
        return True

    def remove_account(self, account):
        path = '{0}/accounts/{1}'.format(self.path, account.props.email)
        auth_token = self.gconf.get_int('{0}/auth_token'.format(path))
        self.keyring.remove_password(auth_token)
        self.gconf.recursive_unset(path, 1)
        self.gconf.suggest_sync()
        hid = self._account_hid[account.props.email]
        account.disconnect(hid)
        del self._account_hid[account.props.email]
        self._accounts.remove(account)

    def _init_properties_from_gconf(self):
        """Set Config properties from GConf."""
        for pspec in self.props:
            path = '{0}/{1}'.format(self.path, pspec.name)
            try:
                # TODO: Verify value is correct type
                val = self.gconf.get_value(path)
            except ValueError:
                val = pspec.default_value
                self.gconf.set_value(path, val)
            setattr(self, '_'+pspec.name, val)

    def _init_account_from_gconf(self, path):
        """Setup an Account class with values from GConf."""
        email = self.gconf.get_value('{0}/email'.format(path))
        account = Account(email)
        for pspec in account.props:
            if pspec.name == 'password':
                auth_token = self.gconf.get_value('{0}/auth_token'.format(path))
                account.props.password = self.keyring.get_password(auth_token)
            elif pspec.name != 'email':
                setattr(account.props, pspec.name,
                        self.gconf.get_value('{0}/{1}'.format(path, pspec.name)))
        self._account_hid[account.props.email] = \
                account.connect('notify', self._account_prop_changed)
        self._accounts.append(account)
        return account

    def _account_prop_changed(self, acc, pspec):
        """Called when an Account property is changed. Save the property to GConf. """
        debug('prop changed in '+acc._email)
        if pspec.name == 'password':
            self.keyring.save_password(acc.props.email, acc.props.password)
        else:
            # Can't use get_property because of libindicate bug (LP#499490)
            self.gconf.set_value('{0}/accounts/{1}/{2}'.format(self.path, acc.props.email, pspec.name),
                                 getattr(acc.props, pspec.name))
                

