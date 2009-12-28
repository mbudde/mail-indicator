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
    
def debug(str):
    print str

def debug_fun(fun):
    def dbg_fun(*args, **kwargs):
        res = fun(*args, **kwargs)
        print '%s ( %s %s ) -> %s' % (fun.__name__, args, kwargs, res)
        return res
    return dbg_fun

def debug_method(fun):
    def dbg_fun(klass, *args, **kwargs):
        print '%s.%s ( %s %s )' % (klass.__class__, fun.__name__, args, kwargs)
        res = fun(klass, *args, **kwargs)
        print '%s.%s -> %s' % (klass.__class__, fun.__name__, res)
        return res
    return dbg_fun
