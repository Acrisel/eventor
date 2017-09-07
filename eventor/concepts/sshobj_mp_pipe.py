'''
Created on Aug 27, 2017

@author: arnon
'''

#from concepts.sshcmd_popen import sshcmd
import pickle
import os
from concepts.sshtypes import RemoteWorker
import struct
import multiprocessing as mp
import sys
import subprocess
import threading as th

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

class SshAgent(object):
    def __init__(self, host, command, user=None, logger=None):
        pipe_read, pipe_write = mp.Pipe()
        
        self.__communicateq = mp.Queue()
        where = "%s%s" % ('' if user is None else "@%s" % user, host)
        self.__agent =  mp.Process(target=self.start_agent, args=(where, command, pipe_read, pipe_write, self.__communicateq), daemon=True) 
        try:
            self.__agent.start()
        except Exception as e:
            raise
        print("agent .start() activated: %s." % self.__agent.pid)
        self.logger = logger
        pipe_read.close()
        self.pipe_writef = os.fdopen(os.dup(pipe_write.fileno()), 'wb')
        
    def start_agent(self, where, command, pipe_read, pipe_write, communicateq):
        pipe_write.close()
        pipe_readf = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
        
        sshrun = subprocess.run(["ssh", where, 'python', command],
                                    shell=False, stdin=pipe_readf, 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,)
        
        communicateq.put(sshrun.returncode, sshrun.stdout, sshrun.stderr)
        
    def __prepare(self, msg):
        workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload
    
    def send(self, msg):
        request = self.__prepare(msg)
        self.pipe_writef.write(request)
        
    def close(self):
        self.send('TERM')
        response = self.__communicateq.get()
        self.__agent.join()
        return response

'''
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
'''

if __name__ == '__main__':
    mp.set_start_method('spawn')
    mp.freeze_support()
    
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_popen.py")
    host='192.168.1.100'
    #host='172.31.99.104'
    
    sshagent = SshAgent(host, agentpy)
    
    worker = RemoteWorker()
    print('Sending worker')
    sshagent.send(worker)

    print('Closing SSH pipe')
    response = sshagent.close()
    print('response: ', response)

