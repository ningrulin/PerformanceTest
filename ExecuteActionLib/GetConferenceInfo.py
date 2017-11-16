# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
import logging
import time
import copy
import json
import traceback
import random


class GetConferenceInfoAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.chairman_phone_num = None
        self.group_obj = None
        self.conf_id = None
        self.conf_mid_map = {}
        self.flage = False
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)
        self._logger_ar = logging.getLogger("AllResult")
        self.check_result = False
        self.chair_mid = None
        self.group_id = None

    def _execute_action(self):
        try:
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            self.executor_phone_num = random.choice(self.user_pool.conf_chair_phone_num_list)
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id

            self.conf_obj = copy.deepcopy(self.user_pool.conf_id_obj_dict[self.attach_conf_id])
            self.conf_mid_map = self.conf_obj.mid_map
            self._logger.debug("self.conf_obj.mid_map" + str(self.conf_obj.mid_map))

            self.chair_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[self.conf_obj.conf_chair_phone_num].user_info_dict["userID"])]
            self._logger.debug("self.chair_mid" + str(self.chair_mid))
            self.group_id = self.conf_obj.group_id

            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.getinfo_mem_phone_num = copy.deepcopy(self.user_pool.in_conf_mem_phone_num_list.pop())
                self.user_pool.cache_lock.release()
            else:
                # 在mid_list中随机选取一个元素
                self.getinfo_mem_phone_num = random.choice(self.conf_obj.in_conf_mem_num_list)

            self.getinfo_mid = self.conf_mid_map[str(
                self.user_pool.user_phone_num_obj_dict[self.getinfo_mem_phone_num].user_info_dict["userID"])]
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                if self.check_result:
                    if not self._result_check(http_response):
                        self._logger.debug("check result is ERROR!")
                        self._logger_ar.debug("execute GetConferenceInfo: check result fail! http.status_code == 200")
                        return False

                    self.user_pool.cache_lock.acquire()
                    self.user_pool.in_conf_mem_phone_num_list.appendleft(self.getinfo_mem_phone_num)
                    self.user_pool.cache_lock.release()
                    self._logger.debug("check result is success!")
                    self._logger_ar.debug("execute GetConferenceInfo: check result success! http.status_code == 200")
                else:
                    self._logger_ar.debug("execute GetConferenceInfo: http.status_code == 200")

                self.properly_executed = True
                self._logger.debug("GetConferenceInfo success!")
                return True
            else:
                self._logger.error("GetConferenceInfo failed!")
                self._logger_ar.debug("execute GetConferenceInfo: http.status_code == " + str(http_response.status_code))
                return False
        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute GetConferenceInfo: except")
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

    def _clean_up_when_fail(self):
        """
        当测试执行失败后，执行该操作
        :return:
        """
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        if self.getinfo_mem_phone_num not in self.user_pool.in_conf_mem_phone_num_list:
            self.user_pool.cache_lock.acquire()
            self.user_pool.in_conf_mem_phone_num_list.appendleft(self.getinfo_mem_phone_num)
            self.user_pool.cache_lock.release()

        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个进程信号
        else:
            pass

    def _execute_http_request(self):
        self._logger.info("execute GET CONFERENCE INFO")
        url = Constant.CONFS_URL + "/" + self.attach_conf_id + "?param=GENERAL"
        method  = "GET"
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/getinfo",
                                        catch_response=False, headers=headers)
        self._logger.debug("aqf r.r" + str(r.status_code))
        self._logger.debug("aqf r.text" + str(r.text))
        return r

    def _result_check(self, http_response):
        restult_body = {}
        restult_body = json.loads(http_response.text)
        self._logger.debug("aqf restult_body" + str(restult_body))
        self._logger.debug("aqf self.chair_mid" + str(self.chair_mid))
        if restult_body["ginfo"]["gid"] == self.group_id and restult_body["ginfo"]["chair"] == self.chair_mid and restult_body["ginfo"]["start"]:
            return True
        else:
            return False