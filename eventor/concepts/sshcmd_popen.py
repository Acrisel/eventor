#!/usr/bin/env python3

# adopted from https://gist.github.com/bortzmeyer/1284249

# Here is the right solution today:

import subprocess
import sys

def sshcmd(host, command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, user=None, ):
    ''' Runs ssh command via subprocess.  Assuming .ssh/config is configured.
    
    Args:
        host: target host to send command to
        command: command to run on host
        user: (optional) user to use to login to host
        stdin: (optional) override sys.stdin
        
    Returns:
        subprocess.CompletedProcess object
    '''
    
    where = "%s" % host if user is None else "%s@%s" % (user, command)
    
    ssh = subprocess.Popen(["ssh", where, command],
                           shell=False,
                           stdin=stdin,
                           stdout=stdout,
                           stderr=stderr,)
    return ssh
    
if __name__ == '__main__':
    pcomm = sshcmd("acrisel", "ls -l",)
    print(pcomm.communicate('',))