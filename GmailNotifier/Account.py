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
import urllib2
import base64
import os
import sys
import time
import calendar
import indicate
import feedparser

from Utils import debug, debug_method

class Account(indicate.Indicator):
    """Account inbox indicator showing in the MessageingMenu.
    
    Warning: Use Account.props to set Account properties and
    Account.{get,set}_property to set Indicator properties.
    See https://bugs.launchpad.net/libindicate/+bug/499490
    """

    __gproperties__ = {
        'email': (
            gobject.TYPE_STRING,
            'Gmail address', '',
            None, # default
            gobject.PARAM_READABLE
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
            gobject.SIGNAL_RUN_LAST, None, (object,)
        ),
        'auth-error': (
            gobject.SIGNAL_RUN_LAST, None, ()
        ),
    }

    def __init__(self, email):
        indicate.Indicator.__init__(self)
        self._email = email
        self.set_property('name', email)
        self.link = 'http://gmail.com'
        self.set_property('subtype', 'mail')
        self._last_check = None
        self._req = None
        self._event_id = None
        self._first_check = True
        self.update_request()

    def do_get_property(self, pspec):
        try:
            return getattr(self, '_'+pspec.name)
        except AttributeError:
            return pspec.default_value

    @debug_method
    def do_set_property(self, pspec, value):
        setattr(self, '_'+pspec.name, value)
        if pspec.name in ('password', 'email'):
            self.update_request()
        if pspec.name == 'interval':
            if self._event_id:
                self.start_check(force=True)

    @debug_method
    def update_request(self):
        auth_string = base64.encodestring('{0}:{1}'.format(self.props.email, self.props.password))[:-1]
        self._req = urllib2.Request('https://mail.google.com/mail/feed/atom/')
        self._req.add_header('Authorization', 'Basic ' + auth_string)

    def start_check(self, force=False):
        if self._event_id:
            if force:
                self.stop_check()
            else:
                return False
        self._event_id = gobject.timeout_add_seconds(self.props.interval*60, self.check_mail)
        return True

    def stop_check(self):
        if self._event_id:
            gobject.source_remove(self._event_id)

    @debug_method
    def check_mail(self):
        """Check for new mail on the account if it is enabled.
        
        If new mail is found a `new-mail` signal is emitted. If an
        authentication error is encountered, the `auth-error` signal is
        emitted.
        """
        if not self.props.enabled:
            debug('Account not enabled')
            return False

        debug('Check for new mail on {0}'.format(self._email))
        atom = None
        try:
            atom = feedparser.parse(urllib2.urlopen(self._req).read())
        except urllib2.HTTPError as e:
            if e.code == 401:
                self.props.enabled = False
                self.hide()
                self.emit('auth-error')
                debug('Auth error')
                return False
        except urllib2.URLError as e:
            # Probably not connect to the internet. Try again later.
            return True

        new_mails = []
        for email in atom['entries']:
            utctime = calendar.timegm(time.strptime(email['issued'], '%Y-%m-%dT%H:%M:%SZ'))
            if not self._last_check or utctime > self._last_check:
                new_mails.append((email['author_detail']['name'], email['title'], email['summary']))
        debug('{0} new mails'.format(len(new_mails)))
        self._last_check = time.time()
        count = atom['feed']['fullcount']
        self.set_property('count', count)
        if len(new_mails) > 0:
            if not self._first_check:
                self.alert()
            else:
                self._first_check = False
            self.show()
            self.emit('new-mail', new_mails)
        elif int(count) > 0:
            self.show()
        else:
            self.hide()

        self.link = atom['feed']['links'][0]['href'] 
        debug('Checking again in {0} minutes'.format(self._interval))
        return True

    def alert(self):
        self.set_property('draw-attention', 'true')

    def lower(self):
        self.set_property('draw-attention', 'false')


