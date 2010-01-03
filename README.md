
## Mail Indicator

Mail Indicator checks your webmail for new mails. Mail Indicator is integrated
with [MessagingMenu][MessagingMenu] first introduced in Ubuntu 9.10 Karmic
Koala. Mail Indicator is also integrated with libnotify which means it will
present you with nice notifications when new mails arrive and it save your
password in Gnome Keyring for increased security.

Mail Indicator is based [Gmail Notifier][gmail-notifier] written by Michael
Tom-Wing <mtomwing@gmail.com>.

### Dependencies

 - Python 2.6
 - PyGTK
 - python-feedparser
 - python-gnomekeyring
 - python-indicate
 - python-notify

Note: Package names may differ in your distribution.

### Installation

To install Mail Indicator first configure with:
    ./waf configure
and then with super user privileges run:
    ./waf install
Run `./waf configure --help` to see installation options.

### License

Mail Indicator is distributed under the terms of the GNU General Public License
version 3. See LICENSE for the full license.

[MessagingMenu]: https://wiki.ubuntu.com/MessagingMenu
[gmail-notifier]: http://ahadiel.org/projects/gmail-notifier
