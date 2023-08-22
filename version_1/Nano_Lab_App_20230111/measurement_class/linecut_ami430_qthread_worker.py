import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from PyQt5.QtCore import QUrl, QThread, pyqtSignal
from utilities.utility_package import *
import os
import threading

class linecut_ami430_qthread_worker(QThread):

    run_sinout = pyqtSignal(list)  # 运行时发出的信号(主要是打印到logScreen上显示)
    stop_sinout = pyqtSignal(list)  # 被暂停时发出的信号
    finish_sinout = pyqtSignal(list)  # 结束时发出的信号
    update_sinout = pyqtSignal(list)  # 更新界面/保存图片的信号 [str, float, float]分别指代扫面方向/剩余时间/已完成百分比

    def __init__(self, test_id:int, fast_obj_list: list, lockin_obj_list: list, update_time:float, user_info: dict, parent=None):
        super(linecut_ami430_qthread_worker, self).__init__(parent)
        ########## 设置工作状态与初始指标
        self.test_id = test_id
        self.flag_stat = "start"  # 4种状态 : start / running / stopped / finished
        self.flag_direction = 1  # +1 forward, -1 backward

        self.fast_obj = fast_obj_list[0]  # scan fast obj : 我认为只有一个fast obj
        self.lockin_obj_list = lockin_obj_list  # lockin objs
        self.update_time = update_time  # update_time一般取在1s左右
        self.user_info = user_info

        self.flag_back = self.fast_obj.flag_back
        self.scan_slow_dims = 1
        self.scan_slow_instr_num = 0
        self.scan_fast_dims = len(self.fast_obj.target_levels_list)
        self.scan_fast_instr_num = 1
        self.current_i = -1  # 行指标
        self.current_j = -1  # 列指标

    def run(self):
        if not self.flag_back:  # 只往前扫
            self.meas_function_only_forward()
        else:
            self.meas_function_both_direction()
        try:
            #################### 结束测试并关闭文件并发送邮件
            if self.flag_stat == "finish":
                for obj in self.fast_obj_list:
                    last_level = obj.last_level
                    obj.set_source_level_fast(target_level=last_level)

                self.__send_email_to_user(test_content=" test finished ! ")
                self.quit()
                self.finish_sinout.emit([" test finished perfectly ! ", self.test_id])
        except Exception as e:
            print("出现了错误？？")
            print(e)

    def all_obj_init(self, flag_rewrite: bool = True):
        write_datfile_header(datfile_path=self.fast_obj.path_list[0], rewrite=flag_rewrite, flag_error=False, flag_leak=False)  ##todo:之后最好把磁场和源表的文件用不同的函数操作,虽然内容差不多
        write_datfile_header(datfile_path=self.fast_obj.path_list[1], rewrite=flag_rewrite, flag_error=False, flag_leak=False)

        for obj in self.lockin_obj_list:
            write_lockin_datfile_header(datfile_path=obj.path_list[0], rewrite=flag_rewrite)
            write_lockin_datfile_header(datfile_path=obj.path_list[1], rewrite=flag_rewrite)

    def set_level_with_cache_clean_backward(self):
        ########## 清空cache
        for obj in self.fast_obj_list:
            obj.clean_backward_cache()
            target_level_start = obj.target_levels_list[self.current_j]
            obj.set_source_level_fast(target_level=target_level_start)
            obj.read_source_level_backward(self.current_j)

        ########## 清空cache
        for obj in self.lockin_obj_list:
            obj.clean_backward_cache()
            obj.read_lockin_levels_backward()

    def save_data_for_all_obj_forward(self):
        ########## 将cache中的数据转入 / 写入文件并保存文件 / 保存当前的图片
        fast_obj = self.fast_obj
        fast_obj.fileIO_forward = open(fast_obj.path_list[0], 'a+')  ## open with a+ mode
        for i in range(len(fast_obj.level_bins_forward_cache)):
            fast_obj.fileIO_forward.write("{: >6d}{: >16.8f}".format(i, fast_obj.level_bins_forward_cache[i]))
            ########## 换行
            fast_obj.fileIO_forward.write("\n")

        fast_obj.fileIO_forward.write("\n")
        fast_obj.fileIO_forward.close()
        fast_obj.level_bins_forward.append(fast_obj.level_bins_forward_cache)

        for obj in self.lockin_obj_list:
            obj.fileIO_forward = open(obj.path_list[0], 'a+')  ## open with a+ mode
            obj.save_data_2_forward_datfile()
            obj.fileIO_forward.close()
            obj.data_x_bins_forward.append(obj.data_x_bins_forward_cache)
            obj.data_y_bins_forward.append(obj.data_y_bins_forward_cache)
            obj.data_m_bins_forward.append(obj.data_m_bins_forward_cache)
            obj.data_t_bins_forward.append(obj.data_t_bins_forward_cache)

    def save_data_for_all_obj_backward(self):
        ########## 将cache中的数据转入 / 写入文件并保存文件 / 保存当前的图片
        fast_obj = self.fast_obj
        fast_obj.fileIO_backward = open(fast_obj.path_list[1], 'a+')  ## open with a+ mode
        for i in range(len(fast_obj.level_bins_backward_cache)):
            fast_obj.fileIO_backward.write("{: >6d}{: >16.8f}".format(i, fast_obj.level_bins_backward_cache[i]))
            ########## 换行
            fast_obj.fileIO_backward.write("\n")

        fast_obj.fileIO_backward.write("\n")
        fast_obj.fileIO_backward.close()
        fast_obj.level_bins_backward.append(fast_obj.level_bins_backward_cache)

        for obj in self.lockin_obj_list:
            obj.fileIO_backward = open(obj.path_list[1], 'a+')  ## open with a+ mode
            obj.save_data_2_backward_datfile()
            obj.fileIO_backward.close()
            obj.data_x_bins_backward.append(obj.data_x_bins_backward_cache)
            obj.data_y_bins_backward.append(obj.data_y_bins_backward_cache)
            obj.data_m_bins_backward.append(obj.data_m_bins_backward_cache)
            obj.data_t_bins_backward.append(obj.data_t_bins_backward_cache)

    def meas_function_only_forward(self, flag_rewrite: bool = True):
        ####################################################################################################
        ########## 初始化
        if self.flag_stat == "start":
            self.all_obj_init(flag_rewrite)

            self.current_i = -1  # 行指标
            self.current_j = -1  # 列指标

        init_level = self.fast_obj.target_levels_list[0]
        self.fast_obj.init_worker(init_level=init_level)
        time.sleep(5.0)

        ami430_obj = self.fast_obj
        target_field = ami430_obj.target_levels_list[-1]
        tol = ami430_obj.tol
        ####################################################################################################
        ########## 进入测试
        self.flag_stat = "running"
        start = time.time()

        ########## 清空cache
        ami430_obj.clean_forward_cache()
        for obj in self.lockin_obj_list:
            obj.clean_forward_cache()

        ami430_obj.target_field = target_field  # 磁场开始升了
        field = ami430_obj.field
        self.current_i = 0
        self.current_j = 0

        while abs(field - target_field) >= tol:  # 进入while循环
            ami430_obj.level_bins_forward_cache.append(field)

            for obj in self.lockin_obj_list:
                obj.read_lockin_levels_forward()

            time.sleep(self.update_time)
            field = ami430_obj.field
        ########## 进行数据保存
        self.save_data_for_all_obj_forward()
        end = time.time()

        ########## 发射一个信号：更新app_one_source_test中的log Screen / progressBar / Remaining Time
        rm_time = (end - start) * (self.scan_slow_dims - 1 - self.current_i)
        progress = (self.current_i + 1) / self.scan_slow_dims
        update_info_list = [self.user_info["test_name"], "forward", rm_time, progress, self.current_i,
                            self.slow_obj_list[0].target_levels_list[self.current_i], self.test_id]
        self.update_sinout.emit(update_info_list)
        self.flag_stat = "finish"

    def meas_function_both_direction(self, flag_rewrite: bool = True):
        ####################################################################################################
        ########## 初始化
        if self.flag_stat == "start":
            self.all_obj_init(flag_rewrite)

            self.current_i = -1  # 行指标
            self.current_j = -1  # 列指标

        init_level = self.fast_obj.target_levels_list[0]
        self.fast_obj.init_worker(init_level=init_level)
        time.sleep(5.0)

        ami430_obj = self.fast_obj
        target_field = ami430_obj.target_levels_list[-1]
        tol = ami430_obj.tol
        ####################################################################################################
        ########## 进入测试
        self.flag_stat = "running"
        ####################################################################################################
        ########## forward
        start = time.time()

        ami430_obj.target_field = target_field  # 磁场开始升了
        field = ami430_obj.field
        self.current_i = 0
        self.current_j = 0

        while abs(field - target_field) >= tol:  # 进入while循环
            ami430_obj.level_bins_forward_cache.append(field)

            for obj in self.lockin_obj_list:
                obj.read_lockin_levels_forward()

            time.sleep(self.update_time)
            field = ami430_obj.field
        ########## 进行数据保存
        self.save_data_for_all_obj_forward()
        self.flag_direction = -1
        end = time.time()
        time1 = (end - start)

        ########## 发射一个信号：更新app_one_source_test中的log Screen / progressBar / Remaining Time
        rm_time = (time1 * 2) * (self.scan_slow_dims - 1 - self.current_i) + time1
        progress = (2 * self.current_i + 1) / (2 * self.scan_slow_dims)
        update_info_list = [self.user_info["test_name"], "forward", rm_time, progress, self.current_i, 0.0, self.test_id]
        self.update_sinout.emit(update_info_list)

        ####################################################################################################
        ########## backward
        start = time.time()
        if self.flag_direction == -1:
            target_field = self.fast_obj.target_levels_list[0]
            ami430_obj.target_field = target_field  # 磁场开始升了
            field = ami430_obj.field

            while abs(field - target_field) >= tol:  # 进入while循环
                ami430_obj.level_bins_forward_cache.append(field)

                for obj in self.lockin_obj_list:
                    obj.read_lockin_levels_forward()

                time.sleep(self.update_time)
                field = ami430_obj.field

            ########## 进行数据保存
            self.save_data_for_all_obj_backward()
            self.flag_direction = 1

        end = time.time()
        time2 = (end - start)
        ########## 发射一个信号：更新app_one_source_test中的log Screen / progressBar / Remaining Time
        rm_time = (time1 + time2) * (self.scan_slow_dims - 1 - self.current_i)
        progress = (self.current_i + 1) / self.scan_slow_dims
        update_info_list = [self.user_info["test_name"], "backward", rm_time, progress, self.current_i, 0.0, self.test_id]
        self.update_sinout.emit(update_info_list)
        self.flag_stat = "finish"


    ####################################################################################################
    ########## 与信号finish_sinout和stop_sinout相连
    def __send_email_to_user(self, test_content: str,
                             mail_sender: str = 'fsj12132836@163.com',
                             mail_host='smtp.163.com',
                             mail_pass: str = 'REZNQDVYIXHUMULI'):
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
        for obj in self.fast_obj_list:
            datfile_list.append(obj.path_list[0])
            try:
                prefix = obj.source_name + "-forward"
            except:
                prefix = obj.ami_name + "-forward"
            prefix_list.append(prefix)

        for obj in self.lockin_obj_list:
            datfile_list.append(obj.path_list[0])
            prefix = obj.lockin_name + "-forward"
            prefix_list.append(prefix)

        if self.flag_back:
            for obj in self.fast_obj_list:
                datfile_list.append(obj.path_list[1])
                try:
                    prefix = obj.source_name + "-backward"
                except:
                    prefix = obj.ami_name + "-backward"
                prefix_list.append(prefix)

            for obj in self.lockin_obj_list:
                datfile_list.append(obj.path_list[1])
                prefix = obj.lockin_name + "-backward"
                prefix_list.append(prefix)

        cola_dat_file = write_coalesce_file(datfile_list, prefix_list)
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