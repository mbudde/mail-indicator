
import Shared
from GmailNotifier.MailApplication import *


class TestMailApp(Shared.TestCase):

    def test_insert_link(self):
        cmd = MailApplication.insert_link('http://test.com', ['foo', '%s', 'bar'])
        self.assertEqual(cmd, ['foo', 'http://test.com', 'bar'])


if __name__ == '__main__':
    Shared.main()
