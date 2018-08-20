# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2018 Matthias Klumpp <matthias@tenstral.net>
#
# Licensed under the GNU Lesser General Public License Version 3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the license, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import shutil
from contextlib import contextmanager


_unicode_allowed = True  # store whether we are allowed to use unicode
_owner_uid = 0  # uid of the user on whose behalf we are running
_owner_gid = 0  # gid of the user on whose behalf we are running


def set_owning_user(user, group=None):
    '''
    Set the user on whose behalf we are running.
    This is useful so we can drop privileges to
    the perticular user in many cases.
    '''
    from pwd import getpwnam, getpwuid
    from grp import getgrnam

    if user.isdecimal():
        uid = int(user)
    else:
        uid = getpwnam(user).pw_uid

    if not group:
        gid = getpwuid(uid).pw_gid
    elif group.isdecimal():
        gid = int(group)
    else:
        gid = getgrnam(group).gr_gid

    global _owner_uid
    global _owner_gid
    _owner_uid = uid
    _owner_gid = gid


def ensure_root():
    '''
    Ensure we are running as root and all code following
    this function is privileged.
    '''
    if os.geteuid() == 0:
        return

    args = sys.argv.copy()

    owner_set = any(a.startswith('--owner=') for a in sys.argv)
    if owner_set:
        # we don't override an owner explicitly set by the user
        args = sys.argv.copy()
    else:
        args = [sys.argv[0]]

        # set flag to tell the new process who it can impersonate
        # for unprivileged actions. It it is root, just omit the flag.
        uid = os.getuid()
        gid = os.getgid()
        if uid != 0 or gid != 0:
            args.append('--owner={}:{}'.format(uid, gid))
        args.extend(sys.argv[1:])

    if shutil.which('sudo'):
        os.execvp("sudo", ["sudo"] + args)
    else:
        print('This command needs to be run as root.')
        sys.exit(1)


@contextmanager
def switch_unprivileged():
    '''
    Run the next actions as the unprivileged user
    that we are running for.
    '''

    global _owner_uid
    global _owner_gid

    if _owner_uid == 0 and _owner_gid == 0:
        # we can't really do much here, we have to run
        # as root, as we don't know an unprivileged user
        # to switch to

        yield
    else:
        orig_egid = os.getegid()
        orig_euid = os.geteuid()

        try:
            os.setegid(_owner_gid)
            os.seteuid(_owner_uid)

            yield
        finally:
            os.setegid(orig_egid)
            os.seteuid(orig_euid)


def get_owner_uid_gid():
    global _owner_uid
    global _owner_gid

    return _owner_uid, _owner_gid


def colored_output_allowed():
    return (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()) or \
           ('TERM' in os.environ and os.environ['TERM'] == 'ANSI')


def unicode_allowed():
    global _unicode_allowed
    return _unicode_allowed


def set_unicode_allowed(val):
    global _unicode_allowed
    _unicode_allowed = val