import pymeasure.instruments
import numpy as np
import time
from scipy import interpolate

####################################################################################################
########## 继承于pymeasure.instruments.srs.SR830的子类
class My_SR830(pymeasure.instruments.srs.SR830):
    def __init__(self, SR830_addr: str, lockin_name: str, voltage: float, phase: float, frequency: float, interval_pause: float,
                 terminal_io:list, I_ac:float, check_ch: str, tol: float, path_list: list, flag_back: bool = True, flag_init:bool = True):
        self.lockin_name = lockin_name
        self.terminal_io = terminal_io

        self.interval_pause = interval_pause  ## 以秒为单位
        self.check_ch = check_ch
        self.tol = tol
        self.I_ac = I_ac

        self.path_list = path_list
        self.flag_back = flag_back

        self.fileIO_forward = None
        self.fileIO_backward = None

        self.data_x_bins_forward = []
        self.data_y_bins_forward = []
        self.data_t_bins_forward = []
        self.data_m_bins_forward = []
        self.data_x_bins_forward_cache = []
        self.data_y_bins_forward_cache = []
        self.data_t_bins_forward_cache = []
        self.data_m_bins_forward_cache = []

        self.data_x_bins_backward = []
        self.data_y_bins_backward = []
        self.data_t_bins_backward = []
        self.data_m_bins_backward = []
        self.data_x_bins_backward_cache = []
        self.data_y_bins_backward_cache = []
        self.data_t_bins_backward_cache = []
        self.data_m_bins_backward_cache = []

        ####################################################################################################
        ########## init worker
        ########## 目前set parameters只包含[voltage, phase, frequency]
        self.set_parameters = np.zeros((3,), dtype=float)
        if flag_init:
            super().__init__(SR830_addr)
            self.addr = SR830_addr
            self.init_SR830(voltage, phase, frequency)
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
        self.data_x_bins_forward = []
        self.data_y_bins_forward = []
        self.data_t_bins_forward = []
        self.data_m_bins_forward = []

        self.clean_backward_cache()
        self.data_x_bins_backward = []
        self.data_y_bins_backward = []
        self.data_t_bins_backward = []
        self.data_m_bins_backward = []

    def init_SR830(self, voltage, phase, frequency):
        ####################################################################################################
        ########## SR830参数设置
        self.sine_voltage = voltage
        self.set_parameters[0] = voltage

        self.phase = phase
        self.set_parameters[1] = phase

        self.frequency = frequency
        self.set_parameters[2] = frequency

    def read_lockin_levels(self):
        ####################################################################################################
        ########## 读取(X,Y,Magnitude,Theta) ---- (0,1,2,3)
        x = self.x
        y = self.y
        m = self.magnitude
        t = self.theta

        return x, y, m, t

    ####################################################################################################
    ########## 读取数据 forward
    def read_lockin_levels_forward(self):
        ####################################################################################################
        ########## 读取(x,y,m,t)
        x, y, m, t = self.read_lockin_levels()

        self.data_x_bins_forward_cache.append(x)
        self.data_y_bins_forward_cache.append(y)
        self.data_m_bins_forward_cache.append(m)
        self.data_t_bins_forward_cache.append(t)

    def save_data_2_forward_datfile(self):
        ###################################################################################################
        ########## 将level_bins_forward_cache中的所有数据保存到文件中
        self.fileIO_forward = open(self.path_list[0], 'a+')  ## open with a+ mode
        for i in range(len(self.data_x_bins_forward_cache)):
            self.fileIO_forward.write(
                "{: >6d}{: >16.8f}{: >16.8f}{: >16.8f}{: >16.8f}".format(i, self.data_x_bins_forward_cache[i],
                                                                            self.data_y_bins_forward_cache[i],
                                                                            self.data_m_bins_forward_cache[i],
                                                                            self.data_t_bins_forward_cache[i]
                                                                         ))
            ########## 换行
            self.fileIO_forward.write("\n")

        self.fileIO_forward.write("\n")
        self.fileIO_forward.close()

    def put_cache_2_forward_list(self):
        self.data_x_bins_forward.append(self.data_x_bins_forward_cache)
        self.data_y_bins_forward.append(self.data_y_bins_forward_cache)
        self.data_m_bins_forward.append(self.data_m_bins_forward_cache)
        self.data_t_bins_forward.append(self.data_t_bins_forward_cache)

    def clean_forward_cache(self):
        self.data_x_bins_forward_cache = []
        self.data_y_bins_forward_cache = []
        self.data_t_bins_forward_cache = []
        self.data_m_bins_forward_cache = []

    def fit_forward_cache(self, level_bins_forward_cache: list, target_levels_list: list):
        f = interpolate.interp1d(level_bins_forward_cache, self.data_x_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_x_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_forward_cache, self.data_y_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_y_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_forward_cache, self.data_m_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_m_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_forward_cache, self.data_t_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_t_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

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

        self.data_x_bins_forward = []
        self.data_y_bins_forward = []
        self.data_t_bins_forward = []
        self.data_m_bins_forward = []
        self.clean_forward_cache()

        count_row = 0
        while self.fileIO_forward.tell() < eof:
            read_line = self.fileIO_forward.readline()
            if read_line == "\n":
                count_row += 1
                self.data_x_bins_forward.append(self.data_x_bins_forward_cache)
                self.data_y_bins_forward.append(self.data_y_bins_forward_cache)
                self.data_m_bins_forward.append(self.data_m_bins_forward_cache)
                self.data_t_bins_forward.append(self.data_t_bins_forward_cache)

                self.clean_forward_cache()
                continue

            data_line = read_line.split("\n")[0]
            data_line_split = data_line.split()

            self.data_x_bins_forward_cache.append(float(data_line_split[1]))
            self.data_y_bins_forward_cache.append(float(data_line_split[2]))
            self.data_m_bins_forward_cache.append(float(data_line_split[3]))
            self.data_t_bins_forward_cache.append(float(data_line_split[4]))

        self.fileIO_forward.close()

    ####################################################################################################
    ########## 读取数据 backward
    def read_lockin_levels_backward(self):
        ####################################################################################################
        ########## 读取(x,y,m,t)
        x, y, m, t = self.read_lockin_levels()

        self.data_x_bins_backward_cache.append(x)
        self.data_y_bins_backward_cache.append(y)
        self.data_m_bins_backward_cache.append(m)
        self.data_t_bins_backward_cache.append(t)

    def save_data_2_backward_datfile(self):
        ###################################################################################################
        ########## 将level_bins_forward_cache中的所有数据保存到文件中
        count = 0
        self.fileIO_backward = open(self.path_list[1], 'a+')  ## open with a+ mode
        for i in range(len(self.data_x_bins_backward_cache)-1, -1, -1):
            self.fileIO_backward.write(
                "{: >6d}{: >16.8f}{: >16.8f}{: >16.8f}{: >16.8f}".format(i, self.data_x_bins_backward_cache[count],
                                                                            self.data_y_bins_backward_cache[count],
                                                                            self.data_m_bins_backward_cache[count],
                                                                            self.data_t_bins_backward_cache[count]
                                                                         ))
            ########## 换行
            self.fileIO_backward.write("\n")
            count += 1

        self.fileIO_backward.write("\n")
        self.fileIO_backward.close()

    def put_cache_2_backward_list(self):
        self.data_x_bins_backward.append(self.data_x_bins_backward_cache)
        self.data_y_bins_backward.append(self.data_y_bins_backward_cache)
        self.data_m_bins_backward.append(self.data_m_bins_backward_cache)
        self.data_t_bins_backward.append(self.data_t_bins_backward_cache)

    def clean_backward_cache(self):
        self.data_x_bins_backward_cache = []
        self.data_y_bins_backward_cache = []
        self.data_t_bins_backward_cache = []
        self.data_m_bins_backward_cache = []

    def fit_backward_cache(self, level_bins_backward_cache: list, target_levels_list: list):
        f = interpolate.interp1d(level_bins_backward_cache, self.data_x_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_x_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_backward_cache, self.data_y_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_y_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_backward_cache, self.data_m_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_m_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_backward_cache, self.data_t_bins_backward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.data_t_bins_backward_cache = output.tolist()  # use interpolation function returned by `interp1d`

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

        self.data_x_bins_backward = []
        self.data_y_bins_backward = []
        self.data_t_bins_backward = []
        self.data_m_bins_backward = []
        self.clean_backward_cache()

        count_row = 0
        while self.fileIO_backward.tell() < eof:
            read_line = self.fileIO_backward.readline()
            if read_line == "\n":
                count_row += 1
                self.data_x_bins_backward.append(self.data_x_bins_backward_cache)
                self.data_y_bins_backward.append(self.data_y_bins_backward_cache)
                self.data_m_bins_backward.append(self.data_m_bins_backward_cache)
                self.data_t_bins_backward.append(self.data_t_bins_backward_cache)

                self.clean_backward_cache()
                continue

            data_line = read_line.split("\n")[0]
            data_line_split = data_line.split()

            self.data_x_bins_backward_cache.append(float(data_line_split[1]))
            self.data_y_bins_backward_cache.append(float(data_line_split[2]))
            self.data_m_bins_backward_cache.append(float(data_line_split[3]))
            self.data_t_bins_backward_cache.append(float(data_line_split[4]))

        self.fileIO_backward.close()


# if __name__ == "__main__":
#     instr = pymeasure.instruments.srs.SR830("GPIB0::3::INSTR")
#     instr.sine_voltage = 0.0
#     instr.input_config = 'A - B'