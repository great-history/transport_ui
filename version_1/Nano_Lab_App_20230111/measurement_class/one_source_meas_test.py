import pyvisa
import os, time

import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.lines as line

from instrument_class.My_YokogawaGS200 import *
from utilities.utility_package import *
from measurement_class.one_source_meas_class import *
from pyqtgraph.Qt import QtGui, QtCore

# # 设置画布尺寸
# plt.figure(figsize=(11, 5.6))

# # 调整画布里图像的位置
# plt.subplots_adjust(top=0.88,
# 				bottom=0.11,
# 				left=0.11,
# 				right=0.9,
# 				hspace=0.2,
# 				wspace=0.2)
# # 使图像在画布上尽可能大，贴着画布边缘
# plt.tight_layout()

# # tight_layout 调整子图之间及其周围的填充。
# fig = plt.figure(tight_layout=True)
# plt.savefig("sin_test1.png")


if __name__ == "__main__":
    # ####################################################################################################
    # #################### 用户输入
    # ########## 第一个样品的测试信息
    # sample_name = "sample32"
    # test_name = "one_gate_test"
    # user_name = "Shijie Fang"
    # # user_email = "12132836@mail.sustech.edu.cn"
    # user_email = "ff335192289@qq.com"
    # user_info = {"sample_name":sample_name, "test_name":test_name, "user_name":user_name, "user_email":user_email}
    #
    # ########## 仪器地址/仪器类型/仪器名称
    # source_obj_list = []
    #
    # rm = pyvisa.ResourceManager()
    # names = rm.list_resources()
    # print(names)
    #
    # [SR830_addr_list, Keithley2400_addr_list, YokogawaGS200_addr_list] = sort_instr(names)
    # print(YokogawaGS200_addr_list)
    #
    # ########## 测试参数:测试range/有几步/起始点/终止点/速率
    # source_name_list = ["top"]
    # source_mode_list = ["voltage"]
    # source_bound_list = [(-5, 5)]
    # interval_pause_list = [0.02]
    # slope_slow_list = [0.005]
    # slope_fast_list = [0.02]
    # slope_list = [[0.005, 0.02]]
    #
    # test_range_list = []
    # num_levels = np.random.randint(8, 16)
    #
    # start_level = np.random.uniform(-3, 1)
    # end_level = np.random.uniform(2, 5)
    # str_test_range = str(start_level) + "," + str(end_level) + "," + str(num_levels)
    # test_range_list.append(str_test_range)
    # tol_list = [0.0001]
    #
    # target_levels_list, scan_steps_list = get_scan_steps_array(num_levels, start_level, end_level, slope_list[0][0])
    # print(target_levels_list)
    #
    # ########## 文件路径
    # sourcefile_list = []
    # test_time = get_time_list(time.localtime(time.time()))
    # root_path = os.getcwd()
    # data_forward_file_path = get_datfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
    #                                           instr_name=source_name_list[0], scan_direction="forward",
    #                                           root_path=root_path)
    #
    # data_backward_file_path = get_datfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
    #                                            instr_name=source_name_list[0], scan_direction="backward",
    #                                            root_path=root_path)
    #
    # info_file_path = get_info_txtfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
    #                                        root_path=root_path)
    # path_list = [data_forward_file_path, data_backward_file_path]
    # sourcefile_list.append(path_list)
    #
    # write_info_txtfile_header(info_file_path, sample_name, test_name, user_name, user_email, True)
    # write_source_info2txtfile(info_file_path, source_name_list, YokogawaGS200_addr_list[0], source_bound_list,
    #                           test_range_list, slope_list, sourcefile_list)
    # start_info_txtfile(info_file_path, test_time)
    #
    # print(test_time)
    # print(data_forward_file_path)
    # print(data_backward_file_path)
    # print(info_file_path)
    #
    # ####################################################################################################
    # ########## 测试之前的预备
    # #################### 定义global variables
    # source_fast_obj = My_YokogawaGS200(YokogawaGS200_addr_list[0], source_name_list[0], source_mode_list[0],
    #                                    interval_pause_list[0],
    #                                    tol_list[0], target_levels_list, scan_steps_list, path_list, flag_back=False)
    # source_obj_list.append(source_fast_obj)
    # one_gate_test_obj = one_source_meas_class(source_obj=source_fast_obj, slope_fast=slope_list[0][1],
    #                                           user_info=user_info)
    #
    # #################### 开始测试
    # start = time.time()
    #
    # one_gate_test_obj.create_FuncAnimation_obj(interval_pause=500)
    #
    # # 为数据更新函数单独创建一个线程，与图像绘制的线程并发执行
    # t = one_gate_test_obj.create_single_meas_thread(scan_repeat=3, stop_level=0.0, flag_back=False, flag_rewrite=True)
    # t.start()  # 线程执行
    # plt.show()  # plt.show()一定要放在start之后, 否则不能实现同步
    # t.join()
    #
    # end = time.time()
    # print("single thread cost : ", end - start, " seconds")

    ####################################################################################################
    ############################## 多线程测试 + FuncAnimation
    ####################################################################################################
    #################### 用户输入
    ########## 三个样品的测试信息
    sample_name = "sample32"
    test_name = "one_gate_test"
    user_name = "Shijie Fang"
    user_email = "ff335192289@qq.com"
    user_info = {"sample_name": sample_name, "test_name": test_name, "user_name": user_name, "user_email": user_email}

    ########## 仪器地址/仪器类型/仪器名称
    source_obj_list = []

    rm = pyvisa.ResourceManager()
    names = rm.list_resources()
    print(names)

    [SR830_addr_list, Keithley2400_addr_list, YokogawaGS200_addr_list] = sort_instr(names)
    print(YokogawaGS200_addr_list)
    num_YokogawaGS200 = len(YokogawaGS200_addr_list)

    ########## 测试参数:测试range/有几步/起始点/终止点/速率
    source_name_list = ["top_gate", "bottom_gate", "dc_bias"]
    source_mode_list = ["voltage", "voltage", "voltage"]
    source_bound_list = [(-5, 5), (-5, 5), (-5, 5)]
    interval_pause_list = [0.02, 0.02, 0.02]
    slope_slow_list = [0.005, 0.005, 0.005]
    slope_fast_list = [0.02, 0.02, 0.02]
    slope_list = [[0.005, 0.02], [0.005, 0.02], [0.005, 0.02]]
    tol_list = [0.0001, 0.0001, 0.0001]
    test_range_list = []
    target_levels_list_list = []
    scan_steps_list_list = []
    for i in range(num_YokogawaGS200):
        num_levels = np.random.randint(8, 16)
        start_level = np.random.uniform(-3, 1)
        end_level = np.random.uniform(2, 5)
        str_test_range = str(start_level) + "," + str(end_level) + "," + str(num_levels)
        test_range_list.append(str_test_range)

        target_levels_list, scan_steps_list = get_scan_steps_array(num_levels, start_level, end_level, slope_list[0][0])
        print(target_levels_list)
        target_levels_list_list.append(target_levels_list)
        scan_steps_list_list.append(scan_steps_list)

    ########## 文件路径
    sourcefile_list = []
    test_time = get_time_list(time.localtime(time.time()))
    root_path = os.getcwd()
    info_file_path = get_info_txtfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time, root_path=root_path)
    write_info_txtfile_header(info_file_path, sample_name, test_name, user_name, user_email, True)

    for i in range(num_YokogawaGS200):
        data_forward_file_path = get_datfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
                                                  instr_name=source_name_list[i], scan_direction="forward",
                                                  root_path=root_path)

        data_backward_file_path = get_datfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
                                                   instr_name=source_name_list[i], scan_direction="backward",
                                                   root_path=root_path)

        path_list = [data_forward_file_path, data_backward_file_path]
        sourcefile_list.append(path_list)

    write_source_info2txtfile(info_file_path, source_name_list, YokogawaGS200_addr_list, source_bound_list,
                              test_range_list, slope_list, sourcefile_list)

    start_info_txtfile(info_file_path, test_time)

    print(test_time)
    print(data_forward_file_path)
    print(data_backward_file_path)
    print(info_file_path)

    ####################################################################################################
    ############################## 开始测试
    one_source_test_list = []
    for i in range(num_YokogawaGS200):
        source_obj = My_YokogawaGS200(YokogawaGS200_addr_list[i], source_name_list[i], source_mode_list[i],
                                      interval_pause_list[i], tol_list[i], target_levels_list_list[i],
                                      scan_steps_list_list[i],
                                      sourcefile_list[i], flag_back=False)
        one_source_test_obj = one_source_meas_class(source_obj=source_obj, slope_fast=slope_list[i][1],
                                                    user_info=user_info)
        one_source_test_list.append(one_source_test_obj)

    # 开始计时
    start = time.time()

    # 动画
    for i in range(num_YokogawaGS200):
        one_source_test_list[i].create_FuncAnimation_obj(interval_pause=50)

    # 为数据更新函数单独创建一个线程，与图像绘制的线程并发执行
    multi_threads = []
    for i in range(num_YokogawaGS200):
        t = one_source_test_list[i].create_single_meas_thread(scan_repeat=10, stop_level=0.0, flag_back=False, flag_rewrite=True)
        multi_threads.append(t)

    for thread in multi_threads:
        thread.daemon = True
        thread.start()

    plt.show()  # plt.show()一定要放在start之后, 否则不能实现同步； plt.show()是把所有的figure都显示出来

    for thread in multi_threads:
        thread.join()

    end = time.time()
    print("single thread cost : ", end - start, " seconds")