import sys
sys.path.insert(0, '..')

import os
import glob
import unittest

os.chdir(os.path.dirname(__file__))

tests_names = []
for test in glob.glob('Test*.py'):
    if test.endswith('TestAll.py'):
        continue
    tests_names.append(test[:-3])
loader = unittest.defaultTestLoader
suites = loader.loadTestsFromNames(tests_names)
unittest.TextTestRunner(verbosity=2).run(suites)

