#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Daemonization function
'''
import os
import resource
import sys


def daemonize(redirect_to=None, rundir='/', umask=None, close_all_files=False):
    '''Detach a process from the controlling terminal and run it in the background as a daemon.'''
    sys.stdout.flush()
    sys.stderr.flush()

    try:
        # Fork a child process so the parent can exit.  This returns control to
        # the command-line or shell.  It also guarantees that the child will not
        # be a process group leader, since the child receives a new process ID
        # and inherits the parent's process group ID.  This step is required
        # to insure that the next call to os.setsid is successful.
        pid = os.fork()
    except OSError as e:
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
        except OSError as e:
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
        print('Process daemonized.', file=sys.stdout)
        sys.stdout.flush()
        os._exit(0)  # Exit parent of the first child.

    # Close all open file descriptors.  This prevents the child from keeping
    # open any file descriptors inherited from the parent.
    if not close_all_files:
        # If we're not closing all open files, we at least need to
        # reset stdin, stdout, and stderr.
        maxfd_to_use = 3
    else:
        maxfd_to_use = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd_to_use == resource.RLIM_INFINITY:
            # If the limit is infinity, use a more reasonable limit
            maxfd_to_use = 2048
    # close file descriptors.
    os.closerange(0, maxfd_to_use)

    # Redirect the standard I/O file descriptors to the specified file.  Since
    # the daemon has no controlling terminal, most daemons redirect stdin,
    # stdout, and stderr to /dev/null.  This is done to prevent side-effects
    # from reads and writes to the standard I/O file descriptors.

    # This call to open is guaranteed to return the lowest file descriptor,
    # which will be 0 (stdin), since it was closed above.
    os.open(os.devnull, os.O_CREAT | os.O_RDWR)  # standard input (0)
    fd = open(redirect_to or os.devnull, 'a+')  # standard output (1)
    os.dup2(fd.fileno(), 2)  # standard error (2)

    # Change sys.stdout and sys.stderr
    sys.stdout = fd
    sys.stderr = fd

    return 0
