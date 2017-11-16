# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import base64
import copy
import random
import requests
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.websocket_clients import WebSocketClient
from requests.exceptions import ConnectionError
import objgraph
import pdb
import gc


class V3ModifyinfoAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)
        self._logger_ar = logging.getLogger("AllResult")
        self.check_result = False
        self.attach_conf_id = None
        self.conf_obj = None
        self.conf_mid_map = None
        self.modifyinfo_mem_phone_num = None
        self.modify_mid = None
        self.info_data_dict = None

    def _execute_action(self):
        try :
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]
            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.modifyinfo_mem_phone_num = copy.deepcopy(self.user_pool.online_user_phone_num_list.pop())
                self.user_pool.cache_lock.release()
            else:
                # 在mid_list中随机选取一个元素
                self.modifyinfo_mem_phone_num = random.choice(self.user_pool.online_user_phone_num_list)

            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.modifyinfo_mem_phone_num]

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                if self.check_result:
                    if not self._check_result():
                        self._logger.error("V3ModifyinfoAction check Fail!")
                        self._logger_ar.debug("execute V3ModifyinfoAction: check result fail! http.status_code == 200")
                        return False
                    self._logger_ar.debug("execute V3ModifyinfoAction: check result success! http.status_code == 200")
                else :
                    self._logger_ar.debug("execute V3ModifyinfoAction: http.status_code == 200")

                self.user_pool.cache_lock.acquire()
                if self.modifyinfo_mem_phone_num not in self.user_pool.online_user_phone_num_list:
                    self.user_pool.online_user_phone_num_list.appendleft(self.modifyinfo_mem_phone_num)
                self.user_pool.cache_lock.release()

                self._logger.debug("V3ModifyinfoAction check success!")
                self.properly_executed = True
                return True
            else:
                self._logger.error("modifyinfo check Fail!")
                if self.check_result:
                    self._logger_ar.debug("execute modifyinfo: check result NA! http.status_code == "  + str(http_response.status_code))

                self._logger_ar.debug("execute modifyinfo: http.status_code == " + str(http_response.status_code))
                return False
        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute modifyinfo: except")
            self._logger.error(traceback.format_exc())
            return False
        finally:
            sleep_after = 0

            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]
            if not self.properly_executed:
                self._clean_up_when_fail()
            time.sleep(sleep_after)
            return self.properly_executed

    def _execute_http_request(self):
        self._logger.info("execute V3ModifyinfoAction")
        self.info_data_dict = {"name": "name"+str(self.executor_obj.user_info_dict['userID']),
                               "nickName": "nickName"+str(self.executor_obj.user_info_dict['userID']),
                               "sign":"我是一个盒子。",
                               "mail":"box@mheart.com"}
        url = Constant.HTTP_HOST_V3 + "/mhuser/mod/profile"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = {"user":{"name": self.info_data_dict["name"],
                        "nickName": self.info_data_dict["nickName"],
                        "sex":"0",
                        "sign": self.info_data_dict["sign"],
                        "mail": self.info_data_dict["mail"]
                        }
                }
        data = json.dumps(data)
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/mhuser/mod/profile",
                                        catch_response=False, headers=headers,
                                        data=data)
        return r

    def _clean_up_when_fail(self):
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        if self.modifyinfo_mem_phone_num not in self.user_pool.online_user_phone_num_list:
            self.user_pool.cache_lock.acquire()
            self.user_pool.online_user_phone_num_list.appendleft(self.modifyinfo_mem_phone_num)
            self.user_pool.cache_lock.release()

        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个测试信号
        else:
            pass

    def _check_result(self):
        r_respone = self._get_self_info()
        if r_respone.status_code != 200:
            return False

        get_u_info = json.loads(r_respone.text)["user"]
        if get_u_info["name"] == self.info_data_dict["name"] and get_u_info["nickName"] == self.info_data_dict["nickName"] and get_u_info["sign"] == self.info_data_dict["sign"] and get_u_info["mail"] == self.info_data_dict["mail"]:
            return True
        else:
            return False

    def _get_self_info(self):
        url = Constant.HTTP_HOST_V3 + "/mhuser/display/profile"
        method = 'GET'
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/mhuser/display/profile",
                                        catch_response=False, headers=headers)
        return r