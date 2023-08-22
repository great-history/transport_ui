import os
import re
import numpy as np

from instrument_class.My_YokogawaGS200 import *
from instrument_class.My_Keithley2400 import *
from instrument_class.My_SR830 import *
from instrument_class.My_AMI430 import *
from instrument_class.My_Ametek7270 import *


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
    # print(time_)
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


def get_info_jsonfile_path(sample_name: str, test_name: str, test_time: list, root_path: str = os.getcwd()):
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

    file_path = sample_test_time_path + "\\" + "test_info" + '.json'

    return file_path


def get_fig_save_path(datfile_path: str):
    datfile_path_split = datfile_path.split('\\')

    figsave_path = "\\".join(datfile_path_split[0:-1]) + "\\" + datfile_path_split[-1].split(".dat")[0] + "_fig_save"
    if not os.path.exists(figsave_path):
        os.makedirs(figsave_path)

    return figsave_path


def get_scan_steps_array(num_levels, start_level, end_level, slope):
    ####################################################################################################
    ##########  得到在测量过程中的步数
    target_levels_list = np.linspace(start_level, end_level, num_levels)
    scan_steps_list = []

    for i in range(1, num_levels):
        steps = int(abs((target_levels_list[i] - target_levels_list[i - 1]) / slope) + 1)
        scan_steps_list.append(steps)

    return target_levels_list, scan_steps_list


def get_scan_step_list(target_level_list: list, num_levels: int, slope: float):
    ####################################################################################################
    ##########  得到在测量过程中的步数
    scan_steps_list = []

    for i in range(1, num_levels):
        steps = int(abs((target_level_list[i] - target_level_list[i - 1]) / slope) + 1)
        scan_steps_list.append(steps)

    return scan_steps_list


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

    else:  # scan_direction == "scan_slow":
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
        "{: >6}{: >16}{: >16}{: >16}{: >16}".format('index', 'X', 'Y', 'R', 'Theta'))
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


def write_scan_datfile_header(datfile_path: str, rewrite: bool):
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
    file_IO.write("{: >6}{: >16}{: >16}{: >16}".format('index', 'read', 'error', 'leak'))
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


def write_mf_info2txtfile(txtfile_path: str, mf_name_list: list, mf_addr_list: list,
                          test_range_list: list, slope_list: list,
                          mffile_list: list):  ## 测试相关的信息
    ####################################################################################################
    ########## 打开一个文件写入测试信息
    file_IO = open(txtfile_path, 'a+')

    for i in range(len(mf_name_list)):
        file_IO.write('source name : {}\n'.format(mf_name_list[i]))
        file_IO.write('source addr : {}\n'.format(mf_addr_list[i]))
        file_IO.write('test range : {}\n'.format(test_range_list[i]))
        file_IO.write('slow slope : {}\n'.format(slope_list[i][0]))
        file_IO.write('fast slope : {}\n'.format(slope_list[i][1]))

        file_IO.write('file path : {}\n'.format(mffile_list[i]))
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
    for index, source_obj in enumerate(my_source_obj_list):
        source_obj.fileIO_list = []


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


def get_source_obj_by_dict(source_info_dict: dict, flag_init: bool = True):
    if source_info_dict["source_type"] == 'YokogawaGS200':
        YokogawaGS200_addr = source_info_dict["source_addr"]
        source_name = source_info_dict["source_name"]
        source_mode = source_info_dict["source_mode"]
        interval_pause = source_info_dict["interval_pause"]
        tol = source_info_dict["tol"]
        path_list = source_info_dict["path_list"]
        flag_back = source_info_dict["flag_back"]
        slope_fast = source_info_dict["slope_fast"]

        target_level_list = []
        for item in source_info_dict["target_level_list"]:
            if type(item) == tuple or type(item) == list:
                target_level_list.extend(np.linspace(item[0], item[1], item[2]))
            else:
                target_level_list.append(item)
        scan_steps_list = get_scan_step_list(target_level_list=target_level_list, num_levels=len(target_level_list),
                                             slope=source_info_dict["slope_slow"])

        source_obj = My_YokogawaGS200(YokogawaGS200_addr=YokogawaGS200_addr, source_name=source_name,
                                      source_mode=source_mode, interval_pause=interval_pause, tol=tol,
                                      target_levels_list=target_level_list, scan_steps_list=scan_steps_list,
                                      slope_fast=slope_fast, path_list=path_list, flag_back=flag_back,
                                      flag_init=flag_init)
        return source_obj

    elif source_info_dict["source_type"] == 'Keithley2400':
        Keithley2400_addr = source_info_dict["source_addr"]
        source_name = source_info_dict["source_name"]
        source_mode = source_info_dict["source_mode"]
        interval_pause = source_info_dict["interval_pause"]
        tol = source_info_dict["tol"]
        path_list = source_info_dict["path_list"]
        flag_back = source_info_dict["flag_back"]
        slope_fast = source_info_dict["slope_fast"]

        target_level_list = []
        for item in source_info_dict["target_level_list"]:
            if type(item) == tuple or type(item) == list:
                target_level_list.extend(np.linspace(item[0], item[1], item[2]))
            else:
                target_level_list.append(item)

        scan_steps_list = get_scan_step_list(target_level_list=target_level_list, num_levels=len(target_level_list),
                                             slope=source_info_dict["slope_slow"])

        source_obj = My_Keithley2400(Keithley2400_addr=Keithley2400_addr, source_name=source_name,
                                     source_mode=source_mode, interval_pause=interval_pause, tol=tol,
                                     target_levels_list=target_level_list, scan_steps_list=scan_steps_list,
                                     slope_fast=slope_fast, path_list=path_list, flag_back=flag_back,
                                     flag_init=flag_init)
        return source_obj


def get_lockin_obj_by_dict(lockin_info_dict: dict, flag_init: bool = True):
    if lockin_info_dict["lockin_type"] == 'SR830':
        SR830_addr = lockin_info_dict["lockin_addr"]
        lockin_name = lockin_info_dict["lockin_name"]

        voltage = lockin_info_dict["voltage"]
        phase = lockin_info_dict["phase"]
        frequency = lockin_info_dict["frequency"]

        interval_pause = lockin_info_dict["interval_pause"]

        terminal_io = lockin_info_dict["terminal_io"]
        I_ac = lockin_info_dict["I_ac"]

        check_ch = lockin_info_dict["check_ch"]
        tol = lockin_info_dict["tol"]

        path_list = lockin_info_dict["path_list"]
        flag_back = lockin_info_dict["flag_back"]

        lockin_obj = My_SR830(SR830_addr=SR830_addr, lockin_name=lockin_name,
                              voltage=voltage, phase=phase, frequency=frequency,
                              interval_pause=interval_pause, terminal_io=terminal_io, I_ac=I_ac, check_ch=check_ch,
                              tol=tol, path_list=path_list, flag_back=flag_back, flag_init=flag_init)
        return lockin_obj
    elif lockin_info_dict["lockin_type"] == "Ametek7270":
        Ametek7270_addr = lockin_info_dict["lockin_addr"]
        lockin_name = lockin_info_dict["lockin_name"]

        voltage = lockin_info_dict["voltage"]
        phase = lockin_info_dict["phase"]
        frequency = lockin_info_dict["frequency"]

        interval_pause = lockin_info_dict["interval_pause"]

        terminal_io = lockin_info_dict["terminal_io"]
        I_ac = lockin_info_dict["I_ac"]

        check_ch = lockin_info_dict["check_ch"]
        tol = lockin_info_dict["tol"]

        path_list = lockin_info_dict["path_list"]
        flag_back = lockin_info_dict["flag_back"]

        lockin_obj = My_Ametek7270(Ametek7270_addr=Ametek7270_addr, lockin_name=lockin_name,
                                   voltage=voltage, phase=phase, frequency=frequency,
                                   interval_pause=interval_pause, terminal_io=terminal_io, I_ac=I_ac, check_ch=check_ch,
                                   tol=tol, path_list=path_list, flag_back=flag_back, flag_init=flag_init)
        return lockin_obj


def get_mf_obj_by_dict(mf_info_dict: dict, flag_init: bool = True):
    if mf_info_dict["mf_type"] == 'AMI430':
        ami_addr = mf_info_dict["mf_addr"]
        mf_name = mf_info_dict["mf_name"]

        tol = mf_info_dict["tol"]
        path_list = mf_info_dict["path_list"]
        flag_back = mf_info_dict["flag_back"]
        ramp_field_rate = mf_info_dict["slope_slow"]
        last_level = mf_info_dict["last_level"]

        target_level_list = []
        for item in mf_info_dict["target_level_list"]:
            if type(item) == tuple or type(item) == list:
                target_level_list.extend(np.linspace(item[0], item[1], item[2]))
            else:
                target_level_list.append(item)

        mf_obj = My_AMI430(ami_addr=ami_addr, ami_name=mf_name, tol=tol, target_levels_list=target_level_list,
                           last_level=last_level, ramp_field_rate=ramp_field_rate, path_list=path_list,
                           flag_back=flag_back, flag_init=flag_init)
        return mf_obj


def coalesce_data_from_datfile_list(datfile_list: list, prefix_list: list):
    ########## 读取所有的数据
    data_list_list = []
    for file in datfile_list:
        with open(file, encoding='utf-8') as file_obj:
            data_list = file_obj.readlines()
            # print(data_list[-2])
            # print(data_list[0])
        data_list_list.append(data_list)
    # print(data_list_list)

    ########## 寻找最小长度
    num_point = len(data_list_list[0])
    for data_list in data_list_list:
        if num_point > len(data_list):
            num_point = len(data_list)

    print(num_point)

    ########## 合并所有的数据
    coalesce_data_list = []
    num_ch_list = []

    for i in range(2, num_point):
        coalesce_data = []
        for data_list in data_list_list:
            data_line = data_list[i]
            data_line = data_line.split("\n")[0]
            data_line_split = data_line.split(" ")
            # print(data_line_split)

            data_list = []
            for data in data_line_split:
                if data == '':
                    continue
                else:
                    data_list.append(float(data))

            coalesce_data.extend(data_list)

            if i == 2:
                num_ch_list.append(len(data_list))

        coalesce_data_list.append(coalesce_data)

    ########## 合并所有的名字
    name_list = []
    for index, data_list in enumerate(data_list_list):
        header = data_list[0]
        header = header.split("\n")[0]
        header_split = header.split(" ")

        count = 0
        for name in header_split:
            if count > num_ch_list[index]:
                break

            if name == '':
                continue
            else:
                count += 1
                name_list.append(prefix_list[index] + "-" + name)

    ########## 找到所有重复的index指标
    num_index_list = []
    for index, name in enumerate(name_list):
        if name == "index" and index != 0:
            num_index_list.append(index)
    print(num_index_list)

    ########## 把数据转置一下并且删去所有重复的index指标
    name_list_new = []
    num_ch = len(name_list) - len(num_index_list)
    coal_data_list = []
    for i in range(len(name_list)):
        if i in num_index_list:
            continue
        else:
            coal_data_ = []
            name_list_new.append(name_list[i])
            for j in range(num_point - 2):
                if coalesce_data_list[j] == []:
                    continue
                else:
                    coal_data_.append(coalesce_data_list[j][i])
            coal_data_list.append(coal_data_)

    return coal_data_list, name_list_new


def write_coalesce_file(datfile_list: list, prefix_list: list, direction: str = "forward"):
    ########## 得到合并的数据
    coal_data_list, name_list = coalesce_data_from_datfile_list(datfile_list, prefix_list)
    ########## 得到文件io
    coal_file_path_split = datfile_list[0].split('\\')

    cola_dat_file = "\\".join(coal_file_path_split[0:-1]) + "\\" + direction + "_all_in_one.dat"
    fileIO_coal = open(cola_dat_file, "w")

    ########## 写入channel name
    for name in name_list:
        if name == "index":
            fileIO_coal.write("{: >6}".format('index'))
        else:
            fileIO_coal.write("{: >20}".format(name))

    fileIO_coal.write("\n")

    ########## 写入数据
    num_ch = len(name_list)
    num_point = len(coal_data_list[0])
    for i in range(num_point):
        fileIO_coal.write("{: >15d}".format(int(coal_data_list[0][i])))
        for j in range(1, num_ch):
            fileIO_coal.write("{: >25.8f}".format(coal_data_list[j][i]))
        ########## 换行
        fileIO_coal.write("\n")

    fileIO_coal.close()
    return cola_dat_file

####################################################################################################
########## utilities (part V)

if __name__ == "__main__":
    import sys
    for i in range(len(sys.path)):
        print(sys.path[i])