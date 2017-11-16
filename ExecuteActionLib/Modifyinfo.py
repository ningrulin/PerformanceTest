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


class ModifyinfoAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.group_shareid = None
        self.is_mute = False
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)
        self._logger_ar = logging.getLogger("AllResult")
        self.check_result = False
        self.attach_conf_id = None
        self.conf_obj = None
        self.conf_mid_map = None
        self.modifyinfo_mem_phone_num = None
        self.modify_mid = None

    def _execute_action(self):
        try :
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            self.executor_phone_num = random.choice(self.user_pool.conf_chair_phone_num_list)
            self._logger.info("XXXXXXXX" + str(self.executor_phone_num))
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id

            self.conf_obj = copy.deepcopy(self.user_pool.conf_id_obj_dict[self.attach_conf_id])
            self.conf_mid_map = self.conf_obj.mid_map


            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self._logger.debug("aqf:pppp start" + str(self.conf_mid_map) + ":" + str(time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))))
                self.modifyinfo_mem_phone_num = copy.deepcopy(self.user_pool.in_conf_mem_phone_num_list.pop())
                self.user_pool.cache_lock.release()
            else:
                # 在mid_list中随机选取一个元素
                self.modifyinfo_mem_phone_num = random.choice(self.user_pool.in_conf_mem_phone_num_list)
            """self.modifyinfo_mem_phone_num = copy.deepcopy(self.user_pool.in_conf_mem_phone_num_list.pop())"""


            self._logger.info("aqf2: getinfo_mem_phone_num" + str(self.modifyinfo_mem_phone_num))

            self.modify_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[self.modifyinfo_mem_phone_num].user_info_dict["userID"])]

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                if self.check_result:
                    if not self._check_result():
                        self._logger.error("modifyinfo check Fail!")
                        self._logger_ar.debug("execute modifyinfo: check result fail! http.status_code == 200")
                        return False
                    self._logger.debug(
                        "aqf:pppp end" +  str(self.conf_mid_map) + ":" +str(time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))))
                    self._logger_ar.debug("execute modifyinfo: check result success! http.status_code == 200")
                else :
                    self._logger_ar.debug("execute modifyinfo: http.status_code == 200")

                self.user_pool.cache_lock.acquire()
                if self.modifyinfo_mem_phone_num not in self.user_pool.in_conf_mem_phone_num_list:
                    self.user_pool.in_conf_mem_phone_num_list.appendleft(self.modifyinfo_mem_phone_num)
                self.user_pool.cache_lock.release()

                self._logger.debug("modifyinfo check success!")
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
        self._logger.info("execute modifyinfo")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members/status"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = [{"mid": self.modify_mid, "name" : "jack"}, {"mid": self.modify_mid, "vs" : 2}]
        data = json.dumps(data)
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/members/status",
                                        catch_response=False, headers=headers,
                                        data=data)
        return r

    def _clean_up_when_fail(self):
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        if self.modifyinfo_mem_phone_num not in self.user_pool.in_conf_mem_phone_num_list:
            self.user_pool.cache_lock.acquire()
            self.user_pool.in_conf_mem_phone_num_list.appendleft(self.modifyinfo_mem_phone_num)
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
        self._logger.debug(
            "r_respone" + str(r_respone.status_code) + str(r_respone.text))
        if r_respone.status_code != 200:
            return False

        chair_info = []
        chair_info = json.loads(r_respone.text)["members"][0]
        if chair_info["name"] == "jack" and chair_info["vs"] == 2 and chair_info["ol"] :
            return True
        else:
            return False

    def _get_self_info(self):
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = [self.modify_mid,]
        data = json.dumps(data)
        self._logger.debug("aqf: print token:" + str(self.executor_obj.user_info_dict["basicToken"]))
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/members",
                                        catch_response=False, headers=headers,
                                        data=data)
        return r

