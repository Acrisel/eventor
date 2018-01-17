'''
Created on Aug 30, 2017

@author: arnon
'''
import subprocess as sp
import os

heredir = os.path.dirname(os.path.abspath(__file__))
projdir = os.path.dirname(heredir)
prog = os.path.join(projdir, 'eventor', 'bin', 'eventor_agent.py')

cmd = [prog, 'act', '--pipe', '--debug', '--host', 'ubuntud01_eventor', '--ssh-server-host', 'mbp_eventor',
       '--log-info', "datefmt: \'%Y-%m-%d,%H:%M:%S.%f\'\nhandler_kwargs: {atTime: 86400, backupCount: 0, consolidate: false, delay: false,\n  encoding: utf8, file_mode: a, file_prefix: \'\', file_suffix: \'\', interval: 1, key: name,\n  logdir: /Users/arnon/log/eventor, maxBytes: 0, utc: false, when: h}\nhost: localhost\nlevel_formats: !!python/object/new:acrilib.idioms.data_types.MergedChainedDict\n  dictitems: {\'10\': \'[ %(asctime)-15s ][ %(levelname)-7s ][ %(host)s ][ %(processName)-11s\n      ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]\', default: \'[ %(asctime)-15s\n      ][ %(levelname)-7s ][ %(host)s ][ %(processName)-11s ][ %(message)s ]\'}\nlogging_level: 10\nname: runly100.py\nport: 55058\nserver_host: arnon-mbp\n",
       '--file', '/tmp/runly100.py.dat']
# cmd = [prog, 'act', '-h']


proc = sp.run(cmd)
print(proc)
