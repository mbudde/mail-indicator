
import gtk
import gnomekeyring

import Shared
from GmailNotifier.Keyring import Keyring


class TestKeyring(Shared.TestCase):

    def setUp(self):
        self.keyring = Keyring('Gmail Notifier Test', 'Test')
        self.defkeyring = gnomekeyring.get_default_keyring_sync()
        self.auth_token = None

    def test_save_password(self):
        self.auth_token = self.keyring.save_password('test@test.com', 'testpass')
        self.assert_(self.auth_token > 0)

    def test_retrive_password(self):
        self.auth_token = self.keyring.save_password('test@test.com', 'testpass')
        password = self.keyring.get_password(self.auth_token)
        self.assertEqual(password, 'testpass')

    def test_delete_password(self):
        self.auth_token = self.keyring.save_password('test@test.com', 'testpass')
        self.keyring.remove_password(self.auth_token)
        password = self.keyring.get_password(self.auth_token)
        self.assertEqual(password, None)

    def tearDown(self):
        if self.auth_token:
            gnomekeyring.item_delete_sync(self.defkeyring, self.auth_token)


if __name__ == '__main__':
    Shared.main()
