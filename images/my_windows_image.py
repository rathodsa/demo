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
import logging
from logging.handlers import TimedRotatingFileHandler

config = oci.config.from_file(file_location="oci-config.ini")
core_client = oci.core.ComputeClient(config)

#Logging
log_file_path = '/home/gitlab-runner/logs/'
log_file_name = "oci_windows.log"
#Logger config
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%m-%d-%Y %H:%M:%S')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
file_handler = logging.FileHandler(f"{log_file_path}/{log_file_name}")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
'''LOG_FORMAT = "[%(asctime)s] %(levelname)s %(threadName)s %(message)s"
formatter = logging.Formatter(LOG_FORMAT)
handler = TimedRotatingFileHandler(LOG_FILE_PATH + "on_prem.log",
                                   when='midnight',
                                   interval=1,
                                   backupCount=5, encoding='utf8')
handler.suffix = "%Y-%m-%d"
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)'''


def run_packer(command_to_run):
    packer_result = subprocess.run(command_to_run, stdout=subprocess.PIPE)
    return packer_result.stdout.decode("utf-8")


def run_checker(command_to_run):
    packer_result = subprocess.run(command_to_run, stdout=subprocess.PIPE)
    return packer_result


def terminate_instance(instance_id):
    command_to_run = ["sudo", "python", "ImageBuild/Windows/oci_compute_instance.py","--terminate", "--instance_ids",\
                      instance_id.strip(), "--config", oci-config.ini]
    packer_result = subprocess.run(command_to_run, stdout=subprocess.PIPE)
    return packer_result.returncode


def get_instance_ip(instance_output):
    serach_string = "Private"
    print(instance_output)
    print(type(instance_output))
    items = instance_output.split()
    return items[-1].strip()


def get_instance_id(instance_output):
    serach_string = "Id"
    print(instance_output)
    print(type(instance_output))
    items = instance_output.split()
    return items[15].strip()


def get_image_ocid(output):
    search_string = "ocid1.image"
    items = re.findall(f"^.*{search_string}.*$", output, re.MULTILINE)
    image_ocid = None
    print(items)
    for item in items[0].split():
        if search_string in item:
            image_ocid = item
            break
    return image_ocid


def prepare_variable_json_for_instance(build_type,os_version, custom_image):
    with open(f"/home/gitlab-runner/windows/{build_type}-instance/{build_type}_instance{os_version}.json", "r") as src:
        data_to_insert = json.load(src)
    data_to_insert[0]["image_id"] = custom_image
    with open(f"/home/gitlab-runner/windows/{build_type}-instance/{build_type}{os_version}_instance.json", "w") as dst:
        dst.write(json.dumps(data_to_insert))


def image_build(build_type,os_version):
    base_dir = "/home/gitlab-runner/windows/"
    logger.info(f"Image build starting with build_type: {build_type} and OS version is: {os_version}")
    log_fuse_json_data = {}
    target_json = f"{base_dir}/{build_type}/{build_type}{os_version}.json"
    log_fuse_json_data["Image_build_start_time"] = str(datetime.now())
    instance_creation_command = ["sudo", "python", "/home/gitlab-runner/oit-image-management-system/ImageBuild/Windows/oci_compute_instance.py", "--create_new",\
                                 "--json_file", target_json]
    initial_instance_output = run_packer(instance_creation_command)
    initial_instance_ip = get_instance_ip(initial_instance_output)
    logger.info(f"Instance created and the instance Ip is : {initial_instance_ip.strip()}")
    initial_instance_id = get_instance_id(initial_instance_output)
    logger.info(f"Created instance ID is : {initial_instance_id.strip()}")
    logger.info(f"sleeping after instance creation..")
    time.sleep(900)
    log_fuse_json_data["Machine_name"] = initial_instance_ip.strip()
    imaging_check_command = ["/usr/bin/pwsh", "-c", "import-module", "/scratch/native/packer_custom_image_windows/"\
                             "imagingcompleted.ps1",";","imagingcompleted", "-i", initial_instance_ip.strip()]
    image_creation_command = ["python", "/home/gitlab-runner/oit-image-management-system/ImageBuild/Windows/scripts/create_image.py", "--create", "--instance_id", \
                            initial_instance_id.strip(), "--compartment_id", "ocid1.compartment.oc1..aaaaaaaaeiu7adsx"\
                        "35aegxbrcsdix7yihrxrs5uzuyobwoeexbxy7leitqbq", "--display_name", f"{build_type}_{os_version}"]
    target_json = f"{base_dir}/{build_type}-instance/{build_type}{os_version}_instance.json"
    post_instance_command = ["sudo", "python", "/home/gitlab-runner/oit-image-management-system/ImageBuild/Windows/oci_compute_instance.py", "--create_new", \
                            "--json_file", target_json]
    print(imaging_check_command)
    for i in range(20):
        imaging_result = run_checker(imaging_check_command)
        print(f"Imaging result is : {imaging_result.stdout.decode('utf-8')}")
        print(imaging_result.returncode)
        if int(imaging_result.returncode) == 0:
            logger.info(f"Imaging file exist and creating the image. file checker status: {imaging_result}")
            time.sleep(1200)
            print("Imaging File exist and creating Image")
            custom_image_output = run_packer(image_creation_command)
            print(custom_image_output)
            custom_image = get_image_ocid(str(custom_image_output))
            print(custom_image)
            if custom_image:
                logger.info(f"Image created and the image OCID is : {custom_image}")
            else:
                logger.info(f"Image creation has errors")
                sys.exit(1)
            log_fuse_json_data["Image_build_end_time"] = str(datetime.now())
            prepare_variable_json_for_instance(build_type, os_version, custom_image.strip())
            time.sleep(300)
            log_fuse_json_data["validation_start_time"] = str(datetime.now())
            logger.info(f"Post instance creation started at {str(datetime.now())}")
            post_instance_output = run_packer(post_instance_command)
            post_instance_ip = get_instance_ip(post_instance_output)
            post_instance_id = get_instance_id(post_instance_output)
            instance_ready_check_command = ["/usr/bin/pwsh", "-c", "import-module","/scratch/native/packer_custom"\
                                            "_image_windows/instanceready.ps1", ";", "instanceready",\
                                            "-i", post_instance_ip.strip()]
            print("waiting for server to become reachable.sleeping")
            time.sleep(900)
            for i in range(20):
                instance_ready_result = run_checker(instance_ready_check_command)
                print(instance_ready_result)
                if int(instance_ready_result.returncode) == 0:
                    log_fuse_json_data["validation_end_time"] = str(datetime.now())
                    image_export_command = ["sudo", "python", "ImageBuild/Windows/scripts/create_image.py", "--export",\
                                            "--image_id", custom_image, "--bucket_name", "bucket-win-images",\
                                            "--display_name", f"{build_type}_{os_version}", "--namespace_name", "peo",\
                                            "--config", "oci-config.ini"]
                    export_result = run_checker(image_export_command)
                    if int(export_result) == 0:
                        logger.info(f"Image export completed and the status is : {export_result}")
                        log_fuse_json_data["image_export_time"] = str(datetime.now())
                        terminate_initial_instance = terminate_instance(initial_instance_id)
                        if int(terminate_initial_instance) == 0:
                            logger.info(f"Initial instance terminated: {initial_instance_ip}")
                        else:
                            logger.error(f"Terminating the instance had errors: {terminate_initial_instance}")
                        terminate_post_instance = terminate_instance(post_instance_id)
                        if int(terminate_post_instance) == 0:
                            logger.info(f"Post instance terminated: {post_instance_ip}")
                        else:
                            logger.error(f"Terminating post instance had errors: {terminate_post_instance}")
                else:
                    time.sleep(300)
                    logger.warning(f"Instance ready file doesnt exist.. trying after sleep time")
        else:
            time.sleep(1200)
            logger.warning(f"Imaging file doesnt exist, trying again after the sleep time..")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json_file', help="JSON file to be processed")
    args = parser.parse_args()
    if args.json_file:
        with open (args.json_file) as json_file_content:
            input_windows_data = json.load(json_file_content)
            build_type = input_windows_data['build_type']
            build_type = 'native'
            os_version = input_windows_data['os_version']
            os_version = '2012'
    build_type = 'native'
    os_version = '2012'
    image_build(build_type,os_version)
        # with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        #     f1 = executor.submit(image_build,build_type,os_version)
        #     f2 = executor.submit(image_build,build_type,os_version)
        #     f3 = executor.submit(image_build,build_type,os_version)
        #     f4 = executor.submit(image_build,build_type,os_version)
        #     f5 = executor.submit(image_build,build_type,os_version)
        #
        #     image_build(build_type,os_version)

if __name__ == '__main__':
    main()
