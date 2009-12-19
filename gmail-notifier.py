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

import gobject
import gtk
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

	__gsignals__ = {
		'new-mail': (gobject.SIGNAL_ACTION, None, (int,)),
	}

	def __init__(self):
		indicate.Indicator.__init__(self)
		self.email = None
		self.password = None
		self.interval = 300
		self.enabled = True
		self.count = 0
		self.link = None
		self.last_check = None
		self.connect("user-display", self.clicked)
		self.set_property("subtype", "mail")
		self.req = None

	@property
	def email(self):
		return self._email
	@email.setter
	def email(self, val):
		self._email = val
		if val:
			self.set_property("name", val)

	def check_mail(self):
		debug("Check for new mail on %s" % self.email)
		if not self.req:
			if not self.email or not self.password:
				raise ValueError("missing username or password")
			self.req = urllib2.Request("https://mail.google.com/mail/feed/atom/")
			self.req.add_header("Authorization", "Basic %s"
			                    % (base64.encodestring("%s:%s" % (self.email, self.password))[:-1]))
		try:
			atom = feedparser.parse(urllib2.urlopen(self.req).read())
		except:
			self.error.show()
			print "Invalid password. Please rerun with any parameter to re-enter your email/password."
			print "\tie. python gmail-notifier.py reset"
			return

		new = 0
		for email in atom["entries"]:
			utctime = calendar.timegm(time.strptime(email["issued"], "%Y-%m-%dT%H:%M:%SZ"))
			if not self.last_check or utctime > self.last_check:
				new += 1
		debug("%d new mails" % new)
		if new > 0:
			self.alert()
			self.show()
			self.emit('new-mail', new)
		self.last_check = time.time()

		count = int(atom["feed"]["fullcount"])
		self.set_property("count", str(count));

		self.link = atom["feed"]["links"][0]["href"] 
		debug("Checking again in %d seconds" % self.interval)
		gobject.timeout_add_seconds(self.interval, self.check_mail)

	def alert(self):
		self.set_property("draw-attention", "true")

	def lower(self):
		self.set_property("draw-attention", "false")

	def clicked(self, indicator):
		if self.link:
			os.popen("gnome-open '%s' &" % (self.link))
		self.lower()
		self.hide()


class Notifier:
	def __init__(self, accounts):
		self.server = indicate.indicate_server_ref_default()
		self.server.set_type("message.mail")
		self.server.set_desktop_file("/usr/share/applications/gmail-notifier/gmail-notifier.desktop")
		self.server.connect("server-display", self.clicked)
		self.server.show()
		self.messages = []
		pynotify.init("icon-summary-body")
		self.error = pynotify.Notification("Gmail Notifier", "Unable to connect.")
		self.first_check = True

		for acc in accounts:
			debug("Account: %s, enabled: %s" % (acc.email, acc.enabled))
			if acc.enabled:
				acc.connect("new-mail", self.notify)
				gobject.timeout_add_seconds(30, acc.check_mail)

	def clicked(self, server):
		# TODO: open config dialog
		pass

	def notify(self, acc, count):
		str = "You have %d %s mail%s." % (count, self.first_check and "unread"
		                                  or "new", count == 1 and "" or "s")
		notification = pynotify.Notification("Gmail Notifier - %s" % acc.email, str)
		notification.show()
		self.first_check = False

	def destroy(self):
		self.server.hide()


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


class Config:
	def __init__(self, path):
		self.gconf = gconf.client_get_default()
		self.path = path
		self.keyring = Keyring("Gmail Notifier", "A simple Gmail Notifier")

	def get_accounts(self):
		paths = self.gconf.all_dirs(os.path.join(self.path, "accounts"))
		accounts = []
		for path in paths:
			accounts.append(self.get_account(path))
		return accounts

	def get_account(self, path):
		account = Account()
		account.enabled  = self.gconf.get_bool("%s/enabled" % path)
		account.email    = self.gconf.get_string("%s/email" % path)
		account.interval = self.gconf.get_int("%s/interval" % path)
		auth_token       = self.gconf.get_int("%s/auth_token" % path)
		account.password = self.keyring.get_password(auth_token)
		return account

	def save_account(self, account):
		path = "%s/accounts/%s" % (self.path, account.email)
		self.gconf.set_bool("%s/enabled" % path, account.enabled)
		self.gconf.set_string("%s/email" % path, account.email) 
		self.gconf.set_int("%s/interval" % path, account.interval) 
		auth_token = self.keyring.save_password(account.email, account.password)
		self.gconf.set_int("%s/auth_token" % path, auth_token)

	def remove_account(self, account):
		path = os.path.join(self.path, "accounts", account.email)
		self.gconf.recursive_unset(path, 0)


if __name__ == "__main__" :
	conf = Config(GCONF_PATH)
	accounts = conf.get_accounts()

	if len(sys.argv) > 1 and sys.argv[1] == "debug":
		DEBUG = True
	elif len(sys.argv) > 1:
		for acc in accounts:
			conf.remove_account(acc)
		account = Account()
		print "Getting username...",
		account.email = getText("email", "")
		print "Done"
		print "Getting password...",
		account.password = getText("password", "", True)
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
		account.interval = i
		print "Done"
		conf.save_account(account)
		accounts.append(account)
	
	notifier = Notifier(accounts)
	print "Running..."
	try:
		gtk.main()
	except KeyboardInterrupt:
		notifier.destroy()
