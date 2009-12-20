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

deps = {"indicate" : "python-indicate", "pynotify" : "python-notify", "feedparser" : "python-feedparser"}
need = []
for dep in deps.keys():
    try:
        exec("import %s" % (dep))
    except:
        need.append(dep)
if(len(need) > 0):
    print "You seem to be missing the following:"
    for dep in need:
        print "\t%s" % (deps[dep])
    print "\nNote: Package names may vary from distro to distro."

import gtk
import gobject
import urllib2
import base64
import os
import sys
import time
import calendar
import gconf
import gnomekeyring


DEBUG = False

GCONF_PATH = "/apps/gmail-notifier"

def debug(str):
    if DEBUG:
        print str

def responseToDialog(entry, dialog, response):
    dialog.response(response)

def getText(name, description, hidden=False):
    dialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_OK, None)
    dialog.set_markup("Please enter your <b>%s</b>:" % (name))
    entry = gtk.Entry()
    if(hidden):
        entry.set_visibility(False)
    entry.connect("activate", responseToDialog, dialog, gtk.RESPONSE_OK)
    hbox = gtk.HBox()
    hbox.pack_start(gtk.Label("%s:" % (name.capitalize())), False, 5, 5)
    hbox.pack_end(entry)
    dialog.format_secondary_markup(description)
    dialog.vbox.pack_end(hbox, True, True, 0)
    dialog.show_all()
    dialog.run()
    text = entry.get_text()
    dialog.destroy()
    return text


class Account(indicate.Indicator):

    __gproperties__ = {
        'email': (
            gobject.TYPE_STRING,
            'Gmail address', '',
            None, # default
            gobject.PARAM_READWRITE
        ),
        'password': (
            gobject.TYPE_STRING,
            'Gmail password', '',
            None,
            gobject.PARAM_READWRITE
        ),
        'interval': (
            gobject.TYPE_INT,
            'Interval between mail checks',
            'The time in seconds to pass before the account is checked for new mail',
            30,
            86400,
            600,
            gobject.PARAM_READWRITE
        ),
        'enabled': (
            gobject.TYPE_BOOLEAN,
            'should the account be checked for new mail', '',
            True,
            gobject.PARAM_READWRITE
        ),
    }

    __gsignals__ = {
        'new-mail': (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_INT,)
        ),
        'auth-error': (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            ()
        ),
    }

    def __init__(self, email=None, password=None, interval=600, enabled=True):
        indicate.Indicator.__init__(self)
        self.email = email
        self.password = password
        self.interval = interval
        self.enabled = enabled
        self.set_property('name', email)
        self.link = None
        self.last_check = None
        self.connect("user-display", self.clicked)
        self.set_property('subtype', 'mail')
        self.req = None
        self.update_request()

    def do_set_property(self, pspec, value):
        if not hasattr(self, pspec.name):
            raise AttributeError, 'unknown property %s' % pspec.name
        setattr(self, pspec.name, value)
        if pspec.name == 'email':
            if value:
                self.set_property('name', email)
        if pspec.name in ('password', 'email'):
            self.update_request()

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def update_request(self):
        self.req = urllib2.Request("https://mail.google.com/mail/feed/atom/")
        self.req.add_header("Authorization", "Basic %s"
                            % (base64.encodestring("%s:%s" % (self.email, self.password))[:-1]))

    def start_check(self):
        gobject.timeout_add_seconds(self.interval, self.check_mail)

    def stop_check(self):
        pass

    def check_mail(self):
        if not self.enabled:
            return

        debug("Check for new mail on %s" % self.email)
        try:
            atom = feedparser.parse(urllib2.urlopen(self.req).read())
        except:
            self.emit("auth-error")
            #self.props.enabled = False
            self.hide()
            return False

        new = 0
        for email in atom["entries"]:
            utctime = calendar.timegm(time.strptime(email["issued"], "%Y-%m-%dT%H:%M:%SZ"))
            if not self.last_check or utctime > self.last_check:
                new += 1
        debug("%d new mails" % new)
        if new > 0:
            self.alert()
            self.show()
            self.emit("new-mail", new)
        self.last_check = time.time()

        count = int(atom["feed"]["fullcount"])
        self.set_property('count', str(count))

        self.link = atom["feed"]["links"][0]["href"] 
        debug("Checking again in %d seconds" % self.interval)
        return True

    def alert(self):
        self.set_property('draw-attention', 'true')

    def lower(self):
        self.set_property('draw-attention', 'false')

    def clicked(self, indicator):
        if self.link:
            os.popen("gnome-open '%s' &" % (self.link))
        self.lower()
        self.hide()


class Keyring:

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


class Config(gobject.GObject):

    def __init__(self, path):
        gobject.GObject.__init__(self)
        self.gconf = gconf.client_get_default()
        self.path = path
        self.keyring = Keyring("Gmail Notifier", "A simple Gmail Notifier")
        self._accounts = None

    def get_accounts(self):
        if self._accounts == None:
            paths = self.gconf.all_dirs('%s/accounts' % self.path)
            self._accounts = []
            for path in paths:
                self._accounts.append(self._init_account_from_gconf(path))
        return self._accounts

    def _init_account_from_gconf(self, path):
        enabled    = self.gconf.get_bool("%s/enabled" % path)
        email      = self.gconf.get_string("%s/email" % path)
        interval   = self.gconf.get_int("%s/interval" % path)
        auth_token = self.gconf.get_int("%s/auth_token" % path)
        password   = self.keyring.get_password(auth_token)
        account    = Account(email=email, password=password, interval=interval, enabled=enabled)
        account.connect('notify', self._prop_changed)
        return account

    def save_account(self, account):
        path = "%s/accounts/%s" % (self.path, account.props.email)
        self.gconf.set_bool("%s/enabled" % path, account.props.enabled)
        self.gconf.set_string("%s/email" % path, account.props.email) 
        self.gconf.set_int("%s/interval" % path, account.props.interval) 
        auth_token = self.keyring.save_password(account.props.email, account.props.password)
        self.gconf.set_int("%s/auth_token" % path, auth_token)

    def remove_account(self, account):
        path = os.path.join(self.path, "accounts", account.props.email)
        self.gconf.recursive_unset(path, 0)

    def _prop_changed(self, acc, prop):
        debug('prop changed in %s' % acc.email)
        if prop.name in ('email', 'interval', 'enabled'):
            self.gconf.set('%s/accounts/%s/%s' % (self.path, acc.props.email, prop.name),
                           acc.get_property(prop.name))
        if prop.name == 'password':
            self.keyring.save_password(acc.props.email, acc.props.password)


class PreferenceDialog(object):

    def __init__(self):
        ui = gtk.Builder()
        ui.add_from_file('gmail-notifier.ui')
        self.window = ui.get_object('prefs_window')
        self.account_store = ui.get_object('account_store')
        # Connect callbacks
        ui.get_object('ok_button').connect('clicked', gtk.main_quit)
        ui.get_object('about').connect('clicked', self.show_aboutdialog)
        ui.get_object('add_account').connect('clicked', self.add_account)
        ui.get_object('remove_account').connect('clicked', self.remove_account)

    def run(self):
        self.window.show()
        gtk.main()

    def show_aboutdialog(self, *args):
        about = gtk.AboutDialog()
        about.set_name('Gmail Notifier')
        about.set_version('1.5.2')
        about.set_license('GPL')
        def close(w, res):
            if res == gtk.RESPONSE_CANCEL: w.destroy()
        about.connect('response', close)
        about.show()

    def add_account(self, w):
        acc = Account()
        acc.email = 'mbudde@gmail.com'
        self.account_store.append((True, acc.email, acc))

    def remove_account(self, w):
        pass


class Notifier:

    def __init__(self, conf):
        self.conf = conf
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.mail")
        self.server.set_desktop_file("/usr/share/applications/gmail-notifier/gmail-notifier.desktop")
        self.server.connect("server-display", self.clicked)
        self.server.show()
        self.first_check = True
        pynotify.init("GmailNotifier")

    def start_mail_checks(self):
        for acc in self.conf.get_accounts():
            debug("Account: %s, enabled: %s" % (acc.email, acc.enabled))
            if acc.enabled:
                acc.connect("new-mail", self.notify)
                acc.connect("auth-error", self.notify_error)
                acc.start_check()

    def clicked(self, server):
        # TODO: open config dialog
        pass

    def notify(self, acc, count):
        str = "You have %d %s mail%s." % (count, self.first_check and "unread"
                                          or "new", count == 1 and "" or "s")
        n = pynotify.Notification("Gmail Notifier - %s" % acc.email, str)
        n.show()
        self.first_check = False

    def notify_error(self, acc):
        n = pynotify.Notification("Gmail Notifier - %s" % acc.email,
                                  "Unable to connect. Email or password may be wrong.")
        n.show()
        password = getText('password', '', True)
        acc.props.password = password
        acc.check_mail()

    def account_enabled_cb(self, acc, prop):
        print prop.value_type.name
        debug('account %s has been %s' % (acc.email, acc.props.enabled and 'enabled'
                                    or 'disabled'))

    def destroy(self):
        self.server.hide()


class GmailNotifier:

    def __init__(self):
        conf = Config(GCONF_PATH)
        notifier = Notifier(conf)
        notifier.start_mail_checks()
        try:
            gtk.main()
        except KeyboardInterrupt:
            notifier.destroy()


if __name__ == "__main__" :

    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        DEBUG = True
    elif len(sys.argv) > 1:
        for acc in accounts:
            conf.remove_account(acc)
        print "Getting username...",
        email = getText("email", "")
        print "Done"
        print "Getting password...",
        password = getText("password", "", True)
        print "Done"
        print "Getting interval...",
        interval = getText("interval", "Interval at which email will be checked\n<i>ie. 1d20m30s</i>").strip()
        nums = [str(x) for x in range(0, 10)]
        units = {"s" : 1, "m" : 60, "h" : 3600, "d" : 86400}
        i = 0
        while(len(interval) != 0):
            for char in interval:
                if(char not in nums):
                    #means it's either a space or a unit
                    if(char in units.keys()):
                        # it's a unit
                        i += int(interval[:interval.find(char)]) * units[char]
                        interval = interval[interval.find(char)+1:]
        interval = i
        print "Done"
        account = Account(email=email, password=password, interval=interval)
        conf.save_account(account)
        accounts.append(account)

    print "Running..."
    GmailNotifier()
