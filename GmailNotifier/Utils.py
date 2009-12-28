

import os
import sys

import info

def get_data_file(filename):
    path = os.path.join(os.path.dirname(__file__), '..', 'data')
    if os.path.exists(path):
        path = os.path.join(path, filename)
        if os.path.exists(path):
            return os.path.abspath(path)
    return None
    
