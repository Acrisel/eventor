'''
Created on Aug 27, 2017

@author: arnon
'''

from eventor.agent.sshcmd import sshcmd
import pickle
import os
from eventor.agent.sshtypes import RemoteWorker
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

def local_agent(host, agentpy, pipein, pipeout, logger_info=None, parentq=None, args=(), kwargs={},):
    ''' Runs agentpy on remote host via ssh overriding stdin as pipein and argument as args.
    '''
    pipeout.close()
    if logger_info is not None:
        logname = logger_info['name']
        logger = MpLogger.get_logger(logger_info, logname)
    else:
        logger = None
    stdin = os.fdopen(os.dup(pipein.fileno()), 'rb')
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
        print(host, remote.stdout)

def local_main(remote_stdin, remote_stdout, load, pack=True, logger=None):
    workload = load
    remote_stdin.close()
    stdout = os.fdopen(os.dup(remote_stdout.fileno()), 'wb')
    if pack:
        workload = pickle.dumps(load)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    stdout.write(magsize_packed)
    stdout.write(workload)


if __name__ == '__main__':
    import multiprocessing as mp
    mp.set_start_method('spawn')
    pipe_read, pipe_write = mp.Pipe(False)
    
    #remote_stdin = os.fdopen(os.dup(pipe_read.fileno()), 'rb')
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/eventor/agent"
    agentpy = os.path.join(agent_dir, "sshagent_pipe.py")
    agent = mp.Process(target=local_agent, args=( '192.168.1.100', agentpy, pipe_read, pipe_write,), daemon=True)
    agent.start()
       
    #remote_stdout = os.fdopen(os.dup(pipe_write.fileno()), 'wb')   
    worker = RemoteWorker()
    local_main(pipe_write, worker)
    
    agent.join()
    
    
    #pid, status = os.waitpid(pid, os.WNOHANG)