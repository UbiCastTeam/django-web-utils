"""
Daemonization function
"""
import os
import resource
import sys


def daemonize(redirect_to=None, rundir='/', umask=0o022, close_all_files=False):
    """
    Detach a process from the controlling terminal and run it in the background as a daemon.
    """
    sys.stdout.flush()
    sys.stderr.flush()

    try:
        # Fork a child process so the parent can exit. This returns control to the command-line or shell.
        # It also guarantees that the child will not be a process group leader, since the child receives
        # a new process ID and inherits the parent's process group ID. This step is required to insure
        # that the next call to os.setsid is successful.
        pid = os.fork()
    except OSError as err:
        raise RuntimeError('%s [%d]' % (err.strerror, err.errno)) from err

    if pid == 0:  # The first child.
        # To become the session leader of this new session and the process group leader of the new process
        # group, we call os.setsid(). The process is also guaranteed not to have a controlling terminal.
        os.setsid()

        try:
            # Fork a second child and exit immediately to prevent zombies. This causes the second child
            # process to be orphaned, making the init process responsible for its cleanup. And, since the
            # first child is a session leader without a controlling terminal, it's possible for it to
            # acquire one by opening a terminal in the future (System V- based systems). This second fork
            # guarantees that the child is no longer a session leader, preventing the daemon from ever
            # acquiring a controlling terminal.
            pid = os.fork()  # Fork a second child.
        except OSError as err:
            raise RuntimeError('%s [%d]' % (err.strerror, err.errno)) from err

        if pid == 0:  # The second child.
            # Since the current working directory may be a mounted filesystem, we avoid the issue of not
            # being able to unmount the filesystem at shutdown time by changing it to the root directory.
            os.chdir(rundir)
            # We probably don't want the file mode creation mask inherited from the parent, so we give the
            # child complete control over permissions.
            if umask is not None:
                os.umask(umask)
        else:
            # exit() or _exit()?  See below.
            os._exit(0)  # Exit parent (the first child) of the second child.
    else:
        # exit() or _exit()?
        # _exit is like exit(), but it doesn't call any functions registered with atexit (and on_exit) or
        # any registered signal handlers. It also closes any open file descriptors. Using exit() may cause
        # all stdio streams to be flushed twice and any temporary files may be unexpectedly removed. It's
        # therefore recommended that child branches of a fork() and the parent branch(es) of a daemon
        # use _exit().
        print('Process daemonized.', file=sys.stdout)
        sys.stdout.flush()
        os._exit(0)  # Exit parent of the first child.

    # Close all open file descriptors.
    # This prevents the child from keeping open any file descriptors inherited from the parent.
    # WARNING: This causes problems in Python 3, especially when using os.exec
    if close_all_files:
        maxfd_to_use = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd_to_use == resource.RLIM_INFINITY:
            # If the limit is infinity, use a more reasonable limit
            maxfd_to_use = 2048
        # close file descriptors.
        os.closerange(0, maxfd_to_use)

    # Redirect the standard I/O file descriptors to the specified file. Since the daemon has no controlling
    # terminal, most daemons redirect stdin, stdout, and stderr to /dev/null. This is done to prevent
    # side-effects from reads and writes to the standard I/O file descriptors.
    fdi = os.open(os.devnull, os.O_CREAT | os.O_RDONLY)
    fdo = os.open(redirect_to or os.devnull, os.O_CREAT | os.O_WRONLY | os.O_APPEND, mode=0o666)
    os.dup2(fdi, 0)
    os.dup2(fdo, 1)
    os.dup2(fdo, 2)
    os.close(fdi)
    os.close(fdo)
    # Reassign sys attributes
    sys.stdin = os.fdopen(0, 'r')
    sys.stdout = os.fdopen(1, 'a+')
    sys.stderr = sys.stdout

    return 0
