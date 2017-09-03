'''
Created on Aug 27, 2017

@author: arnon
'''

from concepts.sshcmd import sshcmd
import pickle
import os
from concepts.sshtypes import RemoteWorker
import struct
import multiprocessing as mp
import sys

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

def get_mp_pipe():
    pipein, pipeout = mp.Pipe()
    return pipein, pipeout

def remote_agent(host, agentpy, pipein, pipeout):
    print('in remote_agent', file=sys.stderr)
    pipeout.close()
    stdin = os.fdopen(pipein.fileno(), 'rb')
    print('in remote_agent', file=sys.stderr)
    remote = sshcmd(host, "python " + agentpy, stdin=stdin)
    if remote.returncode != 0:
        print(remote.stderr.decode())
    print('in remote_agent 99', file=sys.stderr)
    return remote.stdout

def local_main(pipein, pipeout):
    print('in local_main 0', file=sys.stderr)
    pipein.close()
    print('in local_main 1', file=sys.stderr)
    stdout = os.fdopen(pipeout.fileno(), 'wb')
    print('in local_main 2', file=sys.stderr)
    worker = RemoteWorker()
    workload = pickle.dumps(worker)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    stdout.write(magsize_packed)
    stdout.write(workload)
    
    print('in local_main 99', file=sys.stderr)


if __name__ == '__main__':

    pipein, pipeout = get_mp_pipe() 
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
    host='192.168.1.100'
    remote = mp.Process(target=remote_agent, args=(host, agentpy, pipein, pipeout))
    remote.start()
      
    '''
    pid = os.fork()   

    if pid == 0:
        # child process
        agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
        agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
        msg = remote_agent( host, agentpy, pipein)
        print("from remote: %s" % msg.decode(), )
        exit(0)
     '''  
    local_main(pipein, pipeout)
    #pid, status = os.waitpid(pid, os.WNOHANG)
    remote.join()
    #pipein.close()
    #pipeout.close()
