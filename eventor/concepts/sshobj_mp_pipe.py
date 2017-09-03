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
    pipeout.close()
    pipe_reader = os.fdopen(pipein.fileno(), 'rb')
    remote = sshcmd(host, "python " + agentpy, stdin=pipe_reader)
    if remote.returncode != 0:
        print(remote.stderr.decode())
        
    return remote.stdout

def local_main(pipein, pipeout):
    pipein.close()
    stdout = os.fdopen(pipeout.fileno(), 'wb')
    worker = RemoteWorker()
    workload = pickle.dumps(worker)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    stdout.write(magsize_packed)
    stdout.write(workload)


if __name__ == '__main__':

    pipein, pipeout = get_mp_pipe() 
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
    host='192.168.1.100'
    remote = mp.Process(target=remote_agent, args=(host, agentpy, pipein, pipeout))
    remote.start()
      
    '''
    pid = os.fork()   

    if pid == 0:
        # child process
        agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/eventor/concepts"
        agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
        msg = remote_agent( host, agentpy, pipein)
        print("from remote: %s" % msg.decode(), )
        exit(0)
     '''  
    local_main(pipein, pipeout)
    #pid, status = os.waitpid(pid, os.WNOHANG)
    remote.join()
