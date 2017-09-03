'''
Created on Aug 27, 2017

@author: arnon
'''

from concepts.sshcmd import sshcmd
import pickle
import os
from concepts.sshtypes import RemoteWorker
import struct
 

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def get_pipe():
    pipein, pipeout = os.pipe()
    pipe_reader = os.fdopen(pipein, 'rb')
    pipe_writer = os.fdopen(pipeout, 'wb')
    return pipe_reader, pipe_writer

def remote_agent(host, agentpy, pipein):
    remote = sshcmd(host, "python " + agentpy, stdin=pipein)
    if remote.returncode != 0:
        print(remote.stderr.decode())
        
    return remote.stdout

def local_main(stdout):
    worker = RemoteWorker()
    workload = pickle.dumps(worker)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    stdout.write(magsize_packed)
    stdout.write(workload)


if __name__ == '__main__':

    pipein, pipeout = get_pipe() 
      
    pid = os.fork()   

    if pid == 0:
        # child process
        agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/eventor/concepts"
        agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
        msg = remote_agent( '192.168.1.70', agentpy, pipein)
        print("from remote: %s" % msg.decode(), )
        exit(0)
       
    local_main(pipeout)
    pid, status = os.waitpid(pid, os.WNOHANG)
