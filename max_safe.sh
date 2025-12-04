#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
    echo "Run as root"
    exit 1
fi

echo "[1] Backing up..."
cp /etc/security/limits.conf /etc/security/limits.conf.bak.$(date +%s)
cp /etc/sysctl.conf /etc/sysctl.conf.bak.$(date +%s)

echo "[2] Fixing limits.conf..."

cat > /etc/security/limits.conf << 'EOF'
# High performance limits (safe)
* soft nofile 500000
* hard nofile 500000

* soft nproc 65535
* hard nproc 65535

* soft memlock 131072
* hard memlock 131072

root soft nofile 500000
root hard nofile 500000
EOF

echo "[3] Fixing sysctl parameters..."

cat >> /etc/sysctl.conf << 'EOF'

# High but safe values
fs.file-max = 2000000
fs.nr_open = 2000000

kernel.pid_max = 131072
kernel.threads-max = 300000

net.core.somaxconn = 65535
net.core.netdev_max_backlog = 250000
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432

net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535

net.netfilter.nf_conntrack_max = 262144
EOF

sysctl -p

echo "[4] Restoring proper PAM configuration..."

cat > /etc/pam.d/common-session << 'EOF'
session [default=1] pam_permit.so
session requisite pam_deny.so
session required pam_limits.so
session optional pam_umask.so
session optional pam_systemd.so
EOF

cp /etc/pam.d/common-session /etc/pam.d/common-session-noninteractive

echo "[5] Systemd limits (safe)..."
mkdir -p /etc/systemd/system.conf.d
cat > /etc/systemd/system.conf.d/limits.conf << 'EOF'
[Manager]
DefaultLimitNOFILE=500000
DefaultLimitNPROC=65535
EOF

echo "[6] CPU governor..."
for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "$g" 2>/dev/null || true
done

echo "[OK] Safe performance configuration applied."
echo "Reboot now."
