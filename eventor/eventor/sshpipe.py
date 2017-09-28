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
import os
import yaml
import re


module_logger = logging.getLogger(__name__)

'''
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
'''

def stdbin_decode(value, encoding='ascii'):
    try:
        value = value.decode(encoding)
    except:
        pass
    if value.endswith('\n'):
        value = value[:-1]
    return value


class SSHPipe(object):
    ''' Facilitates creation of agent process on remote host using ssh and feeding that 
    process with data to process. 
    '''
    def __init__(self, host, command, user=None, config=None, encoding='ascii', logger=None):
        ''' SSHPipe object runs command on remote host with the intention to pass workloads 
        throughout the lifetime of the run.
        
        Assumptions:
            ssh key configuration among cluster hosts.
                set .profile with: source /var/venv/eventor/bin/activate   
                create environment ssh keys: ssh-keygen -t rsa -C "envname" -f "id_rsa_envname"
                add to authorized_keys proper key:
                    command=". ~/.profile_envname; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
                    then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ...  
        
        Args:
            host: remote host
            command: to run on remote host
            user: user to use to access remote host
            config: SSH configuration to use. ~/.ssh/config 
            encoding: to use in decoding stdout and stderr
            logger: will be used to log information. 
        '''
        
        self.pipe_read, self.pipe_write = mp.Pipe()
        
        self.__communicateq = mp.Queue()
        self.where = "{}{}".format('' if user is None else "@{}".format(user), host)
        self.command = command
        if logger is not None:
            module_logger = logger
        self.result = None
        self.config = config
        self.encoding = encoding
    
    def start(self, wait=None):
        ''' Starts process wherein SSH command will be executed.
        
        Args:
            wait: seconds to sleep between check process status.
        '''
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
        ''' Runs SSH command overriding its stdin and stdout with pipes.
        
        Args:
            where: user@host or host string.
            command: command to run under ssh.
            pipe_read, pipe_write: read and write ends of multiprocessing Pipe().
            communicateq: multiprocessing queue to puss back response.
            
        run_agent is intended to run as a mulitprocessing process.  It uses subprocess run
        to run ssh command on remote host. run_agent overrides subprocess stdin of subprocess with 
        pipe_read.
        
        run_agent collects stdout and stderr and pass them back via communicateq.
        '''
        pipe_write.close()
        
        # convert pipe end to opened file descriptor, so it can be passed to subprocess.
        pipe_readf = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
        
        cmd = ["ssh"]
        if self.config: 
            cmd.append("-F {}".format(self.config))
        cmd.extend([where, command])
        #cmd = ["ssh", where, command]
        module_logger.debug('Starting subprocess run({})'.format(cmd))
        sshrun = run(cmd, shell=False, stdin=pipe_readf, stdout=PIPE, stderr=PIPE, check=False,)
        encoding = self.encoding
        returncode, stdout, stderr = sshrun.returncode, sshrun.stdout.decode(encoding), sshrun.stderr.decode(encoding)
        response = (returncode, stdout, stderr) 
        module_logger.debug('Response placed in SSH queue: returncode: {}, stdout: {}, stderr: '.format(repr(returncode), stdout) + '' if not stderr else '\n'+stderr)
        communicateq.put(response)
        pipe_readf.close()
        
    def is_alive(self):
        ''' Returns True if run_agent process is alive.
        '''
        return self.__agent.is_alive()
        
    def __prepare(self, msg, pack=True):
        ''' Returns byte message prefixed by its length packed into bytes.
        
        Args:
            msg: object to prepate.
            pack: if set, pickle dumps msg.
        '''
        workload = msg
        if pack:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        module_logger.debug('Preparing message of size: %s.' % (msgsize,))
        msgsize_packed = struct.pack(">L", msgsize)
        return msgsize_packed + workload
    
    def send(self, msg, pack=True):
        ''' Writes msg into run_agent pipe (process' stdin)
        
        Args:
            msg: message object
            pack: if set, pickle dumps msg.
        '''
        pipe_writef = os.fdopen(os.dup(self.pipe_write.fileno()), 'wb')
        request = self.__prepare(msg, pack=pack)
        module_logger.debug('Writing message of actual size %s to pipe.' % (len(request),))
        pipe_writef.write(request)
        pipe_writef.close()
        
    def response(self, timeout=None):
        ''' Wait for response from run_agent.
        
        Args:
            timeout: if set, limits wait time.
            
        Returns:
            (returncode, stdout, stderr) resulted by run_agent
        '''
        module_logger.debug('Getting response from SSH control queue.')
        if self.result is None:
            try:
                result = self.__communicateq.get(timeout=timeout)
            except:
                result=None
                
            if result:
                encoding = self.encoding
                returncode, stdout, stderr = result[0], stdbin_decode(result[1], encoding=encoding), stdbin_decode(result[2], encoding=encoding)
                if not stdout:
                    stdout = 'TERM'
                self.result = returncode, stdout, stderr
        module_logger.debug('Received from SSH control queue: %s'  % (repr(self.result)))
        return self.result
    
    def close(self, msg='TREM'):
        ''' Sends termination message to run_agent.
        
        Args:
            msg: termination message, defaults to 'TERM'
            
        Returns:
            same as response()
        '''
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
    
    def join(self, timeout=None):
        ''' Waits for run_agent to finish.
        
        Args:
            timeout: limits time wait as in Process.join()
        '''
        self.__agent.join(timeout)



