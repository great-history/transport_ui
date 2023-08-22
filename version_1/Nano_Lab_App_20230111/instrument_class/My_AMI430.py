import pymeasure.instruments
import numpy as np
import time
from scipy import interpolate

####################################################################################################
########## 继承于pymeasure.instruments.yokogawa.YokogawaGS200的子类
class My_AMI430(pymeasure.instruments.ami.AMI430):
    def __init__(self, ami_addr: str, ami_name: str, tol: float, target_levels_list: list, last_level: float,
                 ramp_field_rate: float, path_list: list, flag_back: bool = True, flag_init:bool = True):
        self.current_target_level = 0.0
        self.target_levels_list = target_levels_list
        self.name = ami_name
        self.last_level = last_level

        self.tol = tol

        self.path_list = path_list
        self.flag_back = flag_back
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
        self.level_bins_fit_forward = []
        self.error_bins_fit_forward = []
        self.leak_bins_fit_forward = []

        self.level_bins_backward_cache = []
        self.error_bins_backward_cache = []
        self.leak_bins_backward_cache = []
        self.level_bins_backward = []
        self.error_bins_backward = []
        self.leak_bins_backward = []
        self.level_bins_fit_backward = []
        self.error_bins_fit_backward = []
        self.leak_bins_fit_backward = []

        ####################################################################################################
        ########## flag_backward : 是否回扫
        ########## ramp_field_rate : 0.06 对应 10 Gauss / s
        if flag_init:
            super().__init__(ami_addr)
            # self.__init_AMI430(ramp_field_rate)  # 磁体的速率控制有点偏差？？# todo:如何精确调控磁场？？
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

        self.level_bins_forward = []
        self.error_bins_forward = []
        self.leak_bins_forward = []

        self.level_bins_backward = []
        self.error_bins_backward = []
        self.leak_bins_backward = []

    def __init_AMI430(self, ramp_field_rate):
        ####################################################################################################
        ########## AMI430参数设置
        self.ramp_rate_field = ramp_field_rate

    ####################################################################################################
    ########## 非测试时使用的函数 : 以较快速度进行数据设置
    def set_level_fast(self, target_level: float):
        ####################################################################################################
        ########## Ramps to a target field
        ########## flag_check = True : 要反复检查(适用于setpoint) ; flag_check = True : 不需反复检查(适用于settime)
        self.target_field = target_level

        current_field = self.field
        while abs(current_field - target_level) > self.tol:
            current_field = self.field

    def set_level(self, target_level: float):
        ####################################################################################################
        ########## Ramps to a target field
        self.target_field = target_level

        current_field = self.field
        while abs(current_field - target_level) > self.tol:
            current_field = self.field

    def read_level(self, index_mod: int):
        ####################################################################################################
        ########## 读取field
        level = self.field

        target_level = self.target_levels_list[index_mod]
        error = level - target_level

        leak = 0.0

        return level, error, leak

    ####################################################################################################
    ########## forward measurement function
    ########## 数据设置
    def set_level_slow_forward(self, index_mod: int):
        self.current_target_level = self.target_levels_list[index_mod]
        self.set_level(target_level=self.current_target_level)

    ########## 读取数据
    def read_level_forward(self, index_mod: int):
        ####################################################################################################
        ########## 读取source_level
        level, error, leak = self.read_level(index_mod)

        self.level_bins_forward_cache.append(level)
        self.error_bins_forward_cache.append(error)
        self.leak_bins_forward_cache.append(leak)  # 对于磁场, 没有Leak, 但为了兼容我还是补了一个0.0

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

    ########## 拟合数据
    def fit_forward_cache(self, level_bins_forward_cache_other: list, target_levels_list: list):
        f = interpolate.interp1d(level_bins_forward_cache_other, self.level_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.level_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        f = interpolate.interp1d(level_bins_forward_cache_other, self.error_bins_forward_cache, fill_value="extrapolate")
        output = f(target_levels_list)  # use interpolation function returned by `interp1d`
        self.error_bins_forward_cache = output.tolist()  # use interpolation function returned by `interp1d`

        self.leak_bins_forward_cache = [0] * len(target_levels_list)

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

    ########## 清空数据
    def clean_forward_cache(self):
        self.level_bins_forward_cache = []
        self.error_bins_forward_cache = []
        self.leak_bins_forward_cache = []

    def put_cache_2_forward_list(self):
        self.level_bins_forward.append(self.level_bins_forward_cache)
        self.error_bins_forward.append(self.error_bins_forward_cache)
        self.leak_bins_forward.append(self.leak_bins_forward_cache)

    ####################################################################################################
    ########## backward measurement function
    ########## 数据设置
    def set_level_slow_backward(self, index_mod: int):
        ####################################################################################################
        ########## set levels in slow slope, 适用于上面提到的三种情形
        self.current_target_level = self.target_levels_list[index_mod]
        self.set_level(target_level=self.current_target_level)

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
            self.fileIO_backward.write("{: >6d}{: >16.8f}{: >16.8f}{: >16.8f}".format(i, self.level_bins_backward_cache[count], self.error_bins_backward_cache[count], self.leak_bins_backward_cache[count]))
            ########## 换行
            self.fileIO_backward.write("\n")
            count += 1

        self.fileIO_backward.write("\n")
        self.fileIO_backward.close()

    ########## 拟合数据
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

    ########## 清空数据
    def clean_backward_cache(self):
        self.level_bins_backward_cache = []
        self.error_bins_backward_cache = []
        self.leak_bins_backward_cache = []

    def put_cache_2_backward_list(self):
        self.level_bins_backward.append(self.level_bins_backward_cache)
        self.error_bins_backward.append(self.error_bins_backward_cache)
        self.leak_bins_backward.append(self.leak_bins_backward_cache)


# ######### only for test
# if __name__ == "__main__":
#     web_address = '192.168.1.102'
#     ami_address = "TCPIP::" + web_address + "::7180::SOCKET"
#     target_levels_list = [0.65, 0.64, 0.63, 0.62, 0.61, 0.60]
#     print(target_levels_list)
#     ami_obj = My_AMI430(ami_addr=ami_address, ami_name="B_field", tol=0.0001, target_levels_list=target_levels_list, last_level=0.45, ramp_field_rate=0.06)
#     ami_obj.set_source_level_fast(target_level=0.5)
#
#     for j in range(len(target_levels_list)):
#         ami_obj.set_level_slow_forward(j)
#         ami_obj.read_level_forward(j)
#
#     print(ami_obj.level_bins_forward_cache)
#     print(ami_obj.error_bins_forward_cache)


########## only for test

# if __name__ == "__main__":
#     web_address = '192.168.1.102'
#
#     magnet = pymeasure.instruments.ami.AMI430("TCPIP::192.168.1.102::7180::SOCKET")  # only for test
#     print(magnet.field)
#     start = time.time()
#     magnet.ramp_rate_field = 0.06  # 对于这台Bluefors而言, 0.06对应 10 Gauss/s
#     magnet.target_field = 1
#
#     current_field = magnet.field
#     while abs(current_field - 1) > 0.0005:
#         current_field = magnet.field
#         print(current_field)
#
#     end = time.time()
#     print(end-start)