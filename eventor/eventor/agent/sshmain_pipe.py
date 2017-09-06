'''
Created on Aug 27, 2017

@author: arnon
'''

from eventor.agent.sshcmd import sshcmd
import pickle
import os
import struct
from acrilog import MpLogger

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def local_agent(host, agentpy, pipe_read, pipe_write, logger_info=None, parentq=None, args=(), kwargs={},):
    ''' Runs agentpy on remote host via ssh overriding stdin as pipein and argument as args.
    '''
    pipe_write.close()
    if logger_info is not None:
        logname = logger_info['name']
        logger = MpLogger.get_logger(logger_info, logname)
    else:
        logger = None
    stdin = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
    kw = ["%s %s" %(name, value) for name, value in kwargs.items()]
    cmd = "%s %s %s" % (agentpy, " ".join(kw), ' '.join(args))
    if logger:
        logger.debug("Starting SSH remote agent %s: command: %s" % (host, cmd))
    remote = sshcmd(host,  cmd, stdin=stdin)
    if remote.returncode != 0:
        if logger:
            logger.critical("SSH Failed: %s" % remote.stderr.decode())
        else:
            print("SSH Failed: %s" % remote.stderr.decode())
        if parentq is not None:
            parentq.put((host, 'TERM'))
       
    if logger:
        logger.debug("Remote agent exiting: stdout: %s" % (remote.stdout.decode(),))
        
    if parentq is not None:
        parentq.put((host, remote.stdout.decode()))
    else:
        print(host, remote.stdout.decode())

def send_to_agent(pipe_write, load, pack=True, logger=None):
    workload = load
    
    pipe_stdin = os.fdopen(os.dup(pipe_write.fileno()), 'wb')
    if pack:
        if logger:
            logger.debug("Pickle dumping workload.")
        workload = pickle.dumps(load)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    if logger:
        logger.debug("Sending message length: %s." % msgsize)
    pipe_stdin.write(magsize_packed)
    if logger:
        logger.debug("Sending messages.")
    pipe_stdin.write(workload)
    if logger:
        logger.debug("Message sent to agent.")


def start_agent(host, workload, pack=True):
    pipe_read, pipe_write = mp.Pipe(False)
    
    #pipe_stdin = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/eventor/agent"
    agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
    agent = mp.Process(target=local_agent, args=( host, agentpy, pipe_read, pipe_write,), daemon=True)
    agent.start()
       
    if pack:
        workload = pickle.dumps(workload)
    
    pipe_read.close()
    #pipe_stdin = os.fdopen(os.dup(pipe_write.fileno()), 'wb')
    send_to_agent(pipe_write, workload)
    
    return agent


if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    
    from eventor.agent.sshtypes import RemoteWorker
    agent = start_agent('192.168.1.100', RemoteWorker(), pack=False)
        
    agent.join()
    
    
    #pid, status = os.waitpid(pid, os.WNOHANG)
