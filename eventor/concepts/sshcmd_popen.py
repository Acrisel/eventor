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
    
    ssh = subprocess.Popen(["ssh", where, command],
                           shell=False,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,)
    return ssh
    
if __name__ == '__main__':
    pcomm = sshcmd("acrisel", "ls -l",)
    print(pcomm.communicate('',))