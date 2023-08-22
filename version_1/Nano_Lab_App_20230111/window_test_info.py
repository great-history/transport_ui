import numpy as np
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from ui_test_info import *
from PyQt5.QtCore import QUrl, QThread, pyqtSignal
import re, json, sys
from utilities.utility_package import *

class window_test_info(QMainWindow, Ui_MainWindow):
    add_test_sinout = pyqtSignal(dict)

    def __init__(self, window_title: str = "Test Info Window"):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle(window_title)

        self.__set_Reg_exp()

        ####################################################################################################
        ########## info dict
        self.user_info_dict = {"sample_name": "",
                               "test_name": "",
                               "test_time": "",
                               "test_type": "",
                               "user_name": "",
                               "user_email": "",
                               "flag_stat": "start",
                               "global_temp": 0.020,
                               "global_mag": 0.000,
                               "root_path": "",
                               "info_file_path": "",
                               "flag_back": False,
                               "scan_fast_name": "",
                               "scan_slow_name": ""
                               }
        self.mf_info_dict_list = []
        self.temp_info_dict_list = []
        self.source_info_dict_list = []
        self.lockin_info_dict_list = []
        self.flag_input = False

        self.add_test_sinout_pushButton.clicked.connect(self.add_a_test_sinout)
        self.add_test_pushButton.clicked.connect(self.add_a_test)

        ####################################################################################################
        ########## source相关
        self.add_source_pushButton.clicked.connect(self.__add_a_source_dict)
        self.rm_source_pushButton.clicked.connect(self.__rm_a_source_dict)
        self.update_source_pushButton.clicked.connect(self.__update_source_dict)
        self.source_id_comboBox.currentIndexChanged.connect(
            lambda: self.__input_source_info_from_list(self.source_id_comboBox.currentIndex()))

        ####################################################################################################
        ########## lockin相关


    def __set_Reg_exp(self):
        # 两个浮点数，float-float
        # twoFloatRegx = QtCore.QRegExp(
        #     r"^(?!;)(((\-?(?!0)\d*\.?\d*)|(\-?(0\.)\d*)|0);(?!;))?((\-?(?!0)\d*\.?\d*)|(\-?(0\.)\d*)|0)")
        # twoFloatRegxValidator = QtGui.QRegExpValidator(twoFloatRegx)

        trans_pattern1 = "-?\d+\.*\d*\*\(-?\d+\.*\d*\,-?\d+\.*\d*\,\d+\)\+\d+\.*\d*"  ###### A*(a,b,c)+B
        trans_pattern2 = "-?\d+\.*\d*\*\(-?\d+\.*\d*\,-?\d+\.*\d*\,\d+\)\-\d+\.*\d*"  ###### A*(a,b,c)-B
        float_pattern = "-?\d+\.*\d*"
        linspace_pattern = "\(-?\d+\.*\d*\,-?\d+\.*\d*\,\d+\)"

        trg_pattern = "%s|%s|%s|%s" % (trans_pattern1, trans_pattern2, float_pattern, linspace_pattern)
        self.trans_pattern1 = trans_pattern1
        self.trans_pattern2 = trans_pattern2
        self.float_pattern = float_pattern
        self.linspace_pattern = linspace_pattern
        self.trg_pattern = re.compile(trg_pattern)
        self.trg_list_pattern = "((%s);)*(%s)" % (trg_pattern, trg_pattern)
        self.trg_list_regx = QtCore.QRegExp(self.trg_list_pattern)

        trg_list_validator = QtGui.QRegExpValidator(self.trg_list_regx)
        self.temp_trg_lev_list_lineEdit.setValidator(trg_list_validator)
        self.mf_trg_lev_list_lineEdit.setValidator(trg_list_validator)
        self.source_trg_lev_list_lineEdit.setValidator(trg_list_validator)

    def __check_valid(self):
        flag_valid = True
        trg_lev_list = self.mf_trg_lev_list_lineEdit.text()
        if not re.fullmatch(pattern=self.trg_list_pattern, string=trg_lev_list):
            flag_valid = False

        return flag_valid

    def __get_trg_lev_list(self, trg_lev_str: str):
        find_trg_lev = re.findall(self.trg_pattern, trg_lev_str)
        trg_lev_list = []

        for item in find_trg_lev:
            if re.fullmatch(self.trans_pattern1, item):
                item_split = item.split("*")
                A = item_split[0]
                A = float(A)
                C = item_split[1]
                B_split = C.split(")")
                linspace = B_split[0] + ")"
                B = B_split[1]
                B = float(B)

                linspace_nums = re.findall(self.float_pattern, linspace)
                linspace_list = np.linspace(float(linspace_nums[0]), float(linspace_nums[1]), int(linspace_nums[2]))
                linspace_list = A * linspace_list + B
                linspace_list = linspace_list.tolist()

                trg_lev_list.extend(linspace_list)
                print("trans_pattern1")

            elif re.fullmatch(self.trans_pattern2, item):
                item_split = item.split("*")
                A = item_split[0]
                A = float(A)
                C = item_split[1]
                B_split = C.split(")")
                linspace = B_split[0] + ")"
                B = B_split[1]
                B = float(B)

                linspace_nums = re.findall(self.float_pattern, linspace)
                linspace_list = np.linspace(float(linspace_nums[0]), float(linspace_nums[1]), int(linspace_nums[2]))
                linspace_list = A * linspace_list + B
                linspace_list = linspace_list.tolist()

                trg_lev_list.extend(linspace_list)
                print("trans_pattern2")

            elif re.fullmatch(self.linspace_pattern, item):
                linspace_nums = re.findall(self.float_pattern, item)
                linspace_list = np.linspace(float(linspace_nums[0]), float(linspace_nums[1]), int(linspace_nums[2]))
                linspace_list = linspace_list.tolist()
                trg_lev_list.extend(linspace_list)
                print("linspace_pattern")

            elif re.fullmatch(self.float_pattern, item):
                trg_lev_list.append(float(item))
                print("float_pattern")

        return trg_lev_list

    ####################################################################################################
    ########## 添加一个test
    def add_a_test(self):

        return

    def add_a_test_sinout(self):
        ####################################################################################################
        ########## check test info

        ########## get test info
        user_name = self.user_name_lineEdit.text()  ## "Shijie_Fang"
        user_email = self.user_email_lineEdit.text()  ## "ff335192289@qq.com"
        sample_name = self.sample_name_lineEdit.text() ## "sample26"
        test_name = self.test_name_lineEdit.text() ## "Landau_Fan_nB"
        test_type = self.test_type_comboBox.currentText() ## "2D map"
        flag_back = self.flag_back_checkBox.isChecked()
        scan_fast_name = self.scan_fast_lineEdit.text()
        scan_slow_name = self.scan_slow_lineEdit.text()

        test_time = get_time_list(time.localtime(time.time()))
        root_path = os.getcwd()
        info_file_path = get_info_jsonfile_path(sample_name=sample_name,
                                                test_name=test_name,
                                                test_time=test_time,
                                                root_path=root_path)

        self.user_info_dict["sample_name"] = sample_name
        self.user_info_dict["test_name"] = test_name
        self.user_info_dict["test_time"] = test_time
        self.user_info_dict["user_name"] = user_name
        self.user_info_dict["user_email"] = user_email
        self.user_info_dict["flag_stat"] = "start"
        self.user_info_dict["root_path"] = root_path
        self.user_info_dict["info_file_path"] = info_file_path
        self.user_info_dict["flag_back"] = flag_back
        self.user_info_dict["scan_fast_name"] = scan_fast_name
        self.user_info_dict["scan_slow_name"] = scan_slow_name

        # dict_list.append(user_info)
        if test_type == "1D_linecut_set-point":
            all_info_list = self.add_a_1D_linecut_set_point_test(user_info=self.user_info_dict)
            self.add_test_sinout.emit(all_info_list[0])
        elif test_type == "1D_linecut_set-time":
            all_info_list = self.add_a_1D_linecut_set_point_test(user_info=self.user_info_dict)
            self.add_test_sinout.emit(all_info_list[0])
        elif test_type == "2D_map-set-point":
            all_info_list = self.add_a_2D_map_set_point_test(user_info=self.user_info_dict)
            self.add_test_sinout.emit(all_info_list[0])
        elif test_type == "2D_map-set-time":
            all_info_list = self.add_a_2D_map_set_point_test(user_info=self.user_info_dict)
            self.add_test_sinout.emit(all_info_list[0])

    def add_a_2D_map_set_point_test(self, user_info:dict):
        ####################################################################################################
        #################### 扫 n-B map(Landau Fan nB) // two-gate map 等等

        ################################################################################
        #################### 磁场
        # mf_info_dict_list = []
        # if self.mf_switch_CheckBox.isChecked():  #################### 要扫磁场
        #     self.mf_info_dict = self.__get_mf_info_dict(user_info)
        #     mf_info_dict_list = [self.mf_info_dict]
        # else:  #################### 不扫磁场
        #     user_info["global_mf"] = self.mf_fix_doubleSpinBox.value()

        ################################################################################
        #################### 温度
        # temp_info_dict_list = []
        # if self.temp_switch_CheckBox.isChecked():  #################### 要扫磁场
        #     self.temp_info_dict = self.__get_temp_info_dict(user_info)
        #     temp_info_dict_list = [self.temp_info_dict]
        # else:  #################### 不扫磁场
        #     user_info["global_temp"] = self.temp_fix_doubleSpinBox.value()

        ################################################################################
        #################### source
        source_info_dict_list = []
        if self.source_switch_CheckBox.isChecked():
            self.__update_source_info_dict(user_info)
            for id in range(self.source_id_comboBox.count()):
                source_info_dict_list.append(self.source_info_dict_list[id])

        ################################################################################
        #################### lockin
        lockin_info_dict_list = []
        if self.lockin_switch_CheckBox.isChecked():
            self.__update_lockin_info_dict(user_info)
            for id in range(self.lockin_id_comboBox.count()):
                lockin_info_dict_list.append(self.lockin_info_dict_list[id])

        ################################################################################
        #################### info all in one
        all_info_list = [user_info]
        # if not mf_info_dict_list:
        #     all_info_list.append(mf_info_dict_list)
        # if not temp_info_dict_list:
        #     all_info_list.append(temp_info_dict_list)
        if not source_info_dict_list:
            all_info_list.extend(source_info_dict_list)
        if not lockin_info_dict_list:
            all_info_list.extend(lockin_info_dict_list)

        ########## 保存信息
        with open(user_info["info_file_path"], mode='w', encoding='utf-8') as f:
            json.dump(all_info_list, f)

        # with open(info_file_path, mode='r', encoding='utf-8') as f:
        #     dict_list = json.load(f)
        #     # 将多个字典从json文件中读出来
        #     print(len(dict_list))
        #     for dict_ in dict_list:
        #         print(dict_)
        # test_info_path_list.append(info_file_path)

        return all_info_list

    def add_a_1D_linecut_set_point_test(self, user_info:dict):
        ################################################################################
        #################### source
        source_info_dict_list = []
        if self.source_switch_CheckBox.isChecked():
            self.__update_source_info_dict(user_info)
            for id in range(self.source_id_comboBox.count()):
                source_info_dict_list.append(self.source_info_dict_list[id])

        ################################################################################
        #################### lockin
        lockin_info_dict_list = []
        if self.lockin_switch_CheckBox.isChecked():
            self.__update_lockin_info_dict(user_info)
            for id in range(self.lockin_id_comboBox.count()):
                lockin_info_dict_list.append(self.lockin_info_dict_list[id])

        ################################################################################
        #################### info all in one
        all_info_list = [user_info]
        # if not mf_info_dict_list:
        #     all_info_list.append(mf_info_dict_list)
        # if not temp_info_dict_list:
        #     all_info_list.append(temp_info_dict_list)
        if not source_info_dict_list:
            all_info_list.extend(source_info_dict_list)
        if not lockin_info_dict_list:
            all_info_list.extend(lockin_info_dict_list)

        ########## 保存信息
        with open(user_info["info_file_path"], mode='w', encoding='utf-8') as f:
            json.dump(all_info_list, f)

        return all_info_list

    def __reset_user_info_dict(self):
        self.user_info_dict = {"sample_name": "",
                               "test_name": "",
                               "test_time": "",
                               "test_type": "",
                               "user_name": "",
                               "user_email": "",
                               "flag_stat": "start",
                               "global_temp": 0.020,
                               "global_mag": 0.000,
                               "root_path": "",
                               "info_file_path": "",
                               "flag_back": False,
                               "scan_fast_name": "",
                               "scan_slow_name": ""
                               }

    ####################################################################################################
    ########## mf info 相关
    def __get_mf_info_dict(self, user_info: dict):
        mf_type = self.mf_type_comboBox.currentText()
        mf_addr = self.mf_addr_lineEdit.text()  #################### "TCPIP::192.168.1.102::7180::SOCKET"
        mf_name = self.mf_name_lineEdit.text()

        trg_lev_list = self.mf_trg_lev_list_lineEdit.text()
        str_nums = re.findall(self.trg_pattern, trg_lev_list)
        #################### 得到trg_level_list

        if self.mf_set_time_checkBox.isChecked():
            mf_update_time = self.mf_set_time_doubleSpinBox.value()
        else:
            mf_update_time = np.nan

        mf_name = self.mf_name_lineEdit.text()
        mf_order = self.mf_order_comboBox.currentText()
        mf_tol = self.mf_tol_doubleSpinBox.value()
        mf_pause = self.mf_pause_doubleSpinBox.value()

        last_level = self.mf_last_lev_doubleSpinBox.value()

        data_forward_file_path = get_datfile_path(sample_name=user_info["sample_name"],
                                                  test_name=user_info["test_name"],
                                                  test_time=user_info["test_time"],
                                                  instr_name=mf_name,
                                                  scan_direction="forward",
                                                  root_path=user_info["root_path"])

        data_backward_file_path = get_datfile_path(sample_name=user_info["sample_name"],
                                                   test_name=user_info["test_name"],
                                                   test_time=user_info["test_time"],
                                                   instr_name=mf_name,
                                                   scan_direction="backward",
                                                   root_path=user_info["root_path"])

        mf_path_list = [data_forward_file_path, data_backward_file_path]

        mf_info_dict = {"mf_type": mf_type, "mf_addr": mf_addr, "mf_name": mf_name,
                        "last_level": last_level, "interval_pause": mf_pause, "tol": mf_tol,
                        "mf_order": mf_order,
                        "target_level_list": trg_lev_list,
                        "path_list": mf_path_list,
                        "update_time": mf_update_time
                        }
        return mf_info_dict

    ####################################################################################################
    ########## temp info 相关
    def __get_temp_info_dict(self, user_info: dict):
        return

    ####################################################################################################
    ########## source info 相关
    def __update_source_info_dict(self, user_info: dict):
        ################################################################################ 写scan fast files
        for i in range(len(self.source_info_dict_list)):
            source_dict = self.source_info_dict_list[i]
            data_forward_file_path = get_datfile_path(sample_name=user_info["sample_name"],
                                                      test_name=user_info["test_name"],
                                                      test_time=user_info["test_time"],
                                                      instr_name=source_dict["source_name"],
                                                      scan_direction="forward",
                                                      root_path=user_info["root_path"])

            data_backward_file_path = get_datfile_path(sample_name=user_info["sample_name"],
                                                       test_name=user_info["test_name"],
                                                       test_time=user_info["test_time"],
                                                       instr_name=source_dict["source_name"],
                                                       scan_direction="backward",
                                                       root_path=user_info["root_path"])

            path_list = [data_forward_file_path, data_backward_file_path]
            source_dict["path_list"] = path_list

    def __reset_source_channel(self):
        self.source_switch_CheckBox.setChecked(False)
        self.source_id_comboBox.clear()
        self.source_type_comboBox.setCurrentIndex(0)
        self.source_addr_lineEdit.setText("")
        self.source_name_lineEdit.setText("")
        self.source_mode_comboBox.setCurrentIndex(0)
        self.source_upper_bound_doubleSpinBox.setValue(9.0)
        self.source_lower_bound_doubleSpinBox.setValue(-9.0)
        self.source_slope_fast_doubleSpinBox.setValue(0.010)
        self.source_slope_slow_doubleSpinBox.setValue(0.002)
        self.source_pause_doubleSpinBox.setValue(0.50)
        self.source_trg_lev_list_lineEdit.setText("")
        self.source_order_comboBox.setCurrentIndex(0)
        self.source_last_lev_doubleSpinBox.setValue(0.000)

        self.source_info_dict_list = []

    def __add_a_source_dict(self):
        source_num = self.source_id_comboBox.count()
        ########## source info 初始化参数
        source_dict = {}
        source_dict["source_type"] = "Keithley2400"
        source_dict["source_addr"] = ""
        source_dict["source_name"] = ""
        source_dict["source_mode"] = "voltage"
        source_dict["source_order"] = "scan_slow"
        source_dict["source_bound"] = (-9.00, 9.00)
        source_dict["slope_fast"] = 0.010
        source_dict["slope_slow"] = 0.002
        source_dict["pause_time"] = 0.500
        source_dict["last_lev"] = 0.000
        source_dict["path_list"] = []
        source_dict["trg_lev_list"] = ""

        self.source_info_dict_list.append(source_dict)
        self.flag_input = False
        self.source_id_comboBox.addItem(str(source_num))
        self.flag_input = True
        # print(self.source_info_dict_list)

    def __rm_a_source_dict(self):
        if self.source_id_comboBox.count() == 0:
            return
        current_index = self.source_id_comboBox.currentIndex()
        reply = self.questionMsg(msg="是否要删除当前的source infos?")
        if not reply:
            return

        self.source_info_dict_list.pop(current_index)
        self.flag_input = False
        self.source_id_comboBox.clear()
        for i in range(len(self.source_info_dict_list)):
            self.source_id_comboBox.addItem(str(i))
        self.flag_input = True

    def __update_source_dict(self):
        if self.source_id_comboBox.count() == 0:
            return
        source_id = self.source_id_comboBox.currentIndex()

        source_dict = self.source_info_dict_list[source_id]
        source_dict["source_type"] = self.source_type_comboBox.currentText()
        addr = self.source_addr_lineEdit.text()
        source_dict["source_addr"] = addr.strip()
        name = self.source_name_lineEdit.text()
        source_dict["source_name"] = name.strip()
        source_dict["source_mode"] = self.source_mode_comboBox.currentText()
        source_dict["source_order"] = self.source_order_comboBox.currentText()
        source_dict["source_bound"] = (self.source_lower_bound_doubleSpinBox.value(), self.source_upper_bound_doubleSpinBox.value())
        source_dict["slope_fast"] = self.source_slope_fast_doubleSpinBox.value()
        source_dict["slope_slow"] = self.source_slope_slow_doubleSpinBox.value()
        source_dict["pause_time"] = self.source_pause_doubleSpinBox.value()

        source_dict["trg_lev_list"] = self.source_trg_lev_list_lineEdit.text()
        source_dict["last_lev"] = self.source_last_lev_doubleSpinBox.value()

    def __input_source_info_from_list(self, source_id: int):
        if not self.flag_input:
            return
        source_dict = self.source_info_dict_list[source_id]
        self.source_type_comboBox.setCurrentText(source_dict["source_type"])
        self.source_addr_lineEdit.setText(source_dict["source_addr"])
        self.source_name_lineEdit.setText(source_dict["source_name"])
        self.source_mode_comboBox.setCurrentText(source_dict["source_mode"])
        self.source_order_comboBox.setCurrentText(source_dict["source_order"])

        self.source_lower_bound_doubleSpinBox.setValue(source_dict["source_bound"][0])
        self.source_upper_bound_doubleSpinBox.setValue(source_dict["source_bound"][1])

        self.source_slope_fast_doubleSpinBox.setValue(source_dict["slope_fast"])
        self.source_slope_slow_doubleSpinBox.setValue(source_dict["slope_slow"])
        self.source_pause_doubleSpinBox.setValue(source_dict["pause_time"])
        self.source_trg_lev_list_lineEdit.setText(source_dict["trg_lev_list"])

        self.source_last_lev_doubleSpinBox.setValue(source_dict["last_lev"])

    ####################################################################################################
    ########## lockin info 相关
    def __update_lockin_info_dict(self, user_info: dict):
        ################################################################################ 写lockin files
        for i in range(len(self.lockin_info_dict_list)):
            lockin_dict = self.lockin_info_dict_list[i]
            data_forward_file_path = get_datfile_path(sample_name=user_info["sample_name"],
                                                      test_name=user_info["test_name"],
                                                      test_time=user_info["test_time"],
                                                      instr_name=lockin_dict["lockin_name"],
                                                      scan_direction="forward",
                                                      root_path=user_info["root_path"])

            data_backward_file_path = get_datfile_path(sample_name=user_info["sample_name"],
                                                       test_name=user_info["test_name"],
                                                       test_time=user_info["test_time"],
                                                       instr_name=lockin_dict["lockin_name"],
                                                       scan_direction="backward",
                                                       root_path=user_info["root_path"])

            path_list = [data_forward_file_path, data_backward_file_path]
            lockin_dict["path_list"] = path_list

    def __reset_lockin_channel(self):
        self.lockin_switch_CheckBox.setChecked(False)
        self.lockin_id_comboBox.clear()
        self.lockin_type_comboBox.setCurrentIndex(0)
        self.lockin_addr_lineEdit.setText("")
        self.lockin_name_lineEdit.setText("")

        self.lockin_voltage_doubleSpinBox.setValue(0.010)
        self.lockin_frequency_doubleSpinBox.setValue(13.339)
        self.lockin_phase_doubleSpinBox.setValue(0.000)

        self.lockin_iac_doubleSpinBox.setValue(10.000)
        self.lockin_time_const_comboBox.setCurrentIndex(0)

        self.lockin_sig_comboBox.setCurrentIndex(0)
        self.lockin_terminal_A_lineEdit.setText("")
        self.lockin_terminal_B_lineEdit.setText("")
        self.lockin_terminal_IO_lineEdit.setText("")

    def __add_a_lockin_dict(self):
        lockin_num = self.lockin_id_comboBox.count()
        self.lockin_id_comboBox.addItem(str(lockin_num))

        lockin_dict = {}
        lockin_dict["lockin_type"] = ""
        lockin_dict["lockin_addr"] = ""
        lockin_dict["lockin_name"] = ""

        lockin_dict["voltage"] = np.nan
        lockin_dict["phase"] = np.nan
        lockin_dict["frequency"] = np.nan

        lockin_dict["I_ac"] = np.nan
        lockin_dict["time_const"] = ""

        lockin_dict["signal_input"] = ""
        lockin_dict["terminal_A"] = ""
        lockin_dict["terminal_B"] = ""

        lockin_dict["terminal_io"] = ""

        lockin_dict["path_list"] = []

        self.lockin_info_dict_list.append(lockin_dict)
        self.flag_input = False
        self.lockin_id_comboBox.addItem(str(lockin_num))
        self.flag_input = True

    def __rm_a_lockin_dict(self):
        if self.lockin_id_comboBox.count() == 0:
            return
        current_index = self.lockin_id_comboBox.currentIndex()
        reply = self.questionMsg(msg="是否要删除当前的lockin infos?")
        if not reply:
            return

        self.lockin_info_dict_list.pop(current_index)
        self.lockin_id_comboBox.clear()
        for i in range(len(self.lockin_info_dict_list)):
            self.lockin_id_comboBox.addItem(str(i))

    def __update_lockin_dict(self):
        if self.lockin_id_comboBox.count() == 0:
            return
        current_index = self.lockin_id_comboBox.currentIndex()

        lockin_dict = self.lockin_info_dict_list[current_index]
        lockin_dict["lockin_type"] = self.lockin_type_comboBox.currentText()
        lockin_dict["lockin_addr"] = self.lockin_addr_lineEdit.text()
        lockin_dict["lockin_name"] = self.lockin_name_lineEdit.text()

        lockin_dict["voltage"] = self.lockin_voltage_doubleSpinBox.value()
        lockin_dict["phase"] = self.lockin_phase_doubleSpinBox.value()
        lockin_dict["frequency"] = self.lockin_frequency_doubleSpinBox.value()

        lockin_dict["I_ac"] = self.lockin_iac_doubleSpinBox.value()
        lockin_dict["time_const"] = self.lockin_tim_const_comboBox.currentText()

        lockin_dict["signal_input"] = self.lockin_sig_comboBox.currentText()
        lockin_dict["terminal_A"] = self.lockin_terminal_A_lineEdit.text()
        lockin_dict["terminal_B"] = self.lockin_terminal_B_lineEdit.text()

        lockin_dict["terminal_io"] = self.lockin_terminal_IO_lineEdit.text()

    def __input_lockin_info_from_list(self, lockin_id: int):
        if not self.flag_input:
            return
        lockin_dict = self.lockin_info_dict_list[lockin_id]

        self.lockin_type_comboBox.setCurrentText(lockin_dict["lockin_type"])
        self.lockin_addr_lineEdit.setText(lockin_dict["lockin_addr"])
        self.lockin_name_lineEdit.setText(lockin_dict["lockin_name"])

        self.lockin_voltage_doubleSpinBox.setValue(lockin_dict["voltage"])
        self.lockin_frequency_doubleSpinBox.setValue(lockin_dict["frequency"])
        self.lockin_phase_doubleSpinBox.setValue(lockin_dict["phase"])

        self.lockin_iac_doubleSpinBox.setValue(lockin_dict["I_ac"])
        self.lockin_time_const_comboBox.setCurrentText(lockin_dict["time_const"])

        self.lockin_sig_comboBox.setCurrentText(lockin_dict["signal_input"])
        self.lockin_terminal_A_lineEdit.setText(lockin_dict["terminal_A"])
        self.lockin_terminal_B_lineEdit.setText(lockin_dict["terminal_B"])

        self.lockin_terminal_IO_lineEdit.setText(lockin_dict["terminal_io"])

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
            # for task in self.multi_thread_list:
            #     for obj in task.slow_obj_list:
            #         obj.shutdown()
            #     for obj in task.fast_obj_list:
            #         obj.shutdown()
            #     for lockin in task.fast_obj_list:
            #         lockin.shutdown()

            event.accept()
            # sys.exit(0)  # 退出程序
        else:
            event.ignore()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    win = window_test_info()
    win.show()

    sys.exit(app.exec_())