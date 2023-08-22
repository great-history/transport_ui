import sys

import os, time
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt5.QtCore import QUrl, QThread, pyqtSignal, QMutex

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

from ui_2dmap_test import *
from map_qthread_worker import *
from linecut_qthread_worker import *
from linecut_qthread_settime_worker import *


class app_quantum_transport(QMainWindow, Ui_MainWindow):
    qmut = QMutex()

    def __init__(self, window_title: str = "2D map test"):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(window_title)

        ####################################################################################################
        ########## 任务的上传/执行/杀掉
        self.loadButton.clicked.connect(self.loadTask)
        self.runButton.clicked.connect(self.runTask)
        self.stopButton.clicked.connect(self.stopTask)
        self.clearButton.clicked.connect(self.clearAllChannel)
        self.deleteButton.clicked.connect(self.deleteAll)

        ####################################################################################################
        ########## 各通道的显示
        self.show_map_ch.clicked.connect(self.show_map_channel)
        self.show_line_ch.clicked.connect(self.show_line_channel)
        self.show_roi_ch.clicked.connect(self.show_roi_channel)
        self.show_error_ch.clicked.connect(self.show_error_channel)
        self.show_leak_ch.clicked.connect(self.show_leak_channel)

        ####################################################################################################
        ########## 计时器及更新
        self.timer = QtCore.QTimer(self)
        self.update_time = int(self.update_doubleSpinBox.value() * 1000)
        self.update_doubleSpinBox.valueChanged.connect(
            lambda: self.update_time_changed(self.update_doubleSpinBox.value()))

        ####################################################################################################
        #################### 图像和曲线的显示
        ########## 图像的指标:(test_id, direction, lockin_index, lockin_channel)
        ########## 曲线的指标:(test_id, direction, lockin_index, lockin_channel, slice_index)
        self.current_test_id = -1
        self.current_direction = ""
        self.current_lockin_index = 0
        self.current_lockin_channel = self.valuech_comboBox.currentText()
        self.current_slice_index = 0
        ########## 响应函数
        self.indexSlider.valueChanged.connect(
            lambda: self.current_slice_index_changed(self.indexSlider.value()))
        self.testname_comboBox.currentIndexChanged.connect(
            lambda: self.current_testid_changed(self.testname_comboBox.currentIndex()))
        self.selectdirection_comboBox.currentTextChanged.connect(
            lambda: self.current_direction_changed(self.selectdirection_comboBox.currentText()))
        self.valuech_comboBox.currentTextChanged.connect(
            lambda: self.current_lockin_channel_changed(self.valuech_comboBox.currentText()))
        self.lockinch_comboBox.currentIndexChanged.connect(
            lambda: self.current_lockin_index_changed(self.lockinch_comboBox.currentIndex()))

        ####################################################################################################
        #################### 图像和曲线的ROI操作
        self.__set_plotwidget_config()

        ####################################################################################################
        #################### 存储
        self.current_root_path = os.getcwd()

        self.multi_thread_list = []
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

    def __set_plotwidget_config(self):
        pg.setConfigOptions(imageAxisOrder='row-major')
        self.plotWidget_roi.hide()

        # Item for displaying image data
        self.plotwidget_img = self.imageView_map.addPlot()
        ########## add Items
        self.img = pg.ImageItem()
        # Custom ROI for selecting an image region
        self.roi = pg.ROI([0,0], [10,10])
        self.roi.addRotateHandle([1, 1], [0.5, 0.5])  # 第一个[]是把手的位置, 第二个[]是中心(在操作过程种中心不变其他部位相对中心运动)
        self.roi.addRotateHandle([0, 0], [0.5, 0.5])

        ## handles rotating around opposite corner
        self.roi.addRotateHandle([1, 0], [0.5, 0.5])
        # self.roi.addRotateHandle([1, 0], [0, 1])
        self.roi.addRotateHandle([0, 1], [0.5, 0.5])
        # self.roi.addRotateHandle([0, 1], [1, 0])

        ## handles rotating/scaling around center
        # self.roi.addScaleRotateHandle([0, 0.5], [0.5, 0.5])
        self.roi.addScaleHandle([1, 0.5], [0, 0.5])
        # self.roi.addScaleRotateHandle([1, 0.5], [0.5, 0.5])
        self.roi.addScaleHandle([0, 0.5], [1, 0.5])
        self.roi.addScaleHandle([0.5, 0], [0.5, 1])
        self.roi.addScaleHandle([0.5, 1], [0.5, 0])
        # Custom ROI for selecting a line region
        self.line_roi = pg.LineSegmentROI([[10, 64], [120, 64]], pen='r')
        # Isocurve drawing
        self.iso = pg.IsocurveItem(level=0.8, pen='g')
        self.iso.setParentItem(self.img)
        self.iso.setZValue(5)
        # Contrast/color control
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img)
        # Draggable line for setting isocurve level
        self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        self.hist.vb.addItem(self.isoLine)
        self.hist.vb.setMouseEnabled(y=False)  # makes user interaction a little easier
        self.isoLine.setValue(0.8)
        self.isoLine.setZValue(1000)  # bring iso line above contrast controls

        self.plotwidget_img.addItem(self.img)  # imageView_map是GraphicaLayoutWidget
        self.plotwidget_img.addItem(self.roi)
        self.plotwidget_img.addItem(self.line_roi)
        self.plotwidget_img.addItem(self.iso)
        # self.plotwidget_img.removeItem(self.img)
        # self.plotwidget_img.removeItem(self.roi)
        # self.plotwidget_img.removeItem(self.line_roi)
        # self.plotwidget_img.removeItem(self.iso)
        self.imageView_map.addItem(self.hist)
        # self.imageView_map.removeItem(self.hist)

        ########## 之后会把该部分代码转移到其他地方
        # Generate image data
        data = np.random.normal(size=(200, 200))
        data[20:80, 20:80] += 2.
        data = pg.gaussianFilter(data, (3, 3))
        data += np.random.normal(size=(200, 200)) * 0.1
        self.img.setImage(data)
        self.hist.setLevels(data.min(), data.max())

        # build isocurves from smoothed data
        self.iso.setData(pg.gaussianFilter(data, (2, 2)))
        # set position and scale of image
        # self.img.scale(0.2, 0.2)
        # self.img.translate(-50, 0)
        # zoom to fit imageo
        self.plotwidget_img.autoRange()

        self.plotWidget_line.setLabel("left", "值")
        self.plotWidget_line.setLabel("bottom", "Volt")
        self.plotWidget_line.showGrid(x=True, y=True)

        self.curve_line_forward = self.plotWidget_line.plot(pen='b')
        self.curve_line_backward = self.plotWidget_line.plot(pen='r')
        self.curve_error_forward = self.plotWidget_error.plot(pen='b')
        backward_pen = pg.mkPen('r', width=1.5, style=QtCore.Qt.DashLine)
        self.curve_error_backward = self.plotWidget_error.plot(pen=backward_pen)
        self.curve_leak_forward = self.plotWidget_leak.plot(pen='b')
        self.curve_leak_backward = self.plotWidget_leak.plot(pen=backward_pen)
        #
        # plt.addLegend()
        # # l = pg.LegendItem((100,60), offset=(70,30))  # args are (size, offset)
        # # l.setParentItem(plt.graphicsItem())   # Note we do NOT call plt.addItem in this case
        #
        # c1 = plt.plot([1, 3, 2, 4], pen='r', symbol='o', symbolPen='r', symbolBrush=0.5, name='red plot')
        # c2 = plt.plot([2, 1, 4, 3], pen='g', fillLevel=0, fillBrush=(255, 255, 255, 30), name='green plot')

    def reset_log_Screen(self):
        # 清空文本
        self.logScreen.clear()
        self.logScreen.setPlainText("This is a log screen :")

    ####################################################################################################
    ########## 小窗口弹出提示
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
            event.accept()
            sys.exit(0)  # 退出程序
        else:
            event.ignore()

    ####################################################################################################
    ########## 任务的上传/执行/杀掉
    def loadTask(self):
        fileName, fileType = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Json File", self.current_root_path,
                                                                   "Text Files(*.json *.txt)")

        if fileName == "":
            self.informMsg(msg=" You did not choose a json file ")
            return

        if self.multi_thread_list != []:
            ########## 清空之前再确认一遍
            reply = self.questionMsg(msg=" Are you sure to delete all the existing threads ? ")
            if reply == False:
                return
            else:
                self.__killTask()
                self.clearAllChannel()
                self.__set_plotwidget_config()

        self.pathEdit.setText(fileName)

        fileType = fileName.split(".")[-1]
        current_path_split = fileName.split('\\')
        self.current_root_path = "\\".join(current_path_split[0:-1])
        self.reset_log_Screen()
        self.testname_comboBox.clear()


        if fileType == "json":  # 单线程测试
            self.loadTask_from_json(fileName)
        elif fileType == "txt":  # 多线程测试
            with open(fileName, mode='r', encoding='utf-8') as f:
                content = f.readlines()  # content是一个列表

            for i in range(len(content)):
                json_filepath = content[i].split('\n')[0]
                self.loadTask_from_json(fileName=json_filepath)

        # print("current_test_id")
        # print(self.current_test_id)
        self.current_test_id = self.testname_comboBox.currentIndex()
        # print(self.current_test_id)
        # print(self.testname_comboBox.count())

        for item in self.slow_ch_list_list[self.current_test_id]:
            self.slowch_comboBox.addItem(item)
        for item in self.fast_ch_list_list[self.current_test_id]:
            self.fastch_comboBox.addItem(item)
        for item in self.lockin_ch_list_list[self.current_test_id]:
            self.lockinch_comboBox.addItem(item)
        self.current_lockin_index = self.lockinch_comboBox.currentIndex()
        # current_lockinch = self.lockinch_comboBox.currentText()

        if self.flag_back_list[self.current_test_id] == True:
            self.selectdirection_comboBox.addItem("forward")
            self.selectdirection_comboBox.addItem("backward")
        else:
            self.selectdirection_comboBox.addItem("forward")
        self.current_direction = "forward"

        self.informMsg(msg=" Task load successfully ")

    def loadTask_from_json(self, fileName: str):
        ####################################################################################################
        ########## load task : 创建一个one_source_meas_class对象
        with open(fileName, mode='r', encoding='utf-8') as f:
            ########## 将多个字典从json文件中读出来
            dict_list = json.load(f)

        # self.current_test_id += 1
        user_info_dict = dict_list[0]
        self.user_info_dict_list.append(user_info_dict)
        test_name = user_info_dict["sample_name"] + "-" + user_info_dict["test_name"]
        self.testname_comboBox.addItem(test_name)

        ########## 清空
        self.fastch_comboBox.clear()
        self.slowch_comboBox.clear()
        self.selectdirection_comboBox.clear()

        ########## 首先是用户信息, 将其打印到logscreen中
        self.logScreen.appendPlainText('json file load successfully !')
        for key, value in user_info_dict.items():
            self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))
        self.logScreen.appendPlainText('\n\n')

        slow_obj_list = []
        fast_obj_list = []
        slow_ch_list = []
        fast_ch_list = []
        lockin_obj_list = []
        lockin_ch_list = []
        for index in range(1, len(dict_list)):
            if 'source_type' in dict_list[index]:  ########## 源表
                source_info_dict = dict_list[index]
                ########## 设置方向
                flag_back = source_info_dict["flag_back"]

                self.logScreen.appendPlainText('第{:d}台仪器的信息:'.format(index))
                for key, value in source_info_dict.items():
                    if key != "path_list":
                        self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))
                self.logScreen.appendPlainText('\n')

                ########## 将source_info转化为source_obj
                source_obj = get_source_obj_by_dict(source_info_dict=source_info_dict)
                if source_info_dict["source_order"] == "scan_fast":
                    fast_obj_list.append(source_obj)
                    fast_ch_list.append(source_info_dict["source_name"])

                if source_info_dict["source_order"] == "scan_slow":
                    slow_obj_list.append(source_obj)
                    slow_ch_list.append(source_info_dict["source_name"])

            elif 'mf_type' in dict_list[index]:  ########## 磁场
                mf_info_dict = dict_list[index]
                ########## 设置方向
                flag_back = mf_info_dict["flag_back"]

                self.logScreen.appendPlainText('第{:d}台仪器的信息:'.format(index))
                for key, value in mf_info_dict.items():
                    if key != "path_list":
                        self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))
                self.logScreen.appendPlainText('\n')

                ########## 将source_info转化为mf_obj
                mf_obj = get_mf_obj_by_dict(mf_info_dict=mf_info_dict)
                if mf_info_dict["mf_order"] == "scan_fast":
                    fast_obj_list.append(mf_obj)
                    fast_ch_list.append(mf_info_dict["mf_name"])

                if mf_info_dict["mf_order"] == "scan_slow":
                    slow_obj_list.append(mf_obj)
                    slow_ch_list.append(mf_info_dict["mf_name"])

            elif 'lockin_type' in dict_list[index]:
                    lockin_info_dict = dict_list[index]
                    ########## 设置方向
                    flag_back = lockin_info_dict["flag_back"]

                    self.logScreen.appendPlainText('第{:d}台仪器的信息:'.format(index))
                    for key, value in lockin_info_dict.items():
                        if key != "path_list":
                            self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))
                    self.logScreen.appendPlainText('\n')

                    ########## 将source_info转化为source_obj
                    lockin_obj = get_lockin_obj_by_dict(lockin_info_dict=lockin_info_dict)
                    lockin_obj_list.append(lockin_obj)
                    lockin_ch_list.append(lockin_info_dict["lockin_name"])

        ########## 创建QThread对象
        self.current_test_id += 1

        if user_info_dict["test_type"] == "2D map":
            map_thread = map_qthread_worker(test_id=self.current_test_id, slow_obj_list=slow_obj_list, fast_obj_list=fast_obj_list, lockin_obj_list=lockin_obj_list, user_info=user_info_dict)
            map_thread.update_sinout.connect(self.__update)
            map_thread.finish_sinout.connect(self.__finish)
            self.multi_thread_list.append(map_thread)
        elif user_info_dict["test_type"] == "linecut":
            linecut_thread= linecut_qthread_worker(test_id=self.current_test_id, fast_obj_list=fast_obj_list, lockin_obj_list=lockin_obj_list, user_info=user_info_dict)
            linecut_thread.update_sinout.connect(self.__update)
            linecut_thread.finish_sinout.connect(self.__finish)
            self.multi_thread_list.append(linecut_thread)
        elif user_info_dict["test_type"] == "linecut_settime":
            linecut_thread= linecut_qthread_settime_worker(test_id=self.current_test_id, fast_obj_list=fast_obj_list, lockin_obj_list=lockin_obj_list, user_info=user_info_dict, update_time=user_info_dict["update_time"])
            linecut_thread.update_sinout.connect(self.__update)
            linecut_thread.finish_sinout.connect(self.__finish)
            self.multi_thread_list.append(linecut_thread)

        ########## 更新几个list_list变量
        self.slow_obj_list_list.append(slow_obj_list)
        self.slow_ch_list_list.append(slow_ch_list)
        self.fast_obj_list_list.append(fast_obj_list)
        self.fast_ch_list_list.append(fast_ch_list)
        self.lockin_obj_list_list.append(lockin_obj_list)
        self.lockin_ch_list_list.append(lockin_ch_list)

        self.flag_back_list.append(flag_back)
        self.progress_list.append(0.0)
        self.remaintime_list.append(0.0)

        # self.test_matrix_forward_list.append(
        #     np.random.normal(size=(map_thread.scan_slow_dims, map_thread.scan_fast_dims)))  # only for test
        # self.test_matrix_backward_list.append(
        #     np.random.normal(size=(map_thread.scan_slow_dims, map_thread.scan_fast_dims)))  # only for test

    def __update(self, update_sinout: list):
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
            '            The slow index {:d} (level : {:.4f}) is finished            '.format(update_sinout[4], update_sinout[5]))
        # self.logScreen.appendPlainText('            The slow index {:d} is starting            '.format(update_sinout[4] + 1))

        if update_sinout[-1] != self.current_test_id:
            return

        self.lcdNumber.display(update_sinout[2])
        self.progressBar.setValue(int(update_sinout[3] * 100))
        self.indexSlider.setMaximum(update_sinout[4])
        self.indexSlider.setValue(update_sinout[4])
        self.indexLabel.setText(str(update_sinout[4]))

        ########## update map & clear linecut
        self.current_direction = update_sinout[1]
        # select_direction = self.selectdirection_comboBox.currentText()
        # print(self.current_direction, select_direction) # only for test

        obj = self.fast_obj_list_list[self.current_test_id][0]
        lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]

        if update_sinout[4] == -1:
            return

        if update_sinout[1] == "forward":
            # scan_fast_dim = len(self.fast_obj_list_list[self.current_test_id][0].level_bins_forward[0])
            if not self.show_line_ch.isChecked():
                x_vals = obj.target_levels_list
                y_vals = self.get_yvals(lockin_obj, index=update_sinout[4], direction="forward")

                self.curve_line_forward.setData(x=x_vals, y=y_vals)
            if not self.show_error_ch.isChecked():
                error_bins = obj.error_bins_forward[update_sinout[4]]
                self.curve_error_forward.setData(error_bins)
            if not self.show_leak_ch.isChecked():
                if obj.leak_bins_forward != []:
                    leak_bins = obj.leak_bins_forward[update_sinout[4]]
                    self.curve_leak_forward.setData(leak_bins)

            if not self.show_map_ch.isChecked():
                if self.selectdirection_comboBox.currentText() == "forward":
                    y_matrix = self.get_ymatrix(lockin_obj, update_sinout[4] + 1, "forward")
                    self.imageView_map.setImage(y_matrix)

            if self.flag_back_list[self.current_test_id] == True:
                self.current_direction = "backward"  # 换方向

        elif update_sinout[1] == "backward":
            self.current_direction = "forward"
            # scan_fast_dim = len(self.fast_obj_list[0].level_bins_forward[0])
            if not self.show_line_ch.isChecked():
                x_vals = obj.target_levels_list[::-1]
                y_vals = self.get_yvals(lockin_obj, index=update_sinout[4], direction="backward")

                self.curve_line_backward.setData(x=x_vals, y=y_vals)
            if not self.show_error_ch.isChecked():
                error_bins = obj.error_bins_backward[update_sinout[4]]
                self.curve_error_backward.setData(error_bins)
            if not self.show_leak_ch.isChecked():
                leak_bins = obj.leak_bins_backward
                if leak_bins != []:
                    self.curve_leak_backward.setData(leak_bins[update_sinout[4]])

            if not self.show_map_ch.isChecked():
                if self.selectdirection_comboBox.currentText() == "backward":
                    y_matrix = self.get_ymatrix(lockin_obj, update_sinout[4] + 1, "backward")
                    self.imageView_map.setImage(y_matrix)

    def __finish(self, finish_sinout: str):
        self.logScreen.appendPlainText("\n")
        self.logScreen.appendPlainText(' ========== test id : {:d} ========== '.format(finish_sinout[-1]))
        self.logScreen.appendPlainText(
            ' {:s} : {:s} '.format(self.user_info_dict_list[self.current_test_id]["test_name"], finish_sinout[0]))

        self.loadButton.setEnabled(True)
        self.runButton.setEnabled(True)
        self.clearButton.setEnabled(True)
        self.deleteButton.setEnabled(True)

        if self.current_test_id == finish_sinout[-1]:
            self.timer.stop()

    def runTask(self):
        if self.multi_thread_list == []:
            self.informMsg(msg="当前没有任务！")
            return

        self.loadButton.setEnabled(False)
        self.stopButton.setEnabled(False)
        self.runButton.setEnabled(False)
        self.clearButton.setEnabled(False)
        self.deleteButton.setEnabled(False)

        self.logScreen.appendPlainText("\n\n")
        test_time = get_time_list(time.localtime(time.time()))
        time_str = "{}-{}-{}_{}-{}-{}".format(test_time[0], test_time[1], test_time[2], test_time[3], test_time[4],
                                              test_time[5])
        self.logScreen.appendPlainText(
            ' ****** {:s}开始进行测试 ******'.format(self.user_info_dict_list[self.current_test_id]["test_name"]))
        self.logScreen.appendPlainText(' ****** : {:s} : ******'.format(time_str))

        for i in range(len(self.multi_thread_list)):
            if self.multi_thread_list[i].flag_stat == "start":
                self.multi_thread_list[i].start()  # 之前错误的写法：self.multi_thread_list[i].run()
                self.indexSlider.setMaximum(0)
                self.indexSlider.setValue(0)
            elif self.multi_thread_list[i].flag_stat == "stopped":
                self.multi_thread_list[i].is_pause = False
                self.indexSlider.setMaximum(self.multi_thread_list[i].current_i - 1)
                self.indexSlider.setValue(self.multi_thread_list[i].current_i - 1)
            self.flag_stat_list.append("running")
        self.__timer_start()

    def deleteAll(self):
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
            self.flag_stat_list = []
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

    def stopTask(self):
        if self.multi_thread_list == []:
            self.informMsg(msg="当前没有任务！")
            return

        self.loadButton.setEnabled(True)
        self.runButton.setEnabled(True)
        self.clearButton.setEnabled(True)
        self.deleteButton.setEnabled(True)

        test_index = self.testname_comboBox.currentIndex()
        test_name = self.testname_comboBox.currentText()
        # print(test_index, test_id)

        self.multi_thread_list[test_index].ispause = True
        self.timer.stop()

    ####################################################################################################
    ########## 各通道的显示
    def show_map_channel(self):
        if (self.show_map_ch.isChecked()):
            self.imageView_map.hide()
        else:
            self.imageView_map.show()

    def show_roi_channel(self):
        if (self.show_roi_ch.isChecked()):
            self.plotWidget_roi.hide()
        else:
            self.plotWidget_roi.show()

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

    def clearAllChannel(self):
        self.imageView_map.clear()
        self.plotWidget_line.clear()
        self.plotWidget_error.clear()
        self.plotWidget_leak.clear()

    ####################################################################################################
    #################### 更新图像和曲线
    #################### 数据的获取
    def get_lockin_channel_from_cache(self, scan_obj, lockin_obj):
        if self.current_direction == "forward":
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_forward_cache
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_forward_cache
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_forward_cache
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_forward_cache
            cache_len = len(y_vals)
            x_vals = scan_obj.level_bins_forward_cache[0:cache_len]
        else:
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_backward_cache
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_backward_cache
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_backward_cache
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_backward_cache
            cache_len = len(y_vals)
            x_vals = scan_obj.level_bins_backward_cache[0:cache_len]

        return x_vals, y_vals

    def get_lockin_channel_from_list(self, scan_obj, lockin_obj):
        #################### 因为lockin的数据读取在source之后, 因此以lockin的长度为准
        if self.current_direction == "forward":
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_forward[self.current_slice_index]
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_forward[self.current_slice_index]
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_forward[self.current_slice_index]
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_forward[self.current_slice_index]
            x_vals = scan_obj.level_bins_forward[self.current_slice_index]
        else:
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_backward[self.current_slice_index]
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_backward[self.current_slice_index]
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_backward[self.current_slice_index]
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_backward[self.current_slice_index]
            x_vals = scan_obj.level_bins_backward[self.current_slice_index]

        return x_vals, y_vals

    def get_lockin_channel_matrix(self):
        lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]
        index = self.indexSlider.maximum()
        if self.current_direction == "forward":
            if self.current_channel == "x":
                y_matrix = np.transpose(lockin_obj.data_x_bins_forward[0:index][:])
            elif self.current_channel == "y":
                y_matrix = np.transpose(lockin_obj.data_y_bins_forward[0:index][:])
            elif self.current_channel == "m":
                y_matrix = np.transpose(lockin_obj.data_m_bins_forward[0:index][:])
            else:  # self.valuech_comboBox.currentText() == "t"
                y_matrix = np.transpose(lockin_obj.data_t_bins_forward[0:index][:])
        else:
            if self.current_channel == "x":
                y_matrix = np.flipud(np.transpose(lockin_obj.data_x_bins_backward[0:index][:]))
            elif self.current_channel == "y":
                y_matrix = np.flipud(np.transpose(lockin_obj.data_y_bins_backward[0:index][:]))
            elif self.current_channel == "m":
                y_matrix = np.flipud(np.transpose(lockin_obj.data_m_bins_backward[0:index][:]))
            else:  # self.valuech_comboBox.currentText() == "t"
                y_matrix = np.flipud(np.transpose(lockin_obj.data_t_bins_backward[0:index][:]))

        return y_matrix

    def get_scan_fast_slice(self):
        scan_obj = self.fast_obj_list_list[self.current_test_id][0]
        lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]

        if self.current_slice_index == self.indexSlider.maximum():
            x_vals, y_vals = self.get_lockin_channel_from_cache(scan_obj, lockin_obj)
        else:
            x_vals, y_vals = self.get_lockin_channel_from_list(scan_obj, lockin_obj)

        return x_vals, y_vals

    #################### 计时器(实时更新)
    def __timer_start(self):
        self.timer.timeout.connect(self.update_all_lines)
        self.timer.start(self.update_time)

    def update_time_changed(self, update_time: float):
        current_status = self.multi_thread_list[self.current_test_id].flag_stat
        if current_status == "start":
            return

        if self.multi_thread_list[self.current_test_id].flag_stat == "running":
            self.timer.stop()
            self.update_time = int(update_time * 1000)
            self.__timer_start()

    def update_all_lines(self):
        if self.current_slice_index != self.indexSlider.maximum():
            return

        ########## update linecut
        obj = self.fast_obj_list_list[self.current_test_id][0]
        lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]
        if self.current_direction == "forward":
            # current_j = self.multi_thread_list[0].current_j - 1  # -1是为了保险起见
            # current_i = self.multi_thread_list[0].current_i
            # if current_j == -1:
            #     return
            if not self.show_line_ch.isChecked():
                y_vals, cache_len = self.get_yvals_and_cachelen(lockin_obj)
                x_vals = obj.target_levels_list[0:cache_len]
                # x_vals = obj.target_levels_list[0:current_j]  ##todo:[0]换成更好的指标

                self.curve_line_forward.setData(x=x_vals, y=y_vals)
                # self.plotWidget_line.plot(self.fast_obj_list[0].level_bins_forward_cache, np.random.normal(size=len(self.fast_obj_list[0].level_bins_forward_cache)),_callSync='off', pen='b')  # 过去蓝线
            if not self.show_error_ch.isChecked():
                error_bins = obj.error_bins_forward_cache
                if error_bins != []:
                    self.curve_error_forward.setData(error_bins)
            if not self.show_leak_ch.isChecked():
                leak_bins = obj.leak_bins_forward_cache
                if leak_bins != []:
                    self.curve_leak_forward.setData(leak_bins)

        elif self.current_direction == "backward":
            # current_i = self.multi_thread_list[0].current_i
            # scan_fast_dim = len(obj.level_bins_backward_cache)
            # if scan_fast_dim == 0:
            #     return
            if not self.show_line_ch.isChecked():
                y_vals, cache_len = self.get_yvals_and_cachelen(lockin_obj)
                x_vals = obj.target_levels_list[-1:(-1-cache_len):-1]
                # x_vals = obj.target_levels_list[-1:(-1 - scan_fast_dim):-1]  ##todo:[0]换成更好的指标
                # y_vals = lockin_obj.data_x_bins_backward_cache[0:scan_fast_dim]
                self.curve_line_backward.setData(x=x_vals, y=y_vals)
                # self.plotWidget_line.plot(self.fast_obj_list[0].level_bins_backward_cache, np.random.normal(size=len(self.fast_obj_list[0].level_bins_backward_cache)), _callSync='off', pen='r')  # 回来红线
            if not self.show_error_ch.isChecked():
                error_bins = obj.error_bins_backward_cache
                self.curve_error_backward.setData(error_bins)
            if not self.show_leak_ch.isChecked():
                if obj.leak_bins_backward_cache != []:
                    leak_bins = obj.leak_bins_backward_cache
                    self.curve_leak_backward.setData(leak_bins)

    def current_testid_changed(self, test_id: int):
        if self.current_test_id == -1:  # 已经清空了
            return

        # print(test_id)
        ########## 清空
        self.slowch_comboBox.clear()
        self.fastch_comboBox.clear()
        self.selectdirection_comboBox.clear()

        ########## add Item
        for item in self.fast_ch_list_list[test_id]:
            self.fastch_comboBox.addItem(item)

        for item in self.slow_ch_list_list[test_id]:
            self.slowch_comboBox.addItem(item)

        if self.flag_back_list[test_id]:
            self.selectdirection_comboBox.addItem("forward")
            self.selectdirection_comboBox.addItem("backward")
        else:
            self.selectdirection_comboBox.addItem("forward")

        print("切换线程")
        ########## reset current_test_id / current_direction / current_lockin_index / current_lockin_channel / current_slice_index
        self.current_test_id = test_id
        # self.current_direction = self.selectdirection_comboBox.currentText()
        self.current_lockin_index = self.lockinch_comboBox.currentIndex()
        self.current_lockin_channel = self.valuech_comboBox.currentText()
        self.indexSlider.setMaximum(self.multi_thread_list[test_id].current_i)
        self.indexSlider.setValue(self.indexSlider.maximum())
        self.current_slice_index = self.indexSlider.value()

        if self.multi_thread_list[self.current_test_id].flag_stat == "start":  # 还没开始跑线程
            return

        self.timer.stop()
        if self.multi_thread_list[test_id].flag_stat == "running":
            if self.multi_thread_list[test_id].flag_direction == 1:
                self.current_direction = "forward"
            else:
                self.current_direction = "backward"
            self.__timer_start()

        self.clearAllChannel()
        self.__set_plotwidget_config()

        # xax = self.plotWidget_line.getAxis('bottom')  # 坐标轴x
        # ticks = [list(zip(range(10), ('16:23', '16:28', '16:33', '16:40', '16:45', '16:23', '16:28', '16:33', '16:40', '16:45')))]
        # xax.setTicks(ticks)
        # self.plotWidget_line.setYRange(padding=0)

    def current_lockin_index_changed(self, index:int):
        self.current_lockin_index = index

    def current_slice_index_changed(self, index: int):
        # if index == self.indexSlider.maximum() and (self.multi_thread_list[0].flag_stat == "finish"):
        #     self.__timer_start()
        # else:
        #     self.timer.stop()

        ########## update linecut
        # if index == 0 and (self.multi_thread_list[self.current_test_id].current_i == -1):
        #     return

        if index == self.indexSlider.maximum() and (self.multi_thread_list[self.current_test_id].flag_stat == "running"):
            return

        # print(index) # only for test
        self.indexLabel.setText(str(index))

        obj = self.fast_obj_list_list[self.current_test_id][0]
        lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]
        if not self.show_line_ch.isChecked():
            y_vals = self.get_yvals(lockin_obj, index=index, direction="forward")
            self.curve_line_forward.setData(x=obj.target_levels_list, y=y_vals)
            if self.flag_back_list[self.current_test_id] == True:
                y_vals = self.get_yvals(lockin_obj, index=index, direction="backward")
                self.curve_line_backward.setData(x=obj.target_levels_list[::-1], y=y_vals)

        if not self.show_error_ch.isChecked():
            self.curve_error_forward.setData(obj.error_bins_forward[index])
            if self.flag_back_list[self.current_test_id] == True:
                self.curve_error_backward.setData((obj.error_bins_backward[index])[::-1])

        if not self.show_leak_ch.isChecked():
            if obj.leak_bins_forward != []:
                self.curve_leak_forward.setData(obj.leak_bins_forward[index])
                if self.flag_back_list[self.current_test_id] == True:
                    self.curve_leak_backward.setData((obj.leak_bins_backward[index])[::-1])

    def current_direction_changed(self, select_direction: str):
        if not self.flag_stat_list:
            return

        if self.multi_thread_list[self.current_test_id].flag_stat == "running":
            index = self.multi_thread_list[self.current_test_id].current_i
        else:
            # index = self.multi_thread_list[self.current_test_id].scan_slow_dims + 1
            index = self.multi_thread_list[self.current_test_id].scan_slow_dims

        lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]

        y_matrix = self.get_ymatrix(lockin_obj, index, select_direction)
        # print(y_matrix)
        if not y_matrix:
            return
        if not self.show_map_ch.isChecked():
            self.imageView_map.setImage(y_matrix)

    def current_lockin_channel_changed(self, update_channel: str):
        self.current_channel = update_channel

        if self.flag_stat_list == []:
            return

        index = self.indexSlider.value()
        if index == self.indexSlider.maximum() and (self.multi_thread_list[self.current_test_id].flag_stat == "running"):  # 正在作的图，还没做完
            obj = self.fast_obj_list_list[self.current_test_id][0]
            lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]
            if not self.show_line_ch.isChecked():
                if self.current_direction == "forward":  # 只需更新一条曲线即可
                    y_vals, cache_len = self.get_yvals_and_cachelen(lockin_obj)
                    self.curve_line_forward.setData(x=obj.target_levels_list[0:cache_len], y=y_vals)
                elif self.current_direction == "backward":
                    y_vals = self.get_yvals(lockin_obj, index, "forward")
                    # print(y_vals)
                    self.curve_line_forward.setData(x=obj.target_levels_list, y=y_vals)
                    y_vals, cache_len = self.get_yvals_and_cachelen(lockin_obj)
                    self.curve_line_backward.setData(x=obj.target_levels_list[-1:(-1-cache_len):-1], y=y_vals)
                    # print(y_vals)
        else:
            self.current_slice_index_changed(index)

    ####################################################################################################
    #################### 被遗弃的函数
    def get_yvals(self, lockin_obj, index:int, direction:str):
        if direction == "forward":
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_forward[index]
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_forward[index]
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_forward[index]
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_forward[index]
        else:
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_backward[index]
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_backward[index]
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_backward[index]
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_backward[index]

        return y_vals

    def get_yvals_and_cachelen(self, lockin_obj):
        if self.current_direction == "forward":
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_forward_cache
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_forward_cache
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_forward_cache
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_forward_cache
            cache_len = len(y_vals)
        else:
            if self.current_channel == "x":
                y_vals = lockin_obj.data_x_bins_backward_cache
            elif self.current_channel == "y":
                y_vals = lockin_obj.data_y_bins_backward_cache
            elif self.current_channel == "m":
                y_vals = lockin_obj.data_m_bins_backward_cache
            else:  # self.valuech_comboBox.currentText() == "t"
                y_vals = lockin_obj.data_t_bins_backward_cache
            cache_len = len(y_vals)

        return y_vals, cache_len

    def get_ymatrix(self, lockin_obj, index:int, direction:str):
        if direction == "forward":
            if self.current_channel == "x":
                y_matrix = np.transpose(lockin_obj.data_x_bins_forward[0:index][:])
            elif self.current_channel == "y":
                y_matrix = np.transpose(lockin_obj.data_y_bins_forward[0:index][:])
            elif self.current_channel == "m":
                y_matrix = np.transpose(lockin_obj.data_m_bins_forward[0:index][:])
            else:  # self.valuech_comboBox.currentText() == "t"
                y_matrix = np.transpose(lockin_obj.data_t_bins_forward[0:index][:])
        else:
            if self.current_channel == "x":
                y_matrix = np.flipud(np.transpose(lockin_obj.data_x_bins_backward[0:index][:]))
            elif self.current_channel == "y":
                y_matrix = np.flipud(np.transpose(lockin_obj.data_y_bins_backward[0:index][:]))
            elif self.current_channel == "m":
                y_matrix = np.flipud(np.transpose(lockin_obj.data_m_bins_backward[0:index][:]))
            else:  # self.valuech_comboBox.currentText() == "t"
                y_matrix = np.flipud(np.transpose(lockin_obj.data_t_bins_backward[0:index][:]))

        return y_matrix

    def get_lockin_channel_slice(self):
        lockin_obj = self.lockin_obj_list_list[self.current_test_id][self.current_lockin_index]
        if self.current_slice_index == self.indexSlider.maximum():
            y_vals = self.get_lockin_channel_from_cache(lockin_obj)
        else:
            y_vals = self.get_lockin_channel_from_list(lockin_obj)

        return y_vals

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    app_single_thread = app_quantum_transport()
    app_single_thread.show()

    sys.exit(app.exec_())