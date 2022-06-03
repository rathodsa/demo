#!/usr/bin/python
# Author : anilkumar.kv@oracle.com
# Date: 16 July 2020
# All rights reserved - Do Not Redistribute

import os
import shutil
import commands
import glob
import platform
import sys
import subprocess
import getpass

files_list = {'sysconf': {
    '1': '/etc/sysconfig/clonefirstboot',
    '2': '/etc/sysconfig/cloneprenetwork',
    '3': '/etc/sysconfig/cloneupdate',
    '4': '/etc/sysconfig/firstboot',
    '5': '/etc/sysconfig/initialization_retries',
    '6': '/etc/sysconfig/localization_retries',
    '7': '/etc/ade.conf/ociMetadata'
},
    'etc_f': {
        '1': '/etc/fstab_*',
        '2': '/etc/fstab.*',
        '3': '/etc/issue.net',
        '4': '/etc/motd',
        '5': '/etc/oragchomelist',
        '6': '/etc/rc3.d/*emagent*',
        '7': '/etc/rc5.d/*emagent*',
        '8': '/etc/resolv.conf.*',
        '9': '/etc/udev/rules.d/70*',
        '10': '/etc/asset/*',
        '11': '/etc/yum.repos.d/*'
    },
    'var_f': {
        '1': '/var/lib/dhclient/*',
        '2': '/var/log/anaconda*',
        '3': '/var/log/audit/audit*',
        '4': '/var/log/boot*',
        '5': '/var/log/btmp-*',
        '6': '/var/log/btmp.*',
        '7': '/var/log/cron*',
        '8': '/var/log/cups/*',
        '9': '/var/log/dmesg*',
        '10': '/var/log/dracut.log-*',
        '11': '/var/log/emagent*',
        '12': '/var/log/faillog*',
        '13': '/var/log/faillog*',
        '14': '/var/log/ibacm*',
        '15': '/var/log/invposts*',
        '16': '/var/log/lastlog*',
        '17': '/var/log/maillog*',
        '18': '/var/log/mcelog*',
        '19': '/var/log/messages*',
        '20': '/var/log/prelink*',
        '21': '/var/log/rpmpkgs*',
        '22': '/var/log/sa/*',
        '23': '/var/log/scrollkeeper*',
        '24': '/var/log/secure*',
        '25': '/var/log/spooler-*',
        '26': '/var/log/spooler.*',
        '27': '/var/log/sudo*',
        '28': '/var/log/systemtap*',
        '29': '/var/log/trace-cmd*',
        '30': '/var/log/wtmp-*',
        '31': '/var/log/wtmp.*',
        '32': '/var/log/yum.log*',
        '33': '/var/chef',
        '34': '/var/log/usage',
        '35': '/var/tmp/*',
        '36': '/var/cache/yum'
    },
    'root_f': {
        '1': '/root/jaytest',
        '2': '/root/.jayoverlay',
        '3': '/root/.ssh/known_hosts',
        '4': '/root/.bassdb_record',
        '5': '/root/.devops.json',
        '6': '/root/overlay_test',
        '7': '/root/anaconda',
        '8': '/root/.chef',
        '9': '/root/.stinstall.log*',
        '10': '/root/.ssh/authorized_*',
        '11': '/root/*.log',
        '12': '/root/*.csv',
        '13': '/root/.nis2ldap*',
        '14': '/root/.stimage*',
        '15': '/root/.krb*',
        '16': '/root/.pditkrb*',
        '17': '/root/.rhosts*',
        '18': '/root/.ks-*',
        '19': '/root/.dis_config_version*',
        '20': '/root/.peo_update*',
        '21': '/root/.nslcd2sssd*',
        '22': '/root/.client.rb',
        '23': '/root/.mailnotfcnlog',
        '24': '/root/.instanceprovisioningsetup.log',
        '25': '/root/stosimage_filers',
        '26': '/root/subnets',
        '27': '/root/cleanup.sh',
        '28': '/root/.viminfo',
        '29': '/root/krb',
        '30': '/root/.bash_history',
        '31': '/root/local-mode-cache/cache/',
        '32': '/root/zero.file',
        '33': '/root/anaconda-ks.cfg',
        '34': '/root/original-ks.cfg',
        '35': '/root/peo_update.repo',
        '36': '/root/backup',
        '37': '/root/local-mode-cache/backup',
        '38': '/root/zero.small.file'
    },
    'other_f': {
        '1': '/boot/grub/grub.conf-*',
        '2': '/scripts/config.env',
        '3': '/scripts/debug.log',
        '4': '/scripts/firstrun',
        '5': '/scripts/setup.log',
        '6': '/swapfile*',
        '7': '/halt',
        '8': '/mnt/*',
        '9': '/parser.out',
        '10': '/parsetab',
        '11': '/poweroff',
        '12': '/scratch/*',
        '13': '/scratch/optena',
        '14': '/scripts/localization',
        '15': '/LOCAL_SWAP/*',
        '16': '/tmp/*',
        '17': '/root/.repo_backup/*'
    }
}


# Cleanup Files
def remove_files(file_name):
    disable_swap = commands.getoutput("swapoff /LOCAL_SWAP/*")
    cmd = "rm -rf " + file_name
    status, output = commands.getstatusoutput(cmd)
    if status != 0:
        sys.exit("Failed to cleanup files")


def remove_em():
    if os.path.exists("/oem/app/oracle/product/emagent/agent_inst/bin/emctl") == True:
        cmd = 'su -c "/oem/app/oracle/product/emagent/agent_inst/bin/emctl stop agent" emcadm'
        status, output = commands.getstatusoutput(cmd)
        if status == 0:
            cmd1 = 'userdel -r emcadm; userdel -r optena; userdel -r emdadm'
            rm_user = commands.getoutput(cmd1)
            rm_oem = commands.getoutput("rm -rf /oem/*")


def service_mgmt(name, srv_cmd):
    # Oracle Linux Service management to start, stop, enable, disable services
    global serv_cmd
    if int(os_vers) >= 7:
        cmd_sysctl = "/usr/bin/systemctl " + srv_cmd + " " + name
        cmd_status, cmd_out = commands.getstatusoutput(cmd_sysctl)
        if cmd_status != 0:
            sys.exit("Enabling service failed " + name)
    else:
        if srv_cmd == "enable" or srv_cmd == "disable":
            if srv_cmd == "enable":
                serv_cmd = "on"
            else:
                serv_cmd = "off"

            cmd_service = "/sbin/chkconfig " + name + " " + serv_cmd
            cmd_status, cmd_out = commands.getstatusoutput(cmd_service)
            if cmd_status != 0:
                sys.exit("Enabling/Disable service failed " + name)

        elif srv_cmd == "start" or srv_cmd == "stop":
            cmd_service = "/sbin/service " + name + " " + srv_cmd
            cmd_status, cmd_out = commands.getstatusoutput(cmd_service)
            if cmd_status != 0:
                sys.exit("Start or Stop of service failed " + name)
        else:
            sys.exit("Invalid service options")


def net_srv():
    if int(os_vers) >= 7:
        if glob.glob("/etc/sysconfig/network-scripts/ifcfg-e*"):
            rm_net = commands.getoutput("rm -f /etc/sysconfig/network-scripts/ifcfg-e*")
            # rm_network = commands.getoutput("rm -f /etc/sysconfig/network")
            set_hname = commands.getoutput("hostnamectl set-hostname localhost")
    else:
        if glob.glob("/etc/sysconfig/network-scripts/ifcfg-eth0"):
            f = open("/etc/sysconfig/network-scripts/ifcfg-eth0", "w")
            f.writelines(["DEVICE=eth0\n", "BOOTPROTO=dhcp\n", "ONBOOT=yes\n", "TYPE=Ethernet\n", "NM_CONTROLLED=no\n"])
            f.close()

    if glob.glob("/etc/sysconfig/network"):
        n = open("/etc/sysconfig/network", "w")
        n.writelines(["NETWORKING=yes\n", "NOZEROCONF=yes\n"])
        n.close()

    c_init = ["cloud-init", "cloud-config", "cloud-final", "cloud-init-local"]
    for srv in c_init:
        service_mgmt(srv, "enable")


def home_host_sshkey_cleanup():
    service_mgmt("autofs", "stop")
    home_stat, home_out = commands.getstatusoutput("mount |grep home")
    if home_stat != 0:
        home_c_stat, home_c_out = commands.getstatusoutput("rm -rf /home/*")
        if home_c_stat != 0:
            sys.exit("home directory cleanup failed")
    else:
        sys.exit("home directory cleanup failed as it is nfs home")

    status, output = commands.getstatusoutput("> /root/.ssh/authorized_keys")
    if status != 0:
        sys.exit("Failed to cleanup ssh keys")

    with open("/etc/hosts", "r") as f:
        lines = f.readlines()
    with open("/etc/hosts", "w") as f:
        for line in lines:
            if "localhost" in line:
                f.write(line)
        f.close()

    with open("/etc/fstab", "r+") as f:
        new_f = f.readlines()
        f.seek(0)
        for line in new_f:
            if "LOCAL_SWAP" not in line:
                f.write(line)
        f.truncate()


def docker_cleanup():
    if int(os_vers) <= 7:
        service_mgmt("docker", "stop")
        service_mgmt("docker", "disable")


def delete_users():
    usernames = ["aime", "aime1", "aime2", "aime3", "aime4", "aime5", "aime6", "aime7", "aime8", "aime9", "aime10", "optena"]
    for username in usernames:
        output = subprocess.run(['userdel', '-f', username])
        if output.returncode == 0:
            print(f"User {username} successfully deleted with given credentials")
        output1 = subprocess.getoutput(f"cat /etc/passwd | grep -i {username} | wc -l")
        if int(output1) == 0:
            print(f"double verified that {username} doesnt exist")
        else:
            print(f"{username} still exist or delete has errors")
            sys.exit(1)

# Main Function
def main():
    global os_vers
    os_vers = platform.linux_distribution()[1].split('.')[0].strip()
    ol_ver = platform.linux_distribution()[1]
    if ol_ver == '6.6' or ol_ver == '6.4':
        pass
    else:
        docker_cleanup()
    sysfiles = files_list.keys()
    for k in sysfiles:
        for v in files_list[k].values():
            if glob.glob(v):
                remove_files(v)
    remove_em()
    net_srv()
    home_host_sshkey_cleanup()
    delete_users()



# Executing main Function

if __name__ == "__main__":
    main()