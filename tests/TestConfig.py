
import gtk
import gconf

import Shared
from GmailNotifier.Config import Config

GCONF_PATH = '/apps/gmail-notifier-test'

class TestConfig(Shared.TestCase):

    props = (
        ('notifications', True),
        ('notification-mode', 'count'),
        ('run-on-startup', False),
        ('mail-application', 'browser'),
        ('custom-app-name', ''),
        ('custom-app-icon', ''),
        ('custom-app-exec', ''),
        ('custom-app-terminal', False)
    )

    def setUp(self):
        self.conf = Config(GCONF_PATH)
        self.gconf = gconf.client_get_default()

    def test_getters(self):
        for prop, _ in self.props:
            self.assertEqual(self.conf.get_property(prop),
                             getattr(self.conf.props, prop))

    def test_defaults(self):
        for prop, val in self.props:
            self.assertEqual(self.conf.get_property(prop), val)

    def test_get_accounts(self):
        self.assertEqual(self.conf.get_accounts(), [])

    def tearDown(self):
        self.gconf.recursive_unset(GCONF_PATH, 1)
        self.gconf.suggest_sync()

if __name__ == '__main__':
    Shared.main()
