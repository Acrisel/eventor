=============================
Development Environment Notes
=============================


On Ubuntu Virtualbox install postgresql and pgAdmin.

Use bridge network on Virtualbox.

sudo emacs /etc/postgresql/9.6/main/pg_hba.conf, add:

    host    all             all             0.0.0.0/0               md5
    host    all             all             ::/0                    md5

sudo emacs /etc/postgresql/9.6/main/postgresql.conf, change:

    listen_addresses = '*'
    
test network tables:

    sudo netstat -tln
    sudo netstat -tulpn

sudo /etc/init.d/postgresql restart

sudo iptables -A INPUT -p tcp --dport 5432 -j ACCEPT

test conncetion from remote: 
    psql -h 192.168.1.70 -d pyground -U arnon 

