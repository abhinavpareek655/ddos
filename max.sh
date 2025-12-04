#!/bin/bash
#
# Maximum Performance Configuration for Ubuntu Server
# WARNING: This removes ALL safety limits - system may crash under load!
# Use only for stress testing in isolated VMs
#

set -e

echo "=========================================="
echo "MAXIMUM PERFORMANCE CONFIGURATION"
echo "WARNING: Removes all safety limits!"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "[!] Please run as root (use sudo)"
    exit 1
fi

echo "[1/7] Configuring system-wide limits..."

# Backup original files
cp /etc/security/limits.conf /etc/security/limits.conf.backup.$(date +%s) 2>/dev/null || true
cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%s) 2>/dev/null || true

# Set unlimited resource limits
cat > /etc/security/limits.conf << 'EOF'
# Maximum Performance Configuration - NO LIMITS
* soft nofile 1000000
* hard nofile 1000000
* soft nproc unlimited
* hard nproc unlimited
* soft memlock unlimited
* hard memlock unlimited
* soft stack unlimited
* hard stack unlimited
root soft nofile 1000000
root hard nofile 1000000
root soft nproc unlimited
root hard nproc unlimited
EOF

echo "[2/7] Configuring kernel parameters..."

# Kernel network and performance tuning
cat >> /etc/sysctl.conf << 'EOF'

# ============================================
# MAXIMUM PERFORMANCE - NO SAFETY LIMITS
# ============================================

# Maximum file handles
fs.file-max = 10000000
fs.nr_open = 10000000

# Maximum processes
kernel.pid_max = 4194304
kernel.threads-max = 4194304

# Network stack tuning for high throughput
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 500000
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.core.rmem_default = 16777216
net.core.wmem_default = 16777216
net.core.optmem_max = 40960

# TCP tuning
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_tw_buckets = 2000000
net.ipv4.ip_local_port_range = 1024 65535

# Increase connection tracking
net.netfilter.nf_conntrack_max = 10485760
net.nf_conntrack_max = 10485760

# Virtual memory aggressive settings
vm.swappiness = 10
vm.dirty_ratio = 80
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1

# Maximum shared memory
kernel.shmmax = 68719476736
kernel.shmall = 4294967296
EOF

# Apply immediately
sysctl -p

echo "[3/7] Setting up connection tracking..."

# Load conntrack module and set max
modprobe nf_conntrack
echo 10485760 > /sys/module/nf_conntrack/parameters/hashsize 2>/dev/null || true

echo "[4/7] Configuring systemd limits..."

# Configure systemd default limits
mkdir -p /etc/systemd/system.conf.d/
cat > /etc/systemd/system.conf.d/limits.conf << 'EOF'
[Manager]
DefaultLimitNOFILE=1000000
DefaultLimitNPROC=unlimited
DefaultLimitMEMLOCK=unlimited
DefaultLimitSTACK=unlimited
EOF

mkdir -p /etc/systemd/user.conf.d/
cat > /etc/systemd/user.conf.d/limits.conf << 'EOF'
[Manager]
DefaultLimitNOFILE=1000000
DefaultLimitNPROC=unlimited
DefaultLimitMEMLOCK=unlimited
DefaultLimitSTACK=unlimited
EOF

echo "[5/7] Creating PAM configuration..."

# PAM limits
cat > /etc/pam.d/common-session << 'EOF'
session required pam_limits.so
EOF

cat > /etc/pam.d/common-session-noninteractive << 'EOF'
session required pam_limits.so
EOF

echo "[6/7] Disabling unnecessary services..."

# Disable CPU frequency scaling (run at max speed)
systemctl disable ondemand 2>/dev/null || true
if [ -f /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor ]; then
    for governor in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$governor" 2>/dev/null || true
    done
fi

# Make CPU governor permanent
cat > /etc/rc.local << 'EOF'
#!/bin/bash
for governor in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "$governor" 2>/dev/null || true
done
exit 0
EOF
chmod +x /etc/rc.local

echo "[7/7] Creating Flask server launcher..."

cat > /tmp/flask_max_perf.sh << 'EOFSCRIPT'
#!/bin/bash

# Set maximum limits for current shell
ulimit -n 1000000     # Open files
ulimit -u unlimited   # Processes
ulimit -s unlimited   # Stack size
ulimit -m unlimited   # Max memory
ulimit -v unlimited   # Virtual memory
ulimit -l unlimited   # Locked memory

export FLASK_ENV=production
export PYTHONUNBUFFERED=1

echo "Current ulimits:"
ulimit -a
echo ""
echo "Starting Flask server with maximum performance..."
echo ""

# Run Flask app
exec "$@"
EOFSCRIPT

chmod +x /tmp/flask_max_perf.sh

echo ""
echo "=========================================="
echo "CONFIGURATION COMPLETE!"
echo "=========================================="
echo ""
echo "IMPORTANT: You must REBOOT for all changes to take effect!"
echo ""
echo "After reboot, verify limits with:"
echo "  ulimit -a"
echo "  cat /proc/sys/fs/file-max"
echo "  cat /proc/sys/net/core/somaxconn"
echo ""
echo "Backup files created with timestamp suffix"
echo ""
echo "=========================================="