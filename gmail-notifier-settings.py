#!/usr/bin/env python
#
# Name: Gmail Notifier
# Version: 1.6
# Copyright 2009 Michael Tom-Wing
# Author: Michael Tom-Wing <mtomwing@gmail.com>
# Date: December 16th, 2009
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

import pygtk
import gtk
import gnomekeyring
import os
import sys
import ConfigParser
import gconf

class Settings:
	def __init__(self):
		self.settings = {}
		self.HOME_FOLDER = "/home/%s" % (os.popen("whoami").read()[:-1])
		self.CONFIG_FOLDER = "%s/.config" % (self.HOME_FOLDER)
		self.GMAIL_CONFIG_FOLDER = "%s/gmail-notifier" % (self.CONFIG_FOLDER)
		self.CONFIG_FILE = "%s/settings.conf" % (self.GMAIL_CONFIG_FOLDER)

		builder = gtk.Builder()
		if(os.path.isfile("settings.glade")):
			builder.add_from_file("settings.glade")
		else:
			builder.add_from_file("/usr/share/applications/gmail-notifier/settings.glade")
		builder.connect_signals({"on_settings_window_destroy" : self.exit, "button_save_clicked" : self.save, "button_close_clicked" : self.exit, "button_about_clicked" : self.showAboutDialog, "popup_close_clicked" : self.hidePopupDialog})
		self.window = builder.get_object("settings_window")
		self.about = builder.get_object("about_dialog")
		self.popup = builder.get_object("popup_dialog")
		self.entryUsername = builder.get_object("entry_username")
		self.entryPassword = builder.get_object("entry_password")
		self.entryCheckTime = builder.get_object("entry_checktime")
		self.imageUsername = builder.get_object("image_username")
		self.imagePassword = builder.get_object("image_password")
		self.imageCheckTime = builder.get_object("image_checktime")
		self.loadConfigFile()
		self.window.show()

	# About/Popup dialog callbacks
	def showAboutDialog(self, widget):
		self.about.show()

	def hidePopupDialog(self, widget):
		self.popup.hide()

	# Other stuff
	def loadConfigFile(self):
		try:
			config = ConfigParser.RawConfigParser()
			config.read(self.CONFIG_FILE)
			self.settings["username"] = config.get("Settings", "username")
			self.settings["check"] = config.get("Settings", "check")
			self.entryUsername.set_text(self.settings["username"])
			self.entryCheckTime.set_text(self.settings["check"])
			gkey = Keyring("Gmail Notifier", "login information", "A simple Gmail Notifier")			
			self.settings["password"] = gkey.getPassword()
			self.entryPassword.set_text(self.settings["password"])
		except:
			self.resetConfigFile()
			self.loadConfigFile()

	def saveConfigFile(self):
		config = ConfigParser.RawConfigParser()
		config.add_section("Settings")
		config.set("Settings", "username", self.settings["username"])
		config.set("Settings", "check", self.settings["check"])
		config.write(open(self.CONFIG_FILE, "wb"))
		gkey = Keyring("Gmail Notifier", "login information", "A simple Gmail Notifier")
		gkey.setPassword(self.settings["password"])
		

	def resetConfigFile(self):
		if(not os.path.exists(self.CONFIG_FOLDER)):
			# .config does not exist
			os.mkdir(self.CONFIG_FOLDER, 0700)

		if(not os.path.exists(self.GMAIL_CONFIG_FOLDER)):
			# .config/gmail-notifier does not exist
			os.mkdir(self.GMAIL_CONFIG_FOLDER, 0700)
		
		if(not os.path.isfile(self.CONFIG_FILE)):
			# .config/gmail-notifier/settings.conf does not exist
			# create one with defaults
			self.settings["username"] = "blah@gmail.com"
			self.settings["check"] = "5"
			self.settings["password"] = "asdf"
			self.saveConfigFile()

	def exit(self, widget):
		print "Closing!"
		gtk.main_quit()

	def save(self, widget):
		username = self.entryUsername.get_text()
		if(username.strip() == ""):
			self.imageUsername.show()
			return
		else:
			self.imageUsername.hide()
			self.settings["username"] = username

		password = self.entryPassword.get_text()
		if(password.strip() == ""):
			self.imagePassword.show()
			return
		else:
			self.imagePassword.hide()
			self.settings["password"] = password

		checktime = self.entryCheckTime.get_text()
		if(checktime.strip() == ""):
			self.imageCheckTime.show()
			return
		else:
			self.imageCheckTime.hide()
			self.settings["check"] = checktime

		# popup dialog saying it's saved
		self.saveConfigFile()
		self.popup.show()

class Keyring:
	def __init__(self, app_name, app_desc1, app_desc2):
		self.keyring = gnomekeyring.get_default_keyring_sync()
		self.app_name = app_name
		self.app_desc1 = app_desc1
		self.app_desc2 = app_desc2

	def getPassword(self):
		auth_token = gconf.client_get_default().get_int("/apps/gnome-python-desktop/keyring_auth_token")
		if auth_token > 0:
			try:
				secret = gnomekeyring.item_get_info_sync(self.keyring, auth_token).get_secret()
			except gnomekeyring.DeniedError:
				password = None
				auth_token = 0
			else:
				password = secret.strip("\n")
		else:
			password = None

		return password

	def setPassword(self, password):
		auth_token = gnomekeyring.item_create_sync(self.keyring, gnomekeyring.ITEM_GENERIC_SECRET, "%s, %s" % (self.app_name, self.app_desc1), dict(appname="%s, %s" % (self.app_name, self.app_desc1)), password, True)
		gconf.client_get_default().set_int("/apps/gnome-python-desktop/keyring_auth_token", auth_token)

if __name__ == "__main__":
	settings = Settings()
	gtk.main()
