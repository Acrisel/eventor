=============================
Development Environment Notes
=============================


On Ubuntu Virtualbox install postgresql and pgAdmin or phpAdmin.

    sudo apt-get -y install postgresql postgresql-contrib phppgadmin
    sudo su
    su - postgres
    psql
    \password postgres
    \q
    exit
    cd /etc/apache2/conf-available/
    gedit phppgadmin.conf
    
        # Only allow connections from localhost:
        #Require local
        Allow From all
    
    cd /etc/phppgadmin/
    gedit config.inc.php
    
        $conf['extra_login_security'] = false;
    
    systemctl restart postgresql
    systemctl restart apache2
    
    localhost/phppgadmin/
    
    create user arnon with password 'arnon42';
    grant all privileges on database postgres to arnon;
    revoke all privileges on postgres from arnon;
    drop user arnon;
    


Use host-only network on Virtualbox
-----------------------------------

VirtualBox -> Preferences -> Network -> Host-only Networks

Make sure you have vboxnet0 or add new one.

Edit vboxnet0 (or the one you use), disable DHCP Server.  Note IpV4 Address 192.168.56.1 (change if need be)

In Virtualbox settings -> Networks

Network Adapter 1: NAT
Network Adapter 2: Host Only

In Ubuntu, make sure you have enp0s8 in /etc/networks/interfaces

sudoedit /etc/network/interfaces
# interfaces(5) file used by ifup(8) and ifdown(8)
auto lo
iface lo inet loopback
auto enp0s8
iface enp0s8 inet static
address 192.168.56.10
netmask 255.255.255.0

Note address is 192.168.56.10 is different from Host-only preference address.  You can chose a different one on the same subnet but must be different than the one on vboxnet0 (or what ever you chose).


Open SSH
========

sudo apt-get install openssh-server
sudo iptables -A INPUT -p tcp --dport ssh -j ACCEPT


sudo emacs /etc/postgresql/9.6/main/pg_hba.conf, add:

    host    all             all             0.0.0.0/0               md5
    host    all             all             ::/0                    md5

sudo emacs /etc/postgresql/9.6/main/postgresql.conf, change:

    listen_addresses = '*'
    
test network tables:

    sudo netstat -tln
    sudo netstat -tulpn

sudo /etc/init.d/postgresql restart
# alternative: sudo invoke-rc.d postgresql restart
# alternative: sudo invoke-rc.d postgresql reload

sudo iptables -A INPUT -p tcp --dport 5432 -j ACCEPT

test conncetion from remote: 
    psql -h 172.31.99.104 -d pyground -U arnon
    psql -h 192.168.1.100 -d pyground -U arnon 
    
multiple keys to the same host with different virtualenv
--------------------------------------------------------

ssh-keygen -t rsa -C "sequent" -f "id_rsa_sequent"

server's ~/.ssh/config

Host remote.com-sequent
     HostName remote.com
     User me
     IdentityFile ~/.ssh/id_rsa_sequent
     IdentitiesOnly yes
     
copy id_rsa_sequent.pub  tp remote.com and add to authorized_keys.

prefix key in authorized_keys:

command="if [[ \"x${SSH_ORIGINAL_COMMAND}x\" != \"xx\" ]]; then source ~/.profile_sequent; eval \"${SSH_ORIGINAL_COMMAND}\"; else /bin/bash --login; fi;" ssh-rsa ...

in ~/.profile_sequent:

source ~/.profile
source /var/venv/sequent/bin/activate



Python
======

sudo apt-get install pip python-dev virtualenv 
pip install virtualenvwrapper

~/.profile
    
    export JAVA_HOME=/opt/java/jdk1.8.0_144
    export PATH=//home/arnon/.local/bin/:$JAVA_HOME/jre/bin:$JAVA_HOME/bin:$PATH
    export WORKON_HOME=/var/venv 

~/.bashrc

    source /home/arnon/.local/bin/virtualenvwrapper.sh
    alias v='workon'
    alias v.deactivate='deactivate'
    alias v.mk='mkvirtualenv --no-site-packages'
    alias v.mk_withsitepackages='mkvirtualenv'
    alias v.rm='rmvirtualenv'
    alias v.switch='workon'
    alias v.add2virtualenv='add2virtualenv'
    alias v.cdsitepackages='cdsitepackages'
    alias v.cd='cdvirtualenv'
    alias v.lssitepackages='lssitepackages'
    
Eventor
=======


    
