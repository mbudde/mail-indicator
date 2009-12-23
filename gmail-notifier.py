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
import gio
import glib
import urllib2
import base64
import os
import sys
import time
import calendar
import gconf
import gnomekeyring


if __name__ == "__main__" :
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        DEBUG = True
    else:
        DEBUG = False

GCONF_PATH = "/apps/gmail-notifier"

def debug(str):
    if DEBUG:
        print str

def debug_fun(fun):
    if not DEBUG:
        return fun
    def dbg_fun(*args, **kwargs):
        res = fun(*args, **kwargs)
        print '%s ( %s %s ) -> %s' % (fun.__name__, args, kwargs, res)
        return res
    return dbg_fun

def debug_method(fun):
    if not DEBUG:
        return fun
    def dbg_fun(klass, *args, **kwargs):
        res = fun(klass, *args, **kwargs)
        print '%s.%s ( %s %s ) -> %s' % (klass.__class__, fun.__name__, args, kwargs, res)
        return res
    return dbg_fun


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
            'The time in minutes to pass before the account is checked for new mail',
            1,
            2880,
            10,
            gobject.PARAM_READWRITE
        ),
        'enabled': (
            gobject.TYPE_BOOLEAN,
            'should the account be checked for new mail', '',
            True,
            gobject.PARAM_READWRITE
        ),
        'notifications': (
            gobject.TYPE_BOOLEAN,
            'should there pop up an notification when theres new mail', '',
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

    def __init__(self):
        indicate.Indicator.__init__(self)
        self.link = None
        self._last_check = None
        self.set_property('subtype', 'mail')
        self._req = None
        self.update_request()

    def do_get_property(self, pspec):
        try:
            return getattr(self, '_'+pspec.name)
        except AttributeError:
            return pspec.default_value

    @debug_method
    def do_set_property(self, pspec, value):
        setattr(self, '_'+pspec.name, value)
        if pspec.name == 'email':
            if value:
                self.set_property('name', value)
        if pspec.name in ('password', 'email'):
            self.update_request()
        if pspec.name == 'interval':
            self.stop_check()
            self.start_check()
            

    @debug_method
    def update_request(self):
        auth_string = base64.encodestring('%s:%s' % (self.props.email, self.props.password))[:-1]
        self._req = urllib2.Request("https://mail.google.com/mail/feed/atom/")
        self._req.add_header('Authorization', 'Basic %s' % auth_string)

    def start_check(self):
        self._event_id = gobject.timeout_add_seconds(self.props.interval*60, self.check_mail)

    def stop_check(self):
        gobject.source_remove(self._event_id)

    @debug_method
    def check_mail(self):
        if not self.props.enabled:
            debug('Account not enabled')
            return False

        debug("Check for new mail on %s" % self._email)
        atom = None
        try:
            atom = feedparser.parse(urllib2.urlopen(self._req).read())
        except urllib2.HTTPError as e:
            if e.code == 401:
                self.emit("auth-error")
                self.props.enabled = False
                self.hide()
                debug('Auth error')
                return False
        except urllib2.URLError as e:
            # Probably not connect to the internet. Try again later.
            return True

        new = 0
        for email in atom["entries"]:
            utctime = calendar.timegm(time.strptime(email["issued"], "%Y-%m-%dT%H:%M:%SZ"))
            if not self._last_check or utctime > self._last_check:
                new += 1
        debug("%d new mails" % new)
        self._last_check = time.time()
        count = atom["feed"]["fullcount"]
        self.set_property('count', count)
        if new > 0:
            self.alert()
            self.show()
            self.emit("new-mail", new)
        elif int(count) > 0:
            self.show()
        else:
            self.hide()

        self.link = atom["feed"]["links"][0]["href"] 
        debug("Checking again in %d minutes" % self._interval)
        return True

    def alert(self):
        self.set_property('draw-attention', 'true')

    def lower(self):
        self.set_property('draw-attention', 'false')


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


class PreferenceDialog(object):

    COL_ENABLED, COL_EMAIL, COL_ACCOUNT = range(3)

    def __init__(self, conf):
        self.conf = conf
        ui = gtk.Builder()
        self.ui = ui
        # TODO: path handling
        ui.add_from_file('gmail-notifier.ui')
        self.window = ui.get_object('prefs_window')
        self.account_editor = ui.get_object('account_editor')
        self.account_store = ui.get_object('account_store')
        self.account_treeview = ui.get_object('account_treeview')

        ui.connect_signals(self)
        # Populate store
        for acc in conf.get_accounts():
            iter = self.account_store.append((
                acc.props.enabled,
                acc.props.email,
                acc
            ))
            acc.connect('notify::enabled', self.account_enabled_changed, iter)

        # Setup application DnD
        icon = ui.get_object('application_icon_eb')
        icon.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                           [('text/uri-list', 0, 1)],
                           gtk.gdk.ACTION_COPY)

        prop2widget_map = {
            'notifications': 'enable_notifications_globally',
            'run-on-startup': 'run_on_startup',
            'notification-mode': [('count', 'notify_count'),
                                  ('mail', 'notify_each_mail')],
            'mail-application': [('browser', 'use_default_browser'),
                                 ('custom', 'use_custom_application')],
        }
        for prop, widget in prop2widget_map.iteritems():
            if type(widget) == str:
                self.ui.get_object(widget).props.active = self.conf.get_property(prop)
            elif type(widget) == list:
                for item in widget:
                    val, radio = item
                    if self.conf.get_property(prop) == val:
                        self.ui.get_object(radio).props.active = True
        self.set_app_display_from_data({
            'name': self.conf.props.custom_app_name,
            'icon': self.conf.props.custom_app_icon})


    def get_widgets(self, *args):
        return [self.ui.get_object(name) for name in args]

    def show(self):
        self.window.present()

    def hide(self, *args):
        self.window.hide()

    def quit(self, *args):
        gtk.main_quit()

    def show_aboutdialog(self, *args):
        about = gtk.AboutDialog()
        about.set_name('Gmail Notifier')
        about.set_version('1.5.2')
        about.set_license('GPL')
        def close(w, res):
            if res == gtk.RESPONSE_CANCEL: w.destroy()
        about.connect('response', close)
        about.show()

    def get_account_selection(self):
        treesel = self.account_treeview.get_selection()
        model, iter = treesel.get_selected()
        if not iter:
            return None
        return model.get_value(iter, self.COL_ACCOUNT)

    def add_account(self, w):
        acc = Account()
        if self.open_account_editor(acc):
            return
        self.account_store.append((acc.props.enabled, acc.props.email, acc))
        self.conf.save_account(acc)

    def remove_account(self, w):
        pass

    def edit_account(self, w):
        acc = self.get_account_selection()
        if acc:
            self.open_account_editor(acc)

    def account_enabled_toggle(self, w, path):
        model = self.account_treeview.get_model()
        row = model[path]
        state = row[self.COL_ENABLED]
        row[self.COL_ENABLED] = not state
        row[self.COL_ACCOUNT].props.enabled = not state

    def account_enabled_changed(self, acc, pspec, iter):
        model = self.account_treeview.get_model()
        path = model.get_path(iter)
        state = model[path][self.COL_ENABLED]
        if state != acc.props.enabled:
            model[path][self.COL_ENABLED] = acc.props.enabled

    def open_account_editor(self, acc):
        self.account_to_editor_map = (
            # account property, widget name, widget property
            ('email', 'email', 'text'),
            ('password', 'password', 'text'),
            ('interval', 'interval', 'value'),
            ('notifications', 'notifications_enabled_account', 'active')
        )
        for aprop, widget, wprop in self.account_to_editor_map:
            # Can't use get_property because of libindicate bug (LP#499490)
            self.ui.get_object(widget).set_property(wprop, getattr(acc.props, aprop))
        self.account_editor.set_data('account', acc)
        self.account_editor.show()

    def close_account_editor(self, w):
        if w.props.name == 'editor_ok':
            acc = self.account_editor.get_data('account')
            # map is defined in open_account_editor
            for aprop, id, wprop in self.account_to_editor_map:
                w = self.ui.get_object(id)
                # Can't use set_property because of libindicate bug (LP#499490)
                setattr(acc.props, aprop, w.get_property(wprop))
        self.account_editor.hide()

    def clear_password(self, w):
        entry = self.ui.get_object('password')
        entry.props.text = ''
        entry.grab_focus()

    def generic_save_state(self, w):
        if not w.props.active:
            return
        save_map = (
            ('use_default_browser', 'mail-application', 'browser'),
            ('only_clear_indicator', 'mail-application', 'none'),
            ('notify_count', 'notification-mode', 'count'),
            ('notify_email', 'notification-mode', 'email'),
        )
        for name, prop, val in save_map:
            if w.name == name:
                self.conf.set_property(prop, val)
                break

    def run_on_startup_toggled(self, w):
        self.conf.props.run_on_startup = w.props.active

    def enable_notifications_globally_toggled(self, w):
        active = w.props.active
        for child in self.get_widgets('notify_count', 'notify_email'):
            child.props.sensitive = active
        self.conf.props.notifications = active

    def use_custom_application_toggled(self, w):
        active = w.props.active
        for child in self.get_widgets('application_icon', 'application_icon_eb', 'application_name'):
            child.props.sensitive = active
        if active:
            self.conf.props.mail_application = 'custom'

    def drag_data_received(self, w, context, x, y, data, info, time):
        app_data = self.get_data_from_desktop_file(data.get_uris()[0])
        context.finish(False, False, time)
        self.set_app_display_from_data(app_data)
        for key, val in app_data.iteritems():
            self.conf.set_property('custom-app-'+key, val)

    def get_data_from_desktop_file(self, uri):
        path = gio.File(uri).get_path()
        data = {'name': None, 'exec': None, 'icon': None, 'terminal': None}
        file = open(path)
        for line in file:
            for s in ('Name', 'Exec', 'Icon', 'Terminal'):
                if line.startswith(s+'='):
                    data[s.lower()] = line.split('=')[1].rstrip()
                    break
        file.close()
        if data['terminal']:
            data['terminal'] = (data['terminal'].lower() == 'true') and True or False
        return data

    def set_app_display_from_data(self, data):
        self.ui.get_object('application_name').props.label = data['name']
        icon = self.ui.get_object('application_icon')
        try:
            if data['icon'].startswith('/'):
                pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(data['icon'], 32, 32)
            else:
                pixbuf = gtk.icon_theme_get_default().load_icon(
                    data['icon'], 32, gtk.ICON_LOOKUP_USE_BUILTIN)
        except glib.GError:
            pixbuf = gtk.icon_theme_get_default().load_icon(
                'gnome-panel-launcher', 32, gtk.ICON_LOOKUP_USE_BUILTIN)
        icon.set_from_pixbuf(pixbuf)


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
        self.notification = pynotify.Notification('Unread mail', '',
                                                  'notification-message-email')
        self.error_notification = pynotify.Notification('Unable to connect', '',
                                                        'notification-message-email')
        self.notification.connect('closed', self.clear_notification)

    def start_mail_checks(self):
        for acc in self.conf.get_accounts():
            debug("Account: %s, enabled: %s" % (acc.props.email, acc.props.enabled))
            acc.connect('new-mail', self.notify)
            acc.connect('auth-error', self.notify_error)
            acc.connect('notify::enabled', self.account_enabled_cb)
            acc.connect('user-display', self.account_clicked)
            if acc.props.enabled:
                acc.show()
                acc.start_check()
                if DEBUG:
                    acc.check_mail()

    def clicked(self, server):
        self.conf.open_pref_window()

    def account_clicked(self, acc):
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

    def notify(self, acc, count):
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

    def clear_notification(self, n):
        self.notification.props.body = ''
        self.first_check = False

    def account_enabled_cb(self, acc, prop):
        debug('account %s has been %s' % (acc.props.email, acc._enabled and 'enabled' or 'disabled'))
        if acc.props.enabled:
            acc.start_check()
        else:
            acc.stop_check()

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
    GmailNotifier()
