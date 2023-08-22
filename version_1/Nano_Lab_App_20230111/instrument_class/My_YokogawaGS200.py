import pymeasure.instruments
import numpy as np
import time
from scipy import interpolate

####################################################################################################
########## 继承于pymeasure.instruments.yokogawa.YokogawaGS200的子类
########## to do : 应该改名为My_YokogawaGS200_worker，它应该被视为一个赋予使命的工作者而不是自由度很大的机器人
class My_YokogawaGS200(pymeasure.instruments.yokogawa.YokogawaGS200):
    def __init__(self, YokogawaGS200_addr: str, source_name: str, source_mode: str, interval_pause: float, tol: float,
                 target_levels_list: list, scan_steps_list: list, slope_fast:float, path_list: list,
                 flag_back: bool = True, last_level: float = 0.0, flag_init:bool = True):
        ####################################################################################################
        ########## flag_backward : 是否回扫
        ########## slope1 : 前进到end_level时每一步voltage的增量(可以为负数)，真实情况下应该给它设置一个范围
        ########## slope2 : 每行测完返回到start_level每一步voltage的增量(可以为负数)，真实情况下应该给它设置一个范围
        ########## slope3 : 全部测完返回到last_level每一步voltage的增量(可以为负数)，真实情况下应该给它设置一个范围
        self.current_target_level = 0.0
        self.target_levels_list = target_levels_list
        self.name = source_name

        self.interval_pause = interval_pause
        self.tol = tol
        self.scan_steps_list = scan_steps_list
        self.scan_ramp_time_list = []  # 第一个值是从当前位置
        for i in range(len(scan_steps_list)):
            self.scan_ramp_time_list.append(float(self.scan_steps_list[i]) * self.interval_pause)
        self.slope_fast = slope_fast

        self.path_list = path_list
        self.flag_back = flag_back
        self.last_level = last_level
        ####################################################################################################
        ########## init worker
        self.fileIO_forward = None
        self.fileIO_backward = None

        self.clean_forward_cache()
        self.level_bins_forward = []
        self.error_bins_forward = []
        self.leak_bins_forward = []

        self.clean_backward_cache()
        self.level_bins_backward = []
        self.error_bins_backward = []
        self.leak_bins_backward = []

        if flag_init:
            super().__init__(YokogawaGS200_addr)
            self.init_YokogawaGS200(source_mode)
        else:  ########## 加载数据
            if self.flag_back:
                self.load_data_from_forward_datfile()
                self.load_data_from_backward_datfile()
            else:
                self.load_data_from_forward_datfile()

    ####################################################################################################
    ########## 初始化函数
    def init_worker(self):
        if self.fileIO_forward != None:
            self.fileIO_forward.close()
            self.fileIO_forward = None

        if self.fileIO_backward != None:
            self.fileIO_backward.close()
            self.fileIO_backward = None

        self.clean_forward_cache()
        self.level_bins_forward = []
        self.error_bins_forward = []
        self.leak_bins_forward = []

        self.clean_backward_cache()
        self.level_bins_backward = []
        self.error_bins_backward = []
        self.leak_bins_backward = []

    def init_YokogawaGS200(self, source_mode):
        ####################################################################################################
        ########## YokogawaGS200参数设置
        self.source_mode = source_mode
        if self.source_enabled == False:  ## True:打开 output  False:关闭 output
            self.source_enabled = True
        self.source_range = np.amax(np.abs(self.target_levels_list))  ## 一定要把量程设置好，否则很有可能会报错

    ####################################################################################################
    ########## 非测试时使用的函数
    ########## 较快速度进行数据设置
    def set_level_fast(self, target_level: float):
        ####################################################################################################
        ########## set levels in slow slope, 适用于上面提到的三种情形
        self.current_target_level = target_level
        current_level = self.source_level
        steps = int(abs((target_level - float(current_level)) / self.slope_fast) + 1)
        ramp_time = self.interval_pause * steps

        ####################################################################################################
        ########## trigger_ramp_to_level应该与sleep_time捆绑在一起
        ########## 因此trigger_ramp_to_level应该与sleep_time捆绑在一起
        self.trigger_ramp_to_level(level=target_level, ramp_time=ramp_time)
        time.sleep(ramp_time + 0.05)

    ####################################################################################################
    ########## forward measurement function
    def clean_forward_cache(self):
        self.level_bins_forward_cache = []
        self.error_bins_forward_cache = []
        self.leak_bins_forward_cache = []

    ########## 数据设置
    def set_level_slow_forward(self, index_mod: int):
        ####################################################################################################
        ########## set levels in slow slope, 适用于上面提到的三种情形
        self.current_target_level = self.target_levels_list[index_mod]
        ramp_time = self.scan_ramp_time_list[index_mod - 1]

        ####################################################################################################
        ########## trigger_ramp_to_level应该与sleep_time捆绑在一起
        ########## 因此trigger_ramp_to_level应该与sleep_time捆绑在一起
        self.trigger_ramp_to_level(level=self.current_target_level, ramp_time=ramp_time)
        time.sleep(ramp_time + 0.05)

    ########## 读取数据
    def read_level_forward(self, index_mod: int, flag_check: bool = False):
        level = self.source_level
        target_level = self.target_levels_list[index_mod]
        error = level - target_level

        if flag_check == True:  ## for test
            for i in range(5):  ## 读100次数，如果误差小于tol就退出
                level = self.source_level
                error = level - target_level
                if abs(error) > self.tol:
                    break

        self.level_bins_forward_cache.append(level)
        self.error_bins_forward_cache.append(error)
        self.leak_bins_forward_cache.append(0.0)

    ########## 保存数据
    def save_data_to_forward_datfile(self, index_mod: int, index: int):
        ####################################################################################################
        ########## 保存数据到文件中
        # 写入第i行数据
        self.fileIO_forward.write("{: >6d}{: >16.8f}{: >16.8f}".format(index_mod, self.level_bins_forward[index], self.error_bins_forward[index]))
        # 换行
        self.fileIO_forward.write("\n")

    def save_data_2_forward_datfile(self):
        ###################################################################################################
        ########## 将level_bins_forward_cache中的所有数据保存到文件中
        self.fileIO_forward = open(self.path_list[0], 'a+')  ## open with a+ mode
        for i in range(len(self.level_bins_forward_cache)):
            self.fileIO_forward.write("{: >6d}{: >16.8f}{: >16.8f}".format(i, self.level_bins_forward_cache[i], self.error_bins_forward_cache[i]))
            ########## 换行
            self.fileIO_forward.write("\n")

        self.fileIO_forward.write("\n")
        self.fileIO_forward.close()

    def fit_forward_cache(self, level_bins_forward_cache_other: list, target_levels_list: list):
        f = interpolate.interp1d(level_bins_forward_cache_other, self.level_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.level_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_forward_cache_other, self.error_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.error_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        self.leak_bins_forward_cache = [0] * len(target_levels_list)

    ########## 读取数据
    def load_data_from_forward_datfile(self):
        self.fileIO_forward = open(self.path_list[0], 'r')  ## open with a+ mode

        self.fileIO_forward.seek(0, 2)  # 移动读的位置
        # 第一个参数表示偏移量（正数表示向后移动，负数表示向前移动），
        # 第二个参数表示位置（0--文件开头，1--当前位置，2--文件末尾）
        # seek(0, 2)表示移到与末尾相差0的位置，也就是移到文件末尾的位置
        eof = self.fileIO_forward.tell()  # 得到文件末尾位置的具体数值
        self.fileIO_forward.seek(0, 0)  # 重新移到文件头，第2个参数可以省略，因为它默认为0（文件头）

        ########## 读掉文件头
        head_line = self.fileIO_forward.readline()
        # head_line = head_line.split("\n")[0]
        # head_line_split = head_line.split()
        # print(head_line_split)
        ########## 读掉第二行
        self.fileIO_forward.readline()

        self.level_bins_forward = []
        self.error_bins_forward = []
        self.leak_bins_forward = []
        self.clean_forward_cache()

        count_row = 0
        while self.fileIO_forward.tell() < eof:
            read_line = self.fileIO_forward.readline()
            if read_line == "\n":
                count_row += 1
                self.level_bins_forward.append(self.level_bins_forward_cache)
                self.error_bins_forward.append(self.error_bins_forward_cache)
                self.leak_bins_forward.append(self.leak_bins_forward_cache)

                self.clean_forward_cache()
                continue

            data_line = read_line.split("\n")[0]
            data_line_split = data_line.split()

            self.level_bins_forward_cache.append(float(data_line_split[1]))
            self.error_bins_forward_cache.append(float(data_line_split[2]))
            self.leak_bins_forward_cache.append(float(data_line_split[3]))

        self.fileIO_forward.close()

    ########## forward all in one ：设置+读取+保存
    def scan_for_one_step_forward(self, index_mod: int, index: int):
        ####################################################################################################
        ########## 一站式服务
        self.set_source_level_slow_forward(index_mod)
        self.read_source_level_forward(index_mod)
        self.save_data_to_forward_datfile(index_mod, index)

    def scan_for_all_in_one_fast(self, current_index_mod: int, current_index: int):
        target_level_slow = self.target_levels_list[current_index_mod]
        self.set_source_level_fast(target_level=target_level_slow)
        self.read_source_level_forward(current_index_mod)
        self.save_data_to_forward_datfile(current_index_mod, current_index)

    ####################################################################################################
    ########## backward measurement function
    def clean_backward_cache(self):
        self.level_bins_backward_cache = []
        self.error_bins_backward_cache = []
        self.leak_bins_backward_cache = []

    ########## 数据设置
    def set_level_slow_backward(self, index_mod: int):
        ####################################################################################################
        ########## set levels in slow slope, 适用于上面提到的三种情形
        self.current_target_level = self.target_levels_list[index_mod]
        ramp_time = self.scan_ramp_time_list[index_mod]
        ####################################################################################################
        ########## trigger_ramp_to_level应该与sleep_time捆绑在一起
        ########## 因此trigger_ramp_to_level应该与sleep_time捆绑在一起
        self.trigger_ramp_to_level(level=self.current_target_level, ramp_time=ramp_time)
        time.sleep(ramp_time + 0.05)

    ########## 读取数据
    def read_level_backward(self, index_mod: int, flag_check: bool = False):
        level = self.source_level
        target_level = self.target_levels_list[index_mod]
        error = level - target_level

        if flag_check == True:  ## for test
            while abs(error) > self.tol:
                level = self.source_level
                error = level - target_level

        self.level_bins_backward_cache.append(level)
        self.error_bins_backward_cache.append(error)
        self.leak_bins_backward_cache.append(0.0)

    ########## 保存数据
    def save_data_to_backward_datfile(self, index_mod: int, index: int):
        # 写入第i行数据
        self.fileIO_backward.write("{: >6d}{: >16.8f}{: >16.8f}".format(index_mod, self.level_bins_backward[-1], self.error_bins_backward[-1]))
        # 换行
        self.fileIO_backward.write("\n")

    def save_data_2_backward_datfile(self):
        ###################################################################################################
        ########## 将level_bins_backward_cache中的所有数据保存到文件中
        count = 0
        self.fileIO_backward = open(self.path_list[1], 'a+')  ## open with a+ mode
        for i in range(len(self.level_bins_backward_cache) - 1, -1, -1):
            self.fileIO_backward.write("{: >6d}{: >16.8f}{: >16.8f}".format(i, self.level_bins_backward_cache[count], self.error_bins_backward_cache[count]))
            ########## 换行
            self.fileIO_backward.write("\n")
            count += 1

        self.fileIO_backward.write("\n")
        self.fileIO_backward.close()

    def fit_backward_cache(self, level_bins_backward_cache_other: list, target_levels_list: list):
        f = interpolate.interp1d(level_bins_backward_cache_other, self.level_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.level_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_backward_cache_other, self.error_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.error_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        self.leak_bins_backward_cache = [0] * len(target_levels_list)

    ########## 加载数据
    def load_data_from_backward_datfile(self):
        self.fileIO_backward = open(self.path_list[1], 'r')  ## open with a+ mode

        self.fileIO_backward.seek(0, 2)  # 移动读的位置
        # 第一个参数表示偏移量（正数表示向后移动，负数表示向前移动），
        # 第二个参数表示位置（0--文件开头，1--当前位置，2--文件末尾）
        # seek(0, 2)表示移到与末尾相差0的位置，也就是移到文件末尾的位置
        eof = self.fileIO_backward.tell()  # 得到文件末尾位置的具体数值
        self.fileIO_backward.seek(0, 0)  # 重新移到文件头，第2个参数可以省略，因为它默认为0（文件头）

        ########## 读掉文件头
        head_line = self.fileIO_backward.readline()
        # head_line = head_line.split("\n")[0]
        # head_line_split = head_line.split()
        # print(head_line_split)
        ########## 读掉第二行
        self.fileIO_backward.readline()

        self.level_bins_backward = []
        self.error_bins_backward = []
        self.leak_bins_backward = []
        self.clean_backward_cache()

        count_row = 0
        while self.fileIO_backward.tell() < eof:
            read_line = self.fileIO_backward.readline()
            if read_line == "\n":
                count_row += 1
                self.level_bins_backward.append(self.level_bins_backward_cache)
                self.error_bins_backward.append(self.error_bins_backward_cache)
                self.leak_bins_backward.append(self.leak_bins_backward_cache)

                self.clean_backward_cache()
                continue

            data_line = read_line.split("\n")[0]
            data_line_split = data_line.split()

            self.level_bins_backward_cache.append(float(data_line_split[1]))
            self.error_bins_backward_cache.append(float(data_line_split[2]))
            self.leak_bins_backward_cache.append(float(data_line_split[3]))

        self.fileIO_backward.close()

    ######### backward all in one ：设置+读取+保存
    def scan_for_one_step_backward(self, index_mod: int, index: int):
        ####################################################################################################
        ########## 一站式服务
        self.set_source_level_slow_backward(index_mod)
        self.read_source_level_backward(index_mod)
        self.save_data_to_backward_datfile(index_mod, index)