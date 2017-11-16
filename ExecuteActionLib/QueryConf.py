# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
from SipOperation.SipCall import *
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from requests.exceptions import ConnectionError
import logging
import time
import random
import requests
import json
import traceback

class QueryConfAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.properly_executed = False
        self.check_result = False
        self._logger = logging.getLogger(log_name)

    def _execute_action(self):
        try:

            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.executor_phone_num = self.user_pool.in_conf_mem_phone_num_list.pop()
                self.user_pool.cache_lock.release()
            else:
                # 在conf_mem_phone_num_list中随机选取一个元素
                self.executor_phone_num = random.choice(self.user_pool.in_conf_mem_phone_num_list)

            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                self.user_pool.cache_lock.acquire()
                self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("QueryConf success!")
                if self.check_result:
                    if not self.check_conf_info():
                        return False
                return True
            else:
                self._logger.error("QueryConf Fail!")
                return False
        except:
            self._logger.warning("Return False because of except.")
            self._logger.warning(traceback.format_exc())
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
        self._logger.info("execute query_conference")
        method = 'GET'
        url = Constant.CONFS_URL + "/" + self.attach_conf_id + "?param=DETAIL"
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="query_conference",
                                        catch_response=False, headers=headers)
        self._logger.info(r.text)
        return r

    def check_conf_info(self):
        """
        检查点：1.成员列表 2.gid 3.id 4.chair 5.uri 6.mode 7.start 8.ppt
        "id": "MXSs6fsUl0S0G0kwLBc6e19Q",
        "gid": "58c20360c8ec4e6e708fe7fa",
        "chair": 3,
        "start": true,
        "ppt": null,
        "uri": "MXSs6fsUl0S0G0kwLBc6e19Q:172.18.16.187",
        "mode": "CHAIRCONTROL"
        :return:
        """
        pass

    def query_confs2(self,conf_id, basicToken):
        try:
            headers = {'authorization': basicToken,
                       "Content-Type": "application/json; charset=utf-8"}
            URL = Constant.HOST +"/cxf/confs2/test/1/11/" + conf_id
            print URL
            r = requests.get(URL, headers=headers)
            r.close()
            if int(r.status_code) == 200:
                return True, r.text
            elif int(r.status_code) == 404:
                return False, "no conf_id"
            else:
                return False, r.status_code
        except ConnectionError as e:
            print e
            return False, "ConnectionError"

    def get_my_mss(self, conf_id, user_mid, basic_token):
        flag_get_mss, r_get_mss = self.query_confs2(conf_id, basic_token)
        if not flag_get_mss:
            return False, "No Conf_id"
        member_json = json.loads(r_get_mss)["members"]

        for member_info in member_json.items():
            if member_info[1]["conferMemberID"] == user_mid:
                return True, member_info[1]["msss2"]

        return False, "No mid"

    def _clean_up_when_fail(self):
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
            if self.executor_phone_num not in self.user_pool.in_conf_mem_phone_num_list:
                self.user_pool.in_conf_mem_phone_num_list.appendleft(self.executor_phone_num)
            self.user_pool.cache_lock.release()
