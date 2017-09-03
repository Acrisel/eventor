'''
Created on Aug 27, 2017

@author: arnon
'''

from concepts.sshcmd import sshcmd
import pickle
import os
from concepts.sshtypes import RemoteWorker
 

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def remote_agent(pipe_name, host, agentpy):
    pipein = open(pipe_name, 'rb')
    remote = sshcmd(host, "python " + agentpy, stdin=pipein)

    if remote.returncode != 0:
        raise Exception(remote.stderr.decode())
    return remote.stdout

def local_main(pipe_name):
    pipeout = open(pipe_name, 'wb')
    worker = RemoteWorker()
    workload = pickle.dumps(worker)
    pipeout.write(workload)

if __name__ == '__main__':
    #mp.freeze_support()
    #mp.set_start_method('spawn')

    pipe_name = 'ssh_pipe'
    
    if not os.path.exists(pipe_name):
        # creating namedpipe
        os.mkfifo(pipe_name)
          
    pid = os.fork()    
    if pid == 0:
        # child process
        agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/eventor/concepts"
        agentpy = os.path.join(agent_dir, "sshagent_namedpipe.py")
        msg = remote_agent(pipe_name, '192.168.1.70', agentpy)
        print(msg.decode(), "from remote.")
        exit(0)
        
    local_main(pipe_name)
    pid, status = os.waitpid(pid, 0)