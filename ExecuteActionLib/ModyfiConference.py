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


class ModifyConfAction(ExecuteAction):
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
        self.attach_conf_id = None
        self.conf_obj = None
        self.conf_mid_map = None
        self.modify_mid = None
        self.conf_mod = None

    def _execute_action(self):
        try :
            conf_mod = "0"
            if "conf_mode" in self.case_info_dict:
                conf_mod = self.case_info_dict["conf_mode"]

            if conf_mod == "0":
                self.conf_mod = "CHAIRCONTROL"
            else:
                self.conf_mod = "FREE"
            self.executor_phone_num = random.choice(self.user_pool.conf_chair_phone_num_list)
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id

            self.conf_obj = copy.deepcopy(self.user_pool.conf_id_obj_dict[self.attach_conf_id])
            self.conf_mid_map = self.conf_obj.mid_map

            self.modify_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[self.executor_phone_num].user_info_dict["userID"])]

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                self._logger.debug("ModifyConferencestatus  success!")
                if self.conf_mod == "CHAIRCONTROL":
                    self.user_pool.cache_lock.acquire()
                    mute_mid_list = []
                    in_conf_mid = None
                    for in_conf_num in self.user_pool.conf_id_obj_dict[self.attach_conf_id].in_conf_mem_num_list:
                        in_conf_mid = self.conf_mid_map[
                            str(self.user_pool.user_phone_num_obj_dict[in_conf_num].user_info_dict["userID"])]
                        mute_mid_list.append(in_conf_mid)
                    self.user_pool.conf_id_obj_dict[self.attach_conf_id].mute_mid_list = copy.deepcopy(mute_mid_list)
                    self.user_pool.conf_id_obj_dict[self.attach_conf_id].unmute_mid_list = []
                    self.user_pool.cache_lock.release()
                else:
                    self.user_pool.cache_lock.acquire()
                    unmute_mid_list = []
                    in_conf_mid = None
                    for in_conf_num in self.user_pool.conf_id_obj_dict[self.attach_conf_id].in_conf_mem_num_list:
                        in_conf_mid = self.conf_mid_map[str(self.user_pool.user_phone_num_obj_dict[in_conf_num].user_info_dict["userID"])]
                        unmute_mid_list.append(in_conf_mid)
                    self.user_pool.conf_id_obj_dict[self.attach_conf_id].unmute_mid_list = copy.deepcopy(unmute_mid_list)
                    self.user_pool.conf_id_obj_dict[self.attach_conf_id].mute_mid_list = []
                    self.user_pool.cache_lock.release()
                self.properly_executed = True
            else:
                self._logger.error("ModifyConferencestatus  Fail!")
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
        self._logger.info("execute ModifyConferencestatus")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/ginfo"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = {"mode": self.conf_mod}
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
        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个测试信号
        else:
            pass
