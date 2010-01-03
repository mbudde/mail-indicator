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
import inspect
from functools import wraps

"""Is debugging enabled?"""
DEBUGGING = False
    
def debug(str):
    global DEBUGGING
    if not DEBUGGING: return
    s = inspect.stack()[1]
    print '{file}:{line}:{func}: {msg}'.format(
        file=os.path.basename(s[1]),
        line=s[2],
        func=s[3],
        msg=str)

def debugfun(fun):
    global DEBUGGING
    if not DEBUGGING: return fun
    @wraps(fun)
    def wrapper(*args, **kwargs):
        res = fun(*args, **kwargs)
        print('{0} ( {1} {2} ) -> {3}'.format(fun.__name__, args, kwargs, res))
        return res
    return wrapper

def debugmethod(fun):
    @wraps(fun)
    def wrapper(klass, *args, **kwargs):
        info = {
            'file': os.path.basename(inspect.stack()[1][1])[:-3],
            'cls': klass.__class__.__name__,
            'fun': fun.__name__,
            'args': args,
            'kwargs': kwargs
        }
        print('{file}.{cls}.{fun} <-- {args} {kwargs}'.format(**info))
        info.update({'res': fun(klass, *args, **kwargs)})
        print('{file}.{cls}.{fun} --> {res}'.format(**info))
        return info['res']
    return wrapper
