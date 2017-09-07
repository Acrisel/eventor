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

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def remote_agent(host, agentpy, qrequest, qresponse):
    try:
        remote = sshcmd(host, "python " + agentpy,)
    except Exception as e:
        raise
    
    while True:
        raw_request = qrequest.get()
        if raw_request == 'Terminate':
            break
        request, wait = raw_request
        timeout = None if not wait else 0
        try:
            response = remote.communicae(input=request, timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        else:
            qresponse.put(response)
    


def send_workload_to_agent(qrequest, qresouse):
    worker = RemoteWorker()
    workload = pickle.dumps(worker)
    msgsize = len(workload)
    magsize_packed = struct.pack(">L", msgsize)
    #stdout.write(magsize_packed)
    qrequest.put((magsize_packed, False))
    qrequest.put((workload, True))
    #stdout.close()
    response = qresouse.get()
    return response


if __name__ == '__main__':
    mp.set_start_method('spawn')
    qrequest = mp.Queue()
    qresouse = mp.Queue()
    
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_popen_pipe.py")
    host='192.168.1.100'
    #host='172.31.99.104'
    remote = mp.Process(target=remote_agent, args=(host, agentpy, qrequest, qresouse), daemon=True)
    remote.start()
      
    response = send_workload_to_agent(qrequest, qresouse)
    print(response)
    qrequest.put('Terminate')
    remote.join()
