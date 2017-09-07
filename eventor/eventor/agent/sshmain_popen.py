'''
Created on Aug 27, 2017

@author: arnon
'''

from eventor.agent.sshcmd_popen import sshcmd
import pickle
import os
import struct
import multiprocessing as mp
import sys
import subprocess

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def stdbin_decode(value, encodeing='ascii'):
    value = value.decode()
    if value.endswith('\n'):
        value = value[:-1]
    return value
    
class SshAgent(object):
    def __init__(self, host, agentpy, logger=None):
        try:
            self.remote = sshcmd(host, "python " + agentpy,)
        except Exception as e:
            raise
        self.logger = logger
        self.pid = self.remote.pid

    def poll(self):
        self.remote.poll()
        
    def returncode(self):
        return self.remote.returncode
    
    def communicate(self, *args, **kwargs):
        stdout, stderr = self.remote.communicate(*args, **kwargs)
        return stdbin_decode(stdout), stdbin_decode(stderr)
        
    def wait(self):
        self.remote.wait()
        
    def check(self):
        self.remote.poll()
        if self.remote.returncode is not None:
            self.logger.critical('Agent process terminated: %s' % (host,))
            _, stderr = sshagent.remote.communicate()
            self.logger.exception(stdbin_decode(stderr))
            return False
        else:
            return True
        
    def prepare_msg(self, msg, pickle_msg=True):
        workload = msg
        if pickle_msg:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload
    
    def send(self, msg, pickle_msg=True):
        request = self.prepare_msg(msg, pickle_msg=pickle_msg)
        self.remote.stdin.write(request)
        
    def close(self):
        self.send('TERM')
        response = self.remote.communicate()
        return response
        

if __name__ == '__main__':
    mp.set_start_method('spawn')
    
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_popen_pipe.py")
    host='192.168.1.100'
    #host='172.31.99.104'
    sshagent = SshAgent(host, agentpy)
    
    #worker = RemoteWorker()
    #sshagent.send(worker)
    #sshagent.send(worker)
    
    response = sshagent.close()
    print('response: ', response)
    

