'''
Created on Aug 27, 2017

@author: arnon
'''

from concepts.sshcmd_popen import sshcmd
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

class SshAgent(object):
    def __init__(self, host, agentpy):
        self.pipe_read, self.pipe_write = mp.Pipe()
        stdin = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
        try:
            self.remote = sshcmd(host, "python " + agentpy, stdin=stdin)
        except Exception as e:
            raise

    def prepare_msg(self, msg):
        workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload
    
    def send(self, msg):
        request = self.prepare_msg(msg)
        self.remote.stdin.write(request)
        
    def close(self):
        self.send('Terminate')
        response = self.remote.communicate()
        return response


def remote_agent(host, agentpy, pipe_read, pipe_write):
    pipe_write.close()
    stdin = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
    remote = sshcmd(host, "python " + agentpy, stdin=stdin)
    if remote.returncode != 0:
        print(remote.stderr.decode(), file=sys.stderr)
        return
    print('remote_agent : %s' % (remote.stdout.decode(),))
    stdin.close()

def send_workload_to_agent(pipe_write):
    stdout = os.fdopen(os.dup(pipe_write.fileno()), 'wb')
    worker = RemoteWorker()
    workload = pickle.dumps(worker)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    stdout.write(magsize_packed)
    stdout.write(workload)
    stdout.close()


if __name__ == '__main__':
    mp.set_start_method('spawn')
    pipe_read, pipe_write = mp.Pipe()
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
    host='192.168.1.100'
    #host='172.31.99.104'
    remote = mp.Process(target=remote_agent, args=(host, agentpy, pipe_read, pipe_write), daemon=True)
    remote.start()
      
    pipe_read.close()
    send_workload_to_agent(pipe_write)
    remote.join()
