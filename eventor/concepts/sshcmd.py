#!/usr/bin/env python3

# adopted from https://gist.github.com/bortzmeyer/1284249

# Here is the right solution today:

import subprocess
import sys

def sshcmd(host, command, stdin=None, stdout=None, user=None, check=False):
    ''' Runs ssh command via subprocess.  Assuming .ssh/config is configured.
    
    Args:
        host: target host to send command to
        command: command to run on host
        user: (optional) user to use to login to host
        stdin: (optional) override sys.stdin
        check: pass to subprocess.run; if set, checks return code and raises subprocess.CalledProcessError if none-zero result
        
    Returns:
        subprocess.CompletedProcess object
    '''
    
    where = "%s" % host if user is None else "%s@%s" % (user, command)
    if stdout is None:
        stdout = subprocess.PIPE
    
    ssh = subprocess.run(["ssh", where, command],
                           shell=False,
                           stdin=stdin,
                           stdout=stdout,
                           stderr=subprocess.PIPE,
                           check=check)
    return ssh
    
if __name__ == '__main__':
    print(sshcmd("192.168.56.10", "eventor_agent.py -h", check=False).stdout)