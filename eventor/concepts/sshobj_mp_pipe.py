'''
Created on Aug 27, 2017

@author: arnon
'''

#from concepts.sshcmd_popen import sshcmd
import pickle
import os
import concepts.sshtypes as sshtypes
import struct
import multiprocessing as mp
from subprocess import run, PIPE
import time
import logging

logger = logging.getLogger(__name__)
'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        agent_program=". ~/.profile; if [ -n \"$SSH_ORIGINAL_agent_program\" ]; 
        then eval \"$SSH_ORIGINAL_agent_program\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''


def stdbin_decode(value, encodeing='ascii'):
    try:
        value = value.decode(encodeing)
    except:
        pass
    if value.endswith('\n'):
        value = value[:-1]
    return value

class SshAgent(object):
    def __init__(self, host, agent_program, user=None,):
        self.pipe_read, self.pipe_write = mp.Pipe()
    
        self.__communicateq = mp.Queue()
        self.agent_program = agent_program
        self.where = "{}{}".format('' if user is None else "@{}".format(user), host)            
        self.result = None
        
    def start(self, wait=None):
        self.__agent =  mp.Process(target=self.run_agent, 
            args=(self.where, self.agent_program, self.pipe_read, self.pipe_write, self.__communicateq), 
            daemon=True) 
        try:
            self.__agent.start()
        except Exception:
            raise
    
        if wait is not None:
            while True:
                time.sleep(wait)
                if self.__agent.is_alive() or self.__agent.exitcode is not None:
                    break

        self.pipe_read.close()
    
    def run_agent(self, where, agent_program, pipe_read, pipe_write, communicateq):
        pipe_write.close()
        pipe_readf = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
    
        cmd = ["ssh", where, 'python', agent_program]
        print('running ssh {}'.format(cmd))
        sshrun = run(cmd, shell=False, stdin=pipe_readf, stdout=PIPE, stderr=PIPE, check=False,)
        response = (sshrun.returncode, sshrun.stdout.decode(), sshrun.stderr.decode())
        communicateq.put(response)
        pipe_readf.close()
    
    def __prepare(self, msg, pack=True):
        workload = msg
        if pack:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload

    def is_alive(self):
        return self.__agent.is_alive()

    def send(self, msg, pack=True):
        pipe_writef = os.fdopen(os.dup(self.pipe_write.fileno()), 'wb')
        request = self.__prepare(msg, pack=pack)
        pipe_writef.write(request)
        pipe_writef.close()
    
    def response(self, timeout=None):
        if self.result is None:
            try:
                result = self.__communicateq.get(timeout=timeout)
            except:
                pass
            if result:
                self.result = result[0], result[1], result[2]
        return self.result
    
    def close(self):
        if self.is_alive():
            self.send('TERM')
        response = self.response()
        self.__agent.join()
        return response


if __name__ == '__main__':
    mp.set_start_method('spawn')
    
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_popen.py")
    host='ubuntud01_eventor'
    
    sshagent = SshAgent(host, agentpy)
    sshagent.start(wait=0.2)
    print('Started')
    if not sshagent.is_alive():
        print(sshagent.response())
        exit()
        
    worker = sshtypes.RemoteWorker()
    print('Sending worker')
    sshagent.send(worker)
    
    if not sshagent.is_alive():
        print(sshagent.response())
        exit()

    print('Sending worker')
    sshagent.send(worker)

    print('Closing SSH pipe')
    response = sshagent.close()
    print('response: ', response)

