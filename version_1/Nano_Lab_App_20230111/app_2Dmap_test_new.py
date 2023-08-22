import sys

import os, time
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QMenu, QAction
from PyQt5 import QtCore

from PyQt5.QtWidgets import QApplication, QFileDialog
import pyqtgraph as pg
import numpy as np
from time import sleep

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from utilities.utility_package import *
import json

from inspector_line_roi import *
from window_test_info import *
# from ui_2dmap import *
from ui_2dmap_new import *

from measurement_class.map_qthread_worker import *
from measurement_class.map_qthread_settime_worker import *
from measurement_class.linecut_qthread_worker import *
from measurement_class.linecut_qthread_settime_worker import *

class app_2Dmap_test(QMainWindow, Ui_MainWindow):
    qmut = QtCore.QMutex()
    ########## 定义信号
    # line_roi_signal = QtCore.pyqtSignal(list)

    def __init__(self, window_title: str = "2D map test"):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(window_title)

        self.lockin_channel_comboBox.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.lockin_channel_comboBox.customContextMenuRequested.connect(self.show_Menu)

        self.loadButton.clicked.connect(self.loadTask)
        self.runButton.clicked.connect(self.__runTask)
        self.stopButton.clicked.connect(self.__stopTask)
        self.clearButton.clicked.connect(self.clearPlot)
        self.deleteButton.clicked.connect(self.__deleteAll)
        self.addButton.clicked.connect(self.show_window_test_info)

        self.show_map_ch.clicked.connect(self.show_map_channel)
        self.show_line_ch.clicked.connect(self.show_line_channel)
        self.show_error_ch.clicked.connect(self.show_error_channel)
        self.show_leak_ch.clicked.connect(self.show_leak_channel)
        self.show_line_roi_ch.clicked.connect(self.show_line_roi_channel)
        # self.show_iso_ch.clicked.connect(self.show_isocurve_channel)
        self.log_radioButton.clicked.connect(lambda: self.log_mode_changed())

        self.update_doubleSpinBox.valueChanged.connect(
            lambda: self.update_time_changed(self.update_doubleSpinBox.value()))
        self.testname_comboBox.currentIndexChanged.connect(
            lambda: self.update_current_test_id(self.testname_comboBox.currentIndex()))
        self.lockin_name_comboBox.currentIndexChanged.connect(
            lambda: self.update_current_lockin_index(self.lockin_name_comboBox.currentIndex()))
        self.lockin_channel_comboBox.currentTextChanged.connect(
            lambda: self.update_current_lockin_channel(self.lockin_channel_comboBox.currentText()))
        self.indexSlider.valueChanged.connect(
            lambda: self.update_current_slice_index(self.indexSlider.value()))
        self.selectdirection_comboBox.currentTextChanged.connect(
            lambda: self.update_current_direction(self.selectdirection_comboBox.currentText()))

        self.current_root_path = os.getcwd()
        self.update_time = int(self.update_doubleSpinBox.value() * 1000)
        self.timer = QtCore.QTimer(self)

        ########## different task cache
        self.current_test_id = -1
        self.current_test_type = ""
        self.current_lockin_index = self.lockin_name_comboBox.currentIndex()
        self.current_lockin_channel = self.lockin_channel_comboBox.currentText()
        self.current_slice_index = self.indexSlider.value()
        self.current_direction = ""
        self.current_update_direction = ""
        self.current_stat = ""
        self.current_flag_back = False

        self.current_img_data = []
        self.current_scan_fast_obj = None
        self.current_scan_slow_obj = None
        self.current_lockin_obj = None

        self.flag_plot = False
        self.flag_update = False

        self.multi_thread_list = []
        self.test_type_list = []
        self.user_info_dict_list = []  # the list of user info dict
        self.slow_obj_list_list = []  # the list of slow obj list
        self.fast_obj_list_list = []  # the list of fast obj list
        self.slow_ch_list_list = []  # 有时候我们可能只需要扫一条或者几条关于n的线, 这时候需要两台source作为slow_ch
        self.fast_ch_list_list = []
        self.lockin_obj_list_list = []
        self.lockin_ch_list_list = []
        self.flag_back_list = []
        self.flag_stat_list = []
        self.progress_list = []
        self.remaintime_list = []
        self.test_log_io_list = []

        # self.test_matrix_forward_list = []  # only for test
        # self.test_matrix_backward_list = []  # only for test
        ########## 各种控件(窗口)
        self.__set_plotwidget_config()

        # 一定要在主窗口类的初始化函数中对子窗口进行实例化，如果在其他函数中实例化子窗口
        # 可能会出现子窗口闪退的问题
        self.inspector_line_roi = inspector_line_roi()
        self.inspector_line_roi.inspector_sinout.connect(self.__update_line_roi)
        self.window_test_info = window_test_info()
        self.window_test_info.add_test_sinout.connect(self.load_Task_from_window)

        # self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        # self.isoLine.sigDragged.connect(self.update_isocurve)
        #
        # self.iso = pg.IsocurveItem(level=0.8, pen='g')
        # img_item = self.imageView_map.getImageItem()
        # self.iso.setParentItem(img_item)

    def show_Menu(self, pos):
        lockin_channel_action_menu = QMenu(self.lockin_channel_comboBox)
        display_action = lockin_channel_action_menu.addAction("display")
        action = lockin_channel_action_menu.exec_(QtGui.QCursor.pos())

        # def atom_list_import_action():  # 这个action不能直接接handleOnImport，这个Import是带参数item的
        #     # 如果能打开menu的话肯定是选中item了的
        #     print("hello world")
        #
        # display_action.triggered.connect(atom_list_import_action)
        # lockin_channel_action_menu.addAction(display_action)

        return

    def __set_plotwidget_config(self):
        pg.setConfigOptions(imageAxisOrder='row-major')

        self.title_label = pg.LabelItem(justify='right')
        self.GLayout_Widget.addItem(self.title_label)
        self.plotWidget_line = self.GLayout_Widget.addPlot(row=1, col=0)
        # self.plotWidget_line = self.GLayout_Widget.addPlot(title="Title", left='y', bottom='x')

        # self.plotWidget_line.setLabel("left", "值")
        # self.plotWidget_line.setLabel("bottom", "Volt")
        # self.plotWidget_line.showGrid(x=True, y=True)
        # self.plotWidget_line.setLabels(title='pyqtgraph test', left='y', bottom='x', right='r', top='u')
        # label_style = {"font-family": "Times", "font-size": "16pt"}
        # pw.getAxis('left').setLabel('Current (A)', **label_style)
        # pw.getAxis('bottom').setLabel('Voltage (V)', **label_style)

        self.curve_line_forward = self.plotWidget_line.plot(pen='b')
        self.curve_line_backward = self.plotWidget_line.plot(pen='r')
        self.curve_error_forward = self.plotWidget_error.plot(pen='b')
        backward_pen = pg.mkPen('r', width=1.5, style=QtCore.Qt.DashLine)
        self.curve_error_backward = self.plotWidget_error.plot(pen=backward_pen)
        self.curve_leak_forward = self.plotWidget_leak.plot(pen='b')
        self.curve_leak_backward = self.plotWidget_leak.plot(pen=backward_pen)

        hist = self.imageView_map.getHistogramWidget()
        hist.vb.setMouseEnabled(y=False)  # makes user interaction a little easier

    ####################################################################################################################
    # 小窗口弹出提示
    ####################################################################################################################
    @classmethod
    def informMsg(cls, msg: str):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("inform")
        msgBox.setText(msg)
        msgBox.exec_()  # 模态

    @classmethod
    def questionMsg(cls, msg: str):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("确认框")
        reply = QMessageBox.information(msgBox,  # 使用infomation信息框
                                        "标题",
                                        msg,
                                        QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            return True
        if reply == QMessageBox.No:
            return False
        msgBox.exec_()  # 模态

    def closeEvent(self, event):
        # reply = QMessageBox.question(self, '提示',
        #                              "是否要关闭所有窗口?",
        #                              QMessageBox.Yes | QMessageBox.No,
        #                              QMessageBox.No)
        reply = self.questionMsg(msg="是否要关闭所有窗口?")
        if reply:
            # for task in self.multi_thread_list:
            #     for obj in task.slow_obj_list:
            #         obj.shutdown()
            #     for obj in task.fast_obj_list:
            #         obj.shutdown()
            #     for lockin in task.fast_obj_list:
            #         lockin.shutdown()

            event.accept()
            sys.exit(0)  # 退出程序
        else:
            event.ignore()

    ####################################################################################################################
    # Task related functions : LOAD / New qthread_obj
    ####################################################################################################################
    def load_Task_from_window(self, add_test_sinout):
        fileName = add_test_sinout["info_file_path"]
        self.load_Task_from_json(fileName)

        ########## 更新
        ########## 每次添加new item后, 当前的item还是原来那个item
        if len(self.multi_thread_list) == 1:  ########## 当前只有一个任务
            self.current_test_id = 0
            self.update_current_test_id(new_id=self.current_test_id)
        else:  ########## 当前已有多个任务
            self.current_test_id = self.testname_comboBox.count() - 1
            self.testname_comboBox.setCurrentIndex(self.current_test_id)  ########## 不需要写update_current_test_id, 它会自动调用

        self.informMsg(msg=" Task load successfully ")

    def loadTask(self):
        ########## 选择文件
        fileName, fileType = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Json File", self.current_root_path,
                                                                   "Text Files(*.json *.txt)")

        if fileName == "":
            self.informMsg(msg=" You did not choose a json file ")
            return
        self.pathEdit.setText(fileName)

        fileType = fileName.split(".")[-1]
        current_path_split = fileName.split('\\')
        self.current_root_path = "\\".join(current_path_split[0:-1])

        ########## 载入
        if fileType == "json":  # 单线程测试
            self.load_Task_from_json(fileName)
        elif fileType == "txt":  # 多线程测试
            with open(fileName, mode='r', encoding='utf-8') as f:
                content = f.readlines()  # content是一个列表

            for i in range(len(content)):
                json_filepath = content[i].split('\n')[0]
                self.load_Task_from_json(fileName=json_filepath)

        ########## 更新
        ########## 每次添加new item后, 当前的item还是原来那个item
        # print("testname combox count", self.testname_comboBox.count())  ########## just for test
        # print("current test id", self.current_test_id)  ########## just for test
        if len(self.multi_thread_list) == 1:  ########## 当前只有一个任务
            self.current_test_id = 0
            self.update_current_test_id(new_id=self.current_test_id)
        else:  ########## 当前已有多个任务
            self.current_test_id = self.testname_comboBox.count() - 1
            self.testname_comboBox.setCurrentIndex(self.current_test_id)  ########## 不需要写update_current_test_id, 它会自动调用

        self.informMsg(msg=" Task load successfully ")

    def load_Task_from_json(self, fileName: str):
        ####################################################################################################
        ##########  load task : 创建一个one_source_meas_class对象
        with open(fileName, mode='r', encoding='utf-8') as f:
            ##########  将多个字典从json文件中读出来
            dict_list = json.load(f)

        print(fileName)
        fileName_split = fileName.split("/")
        print(fileName_split)
        now_path = "\\".join(fileName_split[0:-1])
        print(now_path)
        ##########  修改文件路径:因为换了一台电脑或者改变文件夹路径就会报错
        user_info_dict = dict_list[0]
        user_info_dict["info_file_path"] = fileName
        for index in range(1, len(dict_list)):
            now_dict = dict_list[index]
            now_dict["path_list"] = self.__change_filepath(path_list=now_dict["path_list"], now_path=now_path)

        ########## 把修改后的信息重新写入json文件中
        with open(fileName, mode='w', encoding='utf-8') as f:
            json.dump(dict_list, f)

        ####################################################################################################
        ########## create a qthread obj
        self.__create_new_qthread_obj(dict_list)

        ##########  更新testname_comboBox
        test_name = user_info_dict["sample_name"] + "-" + user_info_dict["test_name"]
        self.testname_comboBox.addItem(test_name)

    def __load_Task_info_on_logScreen(self, dict_list:list):
        ########## 清空log Screen
        self.reset_log_Screen()
        self.logScreen.appendPlainText('json file load successfully !')

        user_info_dict = dict_list[0]
        for key, value in user_info_dict.items():
            self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))
        self.logScreen.appendPlainText('\n\n')

        for index in range(1, len(dict_list)):
            now_dict = dict_list[index]
            ########## 设置方向
            self.logScreen.appendPlainText('第{:d}台仪器的信息:'.format(index))
            for key, value in now_dict.items():
                self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))
            self.logScreen.appendPlainText('\n')

    def reset_log_Screen(self):
        # 清空文本
        self.logScreen.clear()
        self.logScreen.setPlainText("This is a log screen :")

    def __clear_out_comboxes(self):
        self.selectdirection_comboBox.clear()
        self.fastch_comboBox.clear()
        self.slowch_comboBox.clear()
        self.lockin_name_comboBox.clear()

    def __create_new_qthread_obj(self, dict_list:list):
        user_info_dict = dict_list[0]

        ########## 确认是否要对该任务进行测试
        ########## load a new task for acquiring data or only for displaying data
        current_stat = user_info_dict["flag_stat"]
        if current_stat == "finish":
            flag_init = False
        else:
            flag_init = True
            # flag_init = self.questionMsg(msg=" 当前任务的状态为{flag_stat}, 是否对该任务进行测试 ? ".format(flag_stat=current_stat))

        ########## add to list
        slow_obj_list = []
        fast_obj_list = []
        slow_ch_list = []
        fast_ch_list = []
        lockin_obj_list = []
        lockin_ch_list = []

        for index in range(1, len(dict_list)):
            if 'source_type' in dict_list[index]:
                source_info_dict = dict_list[index]
                ########## 将source_info转化为source_obj
                source_obj = get_source_obj_by_dict(source_info_dict=source_info_dict, flag_init=flag_init)
                if source_info_dict["source_order"] == "scan_fast":
                    fast_obj_list.append(source_obj)
                    fast_ch_list.append(source_info_dict["source_name"])

                if source_info_dict["source_order"] == "scan_slow":
                    slow_obj_list.append(source_obj)
                    slow_ch_list.append(source_info_dict["source_name"])

            elif 'mf_type' in dict_list[index]:
                mf_info_dict = dict_list[index]
                ########## 将source_info转化为mf_obj
                mf_obj = get_mf_obj_by_dict(mf_info_dict=mf_info_dict, flag_init=flag_init)
                if mf_info_dict["mf_order"] == "scan_fast":
                    fast_obj_list.append(mf_obj)
                    fast_ch_list.append(mf_info_dict["mf_name"])

                if mf_info_dict["mf_order"] == "scan_slow":
                    slow_obj_list.append(mf_obj)
                    slow_ch_list.append(mf_info_dict["mf_name"])

            elif 'lockin_type' in dict_list[index]:
                lockin_info_dict = dict_list[index]
                ########## 将source_info转化为source_obj
                lockin_obj = get_lockin_obj_by_dict(lockin_info_dict=lockin_info_dict, flag_init=flag_init)
                lockin_obj_list.append(lockin_obj)
                lockin_ch_list.append(lockin_info_dict["lockin_name"])

        ########## create a new qthread obj
        current_test_id = self.testname_comboBox.count()
        if user_info_dict["test_type"] == "2D map":
            map_thread = map_qthread_worker(test_id=current_test_id, slow_obj_list=slow_obj_list,
                                            fast_obj_list=fast_obj_list, lockin_obj_list=lockin_obj_list,
                                            user_info=user_info_dict)
            map_thread.update_sinout.connect(self.__update)
            map_thread.finish_sinout.connect(self.__finish)
            map_thread.run_sinout.connect(self.__run_again)
            if not flag_init:
                map_thread.flag_stat = "finish"

            self.multi_thread_list.append(map_thread)
            self.test_type_list.append("2D map")

        elif user_info_dict["test_type"] == "linecut":
            linecut_thread = linecut_qthread_worker(test_id=current_test_id, fast_obj_list=fast_obj_list,
                                                    lockin_obj_list=lockin_obj_list, user_info=user_info_dict)
            linecut_thread.update_sinout.connect(self.__update)
            linecut_thread.finish_sinout.connect(self.__finish)
            linecut_thread.run_sinout.connect(self.__run_again)
            if not flag_init:
                linecut_thread.flag_stat = "finish"

            self.multi_thread_list.append(linecut_thread)
            self.test_type_list.append("linecut")

        elif user_info_dict["test_type"] == "linecut_settime":
            linecut_thread = linecut_qthread_settime_worker(test_id=current_test_id, fast_obj_list=fast_obj_list,
                                                            lockin_obj_list=lockin_obj_list, user_info=user_info_dict,
                                                            update_time=user_info_dict["update_time"])
            linecut_thread.update_sinout.connect(self.__update)
            linecut_thread.finish_sinout.connect(self.__finish)
            linecut_thread.run_sinout.connect(self.__run_again)
            if not flag_init:
                linecut_thread.flag_stat = "finish"

            self.multi_thread_list.append(linecut_thread)
            self.test_type_list.append("linecut_settime")

        elif user_info_dict["test_type"] == "map_settime":
            map_thread = map_qthread_settime_worker(test_id=current_test_id, slow_obj_list=slow_obj_list,
                                                    fast_obj_list=fast_obj_list, lockin_obj_list=lockin_obj_list,
                                                    user_info=user_info_dict, update_time=user_info_dict["update_time"])
            map_thread.update_sinout.connect(self.__update)
            map_thread.finish_sinout.connect(self.__finish)
            map_thread.run_sinout.connect(self.__run_again)
            if not flag_init:
                map_thread.flag_stat = "finish"

            self.multi_thread_list.append(map_thread)
            self.test_type_list.append("map_settime")

        ########## 更新几个list_list变量
        self.user_info_dict_list.append(user_info_dict)
        self.flag_stat_list.append(current_stat)

        self.slow_obj_list_list.append(slow_obj_list)
        self.slow_ch_list_list.append(slow_ch_list)
        self.fast_obj_list_list.append(fast_obj_list)
        self.fast_ch_list_list.append(fast_ch_list)
        self.lockin_obj_list_list.append(lockin_obj_list)
        self.lockin_ch_list_list.append(lockin_ch_list)

        self.flag_back_list.append(user_info_dict["flag_back"])
        self.progress_list.append(0.0)
        self.remaintime_list.append(0.0)

    def add_items_2_comboxes(self, new_id: int):
        for item in self.slow_ch_list_list[new_id]:
            self.slowch_comboBox.addItem(item)
        for item in self.fast_ch_list_list[new_id]:
            self.fastch_comboBox.addItem(item)
        for item in self.lockin_ch_list_list[new_id]:
            self.lockin_name_comboBox.addItem(item)

        if self.flag_back_list[self.current_test_id]:
            self.selectdirection_comboBox.addItem("forward")
            self.selectdirection_comboBox.addItem("backward")
        else:
            self.selectdirection_comboBox.addItem("forward")

    def get_current_and_flag(self, new_id: int):
        self.current_test_id = new_id  ## 当前的测试序号

        self.current_test_type = self.test_type_list[new_id]
        self.current_stat = self.multi_thread_list[new_id].flag_stat
        if self.multi_thread_list[new_id].flag_direction == 1:
            self.current_update_direction = "forward"
        else:
            self.current_update_direction = "backward"

        self.current_lockin_index = self.lockin_name_comboBox.currentIndex()
        self.current_lockin_channel = self.lockin_channel_comboBox.currentText()
        self.current_slice_index = self.indexSlider.value()
        self.current_direction = self.selectdirection_comboBox.currentText()

        self.current_scan_fast_obj = self.fast_obj_list_list[new_id][0]
        if self.current_test_type == "2D map" or self.current_test_type == "map_settime":
            self.current_scan_slow_obj = self.slow_obj_list_list[new_id][0]
        self.current_lockin_obj = self.lockin_obj_list_list[new_id][self.current_lockin_index]

        if self.flag_back_list[self.current_test_id]:
            self.current_flag_back = True
        else:
            self.current_flag_back = False

        # self.flag_plot = False  # 为了安全起见, 把flag_plot关掉, 这样在切换test_id时就不会由于调用update_current_slice_index()而出错
        if self.current_stat == "start":  # 还没开始测试, 就不用作图
            index_max = -1
        else:  # 需要作图
            if self.current_stat == "running" or self.current_stat == "stop" or self.current_stat == "pause":
                index_max = self.multi_thread_list[new_id].current_i  # 此时current_i对应的是正在被更新的数据的指标
            else:
                index_max = len(self.current_scan_fast_obj.level_bins_forward) - 1 # 此时current_i - 1对应的是已经更新完的最高指标

        self.indexSlider.setMaximum(index_max)
        self.indexSlider.setValue(index_max)
        self.indexLabel.setText(str(index_max))
        self.current_slice_index = self.indexSlider.maximum()
        # print("index max is : ", index_max)
        # print("test index is : ", new_id)
        # print("testname index is : ", self.testname_comboBox.currentIndex())

        #################### 设置indexSlider.max必须在这一步之前完成
        if self.current_stat == "start":  # 还没开始测试, 就不用作图
            self.flag_plot = False
            self.flag_update = False
        else:  # 需要作图
            self.flag_plot = True
            if self.current_stat == "running":
                self.flag_update = True
            else:
                self.flag_update = False

    def __change_filepath(self, path_list:list, now_path:str):
        path_forward = path_list[0]
        path_forward_split = path_forward.split("\\")
        now_path_forward = now_path + "\\" + path_forward_split[-1]

        path_backward = path_list[1]
        path_backward_split = path_backward.split("\\")
        now_path_backward = now_path + "\\" + path_backward_split[-1]

        return [now_path_forward, now_path_backward]

    ####################################################################################################################
    # Task related functions : RUN / STOP / KILL
    ####################################################################################################################
    def __runTask(self):
        ################################################################################################################
        # basic check
        ################################################################################################################
        if self.multi_thread_list == []:
            self.informMsg(msg="当前没有任务！")
            return

        if self.current_stat == "finish":
            return

        ################################################################################################################
        # disable all the buttons for a while
        ################################################################################################################
        self.loadButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.runButton.setEnabled(False)
        self.clearButton.setEnabled(False)
        self.deleteButton.setEnabled(False)

        ################################################################################################################
        # set logScreen PlainText
        ################################################################################################################
        self.logScreen.appendPlainText("\n\n")
        test_time = get_time_list(time.localtime(time.time()))
        time_str = "{}-{}-{}_{}-{}-{}".format(test_time[0], test_time[1], test_time[2], test_time[3], test_time[4],
                                              test_time[5])
        self.logScreen.appendPlainText(
            ' ****** {:s}开始进行测试 ******'.format(self.user_info_dict_list[self.current_test_id]["test_name"]))
        self.logScreen.appendPlainText(' ****** : {:s} : ******'.format(time_str))

        ################################################################################################################
        # run the multi_thread_tests
        ################################################################################################################
        for i in range(len(self.multi_thread_list)):
            if self.multi_thread_list[i].flag_stat == "start":
                self.multi_thread_list[i].start()  # 之前错误的写法：self.multi_thread_list[i].run()
                self.indexSlider.setMaximum(0)
                self.indexSlider.setValue(0)
            elif self.multi_thread_list[i].flag_stat == "stop" or self.multi_thread_list[i].flag_stat == "pause":
                self.multi_thread_list[i].is_pause = False
                self.indexSlider.setMaximum(self.multi_thread_list[i].current_i)
                self.indexSlider.setValue(self.multi_thread_list[i].current_i)
                self.current_slice_index = self.indexSlider.value()

        new_id = self.testname_comboBox.currentIndex()
        self.update_current_test_id(new_id=new_id)

        ################################################################################################################
        # print just for test
        ################################################################################################################
        print("各种flag")
        print(self.flag_plot)
        print(self.flag_update)
        print(self.current_flag_back)

    def __deleteAll(self):
        ########## 清空之前再确认一遍
        reply = self.questionMsg(msg="Are you sure to delete all the information ?")
        if reply == False:
            return
        else:
            self.__killTask()

    def __killTask(self):
        try:
            self.timer.stop()

            self.current_test_id = -1
            self.current_direction = ""

            self.multi_thread_list = []
            self.user_info_dict_list = []
            self.slow_obj_list_list = []
            self.fast_obj_list_list = []
            self.slow_ch_list_list = []
            self.fast_ch_list_list = []

            self.flag_back_list = []
            self.progress_list = []
            self.remaintime_list = []
            self.test_log_io_list = []

            ########## 重置控件
            self.loadButton.setEnabled(True)
            self.reset_log_Screen()

            self.progressBar.setValue(0)
            self.lcdNumber.display(999999)
            self.pathEdit.setText(" current file path ")
        except Exception as e:
            print(e)

    def __stopTask(self):
        if self.multi_thread_list == []:
            self.informMsg(msg="当前没有任务！")
            return

        self.loadButton.setEnabled(True)
        self.runButton.setEnabled(True)
        self.clearButton.setEnabled(True)
        self.deleteButton.setEnabled(True)

        test_index = self.testname_comboBox.currentIndex()
        # test_name = self.testname_comboBox.currentText()
        # print(test_index, test_id)

        self.multi_thread_list[test_index].ispause = True
        self.timer.stop()

    ####################################################################################################################
    # To Do :
    ####################################################################################################################
    def __call_analyzer(self):

        return

    ####################################################################################################################
    # communicate with the qthread_worker through sinout
    ####################################################################################################################
    def __update(self, update_sinout: list):
        if update_sinout[4] == -1:  # 当前的test已经结束测试了
            self.timer.stop()
            return

        if update_sinout[-1] == self.current_test_id:
            if not self.current_flag_back:
                self.current_update_direction = "forward"
                self.flag_update = False
                self.current_stat = "pause"
                self.timer.stop()

                ########## 作二维图像
                self.update_current_direction(direction=self.current_direction)
            elif self.current_flag_back and update_sinout[1] == "backward":
                self.current_update_direction = "forward"
                self.flag_update = False
                self.current_stat = "pause"
                self.timer.stop()

                ########## 作二维图像
                if self.current_direction == "backward":
                    self.update_current_direction(direction=self.current_direction)
            elif self.current_flag_back and update_sinout[1] == "forward":
                self.current_update_direction = "backward"
                self.flag_update = True
                self.current_stat = "running"

                ########## 作二维图像
                if self.current_direction == "forward":
                    self.update_current_direction(direction=self.current_direction)

        ####################################################################################################
        ########## 扫完一条曲线之后将曲线都清空，并将2D mapping更新
        self.logScreen.appendPlainText("\n")
        self.logScreen.appendPlainText(' ========== test id : {:d} ========== '.format(update_sinout[-1]))
        self.logScreen.appendPlainText(' ========== test name : {:s} ========== '.format(update_sinout[0]))
        self.logScreen.appendPlainText('            scan direction : {:s}            '.format(update_sinout[1]))
        self.logScreen.appendPlainText(
            '            {:s} : {:.3f}            '.format("remaining time", update_sinout[2]))
        self.logScreen.appendPlainText('            {:s} : {:.3f}            '.format("progress bar", update_sinout[3]))
        self.logScreen.appendPlainText(
            '            The slow index {:d} (level : {:.4f}) is finished            '.format(update_sinout[4],
                                                                                              update_sinout[5]))

        if update_sinout[-1] != self.current_test_id:
            return

        self.lcdNumber.display(update_sinout[2])
        self.progressBar.setValue(int(update_sinout[3] * 100))

        # self.indexSlider.setMaximum(update_sinout[4])
        # self.indexSlider.setValue(update_sinout[4])
        # self.indexLabel.setText(str(update_sinout[4]))

        ####################################################################################################
        ########## update map & clear linecut
        # self.current_slice_index = self.indexSlider.value()
        ########## 一维曲线不作更新, 在__run_again()函数中会对一维曲线进行更新asdasd

    def __finish(self, finish_sinout: list):
        self.logScreen.appendPlainText("\n")
        self.logScreen.appendPlainText(' ========== test id : {:d} ========== '.format(finish_sinout[-1]))
        self.logScreen.appendPlainText(
            ' {:s} : {:s} '.format(self.user_info_dict_list[self.current_test_id]["test_name"], finish_sinout[0]))

        if self.current_test_id == finish_sinout[-1]:
            self.loadButton.setEnabled(True)
            self.runButton.setEnabled(True)
            self.clearButton.setEnabled(True)
            self.deleteButton.setEnabled(True)

            self.timer.stop()
            self.flag_update = False

    def __run_again(self, run_sinout: list):
        if self.current_test_id == run_sinout[-1]:
            self.current_stat = "running"
            self.flag_plot = True
            self.flag_update = True

            self.clear_all_lines()

            self.indexSlider.setMaximum(run_sinout[0])
            self.indexSlider.setValue(run_sinout[0])
            self.indexLabel.setText(str(run_sinout[0]))

            ###################################################################################################
            ######### update map & clear linecut
            self.current_slice_index = self.indexSlider.value()

            self.__timer_start()

    ####################################################################################################################
    # show or hide the channels
    ####################################################################################################################
    def show_window_test_info(self):
        self.window_test_info.show()

    def show_map_channel(self):
        if self.show_map_ch.isChecked():
            self.imageView_map.hide()
        else:
            self.imageView_map.show()
            ########## 绘制二维图像
            self.update_current_direction()  # 包含了self.current_img_data的更新

    def show_line_channel(self):
        if (self.show_line_ch.isChecked()):
            self.plotWidget_line.hide()
        else:
            self.plotWidget_line.show()

    def show_error_channel(self):
        if (self.show_error_ch.isChecked()):
            self.plotWidget_error.hide()
        else:
            self.plotWidget_error.show()

    def show_leak_channel(self):
        if (self.show_leak_ch.isChecked()):
            self.plotWidget_leak.hide()
        else:
            self.plotWidget_leak.show()

    def show_line_roi_channel(self):
        if len(self.current_img_data) == 0:
            return

        if self.show_line_roi_ch.isChecked():
            ########## movable要设置为False, 如果设置为True, 虽然可以移动, 但坐标轴也会变
            pos_x = self.current_scan_fast_obj.target_levels_list[0]
            pos_y = self.current_scan_slow_obj.target_levels_list[0]
            self.line_roi = pg.LineSegmentROI(positions=([pos_x, pos_y], [pos_x, pos_y]),
                                              handles=(None, None),
                                              pen="r",
                                              movable=False,
                                              maxBounds=QtCore.QRect(0, 0, 10, 10))

            self.line_roi.sigRegionChangeFinished.connect(self.__display_line_roi_info)
            self.imageView_map.addItem(self.line_roi)

            self.inspector_line_roi.flag_close = False
            self.inspector_line_roi.show()
            self.inspector_line_roi.display_line_roi_info([np.nan, np.nan, pos_x, pos_y, pos_x, pos_y])
        else:
            self.inspector_line_roi.flag_close = True
            self.inspector_line_roi.close()
            self.imageView_map.removeItem(self.line_roi)
            # self.imageView_map.addItem(self.line_roi_label)

    def __display_line_roi_info(self):
        point_list = self.line_roi.getLocalHandlePositions()
        point1 = point_list[0][1]
        point2 = point_list[1][1]
        x1 = point1.x()
        y1 = point1.y()
        x2 = point2.x()
        y2 = point2.y()

        ########## just for test
        # print("第一个点坐标")
        # print(x1,y1)
        # print("第二个点坐标")
        # print(x2,y2)

        if x1 == x2:
            self.inspector_line_roi.display_line_roi_info([np.inf, np.inf, x1, y1, x2, y2])
        else:
            slope = (y2 - y1) / (x2 - x1)
            interp = y2 - slope * x2
            self.inspector_line_roi.display_line_roi_info([slope, interp, x1, y1, x2, y2])

    def show_isocurve_channel(self):
        if len(self.current_img_data) == 0:
            return

        if self.show_iso_ch.isChecked():
            # Draggable line for setting isocurve level
            hist = self.imageView_map.getHistogramWidget()
            hist.vb.addItem(self.isoLine)
            levels = hist.getLevels()
            min_level = levels[0]
            max_level = levels[1]

            self.isoLine.setValue(0.8*(max_level - min_level) + min_level)
            self.isoLine.setZValue(1000)  # bring iso line above contrast controls

            # build isocurves from smoothed data
            self.iso.setData(pg.gaussianFilter(self.current_img_data, (2, 2)))
            self.iso.setLevel(self.isoLine.value())
            img_item = self.imageView_map.getImageItem()
            self.iso.setParentItem(img_item)
            self.iso.setZValue(1000)
            # img_item.addItem(self.iso)
        else:
            hist = self.imageView_map.getHistogramWidget()
            hist.vb.removeItem(self.isoLine)
            img_item = self.imageView_map.getImageItem()
            img_item.removeItem(self.iso)

    def update_isocurve(self):
        self.iso.setLevel(self.isoLine.value())

    def clearPlot(self):
        self.imageView_map.clear()
        self.plotWidget_line.clear()
        self.plotWidget_error.clear()
        self.plotWidget_leak.clear()

    def clear_all_lines(self):
        self.plotWidget_line.clear()
        self.plotWidget_error.clear()
        self.plotWidget_leak.clear()

        self.plotWidget_line.setLabel("left", "值")
        self.plotWidget_line.setLabel("bottom", "值")
        self.plotWidget_line.showGrid(x=True, y=True)

        self.curve_line_forward = self.plotWidget_line.plot(pen='b')
        self.curve_line_backward = self.plotWidget_line.plot(pen='r')

        self.curve_error_forward = self.plotWidget_error.plot(pen='b')
        backward_pen = pg.mkPen('r', width=1.5, style=QtCore.Qt.DashLine)
        self.curve_error_backward = self.plotWidget_error.plot(pen=backward_pen)

        self.curve_leak_forward = self.plotWidget_leak.plot(pen='b')
        self.curve_leak_backward = self.plotWidget_leak.plot(pen=backward_pen)

    ####################################################################################################
    #################### 更新图像和曲线
    def update_current_test_id(self, new_id: int):
        if new_id == -1:  ########## 当前无任务或任务正在加载
            return

        self.timer.stop()

        self.flag_plot = False  # 为了安全起见, 把flag_plot关掉, 这样在切换test_id时就不会由于调用update_current_slice_index()而出错
        ########## 清空combox
        self.__clear_out_comboxes()

        ########## 将用户信息打印到logscreen中
        fileName = self.user_info_dict_list[new_id]["info_file_path"]
        with open(fileName, mode='r', encoding='utf-8') as f:
            ##########  将多个字典从json文件中读出来
            dict_list = json.load(f)

        self.__load_Task_info_on_logScreen(dict_list=dict_list)
        ########## 添加
        self.add_items_2_comboxes(new_id=new_id)
        ########## 得到flag_和current_
        self.get_current_and_flag(new_id=new_id)

        # todo:img_plot
        self.imageView_map.clear()
        self.clear_all_lines()
        self.plotWidget_line.setLabel("left", self.lockin_name_comboBox.currentText() + "_" + self.lockin_channel_comboBox.currentText())
        self.plotWidget_line.setLabel("bottom", self.fastch_comboBox.currentText())
        ########## 绘制一维曲线
        self.update_current_slice_index(self.current_slice_index)
        ########## 绘制二维图像
        self.update_current_direction()  # 包含了self.current_img_data的更新
        ########## 重启计时器更新
        if self.flag_update:
            self.__timer_start()

    def update_current_lockin_index(self, lockin_index: int):
        self.current_lockin_index = lockin_index
        self.current_lockin_obj = self.lockin_obj_list_list[self.current_test_id][lockin_index]

        if not self.flag_plot:
            return

        if self.current_stat == "start":
            return

        if self.current_stat == "":
            return

        #################### 作二维图
        self.update_current_direction()

        #################### 作一维图
        self.plotWidget_line.setLabel("left", self.lockin_name_comboBox.currentText() + "_" + self.lockin_channel_comboBox.currentText())
        self.update_current_slice_index()

    def update_current_lockin_channel(self, lockin_channel: str):
        self.current_lockin_channel = lockin_channel

        if not self.flag_plot:
            return

        if self.current_stat == "start":
            return

        if self.current_stat == "":
            return

        #################### 作二维图
        self.update_current_direction()

        #################### 作一维图
        self.plotWidget_line.setLabel("left", self.lockin_name_comboBox.currentText() + "_" + self.lockin_channel_comboBox.currentText())
        self.update_current_slice_index()

    def update_current_slice_index(self, slice_index: int = -1):
        if self.current_test_id == -1:
            return

        if not self.flag_plot:
            return

        if self.current_stat == "start":
            return

        if self.current_stat == "":
            return

        #################### 仅更新一维曲线
        if slice_index != -1:
            self.current_slice_index = slice_index

        if self.current_test_type == "2D map" or self.current_test_type == "map_settime":  ## todo:将label切换道 plotwidget 中显示会更好
            # label.setText("<span style='font-size: 12pt'>x=%0.1f,   <span style='color: red'>y1=%0.1f</span>,   <span style='color: green'>y2=%0.1f</span>"
            #               % (mousePoint.x(), data1[index], data2[index]))
            self.indexLabel.setText(str(self.current_slice_index))

            #################### 添加曲线的标题
            new_title = ""
            for obj in self.slow_obj_list_list[self.current_test_id]:
                new_title += obj.name + " : " + str(round(obj.target_levels_list[self.current_slice_index], 3)) + " , "
            self.title_label.setText(new_title)

            #################### 更新曲线
            self.__plot_all_lines()
        else:
            self.indexLabel.setText(" ")
            self.__plot_all_lines()

    def update_current_direction(self, direction: str = "none"):
        #################### 仅更新二维图像
        if direction != "none":
            self.current_direction = direction

        if not self.flag_plot:
            return

        if self.current_stat == "start":
            return

        if self.current_stat == "":
            return

        if self.show_map_ch.isChecked():
            return

        if self.log_radioButton.isChecked():
            self.__plot_img(True)
        else:
            self.__plot_img(False)

    def log_mode_changed(self):
        if self.show_map_ch.isChecked():
            self.log_radioButton.setChecked(False)
            return

        if not self.flag_plot:
            self.log_radioButton.setChecked(False)
            return

        if len(self.current_img_data) == 0:
            self.log_radioButton.setChecked(False)
            return

        self.imageView_map.clear()
        if self.log_radioButton.isChecked():
            self.__plot_img(flag_log=True)
        else:
            self.__plot_img(flag_log=False)

    def update_time_changed(self, update_time: float):
        if self.flag_update == False:
            return
        self.timer.stop()
        self.update_time = int(update_time * 1000)
        if self.multi_thread_list[self.current_test_id].flag_stat == "running":
            self.__timer_start()

    def __update_line_roi(self, inspector_sinout):
        x_o = inspector_sinout[0]
        y_o = inspector_sinout[1]
        x_e = inspector_sinout[2]
        y_e = inspector_sinout[3]
        # self.line_roi.setPos(([x_o, y_o], [x_e, y_e])) #################### doesn't work
        self.line_roi.movePoint(handle=self.line_roi.getHandles()[0], pos=[x_o, y_o], finish=False)
        self.line_roi.movePoint(handle=self.line_roi.getHandles()[1], pos=[x_e, y_e], finish=True)

        # self.imageView_map.removeItem(self.line_roi)
        # self.line_roi = pg.LineSegmentROI(positions=([x_o, y_o], [x_e, y_e]), handles=(None, None), pen="r",
        #                                   movable=False,
        #                                   maxBounds=QtCore.QRect(0, 0, 10, 10))
        # self.line_roi.sigRegionChangeFinished.connect(self.__display_line_roi_info)
        # self.imageView_map.addItem(self.line_roi)

    #################### 启动定时器 时间间隔秒
    def __timer_start(self):
        self.timer.timeout.connect(self.update_all_lines)
        self.timer.start(self.update_time)

    def update_all_lines(self):
        if not self.flag_plot:  # todo:不要注释掉
            return
        if not self.flag_update:
            return
        if self.current_slice_index != self.indexSlider.maximum():
            return
        if self.current_update_direction == "forward":
            self.__plot_all_lines_from_cache(direction="forward")
        elif self.current_update_direction == "backward":
            self.__plot_all_lines_from_cache(direction="backward")


    #################### 作二维图和一维曲线
    def __plot_all_lines(self):
        if self.current_slice_index == self.indexSlider.maximum():
            if self.current_stat == "running" or self.current_stat == "stop":
                if self.current_update_direction == "forward":
                    self.__plot_all_lines_from_cache(direction="forward")
                    if self.current_flag_back:
                        self.curve_line_backward.setData([])
                elif self.current_update_direction == "backward":
                    # self.clear_all_lines()
                    self.__plot_all_lines_from_list(direction="forward")
                    self.__plot_all_lines_from_cache(direction="backward")
                else:
                    return
            elif self.current_stat == "finish" or self.current_stat == "pause":
                if self.current_flag_back:
                    # self.clear_all_lines()
                    self.curve_line_backward.setData([])
                    self.curve_line_forward.setData([])
                    self.__plot_all_lines_from_list(direction="forward")
                    self.__plot_all_lines_from_list(direction="backward")
                else:
                    # self.clear_all_lines()
                    self.__plot_all_lines_from_list(direction="forward")
        else:
            if self.current_flag_back:
                # self.clear_all_lines()
                self.__plot_all_lines_from_list(direction="forward")
                self.__plot_all_lines_from_list(direction="backward")
            else:
                # self.clear_all_lines()
                self.__plot_all_lines_from_list(direction="forward")

    def __plot_all_lines_from_cache(self, direction: str):
        if direction == "forward":
            #################### 作line_ch
            if not self.show_line_ch.isChecked():
                x_vals, y_vals = self.get_xy_from_cache("forward")
                self.curve_line_forward.setData(x=x_vals, y=y_vals)

            #################### 作error_ch
            if not self.show_error_ch.isChecked():
                error_bins = self.current_scan_fast_obj.error_bins_forward_cache
                self.curve_error_forward.setData(error_bins)

            #################### 作leak_ch
            if not self.show_leak_ch.isChecked():
                leak_bins = self.current_scan_fast_obj.leak_bins_forward_cache
                self.curve_leak_forward.setData(leak_bins)
        else:
            #################### 作line_ch
            if not self.show_line_ch.isChecked():
                x_vals, y_vals = self.get_xy_from_cache("backward")
                self.curve_line_backward.setData(x=x_vals, y=y_vals)

            #################### 作error_ch
            if not self.show_error_ch.isChecked():
                error_bins = self.current_scan_fast_obj.error_bins_backward_cache
                self.curve_error_backward.setData(error_bins)

            #################### 作leak_ch
            if not self.show_leak_ch.isChecked():
                leak_bins = self.current_scan_fast_obj.leak_bins_backward_cache
                self.curve_leak_backward.setData(leak_bins)

    def __plot_all_lines_from_list(self, direction: str):
        if direction == "forward":
            if not self.show_line_ch.isChecked():
                x_vals, y_vals = self.get_xy_from_list("forward")
                self.curve_line_forward.setData(x=x_vals, y=y_vals)

            if not self.show_error_ch.isChecked():
                error_bins = self.current_scan_fast_obj.error_bins_forward[self.current_slice_index]
                self.curve_error_forward.setData(error_bins)

            if not self.show_leak_ch.isChecked():
                leak_bins = self.current_scan_fast_obj.leak_bins_forward[self.current_slice_index]
                self.curve_leak_forward.setData(leak_bins)
        else:
            if not self.show_line_ch.isChecked():
                x_vals, y_vals = self.get_xy_from_list("backward")
                self.curve_line_backward.setData(x=x_vals, y=y_vals)

            if not self.show_error_ch.isChecked():
                error_bins = self.current_scan_fast_obj.error_bins_backward[self.current_slice_index]
                self.curve_error_backward.setData(error_bins)

            if not self.show_leak_ch.isChecked():
                leak_bins = self.current_scan_fast_obj.leak_bins_backward[self.current_slice_index]
                self.curve_leak_backward.setData(leak_bins)

    def __plot_img(self, flag_log: bool):
        if self.current_test_type != "2D map":
            return

        y_matrix = self.get_y_matrix_from_list()
        if len(y_matrix) == 0:
            return
        self.current_img_data = y_matrix

        self.imageView_map.clear()
        #################### 缩放和平移很重要
        pos_x = self.current_scan_fast_obj.target_levels_list[0]
        pos_y = self.current_scan_slow_obj.target_levels_list[0]
        size_x = np.size(self.current_img_data, 0)
        size_y = np.size(self.current_img_data, 1)
        scale_x = (self.current_scan_fast_obj.target_levels_list[size_x-1] -
                   self.current_scan_fast_obj.target_levels_list[0]) / size_x
        scale_y = (self.current_scan_slow_obj.target_levels_list[size_y-1] -
                   self.current_scan_slow_obj.target_levels_list[0]) / size_y
        if flag_log:
            try:
                log_img = np.log(np.abs(y_matrix))
                self.imageView_map.setImage(img=log_img, pos=[pos_x, pos_y], scale=[scale_x, scale_y])
                # self.imageView_map.showAxes(True)
            except Exception as e:
                self.log_radioButton.setChecked(False)
                self.__plot_img(flag_log=False)
                self.informMsg(msg=" Can't do log mode ")
        else:
            self.imageView_map.setImage(img=y_matrix, pos=[pos_x, pos_y], scale=[scale_x, scale_y])
            # img_item = self.imageView_map.getImageItem()
            # img_item.showAxes(True)
            # img.setTransform(tr)
            # self.imageView_map.showAxes(True)


    #################### 数据的获取
    def get_xy_from_cache(self, direction: str):
        if direction == "forward":
            if self.current_lockin_channel == "x":
                y_vals = self.current_lockin_obj.data_x_bins_forward_cache
            elif self.current_lockin_channel == "y":
                y_vals = self.current_lockin_obj.data_y_bins_forward_cache
            elif self.current_lockin_channel == "m":
                y_vals = self.current_lockin_obj.data_m_bins_forward_cache
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = self.current_lockin_obj.data_t_bins_forward_cache

            cache_len = len(y_vals)
            x_vals = self.current_scan_fast_obj.level_bins_forward_cache[0:cache_len]
        else:
            if self.current_lockin_channel == "x":
                y_vals = self.current_lockin_obj.data_x_bins_backward_cache
            elif self.current_lockin_channel == "y":
                y_vals = self.current_lockin_obj.data_y_bins_backward_cache
            elif self.current_lockin_channel == "m":
                y_vals = self.current_lockin_obj.data_m_bins_backward_cache
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = self.current_lockin_obj.data_t_bins_backward_cache
            cache_len = len(y_vals)
            x_vals = self.current_scan_fast_obj.level_bins_backward_cache[0:cache_len]

        return x_vals, y_vals

    def get_xy_from_list(self, direction: str):
        #################### 因为lockin的数据读取在source之后, 因此以lockin的长度为准
        if direction == "forward":
            if self.current_lockin_channel == "x":
                y_vals = self.current_lockin_obj.data_x_bins_forward[self.current_slice_index]
            elif self.current_lockin_channel == "y":
                y_vals = self.current_lockin_obj.data_y_bins_forward[self.current_slice_index]
            elif self.current_lockin_channel == "m":
                # print("current slice index is ", self.current_slice_index)
                y_vals = self.current_lockin_obj.data_m_bins_forward[self.current_slice_index]
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = self.current_lockin_obj.data_t_bins_forward[self.current_slice_index]

            x_vals = self.current_scan_fast_obj.level_bins_forward[self.current_slice_index]
        else:
            if self.current_lockin_channel == "x":
                y_vals = self.current_lockin_obj.data_x_bins_backward[self.current_slice_index]
            elif self.current_lockin_channel == "y":
                y_vals = self.current_lockin_obj.data_y_bins_backward[self.current_slice_index]
            elif self.current_lockin_channel == "m":
                y_vals = self.current_lockin_obj.data_m_bins_backward[self.current_slice_index]
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = self.current_lockin_obj.data_t_bins_backward[self.current_slice_index]

            x_vals = self.current_scan_fast_obj.level_bins_backward[self.current_slice_index]

        return x_vals, y_vals

    def get_y_matrix_from_list(self):
        if self.current_direction == "forward":
            if not self.current_lockin_obj.data_x_bins_forward:
                return []

            if self.current_lockin_channel == "x":
                y_matrix = np.transpose(self.current_lockin_obj.data_x_bins_forward)
            elif self.current_lockin_channel == "y":
                y_matrix = np.transpose(self.current_lockin_obj.data_y_bins_forward)
            elif self.current_lockin_channel == "m":
                y_matrix = np.transpose(self.current_lockin_obj.data_m_bins_forward)
            else:  # self.valuech_comboBox.currentText() == "t"
                y_matrix = np.transpose(self.current_lockin_obj.data_t_bins_forward)

            return y_matrix
        else:
            if not self.current_lockin_obj.data_x_bins_backward:
                return []

            if self.current_lockin_channel == "x":
                y_matrix = np.transpose(self.current_lockin_obj.data_x_bins_backward)
            elif self.current_lockin_channel == "y":
                y_matrix = np.transpose(self.current_lockin_obj.data_y_bins_backward)
            elif self.current_lockin_channel == "m":
                y_matrix = np.transpose(self.current_lockin_obj.data_m_bins_backward)
            else:  # self.valuech_comboBox.currentText() == "t"
                y_matrix = np.transpose(self.current_lockin_obj.data_t_bins_backward)

            return y_matrix


if __name__ == "__main__":
    import sys

    # app = QtWidgets.QApplication(sys.argv)
    # MainWindow = QtWidgets.QMainWindow()
    # ui = Ui_MainWindow()
    # ui.setupUi(MainWindow)
    # MainWindow.show()
    # sys.exit(app.exec_())

    app = QtWidgets.QApplication(sys.argv)
    app_single_thread = app_2Dmap_test()
    app_single_thread.show()

    sys.exit(app.exec_())