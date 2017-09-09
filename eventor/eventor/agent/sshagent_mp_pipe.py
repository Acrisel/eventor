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
from subprocess import PIPE, run
import threading as th
import time

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def stdbin_decode(value, encodeing='ascii'):
    try:
        value = value.decode()
    except:
        pass
    if value.endswith('\n'):
        value = value[:-1]
    return value


class SshAgent(object):
    def __init__(self, host, command, user=None, logger=None):
        self.pipe_read, self.pipe_write = mp.Pipe()
        
        self.__communicateq = mp.Queue()
        self.where = "%s%s" % ('' if user is None else "@%s" % user, host)
        self.command = command
        self.logger = logger
        self.result = None
    
    def start(self, wait=None):
        self.__agent =  mp.Process(target=self.run_agent, args=(self.where, self.command, self.pipe_read, self.pipe_write, self.__communicateq,), daemon=True) 
        try:
            self.__agent.start()
        except Exception:
            raise
        self.pid =self.__agent.pid
        
        self.logger.debug("Agent .start() activated: %s." % self.__agent.pid)
 
        if wait is not None:
            while True:
                time.sleep(wait)
                self.logger.debug("Waiting for start: %s %s" % (self.__agent.is_alive(), self.__agent.exitcode))
                if self.__agent.is_alive() or self.__agent.exitcode is not None:
                    break
           
        self.pipe_read.close()   
        
    def run_agent(self, where, command, pipe_read, pipe_write, communicateq,):
        pipe_write.close()
        pipe_readf = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
        
        cmd = ["ssh", where, command]
        self.logger.debug('Starting subprocess run(%s)' %(cmd))
        sshrun = run(cmd, shell=False, stdin=pipe_readf, stdout=PIPE, stderr=PIPE, check=False,)
        returncode, stdout, stderr = sshrun.returncode, sshrun.stdout.decode(), sshrun.stderr.decode()
        response = (returncode, stdout, stderr) 
        self.logger.debug('Response placed in SSH queue: returncode: %s, stdout: %s, stderr: ' % (repr(returncode), stdout) + '' if not stderr else '\n'+stderr)
        communicateq.put(response)
        pipe_readf.close()
        
    def is_alive(self):
        return self.__agent.is_alive()
        
    def __prepare(self, msg, pack=True):
        workload = msg
        if pack:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        self.logger.debug('Preparing message of size: %s.' % (msgsize,))
        msgsize_packed = struct.pack(">L", msgsize)
        return msgsize_packed + workload
    
    def send(self, msg, pack=True):
        pipe_writef = os.fdopen(os.dup(self.pipe_write.fileno()), 'wb')
        request = self.__prepare(msg, pack=pack)
        self.logger.debug('Writing message of actual size %s to pipe.' % (len(request),))
        pipe_writef.write(request)
        pipe_writef.close()
        
    def response(self, timeout=None):
        self.logger.debug('Getting response from SSH control queue.')
        if self.result is None:
            try:
                result = self.__communicateq.get(timeout=timeout)
            except:
                result=None
                
            if result:
                returncode, stdout, stderr = result[0], stdbin_decode(result[1]), stdbin_decode(result[2])
                if not stdout:
                    stdout = 'TERM'
                self.result = returncode, stdout, stderr
        self.logger.debug('Received from SSH control queue: %s'  % (repr(self.result)))
        return self.result
    
    def close(self, msg='TREM'):
        if self.is_alive():
            self.logger.debug('Sending %s to pipe.' % msg)
            self.send(msg)
        else:
            self.logger.debug('Process is not alive, skipping %s.' % msg)
        response = self.response()
        self.logger.debug('Joining with subprocess.')
        self.__agent.join()
        self.logger.debug('Subprocess joined.')
        return response
    
    def join(self):
        self.__agent.join()


if __name__ == '__main__':
    mp.set_start_method('spawn')
    #mp.freeze_support()
    
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

