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

import gnomekeyring

class Keyring(object):

    def __init__(self, app_name, app_desc):
        self.keyring = gnomekeyring.get_default_keyring_sync()
        self.app_name = app_name
        self.app_desc = app_desc

    def get_password(self, auth_token):
        password = None
        if auth_token > 0:
            try:
                password = gnomekeyring.item_get_info_sync(self.keyring, auth_token).get_secret()
            except:
                pass
        return password

    def save_password(self, email, password):
        auth_token = gnomekeyring.item_create_sync(
            self.keyring,
            gnomekeyring.ITEM_GENERIC_SECRET,
            "%s - %s" % (self.app_name, email),
            dict(appname="%s - %s" % (self.app_name, self.app_desc), email=email),
            password,
            True)
        return auth_token

