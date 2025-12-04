sysctl net.core.somaxconn=4096
ifconfig enp0s3 txqueuelen 5000
echo "/sbin/ifconfig enp0s3 txqueuelen 5000" >> /etc/rc.local
sysctl net.core.netdev_max_backlog=4000
sysctl net.ipv4.tcp_max_syn_backlog=4096
ulimit -n 500000
ulimit -a unlimited