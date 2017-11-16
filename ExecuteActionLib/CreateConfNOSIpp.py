# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
from SipOperation.SipCall import *
from SipOperation.SipRegister import *
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.ConferenceInfo import ConferenceInfo
import logging
import threading
import time
import copy
import json
import requests
import traceback


class CreateConfAction(ExecuteAction):
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
        self.properly_executed = False
        self.is_init_mss = False
        self._logger = logging.getLogger(log_name)

    def _execute_action(self):
        try:
            self.only_self = False
            if "only_self" in self.case_info_dict:
                self.only_self = self.case_info_dict["only_self"]

            self.user_pool.cache_lock.acquire()
            self.conf_group_id = self.user_pool.group_id_list.pop()
            self.user_pool.cache_lock.release()

            self._logger.debug("this group_id is: " + str(self.conf_group_id))
            self._logger.debug("self.user_pool.group_id_list: " + str(self.user_pool.group_id_list))

            self.group_obj = self.user_pool.group_id_obj_dict[self.conf_group_id]
            self.chairman_phone_num = self.group_obj.group_owner_phone_num
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num]

            self.conf_mem_phone_num_list = copy.deepcopy(self.group_obj.group_mem_phone_num_list)
            self.conf_all_mem_phone_num_list = copy.deepcopy(self.conf_mem_phone_num_list)
            self.conf_all_mem_phone_num_list.append(self.chairman_phone_num)

            if self.only_self:
                self.in_conf_mem_phone_num_list = []
                self.out_conf_mem_phone_num_list = self.conf_mem_phone_num_list
            else:
                self.in_conf_mem_phone_num_list = self.conf_mem_phone_num_list
                self.out_conf_mem_phone_num_list = []

            self.all_in_conf_mem_phone_number_list = copy.deepcopy(self.in_conf_mem_phone_num_list)
            self.all_in_conf_mem_phone_number_list.append(self.chairman_phone_num)

            for in_conf_mem_phone_num in self.in_conf_mem_phone_num_list:
                mem_info_dict = {
                    "uid": self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["userID"],
                    "name": self.user_pool.user_phone_num_obj_dict[in_conf_mem_phone_num].user_info_dict["commName"]}

                # 发起会议接口需要携带所有会议成员（包括主席）的信息
                self.all_in_conf_mem_info_dict.append(mem_info_dict)

            chairman_info_dict = {
                # "userID": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"],
                "uid": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["userID"],
                "name": self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num].user_info_dict["commName"]}
            self.all_in_conf_mem_info_dict.append(chairman_info_dict)

            r = self._execute_http_request()

            if r.status_code != 200:
                self._logger.warning(str(r.text))
                self._logger.error("Create confs fail!")
                return False

            conf_id = json.loads(r.text)["id"]
            self.conf_id = conf_id
            self._logger.info("Create confs success!"+str(self.conf_id))

            self.properly_executed = True

        except:
            self._logger.error("Return False because of except.")
            self._logger.error(traceback.format_exc())

        finally:
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]

            if not self.properly_executed:
                self._clean_up_when_fail()

            time.sleep(sleep_after)
            return self.properly_executed

    def delete_conf(self):
        self._logger.info("execute delete_conference")
        url = Constant.CONFS_URL
        # url = "http://test.meetsoon.net/cxf/confs2"
        method = 'DELETE'
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url,
                                        name="create_conference", catch_response=False,
                                        headers=headers)
        if r.status_code == 200:
            self._logger.info("Delete confs success!" + str(self.conf_id))
        elif r.status_code == 404:
            self._logger.info("Confs already end!" + str(self.conf_id))
        else:
            self._logger.error("Delete confs fail!" + str(self.conf_id))

    def _clean_up_when_fail(self):
        """release user source when fail."""
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()
        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个进程信号
        else:
            self.user_pool.cache_lock.acquire()
            if self.conf_group_id not in self.user_pool.group_id_list:
                self.user_pool.group_id_list.appendleft(self.conf_group_id)

            if self.conf_id is not None:
                self.user_pool.conf_id_list.remove(self.conf_id)

            if self.conf_id in self.user_pool.conf_id_obj_dict:
                del self.user_pool.conf_id_obj_dict[self.conf_id]

            for in_conf_mem_phone_num in self.in_conf_mem_phone_num_list:
                if in_conf_mem_phone_num in self.user_pool.in_conf_mem_phone_num_list:
                    self.user_pool.in_conf_mem_phone_num_list.remove(in_conf_mem_phone_num)
            for out_conf_mem_phone_num in self.out_conf_mem_phone_num_list:
                if out_conf_mem_phone_num in self.user_pool.out_conf_mem_phone_num_list:
                    self.user_pool.out_conf_mem_phone_num_list.remove(out_conf_mem_phone_num)

            for conf_mem_phone_num in self.conf_mem_phone_num_list:
                if conf_mem_phone_num in self.user_pool.conf_mem_phone_num_list:
                    self.user_pool.conf_mem_phone_num_list.remove(conf_mem_phone_num)
                if conf_mem_phone_num in self.user_pool.conf_all_mem_phone_num_list:
                    self.user_pool.conf_all_mem_phone_num_list.remove(conf_mem_phone_num)
            if self.chairman_phone_num in self.user_pool.conf_chair_phone_num_list:
                self.user_pool.conf_chair_phone_num_list.remove(self.chairman_phone_num)
            if self.chairman_phone_num in self.user_pool.conf_all_mem_phone_num_list:
                self.user_pool.conf_all_mem_phone_num_list.remove(self.chairman_phone_num)

            self.group_obj.is_in_conf = True
            self.group_obj.conf_id = None
            self.user_pool.cache_lock.release()

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
                                        name="create_conference", catch_response=False, headers=headers,
                                        data=json.dumps(data))
        return r

    def _analyze_notify(self,**kwargs):
        if "message" in kwargs:
            json_data = json.loads(kwargs["message"])
            body = json_data.get("event", {})
            noty_name = body.get("name", "")
            if noty_name == "mx.conf.conf_call_notify" and body.get(
                "confID","") == self.conf_id:
                # self.action_resource_lock.acquire()
                self.received_call_notify_num_list.append(kwargs["user_num"])
                # self.action_resource_lock.release()
                if kwargs["user_num"] != self.chairman_phone_num:
                    url = Constant.CONFS_URL + "/" + self.conf_id + "/callme"
                    basicToken = None
                    if "basicToken" in kwargs:
                        basicToken = kwargs["basicToken"]
                    headers = {'authorization': basicToken,
                               "Content-Type": "application/json; charset=utf-8"}
                    execute_http_client = HttpClient(url)
                    r = execute_http_client.request(method="POST", url=url, name="/callme", catch_response=False,
                                                    headers=headers)
                    return r

    def get_conf_mid(self):
        pass
