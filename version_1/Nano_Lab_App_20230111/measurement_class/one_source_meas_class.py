import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from utilities.utility_package import *
import os
import threading

import os
import matplotlib.pyplot as plt
import matplotlib.lines as line
from matplotlib.animation import FuncAnimation


####################################################################################################
############################## 测试新的one_source_meas_new_class
class one_source_meas_class():
    ####################################################################################################
    ########## 使用一个gate进行测试的类, gate可以是 YokogawaGS200 / Keithley2400
    ########## 需要将用户的输入信息输入这个类中
    def __init__(self, source_obj, user_info: dict, slope_fast: float, flag_back:bool = False):
        self.source_obj = source_obj
        self.slope_fast = slope_fast

        self.user_info = user_info

        self.current_index = -1
        self.current_index_mod = 0
        self.current_sweep_num = -1

        self.flag_stat = ""
        self.flag_direction = 1  # +1 forward, -1 backward
        self.flag_save = False  # 是否保存当前的图片, True为保存, False为不保存
        self.scan_dims = len(self.source_obj.target_levels_list)

        self.forward_fig_save_path = get_fig_save_path(datfile_path=self.source_obj.path_list[0])
        self.flag_back = flag_back
        if self.flag_back == True:
            self.backward_fig_save_path = get_fig_save_path(datfile_path=self.source_obj.path_list[1])
        else:
            self.backward_fig_save_path = ""

    def meas_function_only_forward(self, scan_repeat: int, stop_level: float, flag_rewrite: bool):
        ####################################################################################################
        ########## 初始化
        self.source_obj.init_worker()
        write_source_datfile_header(datfile_path=self.source_obj.path_list[0], rewrite=flag_rewrite)

        self.current_index = -1
        self.current_index_mod = 0
        self.current_sweep_num = -1

        self.source_obj.fileIO_list = []
        ####################################################################################################
        ########## 进入测试
        self.flag_stat = "running"

        for i in range(scan_repeat):  # 这个Loop仅供测试使用
            ####################################################################################################
            ########## forward
            print("第 %d 次扫\n" % int((self.current_index + 1) / self.scan_dims))
            self.current_index_mod = 0
            self.current_index += 1
            self.source_obj.level_bins_forward_cache = []

            target_level_start = self.source_obj.target_levels_list[0]
            self.source_obj.set_source_level_fast(target_level=target_level_start, slope=self.slope_fast)

            self.source_obj.read_source_level_forward(self.current_index_mod)
            for j in range(self.scan_dims - 1):
                self.current_index += 1
                self.current_index_mod += 1
                self.source_obj.set_source_level_slow_forward(self.current_index_mod)
                self.source_obj.read_source_level_forward(self.current_index_mod)
                # self.source_obj.scan_for_one_step_forward(self.current_index_mod, self.current_index)

            self.current_sweep_num += 1
            ########## 写入文件并保存文件 / 保存当前的图片
            # self.fig
            # plt.savefig(self.forward_fig_save_path + '//fig_' + str(self.current_sweep_num) + '.png', format="png", bbox_inches='tight',  transparent=True)

            self.source_obj.fileIO_list.append(open(self.source_obj.path_list[0], 'a+'))  ## open with a+ mode
            self.source_obj.save_data_2_forward_datfile()
            self.source_obj.fileIO_list = []

            ########## 清空cache
            self.source_obj.level_bins_forward.append(self.source_obj.level_bins_forward_cache)

        #################### 结束测试并关闭文件并发送邮件
        try:
            self.flag_stat = "finish"
            self.source_obj.init_worker(init_level=stop_level, slope=self.slope_fast)
            self.send_email_to_user(receiver=self.user_info["user_email"], test_content="test is stopped !")
        except Exception as e:
            print("出现了错误？？")
            print(e)

    def meas_function_both_direction(self, scan_repeat: int, stop_level: float, flag_rewrite: bool):
        ####################################################################################################
        ########## 初始化
        self.source_obj.init_worker()
        write_source_datfile_header(datfile_path=self.source_obj.path_list[0], rewrite=flag_rewrite)

        self.current_index = -1
        self.current_index_mod = 0

        self.source_obj.fileIO_list = []
        ####################################################################################################
        ########## 进入测试
        self.flag_stat = "running"

        target_level_start = self.source_obj.target_levels_list[0]
        self.source_obj.set_source_level_fast(target_level=target_level_start, slope=self.slope_fast)

        for i in range(scan_repeat):  # 这个Loop仅供测试使用
            ####################################################################################################
            ########## forward
            print("第 %d 次前扫\n" % int((self.current_index + 1) / self.scan_dims))
            self.flag_direction = 1
            self.current_index_mod = 0
            self.current_index += 1

            self.source_obj.read_source_level_forward(self.current_index_mod)
            for j in range(self.scan_dims - 1):
                self.current_index += 1
                self.current_index_mod += 1
                self.source_obj.set_source_level_slow_forward(self.current_index_mod)
                self.source_obj.read_source_level_forward(self.current_index_mod)
                # self.source_obj.scan_for_one_step_forward(self.current_index_mod, self.current_index)

            ########## 写入文件并保存
            self.source_obj.fileIO_list.append(open(self.source_obj.path_list[0], 'a+'))  ## open with a+ mode
            self.source_obj.save_data_2_forward_datfile()

            ########## 清空cache
            self.source_obj.level_bins_forward.append(self.source_obj.level_bins_forward_cache)
            self.source_obj.level_bins_forward_cache = []

            ####################################################################################################
            ########## backward
            print("第 %d 次后扫\n" % int((self.current_index + 1) / self.scan_dims - 1))
            self.flag_direction = -1
            self.source_obj.fileIO_list.append(open(self.source_obj.path_list[1], 'a+'))  ## open with a+ mode

            self.source_obj.read_source_level_backward(self.current_index_mod)
            self.source_obj.save_data_to_backward_datfile(self.current_index_mod, self.current_index)

            for j in range(self.scan_dims - 1):
                self.current_index -= 1
                self.current_index_mod -= 1
                self.source_obj.scan_for_one_step_backward(self.current_index_mod, self.current_index)

            self.current_index += self.scan_dims - 1

            ########## 写入文件并保存
            self.source_obj.fileIO_list.append(open(self.source_obj.path_list[1], 'a+'))  ## open with a+ mode
            self.source_obj.save_data_2_backward_datfile()
            self.source_obj.fileIO_list = []

            ########## 清空cache
            self.source_obj.level_bins_backward.append(self.source_obj.level_bins_backward_cache)
            self.source_obj.level_bins_backward_cache = []

        #################### 结束测试并关闭文件并发送邮件

        try:
            self.flag_stat = "finish"
            self.source_obj.init_worker(init_level=stop_level, slope=self.slope_fast)
            self.send_email_to_user(receiver=self.user_info["user_email"], test_content="test is stopped !")
        except Exception as e:
            print("出现了错误？？")
            print(e)

    def send_email_to_user(self, receiver: str, test_content: str,
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
        message['To'] = receiver
        message['Subject'] = '测试结束'

        # 推荐使用html格式的正文内容，这样比较灵活，可以附加图片地址，调整格式等
        # 设置html格式参数
        part1 = MIMEText(test_content, 'html', 'utf-8')

        # 将内容附加到邮件主体中
        message.attach(part1)

        # 登录并发送
        try:
            smtpObj = smtplib.SMTP()
            smtpObj.connect(mail_host)
            smtpObj.login(mail_sender, mail_pass)
            smtpObj.sendmail(
                mail_sender, receiver, message.as_string())
            print('send email success')
            smtpObj.quit()
        except smtplib.SMTPException as e:
            print('send email error', e)

    def create_single_meas_thread(self, scan_repeat: int, stop_level: float, flag_back: bool, flag_rewrite: bool):
        if flag_back == False:
            meas_thread = threading.Thread(target=self.meas_function_only_forward,
                                           args=(scan_repeat, stop_level, flag_rewrite))  # 更新数据
        else:
            meas_thread = threading.Thread(target=self.meas_function_both_direction,
                                           args=(scan_repeat, stop_level, flag_rewrite))  # 更新数据
        return meas_thread