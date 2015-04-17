#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Daemonization function
'''
import os
import sys
import resource
import errno


def daemonize(redirect_to=None, rundir='/', umask=None, maxfd=1024):
    '''Detach a process from the controlling terminal and run it in the background as a daemon.'''
    
    try:
        # Fork a child process so the parent can exit.  This returns control to
        # the command-line or shell.  It also guarantees that the child will not
        # be a process group leader, since the child receives a new process ID
        # and inherits the parent's process group ID.  This step is required
        # to insure that the next call to os.setsid is successful.
        pid = os.fork()
    except OSError, e:
        raise Exception('%s [%d]' % (e.strerror, e.errno))
    
    if pid == 0:  # The first child.
        # To become the session leader of this new session and the process group
        # leader of the new process group, we call os.setsid().  The process is
        # also guaranteed not to have a controlling terminal.
        os.setsid()
        
        try:
            # Fork a second child and exit immediately to prevent zombies.  This
            # causes the second child process to be orphaned, making the init
            # process responsible for its cleanup.  And, since the first child is
            # a session leader without a controlling terminal, it's possible for
            # it to acquire one by opening a terminal in the future (System V-
            # based systems).  This second fork guarantees that the child is no
            # longer a session leader, preventing the daemon from ever acquiring
            # a controlling terminal.
            pid = os.fork()  # Fork a second child.
        except OSError, e:
            raise Exception('%s [%d]' % (e.strerror, e.errno))
    
        if pid == 0:  # The second child.
            # Since the current working directory may be a mounted filesystem, we
            # avoid the issue of not being able to unmount the filesystem at
            # shutdown time by changing it to the root directory.
            os.chdir(rundir)
            # We probably don't want the file mode creation mask inherited from
            # the parent, so we give the child complete control over permissions.
            if umask is not None:
                os.umask(umask)
        else:
            # exit() or _exit()?  See below.
            os._exit(0)  # Exit parent (the first child) of the second child.
    else:
        # exit() or _exit()?
        # _exit is like exit(), but it doesn't call any functions registered
        # with atexit (and on_exit) or any registered signal handlers.  It also
        # closes any open file descriptors.  Using exit() may cause all stdio
        # streams to be flushed twice and any temporary files may be unexpectedly
        # removed.  It's therefore recommended that child branches of a fork()
        # and the parent branch(es) of a daemon use _exit().
        print >>sys.stdout, 'Process daemonized.'
        sys.stdout.flush()
        os._exit(0)  # Exit parent of the first child.
    
    # Close all open file descriptors.  This prevents the child from keeping
    # open any file descriptors inherited from the parent.
    maxfd_to_use = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd_to_use == resource.RLIM_INFINITY:
        maxfd_to_use = maxfd
    
    # Iterate through and close all file descriptors.
    for ofd in range(0, maxfd_to_use):
        try:
            os.close(ofd)
        except OSError, e:  # ERROR, ofd wasn't open to begin with (ignored)
            pass
    
    # Redirect the standard I/O file descriptors to the specified file.  Since
    # the daemon has no controlling terminal, most daemons redirect stdin,
    # stdout, and stderr to /dev/null.  This is done to prevent side-effects
    # from reads and writes to the standard I/O file descriptors.
    
    # This call to open is guaranteed to return the lowest file descriptor,
    # which will be 0 (stdin), since it was closed above.
    try:
        fd = os.open(redirect_to or os.devnull, os.O_CREAT | os.O_RDWR | os.O_APPEND)  # standard input (0)
    except OSError:
        fd = None
    
    # Duplicate standard input to standard output and standard error.
    try:
        os.dup2(0, 1)  # standard output (1)
        if fd:
            sys.stdout = fd
    except OSError, e:
        if e.errno != errno.EBADF:
            raise
    try:
        os.dup2(0, 2)  # standard error (2)
        if fd:
            sys.stderr = fd
    except OSError, e:
        if e.errno != errno.EBADF:
            raise
    
    return 0
