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
    


Use bridge network on Virtualbox.

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
    psql -h 192.168.1.100 -d pyground -U arnon 

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


    
