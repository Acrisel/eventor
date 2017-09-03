'''
Created on Aug 27, 2017

@author: arnon
'''

from eventor.agent.sshcmd import sshcmd
import pickle
import os
from eventor.agent.sshtypes import RemoteWorker
import struct
 

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def get_pipe(binary=True):
    pipein, pipeout = os.pipe()
    binary = 'b' if binary else ''
    pipe_reader = os.fdopen(pipein, 'r' + binary)
    pipe_writer = os.fdopen(pipeout, 'w' + binary)
    return pipe_reader, pipe_writer

def remote_agent(host, agentpy, pipein, args=(), kwargs={},):
    ''' Runs agentpy on remote host via ssh overriding stdin as pipein and argument as args.
    '''
    kw = ["%s %s" %(name, value) for name, value in kwargs.items()]
    cmd = "%s %s %s" % (agentpy, " ".join(kw), ' '.join(args))
    remote = sshcmd(host,  cmd, stdin=pipein)
    if remote.returncode != 0:
        print("SSH Failed:", remote.stderr.decode())
        raise Exception(remote.stderr.decode())
        
    return remote.stdout

def local_main(stdout, load, pack=True):
    workload = load
    if pack:
        workload = pickle.dumps(load)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    stdout.write(magsize_packed)
    stdout.write(workload)


if __name__ == '__main__':

    pipein, pipeout = get_pipe() 
      
    pid = os.fork()   

    if pid == 0:
        # child process
        agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/eventor/agent"
        agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
        msg = remote_agent( '192.168.1.100', agentpy, pipein)
        print("from remote: %s" % msg.decode(), )
        exit(0)
       
    worker = RemoteWorker()
    local_main(pipeout, worker)
    pid, status = os.waitpid(pid, os.WNOHANG)
