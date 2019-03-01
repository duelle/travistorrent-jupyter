#!/usr/bin/env python

from os.path import isdir, isfile
from curses.ascii import isprint
from shutil import copy2,move
import os
import re
import glob
import tarfile
import tempfile
import concurrent.futures
import time

project_dir = "/run/media/duelle/54d52ebe-c232-4b11-a60f-e62374a99090/travistorrent/buildlogs/20-12-2016"
result_dir = "/run/media/duelle/54d52ebe-c232-4b11-a60f-e62374a99090/travistorrent/extracted"
target_dir = "/tmp/tt"
regex1c = re.compile(r'\x1B\[(([0-9]{1,2})?(;)?([0-9]{1,2})?)?[m,K,H,f,J]')
rexex2c = re.compile(r'^M\n')

def process_project(src_file_name):
    with tempfile.TemporaryDirectory() as temp_dir:
        if src_file_name.endswith(".tgz"):
            file_name = temp_dir + os.sep + src_file_name
            copy2(project_dir + os.sep + src_file_name, file_name)
            project_name = os.path.basename(file_name)[:-4] # remove file extension

            print(project_name + " started.")

            tar = tarfile.open(file_name)
            tar.extractall(path=temp_dir)
            parse_dir = temp_dir + os.sep + project_name + os.sep
            tar.close()
            listing = glob.glob(parse_dir + "*.log")

            header_line = "build_number;build_id;job_id;startup;step_firststart;step_lastend;diffduration;logaggregatedduration;worker_hostname;worker_version;worker_instance;os_dist_id;os_description;os_dist_release"

            log_file_name = target_dir + os.sep + "tt_" + project_name + ".csv"
            log_file_basename = os.path.basename(log_file_name)

            with open(log_file_name, "w") as out_log:
                out_log.write(header_line + "\n")

                for log_file in listing:
                    filename_parts = os.path.basename(log_file)[:-4].split('_')
                    build_number = filename_parts[0]
                    build_id = filename_parts[1]
                    job_id = filename_parts[3]

                    log_result = parse_log(sanitize_log(log_file), build_id, project_name)
                    if log_result != "":
                        out_log.write(str(build_number) + ";"
                                      + str(build_id) + ";"
                                      + str(job_id) + ";"
                                      + log_result + "\n")

            move(log_file_name, result_dir + os.sep + log_file_basename)
            print(project_name + " finished.")


def sanitize_log(log_file):
    out_string = ""
    with open(log_file) as f:
        for line in f.readlines():

            out = line
            out = regex1c.sub('', out)
            out = rexex2c.sub('', out)
            out = "".join(filter(isprint, out))
            if out != "":
                out_string += out + '\n'
        #print(out_string)
    return out_string


def split_end_line(line):
    timings = line.split(':')[3]

    start_timings = timings.split(',')[0]
    start_value = start_timings.split('=')[1]

    finish_timings = timings.split(',')[1]
    finish_value = finish_timings.split('=')[1]

    duration_timings = timings.split(',')[2]
    duration_value = duration_timings.split('=')[1]

    return start_value + ";" + finish_value + ";" + duration_value


def parse_log(log, build_id, project_name):

    result_line = ""
    detailed_steps = False

    startup = ''
    worker_hostname = ''
    worker_version = ''
    worker_instance = ''
    os_dist_id = ''
    os_dist_release = ''
    os_description = ''

    step_list = []

    first_start_timing = 0
    last_end_timing = 0
    total_log_duration = 0

    # Indicates whether the next line will be a travis command (command to execute)
    ttcmd_coming = False
    os_details_coming = False
    worker_details_coming = False

    incomplete_command = ""


    for line in log.splitlines():

        # record startup time
        if line.startswith("startup:"):
            startup = line.split(' ')[1]

        if line.startswith("Operating System Details"):
            os_details_coming = True
            worker_details_coming = False

        if os_details_coming:
            if line.startswith("Description:"):
                os_description = line.split(":")[1]
            if line.startswith("Distributor ID:"):
                os_dist_id = line.split(":")[1]
            if line.startswith("Release:"):
                os_dist_release = line.split(":")[1]

        if line.startswith("Worker information"):
            worker_details_coming = True

        if worker_details_coming:
            # record hostname
            if line.startswith("hostname:"):
                worker_hostname = line.split(' ')[1]

            if line.startswith("version:"):
                worker_version = " ".join(line.split(' ')[1:])

            if line.startswith("instance:"):
                worker_instance = line.split(' ')[1]


        # record travis command and remove flag
        elif ttcmd_coming:
            incomplete_command = line
            ttcmd_coming = False

        # after each travis_time:start there is a travis command following
        elif line.startswith("travis_time:start"):
            ttcmd_coming = True
            os_details_coming = False

        # travis_time:end contains timing information for that travis_time block
        elif line.startswith("travis_time:end"):
            timings = split_end_line(line)
            if incomplete_command != "":
                step_list.append(timings + ';' + incomplete_command + '\n')
                incomplete_command = ""

            if first_start_timing == 0:
                first_start_timing = timings.split(';')[0]

            last_end_timing = timings.split(';')[1]

            total_log_duration += int(timings.split(';')[2])

    # If there was at least one step, record information for it
    if len(step_list) > 0:

        result_list = [str(startup),first_start_timing,last_end_timing,str(int(last_end_timing) - int(first_start_timing)),str(total_log_duration),worker_hostname,worker_version,worker_instance,os_dist_id,os_description,os_dist_release]
        result_line = ";".join(result_list)
        #result_line = str(startup) + ";" + first_start_timing + ";" + last_end_timing + ";" + str(int(last_end_timing) - int(first_start_timing)) + ";" + str(total_log_duration) + ";" + str(worker_hostname)

        # In case we want to have all details on the steps executed in the build, set detailed_steps to True.
        if detailed_steps:
            with open(target_dir + os.sep + "tt_" + project_name + "_" + build_id + ".csv", "w") as out_log:
                if startup == "":
                    startup = 0
                else:
                    out_log.write(startup + '\n')

                out_log.write(''.join(step_list) + '\n')

                out_log.write("startup;firststart;lastend;diffduration;logaggregatedduration" + "\n")
                out_log.write(result_line)

    return result_line


if __name__ == '__main__':
    '''
    Traverses all tgz-files in the given folder and calls following process command.
    :param project_folder: folder that contains all project logs in tgz format
    :return: nothing
    '''
    parallel_enabled = True
    start_time = time.time()

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    if parallel_enabled:
        with concurrent.futures.ProcessPoolExecutor(max_workers=7) as executor:
            for tar_file in os.listdir(project_dir):
                if isdir(project_dir) and isfile(project_dir + os.sep + tar_file) and tar_file.endswith(".tgz"):
                    executor.submit(process_project,tar_file)

    else:
        for tar_file in os.listdir(project_dir):
            if isdir(project_dir) and isfile(project_dir + os.sep + tar_file) and tar_file.endswith(".tgz"):
                process_project(tar_file)

    end_time = time.time()
    print("Done in %s" % (end_time - start_time))


