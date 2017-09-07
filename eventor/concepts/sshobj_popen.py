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
import subprocess
import fcntl

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


class SSHAGENTERROR(Exception): pass


class SshAgent(subprocess.Popen):
    def __init__(self, host, command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, user=None, logger=None):
        where = "%s%s" % ('' if user is None else "@%s" % user, host)
        #command = "ssh %s python %s" % (where, command)
        super().__init__(["ssh", where, 'python', command],
                           shell=False,
                           stdin=stdin,
                           stdout=stdout,
                           stderr=stderr,
                           close_fds=True,)
        self.logger = logger
        
        # set stderr as none blocking
        fl = fcntl.fcntl(self.stderr, fcntl.F_GETFL)
        fcntl.fcntl(self.stderr, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
    def check(self):
        ''' returns None is still running, else (stdout, stderr)
        '''
        self.poll()
        stderr_data = self.stderr.read()
        if stderr_data:
            if self.returncode is not None:
                if self.logger is not None:
                    self.logger.critical('Agent process terminated: %s' % (host, stderr_data))
            stdout_data = self.stdout.read()
            return self.returncode, stdout_data, stderr_data
        return None
        
    def prepare(self, msg, pickle_msg=True):
        workload = msg
        if pickle_msg:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload
    
    def send(self, msg, pickle_msg=True):
        request = self.prepare(msg, pickle_msg=pickle_msg)
        self.stdin.write(request)
        
    def close(self):
        self.send('TERM', pickle_msg=True)
        #self.wait()
        response = self.communicate()
        return self.returncode, response[0], response[1]
         

if __name__ == '__main__':
    mp.set_start_method('spawn')
    import signal
    
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_popene.py")
    host='192.168.1.100'
    #host='172.31.99.104'
    sshagent = SshAgent(host, agentpy)
    
    result = sshagent.check()
    if result is not None: 
        print("Dead 1:", result)
        exit()
    
    worker = RemoteWorker()
    sshagent.send(worker)
    
    #sshagent.send_signal(signal.SIGTERM)

    result = sshagent.check()
    if result is not None: 
        print("Dead 2:", result)
        exit()

    sshagent.send(worker)
    
    response = sshagent.close()
    print('response: ', response)
    

