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

class SshBiPipeError(Exception): pass

class SshBiPipe(object):
    def __init__(self, host, agentpy, to_binary=False, from_binary=False, import_msg_module=None):
        self.to_binary = to_binary
        self.from_binary = from_binary
        self.host = host
        self.agentpy = agentpy
        self.import_msg_module = import_msg_module
        
    def initiate_agent(self,):
        pipein, pipeout = os.pipe()
        b = 'b' if self.to_binary else ''
        self.to_pipe_reader = os.fdopen(pipein, 'r'+b)
        self.to_pipe_writer = os.fdopen(pipeout, 'w'+b)
        
        pipein, pipeout = os.pipe()
        b = 'b' if self.from_binary else ''
        self.from_pipe_reader = os.fdopen(pipein, 'r'+b)
        self.from_pipe_writer = os.fdopen(pipeout, 'w'+b)

        self.remote = sshcmd(self.host, "python " + self.agentpy, stdin=self.to_pipe_reader, stdout=self.from_pipe_writer)
        if self.remote.returncode != 0:
            print(self.remote.stderr.decode())
        
    def write_to_remote(self, msg):
        if self.to_pipe_reader is None:
            raise SshBiPipeError("initiate_agent must be called before writing to remote")
        #workload = pickle.dumps(msg)
        msgsize = len(msg)
        magsize_packed = struct.pack(">L", msgsize)
        self.to_pipe_writer.write(magsize_packed)
        self.to_pipe_writer.write(msg)
        
    def read_from_remote(self):
        if self.to_pipe_reader is None:
            raise SshBiPipeError("initiate_agent must be called before reading from remote")
        if self.import_msg_module is not None:
            from importlib import import_module
            import_module(self.import_msg_module)

        msgsize_raw = self.from_pipe_reader.buffer.read(4)
        msgsize = struct.unpack(">L", msgsize_raw)
        workload = self.from_pipe_reader.buffer.read(msgsize[0])
        msg = pickle.loads(workload)
        return msg
    
    @classmethod
    def remote_write_msg(cls):
        pass
        
        
def local_main(stdout):
    worker = RemoteWorker()
    workload = pickle.dumps(worker)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    stdout.write(magsize_packed)
    stdout.write(workload)


if __name__ == '__main__':

    pass
    '''
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
    '''