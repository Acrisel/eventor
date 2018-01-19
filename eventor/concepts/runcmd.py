'''
Created on Aug 30, 2017

@author: arnon
'''
import subprocess as sp
import os


def cmdargs(namespace=None):
    import argparse
    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]

    parser = argparse.ArgumentParser(prog=progname, description="runs EventorAgent object.")
    parser.add_argument('--file', type=str, help="args data file.")
    args = parser.parse_args(namespace=namespace)
    return args


def runcmd(file):
    heredir = os.path.dirname(os.path.abspath(__file__))
    projdir = os.path.dirname(heredir)
    prog = os.path.join(projdir, 'eventor', 'bin', 'eventor_agent.py')

    cmd = [prog, 'rec', '--file', file]

    proc = sp.run(cmd)
    print(proc)


if __name__ == '__main__':
    args = cmdargs()
    runcmd(file=args.file)

