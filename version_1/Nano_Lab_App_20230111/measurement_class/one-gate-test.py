import pyvisa
import os, time

import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.lines as line

from instrument_class.My_YokogawaGS200 import *
from utilities.utility_package import *
from measurement_class.one_source_meas_class import *

# #################### 初始化图像函数
# def plot_init():
#     ax_value.add_line(line_value)
#     ax_error.add_line(line_error)
#     return line_value, line_error  # 必须加逗号,否则会报错（TypeError: 'Line2D' object is not iterable）
#
# #################### 更新图像(animation会不断调用此函数刷新图像，实现动态图的效果)
# def plot_update(i):
#     global source_obj_list  # source_obj_list为全局变量
#     global one_gate_test_obj
#
#     current_index = one_gate_test_obj.current_index
#     if one_gate_test_obj.current_index <= 0:
#         return line_value, line_error,
#
#     x_range = np.arange(0, one_gate_test_obj.current_index, 1)  # x轴的区间范围
#     if min(len(one_gate_test_obj.source_obj.level_bins_forward), len(one_gate_test_obj.source_obj.error_bins_forward)) < current_index:
#         return line_value, line_error,
#
#     values_copy = one_gate_test_obj.source_obj.level_bins_forward[0:current_index]  # 为避免线程不同步导致获取到的data在绘制图像时被更新，这里复制数据的副本，否则绘制图像的时候可能会出现x和y的数据维度不相等的情况
#     errors_copy = one_gate_test_obj.source_obj.error_bins_forward[0:current_index]
#     ax_value.set_xlim(0, one_gate_test_obj.current_index)  # 横坐标范围（横坐标的范围和刻度可根据数据长度更新）
#     ax_value.set_ylim(np.min(values_copy) - 0.001, np.max(values_copy) + 0.001)  # 横坐标范围（横坐标的范围和刻度可根据数据长度更新）
#     ax_value.set_title("one gate value test", fontsize=8)  # 设置title
#     line_value.set_xdata(x_range)  # 更新直线的数据
#     line_value.set_ydata(values_copy)  # 更新直线的数据
#     ax_error.set_xlim(0, current_index)  # 横坐标范围（横坐标的范围和刻度可根据数据长度更新）
#     ax_error.set_ylim(-0.001, 0.001)  # 横坐标范围（横坐标的范围和刻度可根据数据长度更新）
#     ax_error.set_title("one gate error test", fontsize=8)  # 设置title
#     line_error.set_xdata(x_range)  # 更新直线的数据
#     line_error.set_ydata(errors_copy)  # 更新直线的数据
#
#     # 大标题（若有多个子图，可为其设置大标题）
#     plt.suptitle('one-gate-multithread-test', fontsize=8)
#     # 重新渲染子图
#     # fig.canvas.draw()  # 必须加入这一行代码，才能更新title和坐标!!!
#     # ax_error.figure.canvas.draw()  # 必须加入这一行代码，才能更新title和坐标!!!
#
#     return line_value, line_error,  # 必须加逗号,否则会报错（TypeError: 'Line2D' object is not iterable）

# def gen():
#     global one_gate_test_obj
#     i = 0
#     while one_gate_test_obj.flag_stat == True:
#         i += 1
#         yield i

if __name__ == "__main__":
    ####################################################################################################
    ########## 用户输入
    ##########
    ########## 本次测试的信息
    sample_name = "sample32"
    test_name = "one_gate_test"
    user_name = "Shijie Fang"
    # user_email = "12132836@mail.sustech.edu.cn"
    user_email = "ff335192289@qq.com"
    user_info = {"sample_name":sample_name, "test_name":test_name, "user_name":user_name, "user_email":user_email}

    ########## 仪器地址/仪器类型/仪器名称
    source_obj_list = []

    rm = pyvisa.ResourceManager()
    names = rm.list_resources()
    print(names)

    [SR830_addr_list, Keithley2400_addr_list, YokogawaGS200_addr_list] = sort_instr(names)
    print(YokogawaGS200_addr_list)

    ########## 测试参数:测试range/有几步/起始点/终止点/速率
    source_name_list = ["top"]
    source_mode_list = ["voltage"]
    source_bound_list = [(-5, 5)]
    interval_pause_list = [0.02]
    slope_slow_list = [0.005]
    slope_fast_list = [0.02]
    slope_list = [[0.005, 0.02]]

    test_range_list = []
    num_levels = np.random.randint(8, 16)

    start_level = np.random.uniform(-3, 1)
    end_level = np.random.uniform(2, 5)
    str_test_range = str(start_level) + "," + str(end_level) + "," + str(num_levels)
    test_range_list.append(str_test_range)
    tol_list = [0.0001]

    target_levels_list, scan_steps_list = get_scan_steps_array(num_levels, start_level, end_level, slope_list[0][0])
    print(target_levels_list)

    ########## 文件路径
    sourcefile_list = []
    test_time = get_time_list(time.localtime(time.time()))
    root_path = os.getcwd()
    data_forward_file_path = get_datfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
                                              instr_name=source_name_list[0], scan_direction="forward",
                                              root_path=root_path)

    data_backward_file_path = get_datfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
                                               instr_name=source_name_list[0], scan_direction="backward",
                                               root_path=root_path)

    info_file_path = get_info_txtfile_path(sample_name=sample_name, test_name=test_name, test_time=test_time,
                                           root_path=root_path)
    path_list = [data_forward_file_path, data_backward_file_path]
    sourcefile_list.append(path_list)

    write_info_txtfile_header(info_file_path, sample_name, test_name, user_name, user_email, True)
    write_source_info2txtfile(info_file_path, source_name_list, YokogawaGS200_addr_list[0], source_bound_list,
                              test_range_list, slope_list, sourcefile_list)
    start_info_txtfile(info_file_path, test_time)

    print(test_time)
    print(data_forward_file_path)
    print(data_backward_file_path)
    print(info_file_path)

    ####################################################################################################
    ########## 测试之前的预备
    #################### 定义global variables
    source_fast_obj = My_YokogawaGS200(YokogawaGS200_addr_list[0], source_name_list[0], source_mode_list[0],
                                       interval_pause_list[0],
                                       tol_list[0], target_levels_list, scan_steps_list, path_list, flag_back=False)
    source_obj_list.append(source_fast_obj)
    one_gate_test_obj = one_source_meas_class(source_obj=source_fast_obj, slope_fast=slope_list[0][1],
                                              user_info=user_info)

    #################### 开始测试
    start = time.time()

    #################### 绘制动态图
    # fig = plt.figure()
    # ax_value = plt.subplot(1, 2, 1)  ## 根据需求111可以变为任意
    # line_value = line.Line2D([], [])  # 绘制直线
    # ax_error = plt.subplot(1, 2, 2)  ## 根据需求111可以变为任意
    # line_error = line.Line2D([], [])  # 绘制直线
    #
    # ani = animation.FuncAnimation(fig=fig,  # 画布
    #                               func=plot_update,  # 图像更新函数
    #                               init_func=plot_init,  # 图像初始化函数
    #                               frames=10,
    #                               repeat=True,
    #                               interval=source_fast_obj.scan_ramp_time_list[1] * 10,  # 图像更新间隔
    #                               blit=True)

    one_gate_test_obj.create_FuncAnimation_obj(interval_pause=500)

    # 为数据更新函数单独创建一个线程，与图像绘制的线程并发执行
    t = one_gate_test_obj.create_single_meas_thread(scan_repeat=3, stop_level=0.0, flag_back=False, flag_rewrite=True)
    t.start()  # 线程执行
    plt.show()  # plt.show()一定要放在start之后, 否则不能实现同步
    t.join()

    end = time.time()
    print("single thread cost : ", end - start, " seconds")

