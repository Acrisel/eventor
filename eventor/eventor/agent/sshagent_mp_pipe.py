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
    def __init__(self, host, command, user=None, logger=None):
        self.pipe_read, self.pipe_write = mp.Pipe()
        
        self.__communicateq = mp.Queue()
        where = "%s%s" % ('' if user is None else "@%s" % user, host)
        self.logger = logger
        if logger:
            self.__debug = self.logger.debug
            self.__critical = self.logger.critical
            self.__excetion = self.logger.exception
        else:
            self.__debug = print
            self.__critical = print
            self.__excetion = print

        self.__agent =  mp.Process(target=self.start_agent, args=(where, command, self.pipe_read, self.pipe_write, self.__communicateq), daemon=True) 
        try:
            self.__agent.start()
        except Exception:
            raise
        self.pid =self.__agent.pid
        
        self.__debug("agent .start() activated: %s." % self.__agent.pid)
            
        self.pipe_read.close()   
        
    def start_agent(self, where, command, pipe_read, pipe_write, communicateq):
        pipe_write.close()
        pipe_readf = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
        
        cmd = ["ssh", where, 'python', command]
        self.__debug('Starting subprocess run(%s)' %(cmd))
        sshrun = run(cmd, shell=False, stdin=pipe_readf, stdout=PIPE, stderr=PIPE, check=False,)
        self.__debug('subprocess.run() started.')
        response = (sshrun.returncode, sshrun.stdout.decode(), sshrun.stderr.decode())
        communicateq.put(response)
        self.__debug('Response placed in queue: %s' % (repr(response),))
        pipe_readf.close()
        
    def is_alive(self):
        return self.__agent.is_alive()
        
    def __prepare(self, msg, pack=True):
        workload = msg
        if pack:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload
    
    def send(self, msg, pack=True):
        pipe_writef = os.fdopen(os.dup(self.pipe_write.fileno()), 'wb')
        request = self.__prepare(msg, pack=pack)
        pipe_writef.write(request)
        pipe_writef.close()
        
    def response(self, timeout=-1):
        result = self.__communicateq.get(timeout=timeout)
        return result[0], stdbin_decode(result[1]), stdbin_decode(result[2])
    
    def close(self):
        self.send('TERM')
        response = self.response()
        self.__agent.join()
        return response
    
    def wait(self):
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

