# encoding: utf-8
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

import indicate
import pynotify
import subprocess
import gobject

from Utils import get_desktop_file
from Debug import debug

class Notifier(object):
    """Indicate server.
    
    Takes care of showing notifications when new mail is found or error occurs
    and enabling/disabling of accounts.
    """

    DESKTOP_FILE_NAME = 'mail-indicator.desktop'

    def __init__(self, conf, initial_check):
        self.conf = conf
        self._initial_check = initial_check
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type('message.mail')
        desktop_file = get_desktop_file(self.DESKTOP_FILE_NAME)
        if not desktop_file:
            raise Exception('Could not find desktop file `{0}`'.format(self.DESKTOP_FILE_NAME))
        self.server.set_desktop_file(desktop_file)
        self.server.connect('server-display', self._clicked)
        self.server.show()
        self.first_check = True

        # Setup notifications
        pynotify.init('MailIndicator')
        self.notification = \
                pynotify.Notification('Unread mail', '', 'notification-message-email')
        self.error_notification = \
                pynotify.Notification('Unable to connect', '', 'notification-message-email')
        self.notification.connect('closed', self._clear_notification)

        self._setup_accounts()

    def _setup_accounts(self):
        for acc in self.conf.get_accounts():
            debug('Account: {0}, enabled: {1}'.format(acc.props.email, acc.props.enabled))
            acc.connect('new-mail', self.notify_mail)
            acc.connect('auth-error', self.notify_error)
            acc.connect('notify::enabled', self._account_enabled_cb)
            acc.connect('user-display', self._account_clicked)
            if not acc.props.enabled:
                continue
            acc.show()
            def start_check():
                acc.start_check()
                acc.check_mail()
                return False
            gobject.timeout_add_seconds(self._initial_check, start_check)

    def notify_mail(self, acc, mails):
        if not acc.props.notifications:
            return
        word = self.first_check and 'Unread' or 'New'
        if self.conf.props.notification_mode == 'count':
            self.notification.props.summary = '{0} mail'.format(word)
            body = self.notification.props.body or ''
            body += '\nYou have {count} {word} mail{plur} at {acc}.'.format(
                count=len(mails), word=word.lower(),
                plur=len(mails) == 1 and '' or 's', acc=acc.props.email
            )
            self.notification.props.body = body.lstrip()
            self.notification.show()
        else:
            for author, title, summary in mails:
                if len(title) > 30:
                    title = title[:29] + '…'
                n = pynotify.Notification(title, 'From {0}: {1}'.format(author, summary),
                                          'notification-message-email')
                n.show()

    def notify_error(self, acc):
        body = 'An error was encountered while trying to check {0}. '\
               'Check email and password is correct.'.format(acc.props.email)
        self.error_notification.props.body = body                                       
        self.error_notification.show()

    def destroy(self):
        self.server.hide()

    def _clicked(self, server):
        self.conf.open_pref_window()

    def _account_clicked(self, acc):
        app = self.conf.props.mail_application
        if app == 'browser':
            subprocess.Popen(['gnome-open', getattr(acc, 'link', '')])
        elif app == 'custom':
            command = self.conf.props.custom_app_exec.split()
            # Replace %U etc. with link
            for i, arg in enumerate(command):
                if arg.startswith('%'):
                    command[i] = getattr(acc, 'link', '')
            subprocess.Popen(command)
        acc.lower()

    def _clear_notification(self, n):
        self.notification.props.body = ''
        self.first_check = False

    def _account_enabled_cb(self, acc, prop):
        debug('account {0} has been {1}'.format(acc._email, acc._enabled and 'enabled' or 'disabled'))
        if acc.props.enabled:
            acc.start_check()
        else:
            acc.stop_check()

