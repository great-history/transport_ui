import pyvisa
import pymeasure.instruments
import numpy as np
import os,time
import re


####################################################################################################
##########  utilities (part I)
def sort_instr(instr_names_list: list):
    SR830_addrs = []
    Keithley2400_addrs = []
    YokogawaGS200_addrs = []

    for name_ in instr_names_list:
        gpib_index, addr_index = find_instr_indexes(name_)

        new_name = "GPIB" + str(gpib_index) + "_" + str(addr_index) + "_INSTR"

        if addr_index >= 1 and addr_index <= 5:
            SR830_addrs.append(name_)
        elif addr_index >= 6 and addr_index <= 10:
            Keithley2400_addrs.append(name_)
        elif addr_index >= 11 and addr_index <= 15:
            YokogawaGS200_addrs.append(name_)

    return [SR830_addrs, Keithley2400_addrs, YokogawaGS200_addrs]


def find_instr_indexes(instr_name: str):
    gpib_pattern = re.compile(r'GPIB\d+')
    addr_pattern = re.compile(r'::\d+::')
    int_pattern = re.compile(r'(\d+)')

    gpib_index = re.findall(gpib_pattern, instr_name)
    gpib_index = re.findall(int_pattern, gpib_index[0])
    gpib_index = int(gpib_index[0])

    addr_index = re.findall(addr_pattern, instr_name)
    addr_index = re.findall(int_pattern, addr_index[0])
    addr_index = int(addr_index[0])

    return gpib_index, addr_index


def get_time_list(time_):  ## 这里要写成time_或其他名称，不要写成time,因为time已经是一个包了，这样会产生冲突
    print(time_)
    time_list = []
    time_list.append(time_.tm_year)
    time_list.append(time_.tm_mon)
    time_list.append(time_.tm_mday)
    time_list.append(time_.tm_hour)
    time_list.append(time_.tm_min)
    time_list.append(time_.tm_sec)

    return time_list


def get_datfile_path(sample_name: str, test_name: str, test_time: list, instr_name: str, scan_direction: str,
                     root_path: str = os.getcwd()):
    ####################################################################################################
    ########## 得到要保存文件的路径

    sample_path = root_path + "\\" + sample_name
    if not os.path.exists(sample_path):
        os.makedirs(sample_path)

    sample_test_path = sample_path + "\\" + test_name
    if not os.path.exists(sample_test_path):
        os.makedirs(sample_test_path)

    time = "{}-{}-{}_{}-{}-{}".format(test_time[0], test_time[1], test_time[2], test_time[3], test_time[4],
                                      test_time[5])
    sample_test_time_path = sample_test_path + "\\" + time
    if not os.path.exists(sample_test_time_path):
        os.makedirs(sample_test_time_path)

    file_path = sample_test_time_path + "\\" + instr_name + '_' + scan_direction + '.dat'

    return file_path


def get_info_txtfile_path(sample_name: str, test_name: str, test_time: list, root_path: str = os.getcwd()):
    ####################################################################################################
    ########## 保存一个任务中所有仪器的信息

    sample_path = root_path + "\\" + sample_name
    if not os.path.exists(sample_path):
        os.makedirs(sample_path)

    sample_test_path = sample_path + "\\" + test_name
    if not os.path.exists(sample_test_path):
        os.makedirs(sample_test_path)

    time = "{}-{}-{}_{}-{}-{}".format(test_time[0], test_time[1], test_time[2], test_time[3], test_time[4],
                                      test_time[5])
    sample_test_time_path = sample_test_path + "\\" + time
    if not os.path.exists(sample_test_time_path):
        os.makedirs(sample_test_time_path)

    file_path = sample_test_time_path + "\\" + "test_info" + '.txt'

    return file_path


def get_scan_steps_array(num_levels, start_level, end_level, slope):
    ####################################################################################################
    ##########  得到在测量过程中的步数
    target_levels_list = np.linspace(start_level, end_level, num_levels)
    scan_steps_list = []

    for i in range(1, num_levels):
        steps = int(abs((target_levels_list[i] - target_levels_list[i - 1]) / slope) + 1)
        scan_steps_list.append(steps)

    return target_levels_list, scan_steps_list


def get_full_scan_steps_array(num_levels: int, start_level: float, end_level: float, slope_slow: float,
                              init_level: float, slope_fast: float, scan_direction: str, ext_dims: int):
    ####################################################################################################
    ##########  得到scan_slow和scan_fast分别全部的步数
    target_levels_list, scan_steps_list = get_scan_steps_array(num_levels, start_level, end_level, slope_slow)

    if scan_direction == "scan_fast":
        full_scan_step_array = np.zeros((ext_dims, num_levels))  # 第一个指标是scan slow，第二个指标是scan fast
        for ii in range(ext_dims):
            if ii == 0:
                full_scan_step_array[ii, 0] = int(abs((start_level - init_level) / slope_fast) + 1)
            else:
                full_scan_step_array[ii, 0] = int(abs((start_level - end_level) / slope_fast) + 1)

            full_scan_step_array[ii, 1:num_levels] = scan_steps_list

    elif scan_direction == "scan_slow":
        full_scan_step_array = np.zeros((num_levels, ext_dims))  # 第一个指标是scan slow，第二个指标是scan fast
        full_scan_step_array[0, 0] = int(abs((start_level - init_level) / slope_fast) + 1)
        full_scan_step_array[1:num_levels, 0] = scan_steps_list

    return target_levels_list, full_scan_step_array


####################################################################################################
##########  utilities (part II)  ----------   文件相关
def write_lockin_datfile_header(datfile_path: str, rewrite: bool):
    ####################################################################################################
    ########## 如何rewrite == True则要重写dat文件
    if rewrite == True:
        if os.path.exists(datfile_path):
            os.remove(datfile_path)

    ####################################################################################################
    ########## 打开一个文件写入测试信息
    file_IO = open(datfile_path, 'w')
    ####################################################################################################
    ########## 写入文件头
    ####################################################################################################
    ########## 写入测试数据: 设置格式tplt，20代表间隔距离，可根据自己需要调整
    file_IO.write(
        "{: >6}{: >16}{: >16}{: >16}{: >16}{: >16}{: >16}".format('index', 'X', 'X_std', 'Y', 'Y_std', 'R', 'Theta'))
    file_IO.write("\n")
    file_IO.write('========== ========== ========== ========== ========== ==========\n')
    ####################################################################################################
    ########## 结束文件
    file_IO.close()


def write_source_datfile_header(datfile_path: str, rewrite: bool):
    ####################################################################################################
    ########## 如何rewrite == True则要重写dat文件
    if rewrite == True:
        if os.path.exists(datfile_path):
            os.remove(datfile_path)

    ####################################################################################################
    ########## 打开一个文件写入测试信息
    file_IO = open(datfile_path, 'w')
    ####################################################################################################
    ########## 写入文件头
    ####################################################################################################
    ########## 写入测试数据: 设置格式tplt，20代表间隔距离，可根据自己需要调整
    file_IO.write("{: >6}{: >16}{: >16}".format('index', 'read', 'error'))
    file_IO.write("\n")
    file_IO.write('========== ========== ========== ========== ========== ==========\n')
    ####################################################################################################
    ########## 结束文件
    file_IO.close()


def write_info_txtfile_header(txtfile_path: str, sample_name: str, test_name: str, user_name: str, user_email: str,
                              rewrite: bool):
    ####################################################################################################
    ########## 如何rewrite == True则要重写dat文件
    if rewrite == True:
        if os.path.exists(txtfile_path):
            os.remove(txtfile_path)

    ####################################################################################################
    ########## 打开一个文件写入测试信息
    file_IO = open(txtfile_path, 'w')
    ####################################################################################################
    ########## 写入文件头
    file_IO.write('author : Shijie Fang\n')
    file_IO.write('========== ========== ========== ========== ========== ==========\n')
    file_IO.write('sample name : {}\n'.format(sample_name))
    file_IO.write('test name : {}\n'.format(test_name))
    file_IO.write('user name : {}\n'.format(user_name))
    file_IO.write('user email : {}\n'.format(user_email))
    file_IO.write('========== ========== ========== ========== ========== ==========\n')
    ####################################################################################################
    ########## 结束文件
    file_IO.close()


def write_source_info2txtfile(txtfile_path: str, source_name_list: list, source_addr_list: list,
                              source_bound_list: list,  ## 源表仪器相关的信息(待补充)
                              test_range_list: list, slope_list: list,
                              sourcefile_list: list):  ## 测试相关的信息
    ####################################################################################################
    ########## 打开一个文件写入测试信息
    file_IO = open(txtfile_path, 'a+')

    for i in range(len(source_name_list)):
        file_IO.write('source name : {}\n'.format(source_name_list[i]))
        file_IO.write('source addr : {}\n'.format(source_addr_list[i]))
        file_IO.write('source bound : {}\n'.format(source_bound_list[i]))
        file_IO.write('test range : {}\n'.format(test_range_list[i]))
        file_IO.write('slow slope : {}\n'.format(slope_list[i][0]))
        file_IO.write('fast slope : {}\n'.format(slope_list[i][1]))

        file_IO.write('file path : {}\n'.format(sourcefile_list[i]))
        file_IO.write('========== ========== ========== ========== ========== ==========\n')

    file_IO.close()


def write_lockin_info2txtfile(info_file_path: str, lockin_name_list: list, lockin_addr_list: list, voltage_list: list,
                              phase_list: list, frequency_list: list, flag_average_list: list,
                              lockinfile_list: list):  ## 锁相仪器相关的信息(待补充)
    ####################################################################################################
    ########## 打开一个文件写入测试信息
    file_IO = open(info_file_path, 'a+')

    for i in range(len(lockin_name_list)):
        file_IO.write('lockin name : {}\n'.format(lockin_name_list[i]))
        file_IO.write('lockin addr : {}\n'.format(lockin_addr_list[i]))
        file_IO.write('lockin voltage : {}\n'.format(voltage_list[i]))
        file_IO.write('lockin phase : {}\n'.format(phase_list[i]))
        file_IO.write('lockin frequency : {}\n'.format(frequency_list[i]))
        file_IO.write('flag average : {}\n'.format(flag_average_list[i]))

        file_IO.write('file path : {}\n'.format(lockinfile_list[i]))
        file_IO.write('========== ========== ========== ========== ========== ==========\n')

    file_IO.close()


def end_info_txtfile(txtfile_path: str, status: str, test_time: list):
    ####################################################################################################
    ########## 打开一个文件用于读写。如果该文件已存在，文件指针将会放在文件的结尾。
    ########## 文件打开时会是追加模式。如果该文件不存在，创建新文件用于读写。
    file_IO = open(txtfile_path, 'a+')
    file_IO.write('end time : {}-{}-{} {}:{}:{}\n'.format(test_time[0], test_time[1], test_time[2],
                                                          test_time[3], test_time[4], test_time[5]))
    file_IO.write('test status : {}\n'.format(status))
    file_IO.close()


def start_info_txtfile(txtfile_path: str, test_time: list):
    file_IO = open(txtfile_path, 'a+')
    file_IO.write('start time : {}-{}-{} {}:{}:{}\n'.format(test_time[0], test_time[1], test_time[2],
                                                            test_time[3], test_time[4], test_time[5]))
    file_IO.close()


####################################################################################################
########## utilities (part IV)
########## files & obj initialization
def close_all_source_files_forward(my_source_obj_list: list):
    for index, source_obj in enumerate(my_source_obj_list):
        source_obj.fileIO_list[0].close()


def close_all_lockin_files_forward(my_lockin_obj_list: list):
    for index, lockin_obj in enumerate(my_lockin_obj_list):
        lockin_obj.fileIO_list[0].close()


def close_all_source_files_backward(my_source_obj_list: list):
    for index, source_obj in enumerate(my_source_obj_list):
        if source_obj.flag_back == True:
            source_obj.fileIO_list[1].close()


def close_all_lockin_files_backward(my_lockin_obj_list: list):
    for index, lockin_obj in enumerate(my_lockin_obj_list):
        lockin_obj.fileIO_list[1].close()


def close_all_source_files(my_source_obj_list: list):
    close_all_source_files_forward(my_source_obj_list)
    close_all_source_files_backward(my_source_obj_list)


def close_all_lockin_files(my_lockin_obj_list: list):
    close_all_lockin_files_forward(my_lockin_obj_list)
    close_all_lockin_files_backward(my_lockin_obj_list)


def init_worker_and_files(source_obj, flag_rewrite: bool):
    source_obj.init_worker()
    write_source_datfile_header(datfile_path=source_obj.path_list[0], rewrite=flag_rewrite)
    source_obj.fileIO_list.append(open(source_obj.path_list[0], 'a+'))

    if source_obj.flag_back == True:
        write_source_datfile_header(datfile_path=source_obj.path_list[1], rewrite=flag_rewrite)
        source_obj.fileIO_list.append(open(source_obj.path_list[1], 'a+'))