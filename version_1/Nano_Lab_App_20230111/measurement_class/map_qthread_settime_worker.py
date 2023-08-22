import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from PyQt5.QtCore import QUrl, QThread, pyqtSignal
from utilities.utility_package import *
import json
import os
import threading


class map_qthread_settime_worker(QThread):
    run_sinout = pyqtSignal(list)  # 运行时发出的信号(主要是打印到logScreen上显示)
    stop_sinout = pyqtSignal(list)  # 被暂停时发出的信号
    finish_sinout = pyqtSignal(list)  # 结束时发出的信号
    update_sinout = pyqtSignal(list)  # 更新界面/保存图片的信号 [str, float, float]分别指代扫面方向/剩余时间/已完成百分比

    def __init__(self, test_id: int, slow_obj_list: list, fast_obj_list: list, lockin_obj_list: list, user_info: dict,
                 update_time: float, flag_fit: bool = True, parent=None):
        super(map_qthread_settime_worker, self).__init__(parent)
        ########## 设置工作状态与初始指标
        # print(lockin_obj_list)
        self.test_id = test_id

        self.slow_obj_list = slow_obj_list  # scan slow direction, using set-point mode
        self.fast_obj_list = fast_obj_list  # scan fast direction, using set-time mode
        self.fast_obj = fast_obj_list[0]
        self.lockin_obj_list = lockin_obj_list  # lockin objs
        self.user_info = user_info
        self.update_time = update_time

        self.flag_stat = user_info["flag_stat"]  # 4种状态 : start / running / stopped / finish
        self.current_i = len(slow_obj_list[0].level_bins_forward)  # 行指标
        self.current_j = -1  # 列指标
        self.__init_worker()
        self.flag_back = user_info["flag_back"]
        if len(slow_obj_list[0].level_bins_forward) == len(slow_obj_list[0].level_bins_backward):
            self.flag_direction = 1  # +1 forward, -1 backward
        else:
            self.flag_direction = -1
        self.flag_fit = flag_fit

        self.scan_slow_dims = len(self.slow_obj_list[0].target_levels_list)
        self.scan_slow_instr_num = len(self.slow_obj_list)
        self.scan_fast_dims = len(self.fast_obj_list[0].target_levels_list)
        self.scan_fast_instr_num = len(self.fast_obj_list)

    def __init_worker(self):
        return

    def run(self):
        if self.flag_stat == "finish":
            return

        if self.flag_back == False:  # 只往前扫
            self.meas_function_only_forward()
        else:
            self.meas_function_both_direction()

        try:
            self.test_finish()
        except Exception as e:
            print("出现了错误？？")
            print(e)

    def test_finish(self):
        #################### 结束测试并关闭文件并发送邮件
        if self.flag_stat == "finish":
            for obj in self.slow_obj_list:
                if hasattr(obj, "last_level"):
                    last_level = obj.last_level
                else:
                    last_level = 0.0
                obj.set_level_fast(target_level=last_level)

            for obj in self.fast_obj_list:
                if hasattr(obj, "last_level"):
                    last_level = obj.last_level
                else:
                    last_level = 0.0
                obj.set_level_fast(target_level=last_level)

            ########## 把修改后的信息重新写入json文件中
            with open(self.user_info["info_file_path"], mode='r', encoding='utf-8') as f:
                dict_list = json.load(f)

            self.user_info["flag_stat"] = self.flag_stat
            dict_list[0] = self.user_info
            with open(self.user_info["info_file_path"], mode='w', encoding='utf-8') as f:
                json.dump(dict_list, f)

            ########## 发送邮件
            self.__send_email_to_user(test_content=" test finished ! ", direction="forward")
            if self.flag_back:
                self.__send_email_to_user(test_content=" test finished ! ", direction="backward")
            self.quit()
            self.finish_sinout.emit([" test finished perfectly ! ", self.test_id])

    ####################################################################################################
    ########## 与信号finish_sinout和stop_sinout相连
    def __send_email_to_user(self, test_content: str,
                             mail_sender: str = 'fsj12132836@163.com',
                             mail_host='smtp.163.com',
                             mail_pass: str = 'REZNQDVYIXHUMULI', direction: str = "forward"):
        ####################################################################################################
        ########## 测试被终止或结束时发一封邮件
        ####################################################################################################
        ########## 设置eamil信息
        # 添加一个MIMEmultipart类，处理正文及附件
        message = MIMEMultipart()
        message['From'] = mail_sender
        message['To'] = self.user_info["user_email"]
        message['Subject'] = '测试邮件'

        # 推荐使用html格式的正文内容，这样比较灵活，可以附加图片地址，调整格式等
        # 设置html格式参数
        part1 = MIMEText(test_content, 'html', 'utf-8')

        # 将内容附加到邮件主体中
        message.attach(part1)

        ####################################################################################################
        ########## 添加一个dat文本附件
        datfile_list = []
        prefix_list = []
        if direction == "forward":
            for obj in self.slow_obj_list:
                datfile_list.append(obj.path_list[0])
                prefix = obj.name + "-forward"
                prefix_list.append(prefix)

            for obj in self.fast_obj_list:
                datfile_list.append(obj.path_list[0])
                prefix = obj.name + "-forward"
                prefix_list.append(prefix)

            for obj in self.lockin_obj_list:
                datfile_list.append(obj.path_list[0])
                prefix = obj.lockin_name + "-forward"
                prefix_list.append(prefix)

            cola_dat_file = write_coalesce_file(datfile_list, prefix_list, direction="forward")
            with open(cola_dat_file, 'r') as af:
                test_content = af.read()
        elif direction == "backward":
            for obj in self.slow_obj_list:
                datfile_list.append(obj.path_list[1])
                prefix = obj.name + "-forward"
                prefix_list.append(prefix)

            for obj in self.fast_obj_list:
                datfile_list.append(obj.path_list[1])
                prefix = obj.name + "-forward"
                prefix_list.append(prefix)

            for obj in self.lockin_obj_list:
                datfile_list.append(obj.path_list[1])
                prefix = obj.lockin_name + "-forward"
                prefix_list.append(prefix)

            cola_dat_file = write_coalesce_file(datfile_list, prefix_list, direction="backward")
            with open(cola_dat_file, 'r') as af:
                test_content = af.read()

        # 设置txt参数
        part_attach = MIMEText(test_content, 'plain', 'utf-8')
        # 附件设置内容类型，方便起见，设置为二进制流
        part_attach['Content-Type'] = 'application/octet-stream'
        # 设置附件头，添加文件名
        part_attach['Content-Disposition'] = 'attachment;filename="test_content.dat"'

        # 将内容附加到邮件主体中
        message.attach(part_attach)

        # 登录并发送
        try:
            smtpObj = smtplib.SMTP()
            smtpObj.connect(mail_host)
            smtpObj.login(mail_sender, mail_pass)
            smtpObj.sendmail(mail_sender, self.user_info["user_email"], message.as_string())
            print('send email success')
            smtpObj.quit()
        except smtplib.SMTPException as e:
            print('send email error', e)

    ####################################################################################################
    ########## 与测试相关
    def meas_function_only_forward(self, flag_rewrite: bool = True):
        ####################################################################################################
        ########## 初始化
        if self.flag_stat == "start":
            self.all_obj_init(flag_rewrite)

            self.current_i = -1  # 行指标
            self.current_j = -1  # 列指标

        ####################################################################################################
        ########## 进入测试
        self.flag_stat = "running"

        for i in range(self.scan_slow_dims):  # 这个Loop仅供测试使用
            ####################################################################################################
            ########## forward
            self.meas_function_forward_one_round(index=i)

    def meas_function_both_direction(self, flag_rewrite: bool = True):
        ####################################################################################################
        ########## 初始化
        if self.flag_stat == "start":
            self.all_obj_init(flag_rewrite)

            self.current_i = -1  # 行指标
            self.current_j = -1  # 列指标

        ####################################################################################################
        ########## 进入测试
        self.flag_stat = "running"

        for i in range(self.scan_slow_dims):  # 这个Loop仅供测试使用
            ####################################################################################################
            ########## forward + backward
            self.meas_function_both_direction_one_round(index=i)

    def all_obj_init(self, flag_rewrite: bool = True):
        for obj in self.slow_obj_list:
            obj.init_worker()
            write_scan_datfile_header(datfile_path=obj.path_list[0], rewrite=flag_rewrite)
            write_scan_datfile_header(datfile_path=obj.path_list[1], rewrite=flag_rewrite)

        for obj in self.fast_obj_list:
            obj.init_worker()
            write_scan_datfile_header(datfile_path=obj.path_list[0],
                                      rewrite=flag_rewrite)  ##todo:之后最好把磁场和源表的文件用不同的函数操作,虽然内容差不多
            write_scan_datfile_header(datfile_path=obj.path_list[1], rewrite=flag_rewrite)

        for obj in self.lockin_obj_list:
            write_lockin_datfile_header(datfile_path=obj.path_list[0], rewrite=flag_rewrite)
            write_lockin_datfile_header(datfile_path=obj.path_list[1], rewrite=flag_rewrite)

        time.sleep(1.5)  # 因为obj.init_worker的存在

    def meas_function_forward_one_round(self, index: int):
        start = time.time()
        self.current_i = index
        self.current_j = 0

        trg_field_start = self.fast_obj.target_levels_list[0]
        trg_field_end = self.fast_obj.target_levels_list[-1]
        tol = self.fast_obj.tol
        ####################################################################################################
        #################### forward
        ########## 清空forward cache
        self.cache_clean_forward()
        if self.current_i == 0:
            for obj in self.slow_obj_list:
                obj.set_level_fast(target_level=obj.target_levels_list[0])
        else:
            for obj in self.slow_obj_list:
                obj.set_level_slow_forward(self.current_i)
        self.fast_obj.set_level_fast(trg_field_start)

        time.sleep(5.0)
        print("开始往前扫")
        self.cache_read_forward()
        ########## 开始测试
        self.flag_stat = "running"
        self.run_sinout.emit([self.current_i, self.test_id])

        ########## 测试forward主体
        self.fast_obj.target_field = trg_field_end
        while abs(self.current_field - trg_field_end) >= tol:
            self.cache_read_forward()
            self.current_j += 1
            time.sleep(self.update_time)

        ########## 保存forward
        self.save_data_for_all_obj_forward()

        end = time.time()
        time1 = (end - start)
        ########## 发射一个信号：更新app_one_source_test中的log Screen / progressBar / Remaining Time
        rm_time = (time1 * 2) * (self.scan_slow_dims - 1 - self.current_i) + time1
        progress = (self.current_i + 1) / self.scan_slow_dims

        if self.current_i == (self.scan_slow_dims - 1):
            update_info_list = [self.user_info["test_name"], "forward", rm_time, progress, -1,
                                self.slow_obj_list[0].target_levels_list[self.current_i], self.test_id]
            self.update_sinout.emit(update_info_list)
            self.flag_stat = "finish"
        else:
            update_info_list = [self.user_info["test_name"], "forward", rm_time, progress, self.current_i,
                                self.slow_obj_list[0].target_levels_list[self.current_i], self.test_id]
            self.update_sinout.emit(update_info_list)
            self.flag_stat = "pause"

    def meas_function_both_direction_one_round(self, index: int):
        start = time.time()
        self.current_i = index
        self.current_j = 0

        trg_field_start = self.fast_obj.target_levels_list[0]
        trg_field_end = self.fast_obj.target_levels_list[-1]
        tol = self.fast_obj.tol

        ####################################################################################################
        #################### forward
        ########## 清空forward cache
        self.cache_clean_forward()
        if self.current_i == 0:
            for obj in self.slow_obj_list:
                obj.set_level_fast(target_level=obj.target_levels_list[0])
        else:
            for obj in self.slow_obj_list:
                obj.set_level_slow_forward(self.current_i)
        self.fast_obj.set_level_fast(trg_field_start)

        time.sleep(5.0)
        print("开始往前扫")
        self.cache_read_forward()
        ########## 开始测试
        self.flag_stat = "running"
        self.run_sinout.emit([self.current_i, self.test_id])

        ########## 测试forward主体
        self.fast_obj.target_field = trg_field_end
        while abs(self.current_field - trg_field_end) >= tol:
            self.cache_read_forward()
            self.current_j += 1
            time.sleep(self.update_time)

        ########## 保存forward
        self.save_data_for_all_obj_forward()

        end = time.time()
        time1 = (end - start)
        ########## 发射一个信号：更新app_one_source_test中的log Screen / progressBar / Remaining Time
        rm_time = (time1 * 2) * (self.scan_slow_dims - 1 - self.current_i) + time1
        progress = (2 * self.current_i + 1) / (2 * self.scan_slow_dims)
        update_info_list = [self.user_info["test_name"], "forward", rm_time, progress, self.current_i, 0.0,
                            self.test_id]
        self.update_sinout.emit(update_info_list)

        ####################################################################################################
        #################### backward
        ########## 清空cache
        self.cache_clean_backward()
        self.fast_obj.set_level_fast(trg_field_end)
        time.sleep(2.0)
        print("开始往后扫")
        self.cache_read_backward()

        ########## 测试forward主体
        self.fast_obj.target_field = trg_field_start
        while abs(self.current_field - trg_field_start) >= tol:
            self.cache_read_backward()
            self.current_j -= 1
            time.sleep(self.update_time)

        self.save_data_for_all_obj_backward()

        end = time.time()
        time2 = (end - start)
        ########## 发射一个信号：更新app_one_source_test中的log Screen / progressBar / Remaining Time
        rm_time = (time1 + time2) * (self.scan_slow_dims - 1 - self.current_i)
        progress = (self.current_i + 1) / self.scan_slow_dims

        if self.current_i == (self.scan_slow_dims - 1):
            update_info_list = [self.user_info["test_name"], "backward", rm_time, progress, -1,
                                self.slow_obj_list[0].target_levels_list[self.current_i], self.test_id]
            self.update_sinout.emit(update_info_list)
            self.flag_stat = "finish"
        else:
            update_info_list = [self.user_info["test_name"], "backward", rm_time, progress, self.current_i,
                                self.slow_obj_list[0].target_levels_list[self.current_i], self.test_id]
            self.update_sinout.emit(update_info_list)
            self.flag_stat = "pause"

    ####################################################################################################
    ########## forward measurement
    def cache_clean_forward(self):
        self.fast_obj.clean_forward_cache()

        for obj in self.slow_obj_list:
            obj.clean_forward_cache()

        for obj in self.lockin_obj_list:
            obj.clean_forward_cache()

    def cache_read_forward(self):
        current_field = self.fast_obj.field
        self.current_field = current_field
        self.fast_obj.level_bins_forward_cache.append(current_field)
        self.fast_obj.error_bins_forward_cache.append(0.0)
        self.fast_obj.leak_bins_forward_cache.append(0.0)

        for obj in self.slow_obj_list:
            obj.read_level_forward(self.current_i)

        for obj in self.lockin_obj_list:
            obj.read_lockin_levels_forward()

    def save_data_for_all_obj_forward(self):
        ########## 将cache中的数据转入 / 写入文件并保存文件 / 保存当前的图片
        if self.flag_fit:
            level_bins_forward_cache_fast = self.fast_obj.level_bins_forward_cache
            target_level_list = self.fast_obj.target_levels_list

            for obj in self.slow_obj_list:
                obj.fit_forward_cache(level_bins_forward_cache_fast, target_level_list)
                obj.save_data_2_forward_datfile()
                obj.put_cache_2_forward_list()

            for obj in self.lockin_obj_list:
                obj.fit_forward_cache(level_bins_forward_cache_fast, target_level_list)
                obj.save_data_2_forward_datfile()
                obj.put_cache_2_forward_list()

            self.fast_obj.fit_forward_cache(level_bins_forward_cache_fast, target_level_list)
            self.fast_obj.save_data_2_forward_datfile()
            self.fast_obj.put_cache_2_forward_list()
        else:
            for obj in self.fast_obj_list:
                obj.save_data_2_forward_datfile()
                obj.put_cache_2_forward_list()

            for obj in self.slow_obj_list:
                obj.save_data_2_forward_datfile()
                obj.put_cache_2_forward_list()

            for obj in self.lockin_obj_list:
                obj.save_data_2_forward_datfile()
                obj.put_cache_2_forward_list()

    ####################################################################################################
    ########## backward measurement
    def cache_clean_backward(self):
        ########## 清空cache
        self.fast_obj.clean_backward_cache()

        for obj in self.slow_obj_list:
            obj.clean_backward_cache()

        ########## 清空cache
        for obj in self.lockin_obj_list:
            obj.clean_backward_cache()

    def cache_read_backward(self):
        current_field = self.fast_obj.field
        self.current_field = current_field
        self.fast_obj.level_bins_backward_cache.append(current_field)
        self.fast_obj.error_bins_backward_cache.append(0.0)
        self.fast_obj.leak_bins_backward_cache.append(0.0)

        for obj in self.slow_obj_list:
            obj.read_level_backward(self.current_i)

        for obj in self.lockin_obj_list:
            obj.read_lockin_levels_backward()

    def save_data_for_all_obj_backward(self):
        ########## 将cache中的数据转入 / 写入文件并保存文件 / 保存当前的图片
        if self.flag_fit:
            target_level_list = self.fast_obj.target_levels_list
            target_level_list = target_level_list[::-1]
            level_bins_backward_cache_fast = self.fast_obj.level_bins_backward_cache

            for obj in self.slow_obj_list:
                obj.fit_backward_cache(level_bins_backward_cache_fast, target_level_list)
                obj.save_data_2_backward_datfile()
                obj.put_cache_2_backward_list()

            for obj in self.lockin_obj_list:
                obj.fit_backward_cache(level_bins_backward_cache_fast, target_level_list)
                obj.save_data_2_backward_datfile()
                obj.put_cache_2_backward_list()

            self.fast_obj.fit_backward_cache(level_bins_backward_cache_fast, target_level_list)
            self.fast_obj.save_data_2_backward_datfile()
            self.fast_obj.put_cache_2_backward_list()
        else:
            self.fast_obj.save_data_2_backward_datfile()
            self.fast_obj.put_cache_2_backward_list()

            for obj in self.slow_obj_list:
                obj.save_data_2_backward_datfile()
                obj.put_cache_2_backward_list()

            for obj in self.lockin_obj_list:
                obj.save_data_2_backward_datfile()
                obj.put_cache_2_backward_list()
