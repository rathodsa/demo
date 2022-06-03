#!/usr/bin/python3.6
import argparse
import json
import sys
import paramiko
from time import sleep
import os
import subprocess
import sys
import argparse
from subprocess import Popen, PIPE
import threading
import subprocess
import re
import time
import base64
import concurrent.futures
import oci
from datetime import datetime
from datetime import date
import os
from oci_oit_logging_sdk.oit_logger import OITLoggerClient
print(os.getenv('API_URL'))
print(os.getenv('API_TOKEN'))

config = oci.config.from_file(file_location="oci-config.ini")
core_client = oci.core.ComputeClient(config)


oit_logger = OITLoggerClient(
    api_url='https://logfuse-api-dev.appoci.oraclecorp.com',
token='ZXlKMGVYQWlPaUpLVjFRaUxDSmhiR2NpT2lKSVV6STFOaUo5LmV5SmxlSEFpT2pFM01EWTBOVE14TURrc0ltbGhkQ0k2TVRZME16TTRNVEV3T1N3aWMzVmlJam95ZlEuZWRVdEh3MHhnMkltclFtdjJXNkstN0N2b1A4emxzaWJ4ejduSEZEckpONA=='
)


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


def execute_command(command, session, wait_flag=False, timeout=600):
    if not session:
        print("Invalid connection session to connect to server.")
    std_in, stdout, stderr = session.exec_command(command=command, timeout=timeout)
    if wait_flag:
        while stdout.channel.recv_exit_status():
            time.sleep(1)
    command_response = {'stdout': stdout.readlines(), 'stderr': stderr.readlines()}
    # session.close()
    return command_response


def get_base_sp(image_ver,compartment_id):
    list_images_response = core_client.list_images(
        compartment_id=compartment_id,
        display_name=image_ver,
        lifecycle_state="AVAILABLE")
    if list_images_response:
        return list_images_response.data[0].id
    return None


def run_packer(command_to_run):
    packer_result = subprocess.run(command_to_run, stdout=subprocess.PIPE)
    return packer_result.stdout.decode("utf-8")


def get_image_ocid(output):
    serach_string = "ocid1.image"
    items = re.findall(f"^.*{serach_string}.*$", output, re.MULTILINE)
    image_ocid = None
    print(items)
    for item in items[0].split():
        if serach_string in item:
            image_ocid = item
            break
    return image_ocid.replace(")", "")



def prepare_variable_json_for_packer(image_ver, image_id, password, template_name):
    with open(f"/home/gitlab-runner/variables/variables{image_ver}.json", "r") as src:
        data_to_insert = json.load(src)
    data_to_insert["let_image"] = image_id
    data_to_insert["ssh_password"] = password
    data_to_insert["image_name"] = template_name
    with open(f"/home/gitlab-runner/new-variables/new-variables{image_ver}.json", "w") as dst:
        dst.write(json.dumps(data_to_insert))


def prepare_variable_json_for_instance(image_version,instance_name,image_ocid,user_data_file):
    with open(f"/home/gitlab-runner/custom-instance/custom_instance{image_version}.json", "r") as src:
        data_to_insert = json.load(src)
    data_to_insert[0]["instance_name"] = instance_name
    data_to_insert[0]["image_id"] = image_ocid
    data_to_insert[0]["user_data_file"] = user_data_file
    with open(f"/home/gitlab-runner/custom-instance/custom{image_version}_instance.json", "w") as dst:
        dst.write(json.dumps(data_to_insert))


def get_instance_ip(instance_output):
    serach_string = "Private"
    print(instance_output)
    print(type(instance_output))
    items = instance_output.split()
    return items[-1].strip()


def image_build(values):
    image_version = values.get('image_version')
    image_name = values.get('image_name')
    image_id = values.get('image_id')
    username = values.get('username')
    password = values.get('password')
    rel_date = values.get('rel_date')
    qualis_flag = values.get('qualis_flag')
    log_fuse_json_data = {}
    log_fuse_json_data['service_name'] = "image_automation"
    print(image_name,image_id,username,password,rel_date,qualis_flag)
    base_dir = "/home/gitlab-runner"
    base_var_directory = f"{base_dir}/variables/variables{image_version}.json"
    base_new_var_directory = f"{base_dir}/new-variables/new-variables{image_version}.json"
    base_pcr_directory = f"{base_dir}/pcr/custom-image-build{image_version}.json"
    base_packer_output_file = f"{base_dir}/customeimage{image_version}.txt"
    instance_creation_command = f"{base_dir}/oit-image-management-system/deploy/Instance-creation/oci_compute_instance.py"
    custom_instance_folder = f"{base_dir}/custom-instance/custom{image_version}_instance.json"
    object_store_command = f"{base_dir}/oit-image-management-system/deploy/Instance-creation/create_image.py"
    packer_command = ["sudo", "/usr/local/packer", "build", "-on-error=abort", f"-var-file={base_new_var_directory}", base_pcr_directory]
    post_instance_create_command = ["python", instance_creation_command, "--create_new", "--json_file", custom_instance_folder]
    if '8.5' in image_name:
        template_name = "ee-ol8u5-qi" + '-' + str(date.today())
    else:
        template_name = str(image_name) + '-' + str(date.today())
    prepare_variable_json_for_packer(image_version,image_id,password,template_name)
    log_fuse_json_data["Image_build_start_time"] = str(datetime.now())
    packer_output = run_packer(packer_command)
    image_ocid = get_image_ocid(packer_output)
    print(image_ocid)
    instance_name = f"Post-instance-ol{image_version}"
    user_data_file = '/home/gitlab-runner/test_wrap/user_data.txt'
    prepare_variable_json_for_instance(image_version,instance_name,image_ocid,user_data_file)
    if image_ocid:
        log_fuse_json_data["Image_build_end_time"] = str(datetime.now())
        log_fuse_json_data["image_name"] = str(template_name)
        log_fuse_json_data["image_build_status"] = "Success"
        log_fuse_json_data["snapshot_date"] = str(rel_date)
        log_fuse_json_data["Image_validation_start_time"] = str(datetime.now())
        instance_output = run_packer(post_instance_create_command)
        instance_ip = get_instance_ip(instance_output)
        log_fuse_json_data['host_name'] = instance_ip.strip()
    else:
        log_fuse_json_data["Image_build_end_time"] = "Image not built"
        print("Unable to get image OCID")
        log_fuse_json_data['host_name'] = "host_name not available"
        log_fuse_json_data["image_build_status"] = "Failure"
        log_fuse_json_data["snapshot_date"] = str(rel_date)
        oit_logger.send_log(log_fuse_json_data)
        sys.exit(1)
    time.sleep(900)
    server_name = instance_ip.strip()
    check_cloudinit_status_command = 'egrep -i \"Chef run process exited unsuccessfully|Chef client finished|ORC Client finished\" /root/.stinstall.log'
    export_to_object_command = ["sudo", "python", object_store_command, "--export", "--image_id", image_ocid, "--bucket_name", "bucket-cust_images", "--display_name", template_name, "--namespace_name", "peo", "--config", "oci-config.ini"]
    for i in range(20):
        session = establish_ssh_session(server_name, username, password)
        if session:
            exec_result = execute_command(check_cloudinit_status_command, session, True)
            result = exec_result['stdout']
            print(result)
            if len(result) > 1:
                if "Chef Client finished" in result[0] and "Chef Client finished" in result[1]:
                    cloudinit_status = "Overlay is finished"
                    log_fuse_json_data["Image_validation_end_time"] = str(datetime.now())
                    break
                elif "ORC Client finished" in result[0] and "ORC Client finished" in result[1]:
                    log_fuse_json_data["Image_validation_end_time"] = str(datetime.now())
                    cloudinit_status = "Overlay is finished"
                    break
            else:
                print("overlay is not finished..Trying again")
                time.sleep(600)
        else:
            print("Unable to connect, trying again")
            time.sleep(300)
    if cloudinit_status == "Overlay is finished":
        print(f"Exporting image {image_name} to object store")
        export_result = run_packer(export_to_object_command)
        print(export_result)
    else:
        print("exiting as cloud inint is not finished after 20 iters")
        sys.exit(1)
    if qualis_flag == "True":
        instance_name_qualis = f"Post-instance-ol{image_version}-qualis"
        user_data_file = '/home/gitlab-runner/test_wrap/user_data_qualis.txt'
        prepare_variable_json_for_instance(image_version,instance_name_qualis,image_ocid,user_data_file)
        instance_output_qualis = run_packer(post_instance_create_command)
        qualis_instance_ip = get_instance_ip(instance_output_qualis)
        print(f"Qualis instance IP is {qualis_instance_ip}")
    else:
        print("qualis flag is not selected, hence exiting")
    print(log_fuse_json_data)
    oit_logger.send_log(log_fuse_json_data)
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json_file', help="JSON file to be processed")
    args = parser.parse_args()
    if args.json_file:
        print("Parsing JSON file")
        with open(args.json_file) as json_file_content:
            input_data = json.load(json_file_content)
            pass_wd = str(base64.b64decode(input_data['std_pass']).decode("utf-8"))
            qualis_flag = input_data['qualis_flag']
            rel_date = input_data['release_date']
            image_names = input_data['image_names']
            comp_ocid = input_data['comp_ocid']
            username = input_data['username']
            test_images = image_names.split(",")
            ver_dict = {}
            values = []
            for ver in test_images:
                ver_key = f"{ver.replace('.', '')}"
                if ver == '8.5':
                    ver_val = f"ee-ol{ver.replace('.', 'u')}-qi"
                   # img = "Oracle-Linux-%s-[0-9]*"%ver
                   # cmd1_out = subprocess.run(["prerequisites/scripts/get_the_image_name.sh",comp_ocid,img],stdout=PIPE,stderr=PIPE)
                   # ver_val = cmd1_out.stdout.decode("utf-8")
                else:
                    ver_val = f"peo-ol{ver.replace('.', 'u')}-qi"
                ver1_key = f"image_name{ver.replace('.', '')}"
                ver1_val = ver
                ver_dict[ver_key] = ver_val
                ver_dict[ver1_key] = ver1_val
                image_id = get_base_sp(ver_val.strip(), comp_ocid).strip()
                time.sleep(60)
                if image_id:
                    val = {"image_name": ver_val, "image_id": image_id, "username": username,
                   "password": pass_wd, "rel_date": rel_date, "qualis_flag": qualis_flag, "image_version": ver_key}
                    values.append(val)
                else:
                    print(f"Run skipped for {ver}. Image ID is not returned")    
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            result = executor.map(image_build, values)




if __name__ == '__main__':
    main()

