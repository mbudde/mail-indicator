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

import gtk
import gio

import Utils
import info

from Account import Account

_pref_instance = None

class PreferenceDialog(object):

    COL_ENABLED, COL_EMAIL, COL_ACCOUNT = range(3)

    @classmethod
    def open(cls, conf):
        global _pref_instance
        if not _pref_instance:
            _pref_instance = cls(conf)
        _pref_instance.show()


    def __init__(self, conf):
        self.conf = conf
        ui = gtk.Builder()
        self.ui = ui
        # TODO: path handling
        ui.add_from_file(Utils.get_data_file('gmail-notifier.ui'))
        ui.connect_signals(self)

        self.window = ui.get_object('prefs_window')
        self.account_editor = ui.get_object('account_editor')
        self.account_store = ui.get_object('account_store')
        self.account_treeview = ui.get_object('account_treeview')

        # Remove and edit buttons should be disabled when no account is
        # selected
        btns = self.get_widgets('edit_account', 'remove_account')
        viewsel = self.account_treeview.get_selection()
        def sel_changed(sel):
            state = (sel.count_selected_rows() == 1)
            for btn in btns: btn.props.sensitive = state
        viewsel.connect('changed', sel_changed)

        # Populate account store
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

        # Load preferences from Config
        self.prop2widget_map = {
            'notifications': 'enable_notifications_globally',
            'run-on-startup': 'run_on_startup',
            'notification-mode': [
                ('count', 'notify_count'),
                ('email', 'notify_email')
            ],
            'mail-application': [
                ('browser', 'use_default_browser'),
                ('custom', 'use_custom_application'),
                ('none', 'only_clear_indicator')
            ],
        }
        for prop, widget in self.prop2widget_map.iteritems():
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
        about.set_program_name(info.NAME)
        about.set_version(info.VERSION)
        about.set_comments(info.DESCRIPTION)
        about.set_website(info.WEBSITE)
        about.set_authors(info.AUTHORS)
        about.set_license(info.LICENSE_TEXT)
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
        self.open_account_editor(new=True)

    def remove_account(self, w):
        treesel = self.account_treeview.get_selection()
        model, iter = treesel.get_selected()
        if not iter:
            return None
        acc = model.get_value(iter, self.COL_ACCOUNT)
        if acc:
            self.conf.remove_account(acc)
        del self.account_store[iter]

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

    def open_account_editor(self, acc=None, new=False):
        self.account_to_editor_map = (
            # account property, widget name, widget property
            ('email', 'email', 'text'),
            ('password', 'password', 'text'),
            ('interval', 'interval', 'value'),
            ('notifications', 'notifications_enabled_account', 'active')
        )
        if new:
            self.ui.get_object('email').props.sensitive = True
            self.ui.get_object('email_help').props.visible = True
            self.ui.get_object('account_table').props.row_spacing = 0
            map = (
                ('email', 'text', ''),
                ('password', 'text', ''),
                ('interval', 'value', 10),
                ('notifications_enabled_account', 'active', True)
            )
            for w, prop, default in map:
                self.ui.get_object(w).set_property(prop, default)
        else:
            self.ui.get_object('email').props.sensitive = False
            self.ui.get_object('email_help').props.visible = False
            self.ui.get_object('account_table').props.row_spacing = 3
            for aprop, widget, wprop in self.account_to_editor_map:
                self.ui.get_object(widget).set_property(wprop, getattr(acc.props, aprop))
            self.account_editor.set_data('account', acc)
        self.account_editor.set_data('new', new)
        self.account_editor.show()

    def close_account_editor(self, w):
        new = self.account_editor.get_data('new')
        if w.props.name == 'editor_ok':
            if new:
                acc = Account(self.ui.get_object('email').props.text)
            else:
                acc = self.account_editor.get_data('account')
            # map is defined in open_account_editor
            for aprop, id, wprop in self.account_to_editor_map:
                if id == 'email': continue
                w = self.ui.get_object(id)
                setattr(acc.props, aprop, w.get_property(wprop))
            if new:
                if self.conf.save_account(acc):
                    self.account_store.append((acc.props.enabled, acc.props.email, acc))
                else:
                    # TODO: inform user that the account already exists
                    pass
        self.account_editor.hide()

    def clear_password(self, entry, pos, event):
        entry.props.text = ''
        entry.grab_focus()

    def generic_save_state(self, w):
        for prop, widget in self.prop2widget_map.iteritems():
            if type(widget) == str and widget == w.name:
                self.conf.set_property(prop, w.props.active)
            elif type(widget) == list:
                # Toggle, only let the active one through
                if not w.props.active:
                    return
                for item in widget:
                    val, radio = item
                    if radio == w.name:
                        self.conf.set_property(prop, val)

    def run_on_startup_toggled(self, w):
        self.conf.props.run_on_startup = w.props.active

    def enable_notifications_globally_toggled(self, w):
        active = w.props.active
        for child in self.get_widgets('notify_count', 'notify_email'):
            child.props.sensitive = active
        self.generic_save_state(w)

    def use_custom_application_toggled(self, w):
        active = w.props.active
        for child in self.get_widgets('application_icon', 'application_icon_eb', 'application_name'):
            child.props.sensitive = active
        self.generic_save_state(w)

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

