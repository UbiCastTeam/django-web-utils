"""
Scripts utility functions
"""
import sys
import subprocess


class Colors():
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    TEAL = '\033[96m'
    DEFAULT = '\033[0m'


def log(msg, color=None):
    print('%s%s%s' % (color, msg, Colors.DEFAULT) if color else msg, file=sys.stdout)
    sys.stdout.flush()


def log_err(msg, color=None):
    print('%s%s%s' % (color, msg, Colors.DEFAULT) if color else msg, file=sys.stderr)
    sys.stderr.flush()


def log_info(msg):
    log(msg, Colors.TEAL)


def log_succes(msg):
    log(msg, Colors.GREEN)


def log_warning(msg):
    log(msg, Colors.YELLOW)


def log_error(msg):
    log(msg, Colors.RED)


def run_cmd(cmd):
    shell = not isinstance(cmd, (list, tuple))
    p = subprocess.run(cmd, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr, shell=shell)
    sys.stdout.flush()
    sys.stderr.flush()
    return p.returncode == 0


def get_output(cmd):
    shell = not isinstance(cmd, (list, tuple))
    p = subprocess.run(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr, shell=shell)
    sys.stderr.flush()
    return p.returncode == 0, p.stdout.decode('utf-8') if p.stdout else ''


def create_link(src, dst):
    return run_cmd(['ln', '-sf', src, dst])


def is_different(src, dst):
    p1 = subprocess.Popen(['diff', '-Naur', src, dst], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr)
    p2 = subprocess.Popen(['grep', '--', '---'], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=sys.stderr)
    p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
    p2.communicate()
    sys.stderr.flush()
    return p2.returncode == 0
