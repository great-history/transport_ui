import numpy as np
from PyQt5.QtWidgets import QMainWindow
from ui_lineroi import *
from PyQt5.QtCore import QUrl, QThread, pyqtSignal

class inspector_line_roi(QMainWindow, Ui_MainWindow):
    inspector_sinout = pyqtSignal(list)

    def __init__(self, window_title: str = "line roi inspector"):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(window_title)

        self.slope = np.nan
        self.interp = np.nan
        self.point1 = [0.0, 0.0]
        self.point2 = [0.0, 0.0]

        self.flag_close = True
        self.flag_emit = False
        self.input_x_doubleSpinBox.valueChanged.connect(
            lambda: self.update_input_y(self.input_x_doubleSpinBox.value()))
        self.input_y_doubleSpinBox.valueChanged.connect(
            lambda: self.update_input_x(self.input_y_doubleSpinBox.value()))
        self.angle_doubleSpinBox.valueChanged.connect(
            lambda: self.emit_inspector_sinout())
        self.length_doubleSpinBox.valueChanged.connect(
            lambda: self.emit_inspector_sinout())


    def closeEvent(self, event):
        if self.flag_close:
            event.accept()
            # sys.exit(0)  # 退出程序
        else:
            event.ignore()

    def display_line_roi_info(self, info_list):
        self.slope = info_list[0]
        self.interp = info_list[1]

        self.slope_lineEdit.setText("%0.3f" % (self.slope))
        self.interp_lineEdit.setText("%0.3f" % (self.interp))
        self.point1_lineEdit.setText("( %0.3f , %0.3f )" % (info_list[2], info_list[3]))
        self.point2_lineEdit.setText("( %0.3f , %0.3f )" % (info_list[4], info_list[5]))

        self.point1 = [info_list[2], info_list[3]]
        self.point2 = [info_list[4], info_list[5]]

        self.input_x_doubleSpinBox.setValue(info_list[2])
        self.input_y_doubleSpinBox.setValue(info_list[3])
        # if self.slope is np.nan:
        #     self.input_x_doubleSpinBox.setValue(self.point1[0])
        #     self.input_y_doubleSpinBox.setValue(self.point1[1])
        # elif self.slope is np.inf:  # 平行于y轴的直线
        #     self.input_x_doubleSpinBox.setValue(self.point1[0])
        # else:
        #     input_x = self.input_x_doubleSpinBox.value()
        #     input_y = input_x * self.slope + self.interp
        #     self.input_y_doubleSpinBox.setValue(input_y)

        length = np.sqrt((info_list[2] - info_list[4]) ** 2 + (info_list[3] - info_list[5]) ** 2)
        z = (info_list[4] - info_list[2]) + 1j * (info_list[5] - info_list[3])
        angle_now = np.angle(z, deg=True)
        self.flag_emit = False
        self.length_doubleSpinBox.setValue(length)
        self.angle_doubleSpinBox.setValue(angle_now)
        self.flag_emit = True

    def update_input_x(self, input_y: float):
        if self.slope is np.nan:
            return

        if self.interp is np.nan:
            return

        if self.slope == 0:
            return
        else:
            input_x = (input_y - self.interp) / self.slope
            self.input_x_doubleSpinBox.setValue(input_x)

    def update_input_y(self, input_x: float):
        if self.slope is np.nan:
            return
        if self.slope is np.inf:
            return

        input_y = input_x * self.slope + self.interp
        self.input_y_doubleSpinBox.setValue(input_y)

    def emit_inspector_sinout(self):
        if not self.flag_emit:
            return
        x_o = self.input_x_doubleSpinBox.value()
        y_o = self.input_y_doubleSpinBox.value()
        angle = self.angle_doubleSpinBox.value()
        length = self.length_doubleSpinBox.value()

        x_e = x_o + length * np.cos(angle / 180 * np.pi)
        y_e = y_o + length * np.sin(angle / 180 * np.pi)
        self.inspector_sinout.emit([x_o, y_o, x_e, y_e])