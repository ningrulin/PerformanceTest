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


class KickMemberAction(ExecuteAction):
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
        self._logger_cn = logging.getLogger("Count")
        self.check_result = False
        self.attach_conf_id = None
        self.conf_obj = None
        self.conf_mid_map = None
        self.kick_mem_phone_num_list = []
        self.kick_mid_list = []
        self.chair_mid = None
        self.chair_num = None
        self.kick_num = 0
        self.chair_obj = None
        self._logger_ar = logging.getLogger("AllResult")


    def _execute_action(self):
        try :
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            if "kick_num" in self.case_info_dict:
                self.kick_num = self.case_info_dict["kick_num"]


            self.attach_conf_id = random.choice(self.user_pool.conf_id_list)
            self.conf_obj = self.user_pool.conf_id_obj_dict[self.attach_conf_id]
            self.conf_mid_map = self.conf_obj.mid_map
            self.chair_num = self.conf_obj.conf_chair_phone_num
            self.chair_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[self.chair_num].user_info_dict["userID"])]
            self.chair_obj = self.user_pool.user_phone_num_obj_dict[self.chair_num]

            if self.kick_num==0:
                self.kick_num = len(self.user_pool.in_conf_mem_phone_num_list) - 40

            if self.kick_num == 0:
                return False

            self.kick_mem_phone_num_list = random.sample(self.user_pool.in_conf_mem_phone_num_list, self.kick_num)

            for kick_num in self.kick_mem_phone_num_list:
                kick_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[kick_num].user_info_dict["userID"])]
                self.kick_mid_list.append(kick_mid)

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                self.user_pool.cache_lock.acquire()
                self.user_pool.in_conf_mem_phone_num_list =copy.deepcopy(list(set(self.user_pool.in_conf_mem_phone_num_list)^set(self.kick_mem_phone_num_list)))
                self.user_pool.out_conf_mem_phone_num_list.extend(self.kick_mem_phone_num_list)
                self.user_pool.cache_lock.release()

                self._logger.debug("kick_member success!")
                self.properly_executed = True
                return True
            else:
                self._logger.error("kick_member Fail!")
                return False
        except:
            self._logger.error("Return False because of except.")
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
        self._logger.info("execute kick_memeber")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members/kick"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = self.kick_mid_list
        data = json.dumps(data)
        headers = {'authorization': self.chair_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/members/mute",
                                        catch_response=False, headers=headers,
                                        data=data)

        return r

    def _clean_up_when_fail(self):
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个测试信号
        else:
            pass


    """
    def _check_resutl(self):
        server_affdata_flag, server_affdata = self.query_confs3_DETAIL()

        if not server_affdata_flag:
            self._logger.error("error:"+str(server_affdata))
            return False

        except_ismute_status = self.is_mute

        member_list = []
        if "members" in server_affdata:
            member_list = json.loads(server_affdata)["members"]["set"]

        now_ismute_status = False
        mute_status = False
        for member in member_list:
            if str(member["mid"]) == str(self.kick_mid):
                now_ismute_status = True
                mute_status = member["mute"]
                break

        if not now_ismute_status:
            self._logger.error("Can not get the member information in the meeting info! mid:" + str(self.kick_mid))
            return False

        if except_ismute_status == mute_status:
            self._logger.info("check mute info success, " + "mid:" + str(self.kick_mid)
                              + " phone_num:" + str(self.kick_mem_phone_num)
                              + " except_ismute_status:" + str(except_ismute_status)
                              + " mute_status:" + str(mute_status))
            return True
        else:
            self._logger.info("check mute info failed, " + "mid:" + str(self.kick_mid)
                              + " phone_num:" + str(self.kick_mem_phone_num)
                              + " except_ismute_status:" + str(except_ismute_status)
                              + " mute_status:" + str(mute_status))
            return False"""


    def query_confs3_DETAIL(self):
        try:
            self._logger.info("execute query_conference")

            url = Constant.CONFS_URL + "/" + self.attach_conf_id + "?param=MEMBERS"
            headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                       "Content-Type": "application/json; charset=utf-8"}

            r = requests.get(url, headers=headers)
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