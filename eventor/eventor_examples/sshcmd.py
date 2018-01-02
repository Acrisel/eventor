#!/usr/bin/env python3

# adopted from https://gist.github.com/bortzmeyer/1284249

# Here is the right solution today:

import subprocess


def sshcmd(host, command, user=None, check=False):
    ''' Runs ssh command via subprocess.  Assuming .ssh/config is configured.

    Args:
        host: target host to send command to
        command: command to run on host
        user: (optional) user to use to login to host
        check: pass to subprocess.run; if set, checks return code and raises subprocess.CalledProcessError if none-zero result

    Returns:
        subprocess.CompletedProcess object
    '''

    where = "%s" % host if user is None else "%s@%s" %(user, host)
    result = subprocess.run(["ssh", where, command],
                            shell=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=check)
    return result


if __name__ == '__main__':
    out=sshcmd("ubly", "ls -l", check=False).stdout.decode()
    print(out)
