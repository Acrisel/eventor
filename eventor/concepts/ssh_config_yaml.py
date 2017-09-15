'''
Created on Sep 14, 2017

@author: arnon
'''

import os
import yaml
import re

re_spaces_prefix = re.compile("^\s*")
re_one_space = re.compile("\s+")

def read_ssh_config(config=None):
    config = config if config else "~/.ssh/config"
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
    
if __name__ == '__main__':
    print(read_ssh_config())