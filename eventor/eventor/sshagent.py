'''
Created on Aug 27, 2017

@author: arnon
'''

#from concepts.sshcmd_popen import sshcmd
import pickle
import struct
import multiprocessing as mp
from subprocess import PIPE, run
import time

import logging

module_logger = logging.getLogger(__name__)
'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

import os
import yaml
import re

re_spaces_prefix = re.compile("^\s*")
re_one_space = re.compile("\s+")

def read_ssh_config(config):
    config = os.path.expanduser(config)
    with open(config, 'r') as config_stream:
        config_lines = config_stream.read()
    
    config_data = list()
    for line in config_lines.split('\n'):
        space_prefix = re_spaces_prefix.search(line)
        space_prefix = space_prefix.group(0)
        if space_prefix == line: 
            continue
        if line.startswith('Host'):
            host = re_one_space.sub(" ", line,).partition(" ")[2]
            if host.startswith('*'):
                host = 'default'
            config_data.append("{}:".format(host))
            continue
        line = line[len(space_prefix):].partition(" ")
        config_data.append("    {}: {}".format(line[0], line[2]))
        
    config_data = '\n'.join(config_data)
    
    config_map = yaml.load(config_data)
    config_stream.close()
    return config_map


def stdbin_decode(value, encodeing='ascii'):
    try:
        value = value.decode()
    except:
        pass
    if value.endswith('\n'):
        value = value[:-1]
    return value


class SshAgent(object):
    def __init__(self, host, command, user=None, config=None, logger=None):
        
        self.pipe_read, self.pipe_write = mp.Pipe()
        
        self.__communicateq = mp.Queue()
        self.where = "{}{}".format('' if user is None else "@{}".format(user), host)
        self.command = command
        if logger is not None:
            module_logger = logger
        self.result = None
        self.config = config
    
    def start(self, wait=None):
        self.__agent =  mp.Process(target=self.run_agent, args=(self.where, self.command, self.pipe_read, self.pipe_write, self.__communicateq,), daemon=True) 
        try:
            self.__agent.start()
        except Exception:
            raise
        self.pid =self.__agent.pid
        
        module_logger.debug("Agent .start() activated: {}.".format(self.__agent.pid))
 
        if wait is not None:
            while True:
                time.sleep(wait)
                module_logger.debug("Waiting for start: {} {}".format(self.__agent.is_alive(), self.__agent.exitcode))
                if self.__agent.is_alive() or self.__agent.exitcode is not None:
                    break
           
        self.pipe_read.close()   
        
    def run_agent(self, where, command, pipe_read, pipe_write, communicateq,):
        pipe_write.close()
        pipe_readf = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
        
        cmd = ["ssh"]
        if self.config: 
            cmd.append("-F {}".format(self.config))
        cmd.extend([where, command])
        #cmd = ["ssh", where, command]
        module_logger.debug('Starting subprocess run({})'.format(cmd))
        sshrun = run(cmd, shell=False, stdin=pipe_readf, stdout=PIPE, stderr=PIPE, check=False,)
        returncode, stdout, stderr = sshrun.returncode, sshrun.stdout.decode(), sshrun.stderr.decode()
        response = (returncode, stdout, stderr) 
        module_logger.debug('Response placed in SSH queue: returncode: {}, stdout: {}, stderr: '.format(repr(returncode), stdout) + '' if not stderr else '\n'+stderr)
        communicateq.put(response)
        pipe_readf.close()
        
    def is_alive(self):
        return self.__agent.is_alive()
        
    def __prepare(self, msg, pack=True):
        workload = msg
        if pack:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        module_logger.debug('Preparing message of size: %s.' % (msgsize,))
        msgsize_packed = struct.pack(">L", msgsize)
        return msgsize_packed + workload
    
    def send(self, msg, pack=True):
        pipe_writef = os.fdopen(os.dup(self.pipe_write.fileno()), 'wb')
        request = self.__prepare(msg, pack=pack)
        module_logger.debug('Writing message of actual size %s to pipe.' % (len(request),))
        pipe_writef.write(request)
        pipe_writef.close()
        
    def response(self, timeout=None):
        module_logger.debug('Getting response from SSH control queue.')
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
        module_logger.debug('Received from SSH control queue: %s'  % (repr(self.result)))
        return self.result
    
    def close(self, msg='TREM'):
        if self.is_alive():
            module_logger.debug('Sending %s to pipe.' % msg)
            self.send(msg)
        else:
            module_logger.debug('Process is not alive, skipping %s.' % msg)
            pass
        response = self.response()
        module_logger.debug('Joining with subprocess.')
        self.__agent.join()
        module_logger.debug('Subprocess joined.')
        return response
    
    def join(self):
        self.__agent.join()


