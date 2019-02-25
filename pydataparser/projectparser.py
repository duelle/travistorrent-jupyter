#!/usr/bin/env python

from os.path import isdir, isfile
from curses.ascii import isprint
from shutil import copy2
import os
import re
import glob
import tarfile
import tempfile
import concurrent.futures
import time

target_dir = "/tmp/tt"
regex1c = re.compile(r'\x1B\[(([0-9]{1,2})?(;)?([0-9]{1,2})?)?[m,K,H,f,J]')
rexex2c = re.compile(r'^M\n')

def process_project(src_file_name):
    with tempfile.TemporaryDirectory() as tmp_dir:
        if src_file_name.endswith(".tgz"):
            file_name = tmp_dir + os.sep + src_file_name
            copy2(src_file_name, file_name)
            project_name = os.path.basename(file_name)[:-4] # remove file extension
            print(project_name + " started.")
            tar = tarfile.open(file_name)
            tar.extractall(path=tmp_dir)
            parse_dir = tmp_dir + os.sep + project_name + os.sep
            tar.close()
            listing = glob.glob(parse_dir + "*.log")

            with open(target_dir + os.sep + "tt_" + project_name + ".csv", "w") as out_log:
                out_log.write("startup;firststart;lastend;diffduration;logaggregatedduration\n")
                for log_file in listing:
                    build_id = os.path.basename(log_file).split('_')[0]
                    log_result = parse_log(sanitize_log(log_file), build_id, project_name)
                    if log_result != "":
                        out_log.write(build_id + ";" + log_result + "\n")
            #os.remove(file_name)
            print(project_name + " finished.")


def sanitize_log(log_file):
    out_string = ""
    with open(log_file) as f:
        for line in f.readlines():

            out = line

            #out = re.sub(r'\x1B\[(([0-9]{1,2})?(;)?([0-9]{1,2})?)?[m,K,H,f,J]', '', out)
            out = regex1c.sub('', out)

            #out = re.sub(r'^M\n', '', out)
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
    step_list = []

    first_start_timing = 0
    last_end_timing = 0
    total_log_duration = 0

    # Indicates whether the next line will be a travis command (command to execute)
    ttcmd_coming = False

    incomplete_command = ""

    for line in log.splitlines():

        # record startup time
        if line.startswith("startup:"):
            startup = line.split(' ')[1]

        # record travis command and remove flag
        elif ttcmd_coming:
            incomplete_command = line
            ttcmd_coming = False

        # after each travis_time:start there is a travis command following
        elif line.startswith("travis_time:start"):
            ttcmd_coming = True

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

        result_line = str(startup) + ";" + first_start_timing + ";" + last_end_timing + ";" + str(int(last_end_timing) - int(first_start_timing)) + ";" + str(total_log_duration)

        if detailed_steps:
            with open(target_dir + os.sep + "tt_" + project_name + "_" + build_id + ".csv", "w") as out_log:
                if startup == "":
                    startup = 0
                else:
                    out_log.write(startup + '\n')

                out_log.write(''.join(step_list) + '\n')

                out_log.write("startup;firststart;lastend;diffduration;logaggregatedduration\n")
                out_log.write(result_line)

    return result_line


if __name__ == '__main__':
    '''
    Traverses all tgz-files in the given folder and calls following process command.
    :param project_folder: folder that contains all project logs in tgz format
    :return: nothing
    '''

    start_time = time.time()

    project_folder = "/home/duelle/Repositories/git/travistorrent-jupyter/pydataparser"

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
        for tar_file in os.listdir(project_folder):
            if isdir(project_folder) and isfile(tar_file) and tar_file.endswith(".tgz"):
                executor.submit(process_project,tar_file)
                #process_project(tar_file)

    end_time = time.time()
    print("Done in %s" % (end_time - start_time))

