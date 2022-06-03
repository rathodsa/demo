import argparse
import json
import time
import socket
import paramiko
import subprocess
from subprocess import PIPE
import base64


def check_png(ip):
    loop_val = True
    while loop_val is True:
        my_png = "ping -c 3 %s | tail -2 | grep -i packets | awk '{print $4 }'"%ip
        out1 = subprocess.run([my_png], stdout=PIPE, stderr=PIPE, shell=True)
        res = out1.stdout.decode("utf-8")
        response = res.strip()
        if int(response) == 0:
            print("Installation is complete and hence VM is not connecting")
            return response
        if int(response) == 3:
            print("It is waiting for Installation to finish for %s"%ip)
            time.sleep(180)


def host_check(ip_address):
    try:
        socket.gethostbyname(ip_address)
    except socket.gaierror:
        print("DNSLookupFailure")
        exit(1)


def ssh_connection(address, username, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(address, username=username, password=password, timeout=60)
        return True, client
    except Exception as e:
        return False, None


def establish_ssh_session(host_to_connect, username, password):
    status, session = ssh_connection(host_to_connect, username, password)
    if status:
        return session
    return None


def execute_command(command, host_to_connect=None, username=None, password=None, session=None, timeout=600):
    if not session:
        session = establish_ssh_session(host_to_connect, username, password)
        if not session:
            exit(1)
    std_in, stdout, stderr = session.exec_command(command=command, timeout=timeout)
    command_response = {'stdout': stdout.readlines(), 'stderr': stderr.readlines()}
    session.close()
    return command_response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json_file', help="JSON file to be processed")
    parser.add_argument('--version', help="version to be processed")
    args = parser.parse_args()
    provided_version = args.version

    if args.json_file:
        print("Parsing JSON file")
        with open(args.json_file) as json_file_content:
            data = json.load(json_file_content)
            version_details = data[provided_version]
            build_type = version_details['build_type']
            version = version_details['version']
            sub_version = version_details['sub_version']
            mac_address = version_details['mac_address']
            host_name = version_details['host_name']
            ip_address = version_details['ip_address']
            password_dec = version_details['std_pass']
            password = str(base64.b64decode(password_dec).decode("utf-8"))
            username = 'root'

            print(build_type, version, sub_version, mac_address, host_name, ip_address)
            install_command = "virt-install -d --mac=%s -n %s --os-type=Linux --ram=8192 --vcpus=2 '--extra-args=ks=http://slc16izo.us.oracle.com/ks/OVM_KVM-LINUX-%s0u%s-X8664.cfg ip=%s netmask=255.255.248.0 gateway=10.241.88.1 dns=10.231.225.65' --virt-type xen --disk path=/OVS/Repositories/F75CF23BD44F468AA089698044CFEDC9/VirtualDisks/%s_root.img,size=50 --location http://pd-yum-slc-01.us.oracle.com/bootable/OracleLinux/%s/%s/base/x86_64/ --graphics vnc,listen=0.0.0.0"%(mac_address, host_name, version, sub_version, ip_address, host_name, version, sub_version)
            print(install_command)
            print(build_type)
            if build_type == 'OVM':
                host_to_connect = 'slcav928.us.oracle.com'
            else:
                host_to_connect = 'slcal653.us.oracle.com'
            export_variable_command = 'export LC_ALL=en_US.utf-8;export LANG=en_US.utf-8'
            execute_command(export_variable_command, host_to_connect, username, password)
            print("-----------Installation started------------")
            exec_result = execute_command(install_command, host_to_connect, username, password)
            time.sleep(180)
            print(exec_result)
            print("waiting for installation to finish and VM become available")
            time.sleep(1000)
            ping_response = check_png(ip_address)
            print(ping_response)
            print("ping check is complete")
            if int(ping_response) == 0:
                print("ping check working")
                print("we are able to ping the server.. hence trying xm start.. ")
                start_server_command = "xm create /OVS/Repositories/F75CF23BD44F468AA089698044CFEDC9/VirtualMachines/%s/vm.cfg"%(host_name)
                #start_server_command = f"{start_server_command}%{host_name}"
                exec_result = execute_command(start_server_command, host_to_connect, username, password)
                exec_result = str(exec_result)
                if "Error" in exec_result:
                    print("There is error in the xm start .. so we are destroying and trying start again.. ")
                    destroy_host_command = "xm destroy %s"%(host_name)
                    delete_host_command = "xm delete %s"%(host_name)
                    execute_command(destroy_host_command, host_to_connect, username, password)
                    print("destroy complete")
                    execute_command(delete_host_command, host_to_connect, username, password)
                    print("delete complete")
                    exec_result = execute_command(start_server_command, host_to_connect, username, password)
                    exec_result = str(exec_result)
                    print(exec_result)
                    if "Started" in exec_result:
                        print("VM started successfully and able to connect")
            execute_command(export_variable_command, host_to_connect, username, password)
            my_overlay_hosts = list()
            host_name = f"{str(host_name)}.us.oracle.com"
            my_overlay_hosts.append(host_name)
            print(host_name)
            for i in range(20):
                first_password_to_connect = 'welcome'
                grep_command = 'egrep -i \"Chef run process exited unsuccessfully|Chef client finished\" /root/.stinstall.log'
                session = establish_ssh_session(host_name, username, first_password_to_connect)
                if not session:
                    root_password = 'S$1v!@nE_p'
                    session = establish_ssh_session(host_name, username, root_password)
                exec_result = execute_command(grep_command, None, None, None, session)
                print(exec_result)
                if "Chef Client finished" in str(exec_result):
                    print("Overlay is completed and server is ready to connect")
                    print("Running patching script")
                    patch_command = 'cd /tmp;wget https://pds-chef-dr-infrastructure.us.oracle.com/dis_chef_repo/security/ol_cpu_patching.py;chmod +x ol_cpu_patching.py;./ol_cpu_patching.py --monthly --security-patch --force-fix'
                    session = establish_ssh_session(host_name, username, root_password)
                    exec_result = execute_command(patch_command, None, None, None, session)
                    print(exec_result)
                    if "OL_PATCH_SUCCESSFUL" in str(exec_result) or "SECURITY AND KERNEL PATCH IS ALREADY UPDATED" in str(exec_result):
                        print("Patching is complete")
                    print("=========proceeding with image cleaup===========")
                    clean_command = "cd /tmp;wget http://pds-chef-infrastructure.us.oracle.com/dis_chef_repo/cleanup_script/image_cleanup.py;chmod +x image_cleanup.py;./image_cleanup.py"
                    session = establish_ssh_session(host_name, username, root_password)
                    execute_command(clean_command, None, None, None, session)
                    print("=========image cleanup complete=====")
                    print("moving the file to standard location")
                    copy_command = "scp -i /tmp/.anskey -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no /OVS/Repositories/F75CF23BD44F468AA089698044CFEDC9/VirtualDisks/%s_root.img root@slcal653:/var/www/html/images/VirtualDisk/%s_pipeline_22102021/"%(host_name, build_type)
                    session = establish_ssh_session(host_to_connect, username, first_password_to_connect)
                    copy_res = execute_command(copy_command, None, None, None, session)
                    print(copy_res)
                    break
                else:
                    print("Overlay not finished.trying again for %s"%host_name)
                    time.sleep(300)
            print("Image build finished for major version : %s and minor version: %s on the host"%(version, sub_version, host_name))

if __name__ == '__main__':
    main()
