
import unittest
import sys
sys.path.insert(0, '..')

class TestCase(unittest.TestCase):
    pass

def main():
    unittest.main(testRunner=unittest.TextTestRunner(verbosity=2))
