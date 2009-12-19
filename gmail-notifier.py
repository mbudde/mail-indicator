#!/usr/bin/env python
#
# Name: Gmail Notifier
# Version: 1.5.2
# Copyright 2009 Michael Tom-Wing
# Author: Michael Tom-Wing <mtomwing@gmail.com>
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

class Message(indicate.Indicator):
	def __init__(self, title, sender, time, link):
		indicate.Indicator.__init__(self)
		self.title = title
		self.sender = sender
		self.link = link
		self.time = time
		self.show()
		self.connect("user-display", self.clicked)
		self.set_property("subtype", "mail")
		if sender:
			self.set_property("name", "%s - %s" % (title, sender))
		else:
			self.set_property("name", "%s" % title)
		self.set_property_time("time", self.time)
		self.alert()
		self.last = 0

	def alert(self):
		self.set_property("draw-attention", "true")

	def lower(self):
		self.set_property("draw-attention", "false")

	def clicked(self, indicator):
		os.popen("gnome-open '%s' &" % (self.link))
		self.set_property("draw-attention", "false")
	
class Notifier:
	def __init__(self, username, password, check_time):
		self.server = indicate.indicate_server_ref_default()
		self.server.set_type("message.mail")
		self.server.set_desktop_file("/usr/share/applications/gmail-notifier/gmail-notifier.desktop")
		self.server.connect("server-display", self.clicked)
		self.messages = []
		self.check_time = check_time
		pynotify.init("icon-summary-body")
		self.notification = pynotify.Notification("Gmail Notifier", "You have mail.")
		self.error = pynotify.Notification("Gmail Notifier", "Unable to connect.")
		self.req = urllib2.Request("https://mail.google.com/mail/feed/atom/")
		self.req.add_header("Authorization", "Basic %s" % (base64.encodestring("%s:%s" % (username, password))[:-1]))
		self.messages.append(Message("Initial check in 30s", None, time.time(), "http://ahadiel.org"))
		gobject.timeout_add_seconds(30, self.checkMail)

	def clicked(self, server):
		os.popen("gnome-open 'http://gmail.com' &")

	def checkMail(self):
		try:
			atom = feedparser.parse(urllib2.urlopen(self.req).read())
		except:
			self.error.show()
			print "Invalid password. Please rerun with any parameter to re-enter your email/password."
			print "\tie. python gmail-notifier.py reset"
			return

		new = False
		for email in atom["entries"][::-1]:
			if(email["title"] in [message.title for message in self.messages]):
				# already in self.messages
				for message in self.messages:
					if(email["title"] == message.title):
						message.lower()
						break
			else:
				# not in self.messages
				self.messages.append(Message(email["title"], email["author_detail"]["name"], time.mktime(time.localtime(calendar.timegm(time.strptime(email["issued"].replace("T24", "T00"), "%Y-%m-%dT%H:%M:%SZ")))), email["link"]))
				self.messages[-1].alert()
				new = True

		if(new):
			self.notification.show()

		to_delete = []
		for message in self.messages:
			if(message.title not in [email["title"] for email in atom["entries"]]):
				# the email is no longer unread
				# remove it from self.messages
				to_delete.append(message)
			else:
				pass

		for message in to_delete:
			message.lower()
			message.hide()
			self.messages.remove(message)

		#self.server.set_property("count", len(self.messages))
		gobject.timeout_add_seconds(self.check_time, self.checkMail)

class Keyring:
	def __init__(self, app_name, app_desc1, app_desc2):
		self.keyring = gnomekeyring.get_default_keyring_sync()
		self.app_name = app_name
		self.app_desc1 = app_desc1
		self.app_desc2 = app_desc2

	def getInfo(self):
		auth_token = gconf.client_get_default().get_int("/apps/gnome-python-desktop/keyring_auth_token")
		if auth_token > 0:
			try:
				secret = gnomekeyring.item_get_info_sync(self.keyring, auth_token).get_secret()
			except gnomekeyring.DeniedError:
				login = None
				password = None
				check = None
				auth_token = 0
			else:
				login, password, check = secret.split('\n')
		else:
			login = None
			password = None
			check = None

		return login, password, int(check)

	def setInfo(self, login, password, check):
		auth_token = gnomekeyring.item_create_sync(self.keyring, gnomekeyring.ITEM_GENERIC_SECRET, "%s, %s" % (self.app_name, self.app_desc1), dict(appname="%s, %s" % (self.app_name, self.app_desc1)), "\n".join((login, password,str(check))), True)
		gconf.client_get_default().set_int("/apps/gnome-python-desktop/keyring_auth_token", auth_token)

if(__name__ == "__main__"):
	gkey = Keyring("Gmail Notifier", "login information", "A simple Gmail Notifier")
	
	try:
		if(len(sys.argv) > 1):
			raise
		else:
			USERNAME, PASSWORD, CHECK_TIME = gkey.getInfo()
	except:
		print "Getting username...",
		USERNAME = getText("email", "")
		print "Done"
		print "Getting password...",
		PASSWORD = getText("password", "", True)
		print "Done"
		print "Getting interval...",
		CHECK_TIME = getText("interval", "Interval at which email will be checked\n<i>ie. 1d20m30s</i>").strip()
		nums = [str(x) for x in range(0, 10)]
		units = {"s" : 1, "m" : 60, "h" : 3600, "d" : 86400}
		i = 0
		while(len(CHECK_TIME) != 0):
			for char in CHECK_TIME:
				if(char not in nums):
					#means it's either a space or a unit
					if(char in units.keys()):
						# it's a unit
						i += int(CHECK_TIME[:CHECK_TIME.find(char)])*units[char]
						CHECK_TIME = CHECK_TIME[CHECK_TIME.find(char)+1:]
		CHECK_TIME = i
		print "Done"
		gkey.setInfo(USERNAME, PASSWORD, CHECK_TIME)
	
	x = Notifier(USERNAME, PASSWORD, CHECK_TIME)
	print "Running..."
	gtk.main()
