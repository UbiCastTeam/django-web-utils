"""
System utility functions
"""
import os
import sys
import errno
import datetime
import random
import pwd
import grp
import subprocess
from pathlib import Path

try:
    from django.utils.translation import gettext as _
except ImportError:
    def _(text):
        return text


# get_unix_user function
# ----------------------------------------------------------------------------
def get_unix_user():
    uid = os.getuid()
    if uid == 0:
        return 'root'
    return pwd.getpwuid(uid).pw_name


# run_as function
# ----------------------------------------------------------------------------
def run_as(username, umask=0o22, exit_on_error=True):
    """
    Drop privileges to given user, and set up environment.
    Assumes the parent process has root privileges.
    """
    if get_unix_user() == username:
        return

    try:
        pwent = pwd.getpwnam(username)
    except KeyError as e:
        if exit_on_error:
            print(e, file=sys.stderr)
            sys.exit(1)
        else:
            raise

    os.umask(umask)
    home = pwent.pw_dir
    try:
        os.chdir(home)
    except OSError:
        os.chdir('/')

    groups = list()
    for group in grp.getgrall():
        if username in group.gr_mem:
            groups.append(group.gr_gid)

    # drop privs to user
    os.setgroups(groups)
    os.setgid(pwent.pw_gid)
    os.setegid(pwent.pw_gid)
    os.setuid(pwent.pw_uid)
    os.seteuid(pwent.pw_uid)
    os.environ['HOME'] = home
    os.environ['USER'] = pwent.pw_name
    os.environ['LOGNAME'] = pwent.pw_name
    os.environ['SHELL'] = pwent.pw_shell
    # os.environ['PATH'] = '/bin:/usr/bin:/usr/local/bin'
    return


# execute_command function
# ----------------------------------------------------------------------------
def execute_command(cmd, user='self', pwd=None, request=None, is_root=False):
    cmd = cmd.replace('"', '\\"')
    if user == 'self':
        cmd_prompt = '/bin/bash -c "%s"'
        need_password = False
    elif user == 'root':
        cmd_prompt = 'sudo%s /bin/bash -c "%%s"' % ('' if is_root else ' -kS')
        need_password = False if is_root else True
    else:
        cmd_prompt = 'sudo%s su %s -c "%%s"' % ('' if is_root else ' -kS', user)
        need_password = False if is_root else True

    command = cmd_prompt % cmd
    p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if need_password:
        if not pwd and (not request or not request.session.get('pwd')):
            return False, str(_('Password required.'))
        out, err = p.communicate(input=bytes('%s\n' % (pwd if pwd else request.session['pwd']), 'utf-8'))
    else:
        out, err = p.communicate()
    out = out.decode('utf-8') if out else ''
    if p.returncode != 0:
        if err:
            err = err.decode('utf-8')
        else:
            err = str(_('Command exited with code %s.' % p.returncode))
        if out:
            return False, '%s\n---- stderr ----\n%s' % (out, err)
        return False, err
    if out:
        return True, out
    return True, ''


# is_pid_running
# ----------------------------------------------------------------------------
def is_pid_running(pid_file_path, user='self', request=None):
    success, output = execute_command(f'cat "{pid_file_path}"', user=user, request=request)
    if success:
        cmd = f'ps -p {output.strip()}'
        success, output = execute_command(cmd, user=user, request=request)
    return success


# is_process_running
# ----------------------------------------------------------------------------
def is_process_running(process_name, user='self', request=None):
    cmd = f"ps ax | grep '{process_name}' | grep -v 'grep' > /dev/null 2>&1"
    success, output = execute_command(cmd, user=user, request=request)
    return success


# write_file_as
# ----------------------------------------------------------------------------
def write_file_as(request, content, file_path, user='self'):
    file_path = Path(file_path)
    if file_path.is_dir():
        return False, '%s %s' % (_('Unable to write file.'), _('Specified path is a directory.'))
    path_str = str(file_path)
    if '"' in path_str or '\'' in path_str or '$' in path_str:
        return False, '%s %s' % (_('Unable to write file.'), _('Invalid file path.'))
    try:
        # try to write file like usual
        file_path.write_text(content)
    except OSError as err:
        if err.errno != errno.EACCES:
            return False, '%s %s' % (_('Unable to write file.'), err)
        # write file as given user
        #   to write as given user we first write the content in a temporary file then we
        #   transfer the content to the destination file. This method is used to avoid
        #   problems with special characters.
        if 'pwd' not in request.session:
            return False, _('You need to send the main password to edit this file.')
        # write tmp file
        rd_chars = ''.join([random.choice('0123456789abcdef') for i in range(10)])
        date_dump = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
        tmp_path = Path(f'/tmp/djwutils-tmp_{date_dump}_{rd_chars}')
        try:
            tmp_path.write_text(content)
        except OSError as err:
            return False, '%s %s' % (_('Unable to create temporary file "%s".') % tmp_path, err)
        # transfer content in final file without altering file permissions
        cmd = f"cat '{tmp_path}' > '{file_path}'"
        success, output = execute_command(cmd, user=user, request=request)
        tmp_path.unlink(missing_ok=True)
        if not success:
            return False, '%s %s' % (_('Unable to write file.'), output)
    return True, _('File updated.')
