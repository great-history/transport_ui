import pymeasure.instruments
import numpy as np
import time
from scipy import interpolate

####################################################################################################
########## 继承于pymeasure.instruments.yokogawa.YokogawaGS200的子类
class My_Keithley2400(pymeasure.instruments.keithley.Keithley2400):
    def __init__(self, Keithley2400_addr: str, source_name: str, source_mode: str, interval_pause: float, tol: float,
                 target_levels_list: list, scan_steps_list: list, slope_fast: float, path_list: list,
                 flag_back: bool = True, last_level: float = 0.0, flag_init:bool = True):
        ####################################################################################################
        ########## flag_backward : 是否回扫
        ########## slope1 : 前进到end_level时每一步voltage的增量(可以为负数)，真实情况下应该给它设置一个范围
        ########## slope2 : 每行测完返回到start_level每一步voltage的增量(可以为负数)，真实情况下应该给它设置一个范围
        ########## slope3 : 全部测完返回到last_level每一步voltage的增量(可以为负数)，真实情况下应该给它设置一个范围
        self.current_target_level = 0.0
        self.target_levels_list = target_levels_list
        # print(target_levels_list)  ########## only for test
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

        self.level_bins_forward_cache = []
        self.error_bins_forward_cache = []
        self.leak_bins_forward_cache = []
        self.level_bins_forward = []
        self.error_bins_forward = []
        self.leak_bins_forward = []

        self.level_bins_backward_cache = []
        self.error_bins_backward_cache = []
        self.leak_bins_backward_cache = []
        self.level_bins_backward = []
        self.error_bins_backward = []
        self.leak_bins_backward = []

        if flag_init:  # 一切处于初始化状态
            super().__init__(Keithley2400_addr)
            self.init_Keithley2400(source_mode)
        else:  ########## 加载数据
            if self.flag_back:
                self.load_data_from_forward_datfile()
                self.load_data_from_backward_datfile()
            else:
                self.load_data_from_forward_datfile()

    def init_worker(self):
        ####################################################################################################
        ########## 初始化函数
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

    def init_Keithley2400(self, source_mode):
        ####################################################################################################
        ########## Keithley2400参数设置
        if source_mode == "voltage":
            self.source_mode = source_mode
        elif source_mode == "current":
            self.source_mode = source_mode

    ####################################################################################################
    ########## 非测试时使用的函数
    ########## 较快速度进行数据设置
    def set_level_fast(self, target_level: float):
        ####################################################################################################
        ########## set levels in slow slope, 适用于上面提到的三种情形
        self.current_target_level = target_level
        ########## 读取source_level
        if self.source_mode == "voltage":
            current_level = self.source_voltage
        else:  # "current" mode
            current_level = self.source_current
        steps = int(abs((target_level - float(current_level)) / self.slope_fast) + 2)

        ####################################################################################################
        ########## Ramps to a target voltage from the set voltage value over a certain number of linear steps,
        ########## each separated by a pause duration.
        if self.source_mode == "voltage":
            self.ramp_to_voltage(target_voltage=self.current_target_level, steps=steps, pause=self.interval_pause)
        else:  # "current" mode
            self.ramp_to_current(target_current=self.current_target_level, steps=steps, pause=self.interval_pause)
        ########## 在快速设置之后要多读几次
        level, leak = self.just_read_it()
        time.sleep(0.5)
        level, leak = self.just_read_it()
        time.sleep(0.4)
        level, leak = self.just_read_it()
        time.sleep(0.3)
        level, leak = self.just_read_it()
        time.sleep(0.2)
        level, leak = self.just_read_it()
        time.sleep(0.1)

    def just_read_it(self):
        ####################################################################################################
        ########## 读取source_level
        if self.source_mode == "voltage":
            read_data = self.current
            level = read_data[0]
            leak = read_data[1] / 10**(-9)
        else:  # if self.source_mode == "current":
            level = self.source_current
            leak = self.source_voltage

        return level, leak

    def read_level(self, index_mod: int):
        ####################################################################################################
        ########## 读取source_level
        if self.source_mode == "voltage":
            read_data = self.current
            level = read_data[0]
            leak = read_data[1] / 10**(-9)
        else: #if self.source_mode == "current":
            level = self.source_current
            leak = self.source_voltage

        target_level = self.target_levels_list[index_mod]
        error = level - target_level

        return level, error, leak

    ####################################################################################################
    #################### forward measurement function
    ########## 清空cache
    def clean_forward_cache(self):
        self.level_bins_forward_cache = []
        self.error_bins_forward_cache = []
        self.leak_bins_forward_cache = []

    ########## 数据设置
    def set_level_slow_forward(self, index_mod: int):
        ####################################################################################################
        ########## set levels in slow slope, 适用于上面提到的三种情形
        self.current_target_level = self.target_levels_list[index_mod]
        steps = self.scan_steps_list[index_mod - 1]

        ####################################################################################################
        ########## Ramps to a target voltage from the set voltage value over a certain number of linear steps,
        ########## each separated by a pause duration.
        if self.source_mode == "voltage":
            self.ramp_to_voltage(target_voltage=self.current_target_level, steps=steps, pause=self.interval_pause)
        elif self.source_mode == "current":
            self.ramp_to_current(target_current=self.current_target_level, steps=steps, pause=self.interval_pause)

    ########## 读取数据
    def read_level_forward(self, index_mod: int):
        ####################################################################################################
        ########## 读取source_level
        level, error, leak = self.read_level(index_mod)
        self.level_bins_forward_cache.append(level)
        self.error_bins_forward_cache.append(error)
        self.leak_bins_forward_cache.append(leak)

    ########## 保存数据
    def save_data_2_forward_datfile(self):
        ###################################################################################################
        ########## 将level_bins_forward_cache中的所有数据保存到文件中
        self.fileIO_forward = open(self.path_list[0], 'a+')  ## open with a+ mode

        for i in range(len(self.level_bins_forward_cache)):
            self.fileIO_forward.write("{: >6d}{: >16.8f}{: >16.8f}{: >16.8f}".format(i,
                                                                                     self.level_bins_forward_cache[i],
                                                                                     self.error_bins_forward_cache[i],
                                                                                     self.leak_bins_forward_cache[i]))
            ########## 换行
            self.fileIO_forward.write("\n")

        self.fileIO_forward.write("\n")
        self.fileIO_forward.close()

    def put_cache_2_forward_list(self):
        self.level_bins_forward.append(self.level_bins_forward_cache)
        self.error_bins_forward.append(self.error_bins_forward_cache)
        self.leak_bins_forward.append(self.leak_bins_forward_cache)

    def fit_forward_cache(self, level_bins_forward_cache_other: list, target_levels_list: list):
        f = interpolate.interp1d(level_bins_forward_cache_other, self.level_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.level_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_forward_cache_other, self.error_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.error_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_forward_cache_other, self.leak_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.leak_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

    ########## 加载数据
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
    #################### backward measurement function
    ########## 清空cache
    def clean_backward_cache(self):
        self.level_bins_backward_cache = []
        self.error_bins_backward_cache = []
        self.leak_bins_backward_cache = []

    ########## 数据设置
    def set_level_slow_backward(self, index_mod: int):
        ####################################################################################################
        ########## set levels in slow slope, 适用于上面提到的三种情形
        self.current_target_level = self.target_levels_list[index_mod]
        steps = self.scan_steps_list[index_mod]

        ####################################################################################################
        ########## Ramps to a target voltage from the set voltage value over a certain number of linear steps,
        ########## each separated by a pause duration.
        if self.source_mode == "voltage":
            self.ramp_to_voltage(target_voltage=self.current_target_level, steps=steps, pause=self.interval_pause)
        elif self.source_mode == "current":
            self.ramp_to_current(target_current=self.current_target_level, steps=steps, pause=self.interval_pause)

    ########## 读取数据
    def read_level_backward(self, index_mod: int):
        ####################################################################################################
        ########## 读取source_level
        level, error, leak = self.read_level(index_mod)

        self.level_bins_backward_cache.append(level)
        self.error_bins_backward_cache.append(error)
        self.leak_bins_backward_cache.append(leak)

    ########## 保存数据
    def save_data_2_backward_datfile(self):
        ###################################################################################################
        ########## 将level_bins_backward_cache中的所有数据保存到文件中
        count = 0
        self.fileIO_backward = open(self.path_list[1], 'a+')  ## open with a+ mode
        for i in range(len(self.level_bins_backward_cache) - 1, -1, -1):
            self.fileIO_backward.write("{: >6d}{: >16.8f}{: >16.8f}{: >16.8f}".format(i,
                                                                                      self.level_bins_backward_cache[count],
                                                                                      self.error_bins_backward_cache[count],
                                                                                      self.leak_bins_backward_cache[count]))
            ########## 换行
            self.fileIO_backward.write("\n")
            count += 1

        self.fileIO_backward.write("\n")
        self.fileIO_backward.close()

    def put_cache_2_backward_list(self):
        self.level_bins_backward.append(self.level_bins_backward_cache)
        self.error_bins_backward.append(self.error_bins_backward_cache)
        self.leak_bins_backward.append(self.leak_bins_backward_cache)

    def fit_backward_cache(self, level_bins_backward_cache_other: list, target_levels_list: list):
        f = interpolate.interp1d(level_bins_backward_cache_other, self.level_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.level_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_backward_cache_other, self.error_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.error_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_backward_cache_other, self.leak_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.leak_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

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


# if __name__ == "__main__":
#     source_instr = My_Keithley2400("GPIB0::7::INSTR", "top_gate", "voltage", 0.01, 0.001, [-2,-1,0,1,2], [10,10,10,10], 0.02, ["asdasd.txt"], True)
#     source_instr.ramp_to_voltage(target_voltage=0.0, steps=200, pause=0.05)
#     level = source_instr.current
#     source_instr.ramp_to_voltage(target_voltage=0.1, steps=20, pause=0.05)
#     level = source_instr.current
#     source_instr.ramp_to_voltage(target_voltage=0.2, steps=20, pause=0.05)
#     level = source_instr.current
#     source_instr.ramp_to_voltage(target_voltage=0.3, steps=20, pause=0.05)
#     level = source_instr.current
#     source_instr.ramp_to_voltage(target_voltage=0.4, steps=20, pause=0.05)
#     level = source_instr.current
#     source_instr.ramp_to_voltage(target_voltage=0.5, steps=20, pause=0.05)
#     level = source_instr.current
#     # print(source_instr.source_current)
#     # print(source_instr.source_mode)
#     # print(source_instr.source_voltage)
#     # source_instr.enable_source()
#     # print(source_instr.current[1])
#     # print(source_instr.mean_current)
#     # current_level = source_instr.source_voltage
#     # source_instr.output_off_state
