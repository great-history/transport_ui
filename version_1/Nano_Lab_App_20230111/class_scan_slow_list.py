import threading

import json

class class_scan_slow_list():
    def __init__(self, slow_obj_list: list):
        ########## 设置工作状态与初始指标
        # print(lockin_obj_list)
        self.slow_obj_list = slow_obj_list