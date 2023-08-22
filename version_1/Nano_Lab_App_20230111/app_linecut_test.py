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

from ui_linecut import *
from measurement_class.linecut_qthread_worker import *

class app_linecut_test(QMainWindow, Ui_MainWindow):
    qmut = QMutex()

    def __init__(self, update_time:float = 500, parameter_info:dict = None):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("single thread test")

        self.loadButton.clicked.connect(self.loadTask)
        self.runButton.clicked.connect(self.runTask)
        self.stopButton.clicked.connect(self.stopTask)
        self.clearButton.clicked.connect(self.clearPlot)
        self.deleteButton.clicked.connect(self.deleteAll)

        self.show_value_ch.clicked.connect(self.show_value_channel)
        self.show_error_ch.clicked.connect(self.show_error_channel)
        self.colors = ["r", "b", "g"]  # only for test

        self.current_root_path = os.getcwd()
        self.update_time = update_time
        self.timer = QtCore.QTimer(self)
        self.user_info_dict = {}
        self.source_obj_list = []
        self.multi_thread_list = []

        self.count = 0  # only for test

    def __set_plotwidget_config(self):
        self.plotWidget_value.setLabel("left", "值")
        self.plotWidget_value.setLabel("bottom", "Time")
        self.plotWidget_value.showGrid(x=True, y=True)

    def reset_log_Screen(self):
        # 清空文本
        self.logScreen.clear()
        self.logScreen.setPlainText("This is a log screen :")

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

    def loadTask(self):
        fileName, fileType = QtWidgets.QFileDialog.getOpenFileName(self, "Choose Json File", self.current_root_path,  "Text Files(*.json)")
        self.pathEdit.setText(fileName)

        if fileName == "":
            self.informMsg(msg=" You did not choose a json file ")
            return

        current_path_split = fileName.split('\\')
        self.current_root_path = "\\".join(current_path_split[0:-1])

        self.reset_log_Screen()
        ####################################################################################################
        ########## load task : 创建一个one_source_meas_class对象
        with open(fileName, mode='r', encoding='utf-8') as f:
            dict_list = json.load(f)
            self.logScreen.appendPlainText('json file load successfully !')
            ########## 将多个字典从json文件中读出来
            ########## 首先是用户信息, 将其打印到logscreen中
            self.user_info_dict = dict_list[0]
            for key, value in self.user_info_dict.items():
                self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))

            self.logScreen.appendPlainText('\n\n')

            for index in range(1, len(dict_list)):
                source_info_dict = dict_list[index]
                self.logScreen.appendPlainText('第{:d}台仪器的信息:'.format(index))
                for key, value in source_info_dict.items():
                    if key != "path_list":
                        self.logScreen.appendPlainText('{key} : {value}'.format(key=key, value=value))
                self.logScreen.appendPlainText('\n')

                ########## 将source_info转化为source_obj
                source_obj = get_source_obj_by_dict(source_info_dict=source_info_dict)
                self.source_obj_list.append(source_obj)
                one_source_thread = linecut_qthread_worker(source_obj=source_obj, user_info=self.user_info_dict)
                one_source_thread.update_sinout.connect(self.__update)
                one_source_thread.finish_sinout.connect(self.__finish)
                self.multi_thread_list.append(one_source_thread)
                # self.plotWidget_value.setYRange(max=100, min=0)

        self.informMsg(msg=" Task load successfully ")

    def __update(self, update_sinout:list):
        self.logScreen.appendPlainText("\n")
        self.logScreen.appendPlainText('===== test name : {:s} ====='.format(update_sinout[0]))
        self.logScreen.appendPlainText('      scan direction : {:s}      '.format(update_sinout[1]))
        self.logScreen.appendPlainText('      {:s} : {:.3f}      '.format("remaining time", update_sinout[2]))
        self.logScreen.appendPlainText('      {:s} : {:.3f}      '.format("progress bar", update_sinout[3]))

        self.lcdNumber.display(update_sinout[2])
        self.progressBar.setValue(int(update_sinout[3] * 100))

        ########## save figure
        # ex = pg_exporter.ImageExporter(self.plotWidget_value.scene())
        # ex.export(fileName="test.png")

        ########## clean figure
        self.plotWidget_error.clear()
        self.plotWidget_value.clear()

    def __finish(self, finish_sinout:str):
        self.logScreen.appendPlainText("\n")
        self.logScreen.appendPlainText(' {:s} : {:s} '.format(self.user_info_dict["test_name"], finish_sinout))

        self.qmut.lock()  # 加锁
        self.count += 1
        if self.count == 3:
            self.__killTask()
        self.qmut.unlock()  # 解锁

    def clearPlot(self):
        self.plotWidget_value.clear()
        self.plotWidget_error.clear()

    def runTask(self):
        if self.multi_thread_list == []:
            return
        self.loadButton.setEnabled(False)
        self.logScreen.appendPlainText("\n\n")
        test_time = get_time_list(time.localtime(time.time()))
        time_str = "{}-{}-{}_{}-{}-{}".format(test_time[0], test_time[1], test_time[2], test_time[3], test_time[4], test_time[5])
        self.logScreen.appendPlainText(' ****** {:s}开始进行测试 ******'.format(self.user_info_dict["test_name"]))
        self.logScreen.appendPlainText(' ****** : {:s} : ******'.format(time_str))

        for i in range(len(self.multi_thread_list)):
            self.multi_thread_list[i].start()  # 之前错误的写法：self.multi_thread_list[i].run()

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
            self.multi_thread_list = []
            self.source_obj_list = []
            self.loadButton.setEnabled(True)
            self.reset_log_Screen()
            self.progressBar.setValue(0)
            self.lcdNumber.display(999999)
            self.pathEdit.setText(" current file path ")
        except Exception as e:
            print(e)

    def stopTask(self):
        if self.multi_thread_list == []:
            return
        self.timer.stop()

    ####################################################################################################
    ########## 启动定时器 时间间隔秒
    def __timer_start(self):
        self.timer.timeout.connect(self.update_plot_channel)
        self.timer.start(int(self.update_time))

    def update_plot_channel(self):
        if not self.show_error_ch.isChecked():
            self.plotWidget_value.plot(self.source_obj_list[0].level_bins_forward_cache, _callSync='off', pen=self.colors[0])
        if not self.show_value_ch.isChecked():
            self.plotWidget_error.plot(self.source_obj_list[0].error_bins_forward_cache, pen=self.colors[0])

        # for i in range(len(self.source_obj_list)):
        #     self.plotWidget_value.plot(self.source_obj_list[i].level_bins_forward_cache, _callSync='off', pen=self.colors[i])
        #     self.plotWidget_error.plot(self.source_obj_list[i].error_bins_forward_cache, pen=self.colors[i])

    def update_value_channel(self):
        return

    def update_error_channel(self):
        return

    def show_value_channel(self):
        if (self.show_value_ch.isChecked()):
            self.plotWidget_value.hide()
        else:
            self.plotWidget_value.show()

    def show_error_channel(self):
        if (self.show_error_ch.isChecked()):
            self.plotWidget_error.hide()
        else:
            self.plotWidget_error.show()


if __name__ == "__main__":
    import sys
    # app = QtWidgets.QApplication(sys.argv)
    # MainWindow = QtWidgets.QMainWindow()
    # ui = Ui_MainWindow()
    # ui.setupUi(MainWindow)
    # MainWindow.show()
    # sys.exit(app.exec_())

    app = QtWidgets.QApplication(sys.argv)
    app_single_thread = app_linecut_test()
    app_single_thread.show()

    sys.exit(app.exec_())