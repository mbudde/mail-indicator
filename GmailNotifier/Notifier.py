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

from Utils import debug

class Notifier(object):
    """Indicate server.
    
    Takes care of showing notifications when new mail is found or error occurs
    and enabling/disabling of accounts.
    """

    def __init__(self, conf):
        self.conf = conf
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.mail")
        self.server.set_desktop_file("/usr/share/applications/gmail-notifier/gmail-notifier.desktop")
        self.server.connect("server-display", self._clicked)
        self.server.show()
        self.first_check = True
        pynotify.init("GmailNotifier")
        self.notification = pynotify.Notification('Unread mail', '',
                                                  'notification-message-email')
        self.error_notification = pynotify.Notification('Unable to connect', '',
                                                        'notification-message-email')
        self.notification.connect('closed', self._clear_notification)

    def start_mail_checks(self):
        for acc in self.conf.get_accounts():
            debug("Account: %s, enabled: %s" % (acc.props.email, acc.props.enabled))
            acc.connect('new-mail', self.notify_mail)
            acc.connect('auth-error', self.notify_error)
            acc.connect('notify::enabled', self._account_enabled_cb)
            acc.connect('user-display', self._account_clicked)
            if acc.props.enabled:
                acc.show()
                acc.start_check()
                # TODO: Make non-blocking
                acc.check_mail()

    def notify_mail(self, acc, count):
        if not acc.props.notifications:
            return
        word = self.first_check and 'Unread' or 'New'
        self.notification.props.summary = '%s mail' % (word)
        body = self.notification.props.body or ''
        body += '\nYou have %d %s mail%s at %s.' % \
                (count, word.lower(), count == 1 and "" or "s", acc.props.email)
        self.notification.props.body = body.lstrip()
        self.notification.show()

    def notify_error(self, acc):
        body = 'An error was encountered while trying to check %s. '\
               'Check email and password is correct.' % acc.props.email
        self.error_notification.props.body = body                                       
        self.error_notification.show()

    def destroy(self):
        self.server.hide()

    def _clicked(self, server):
        self.conf.open_pref_window()

    def _account_clicked(self, acc):
        app = self.conf.props.mail_application
        if app == 'browser':
            os.popen("gnome-open '%s' &" % getattr(acc, 'link', ''))
        elif app == 'custom':
            command = self.conf.props.custom_app_exec
            # Replace %U etc. with link
            if '%' in command:
                pos = command.find('%')
                command = command[:pos] + "'%s'" % getattr(acc, 'link', '') + command[pos+2:]
            os.popen(command + ' &')
        acc.lower()

    def _clear_notification(self, n):
        self.notification.props.body = ''
        self.first_check = False

    def _account_enabled_cb(self, acc, prop):
        debug('account %s has been %s' % (acc._email, acc._enabled and 'enabled' or 'disabled'))
        if acc.props.enabled:
            acc.start_check()
        else:
            acc.stop_check()

