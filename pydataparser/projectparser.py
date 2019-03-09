#!/usr/bin/env python

# TODO:
# - fix UTC issue: database/dateissue.txt
# - create DDL for extracted data
# - run through all logs and import them into the database (repo-data, buildlog, extracted)


from os.path import isdir, isfile
from curses.ascii import isprint
from shutil import copy2,move,copyfileobj
import os
import re
import glob
import tarfile
import tempfile
import concurrent.futures
import time
from datetime import timedelta

# If set to true, the results will be stored in /tmp/ directory instead of externally
local_test = False

# We skip projects that have been extracted already. If they should be overwritten instead, set this to True
overwrite_enabled = False

# Parallel execution enabled
parallel_enabled = True

# Number of parallel workers (in case parallel execution is enabled
max_parallel_workers = 8

if local_test:
    extdisk_path = "/tmp/tt_test/travistorrent"
else:
    extdisk_path = "/run/media/duelle/54d52ebe-c232-4b11-a60f-e62374a99090/travistorrent"

project_dir = extdisk_path + os.sep + "buildlogs/20-12-2016"
result_dir =  extdisk_path + os.sep + "extracted"

buildlog_path = result_dir + os.sep + "buildlogs"
buildlog_file = "buildlog-data-travis.csv"

repodata_path = result_dir + os.sep + "repodata"
repodata_file = "repo-data-travis.csv"

extracteddata_path = result_dir + os.sep + "extracteddata"

# Directory where unpacking and parsing is done (best-case in memory)
temporary_dir = "/tmp/tt"

# Regexes for removing color coding from travis log files
regex1c = re.compile(r'\x1B\[(([0-9]{1,2})?(;)?([0-9]{1,2})?)?[m,K,H,f,J]')
rexex2c = re.compile(r'^M\n')

# Regex used for parsing duration time format used for 'startup' field
duration_regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?((?P<milliseconds>\d+?)ms)?')


def process_project(src_file_name):

    # Make sure input file is a .tgz file
    if src_file_name.endswith(".tgz"):

        # Deduct project name from the file name without file type extension
        project_name = os.path.basename(src_file_name)[:-4]  # remove file extension

        project = project_name.replace('@','/')


        temp_log_file_name = temporary_dir + os.sep + "tt_" + project_name + ".csv"
        log_file_basename = os.path.basename(temp_log_file_name)

        target_log_file = extracteddata_path + os.sep + log_file_basename

        if os.path.isfile(target_log_file) and not overwrite_enabled:
            print(project_name + " skipped (exists).")

        else:
            print(project_name + " started.")

            with tempfile.TemporaryDirectory() as temp_dir:
                file_name = temp_dir + os.sep + src_file_name

                parse_dir = temp_dir + os.sep + project_name

                copy2(project_dir + os.sep + src_file_name, file_name)

                tar = tarfile.open(file_name)
                tar.extractall(path=temp_dir)
                tar.close()

                log_listing = glob.glob(parse_dir + os. sep + "*.log")

                header_line = "build_number;" +\
                              "build_id;" + \
                              "project;" + \
                              "commit_hash;" +\
                              "job_id;" +\
                              "startup_duration_seconds;" +\
                              "step_first_start_timestamp;" +\
                              "step_last_end_timestamp;" +\
                              "duration_diff_timestamp;" +\
                              "duration_aggregated_timestamp;" +\
                              "worker_hostname;" +\
                              "worker_version;" +\
                              "worker_instance;" +\
                              "os_dist_id;" +\
                              "os_description;" +\
                              "os_dist_release"

                with open(temp_log_file_name, "w") as out_log:
                    out_log.write(header_line + "\n")

                    for log_file in log_listing:
                        filename_parts = os.path.basename(log_file)[:-4].split('_')
                        build_number = filename_parts[0]
                        build_id = filename_parts[1]
                        commit_hash = filename_parts[2]
                        job_id = filename_parts[3]

                        log_result = parse_log(sanitize_log(log_file), build_id, project_name)
                        if log_result != "":
                            out_log.write(str(build_number) + ";"
                                          + str(build_id) + ";"
                                          + str(project) + ";"
                                          + str(commit_hash) + ";"
                                          + str(job_id) + ";"
                                          + log_result + "\n")

                # Move result log file to target folder
                move(temp_log_file_name, target_log_file)

                # Copy project-level buildlogs
                buildlog_file_path = parse_dir + os.sep + buildlog_file
                if os.path.isfile(buildlog_file_path):
                    copy2(buildlog_file_path, buildlog_path + os.sep + project_name + "_" + buildlog_file)
                else:
                    print(project_name + " has no buildlog file.")

                # Copy project-level repodata
                repodata_file_path = parse_dir + os.sep + repodata_file
                if os.path.isfile(repodata_file_path):
                    copy2(repodata_file_path, repodata_path + os.sep + project_name + "_" + repodata_file)
                else:
                    print(project_name + " has no repodata file.")

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

    step_first_start_timestamp = 0
    step_last_end_timestamp = 0
    duration_aggregated_timestamp = 0

    # Indicates whether the next line will be a travis command (command to execute)
    ttcmd_coming = False
    os_details_coming = False
    worker_details_coming = False

    incomplete_command = ""

    for line in log.splitlines():

        # record startup time
        if line.startswith("startup:"):
            startup = parse_time(line.split(' ')[1])

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

        # Record travis command and remove flag
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

            if step_first_start_timestamp == 0:
                step_first_start_timestamp = timings.split(';')[0]

            step_last_end_timestamp = timings.split(';')[1]

            duration_aggregated_timestamp += int(timings.split(';')[2])

    # If there was at least one step, record information for it
    if len(step_list) > 0:

        result_list = [str(startup),
                       step_first_start_timestamp,
                       step_last_end_timestamp,
                       str(int(step_last_end_timestamp) - int(step_first_start_timestamp)),
                       str(duration_aggregated_timestamp),
                       worker_hostname,
                       worker_version,
                       worker_instance,
                       os_dist_id,
                       os_description,
                       os_dist_release]
        result_line = ";".join(result_list)

        # In case we want to have all details on the steps executed in the build, set detailed_steps to True.
        if detailed_steps:
            temp_build_details_file =  "tt_" + project_name + "_" + build_id + ".csv"
            with open(temporary_dir + os.sep + temp_build_details_file, "w") as out_log:

                out_log.write(startup + '\n')
                out_log.write(''.join(step_list) + '\n')

                out_log.write("startup;step_first_start_timestamp;step_last_end_timestamp;duration_diff_timestamp;duration_aggregated_timestamp" + "\n")
                out_log.write(result_line)

    return result_line


def merge_csv_files(folder):
    header_added = False
    if os.path.isdir(folder):
        target_name = os.path.basename(folder)
        csv_listing = glob.glob(folder + os.sep + "*.csv")
        if len(csv_listing) > 0:
            with open(result_dir + os.sep + "0_" + target_name + ".csv", 'wb') as outfile:
                for file in csv_listing:
                    with open(file, 'rb') as infile:
                        if header_added:
                            infile.__next__()
                        else:
                            header_added = True
                        copyfileobj(infile, outfile)


# Adopted from https://stackoverflow.com/a/4628148
def parse_time(time_str):
    parts = duration_regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}

    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params).seconds


if __name__ == '__main__':
    '''
    Traverses all tgz-files in the given folder and calls following process command.
    :param project_folder: folder that contains all project logs in tgz format
    :return: nothing
    '''
    start_time = time.time()

    if not os.path.exists(temporary_dir):
        os.makedirs(temporary_dir)

    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    if not os.path.exists(buildlog_path):
        os.makedirs(buildlog_path)

    if not os.path.exists(repodata_path):
        os.makedirs(repodata_path)

    if not os.path.exists(extracteddata_path):
        os.makedirs(extracteddata_path)

    if parallel_enabled:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_parallel_workers) as executor:
            for tar_file in os.listdir(project_dir):
                if isdir(project_dir) and isfile(project_dir + os.sep + tar_file) and tar_file.endswith(".tgz"):
                    executor.submit(process_project,tar_file)
    else:
        for tar_file in os.listdir(project_dir):
            if isdir(project_dir) and isfile(project_dir + os.sep + tar_file) and tar_file.endswith(".tgz"):
                process_project(tar_file)

    if parallel_enabled:
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_parallel_workers) as executor:
            for csv_folder in [buildlog_path, repodata_path, extracteddata_path]:
                merge_csv_files(csv_folder)
    else:
        for csv_folder in [buildlog_path, repodata_path, extracteddata_path]:
            merge_csv_files(csv_folder)

    end_time = time.time()
    print("Done in %s" % (end_time - start_time))
