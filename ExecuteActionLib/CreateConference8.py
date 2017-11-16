# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
from SipOperation.SipCall import *
from SipOperation.SipRegister import *
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.ConferenceInfo import ConferenceInfo
from requests.exceptions import ConnectionError
import logging
import threading
import time
import copy
import json
import requests
import traceback
import random
import uuid


class CreateConf8Action(ExecuteAction):
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
        self.all_in_conf_mem_info_dict = []
        self.conf_mem_phone_num_list = []
        self.in_conf_mem_sip_number_list = []
        self.all_in_conf_mem_sip_number_list = []
        self.all_in_conf_mem_phone_number_list = []
        self.action_resource_lock = threading.Lock()
        self.received_call_notify_num_list = []
        self.received_inconf_info = []
        self.flage = False
        self.received_member_num_list = []
        self.members_num_list = []
        self.properly_executed = False
        self.is_init_mss = False
        self._logger = logging.getLogger(log_name)
        self._logger_ar = logging.getLogger("AllResult")

    def _execute_action(self):
        try:
            reg_callee_caps = 10
            if "reg_callee_caps" in self.case_info_dict:
                reg_callee_caps = self.case_info_dict["reg_callee_caps"]

            self.only_self = False
            if "only_self" in self.case_info_dict:
                self.only_self = self.case_info_dict["only_self"]

            if "is_init_mss" in self.case_info_dict:
                self.is_init_mss = self.case_info_dict["is_init_mss"]

            self.user_pool.cache_lock.acquire()
            self.conf_group_id = self.user_pool.group_id_list.pop()
            self.user_pool.cache_lock.release()

            self.group_obj = self.user_pool.group_id_obj_dict[self.conf_group_id]
            self.chairman_phone_num = self.group_obj.group_owner_phone_num
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num]

            self.conf_all_mem_phone_num_list = copy.deepcopy(self.chairman_phone_num)

            chairman_info_dict = {
                "uid": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"],
                "name": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["commName"]}

            self.all_in_conf_mem_info_dict.append(chairman_info_dict)

            r = self._execute_http_request()
            if r.status_code != 200:
                self._logger.warning(str(r.text))
                self._logger.error("Create confs fail!")
                self._logger_ar.debug("execute createconf : is failed! http.status_code == "+ str(r.status_code))
                return False

            self.user_pool.cache_lock.acquire()
            self.user_pool.group_id_list.appendleft(self.conf_group_id)
            self.user_pool.cache_lock.release()

            self._logger.debug("Create confs successfully!")
            self._logger_ar.debug("execute createconf : is success! http.status_code == 200")
            self.properly_executed = True

        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute createconf is except!")
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

        if self.conf_group_id not in self.user_pool.group_id_list:
            self.user_pool.cache_lock.acquire()
            self.user_pool.group_id_list.appendleft(self.conf_group_id)
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
        self._logger.info("execute create_conference")
        url = Constant.CONFS_URL
        # url = "http://test.meetsoon.net/cxf/confs2"
        method = 'POST'
        # 使用把参数列表中的groupshareid

        data = {"gid": self.conf_group_id,
                "members": self.all_in_conf_mem_info_dict,
                "systemOpenGroup": "false",
                "onlyself": self.only_self
                }
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url,
                                        name="create_conference",
                                        catch_response=False, headers=headers,
                                        data=json.dumps(data))
        return r