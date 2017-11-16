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


class MuteMemberAction(ExecuteAction):
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
        self.mute_mem_phone_num = None
        self.mute_mid = False
        self._logger_ar = logging.getLogger("AllResult")


    def _execute_action(self):
        try :
            if "check_result" in self.case_info_dict:
                self.check_result = self.case_info_dict["check_result"]

            self.executor_phone_num = random.choice(self.user_pool.conf_chair_phone_num_list)
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.attach_conf_id = self.executor_obj.attach_conf_id

            self.conf_obj = copy.deepcopy(self.user_pool.conf_id_obj_dict[self.attach_conf_id])
            self.conf_mid_map = self.conf_obj.mid_map

            if self.check_result:
                self.user_pool.cache_lock.acquire()
                self.mute_mem_phone_num = copy.deepcopy(self.user_pool.in_conf_mem_phone_num_list.pop())
                self.user_pool.cache_lock.release()
            else:
                # 在mid_list中随机选取一个元素
                self.mute_mem_phone_num = random.choice(self.conf_obj.in_conf_mem_num_list)

            self.mute_mid = self.conf_mid_map[str(
                self.user_pool.user_phone_num_obj_dict[self.mute_mem_phone_num].user_info_dict["userID"])]

            if self.mute_mid in self.conf_obj.unmute_mid_list:
                self.is_mute = True

            http_response = self._execute_http_request()
            if http_response.status_code == 200:
                if self.check_result:
                    time.sleep(0.2)
                    if not self.check_ismute_info():
                        self._logger_ar.debug("execute Mute: check result error! http.status_code == 200")
                        return False
                    self.user_pool.cache_lock.acquire()
                    self.user_pool.in_conf_mem_phone_num_list.appendleft(self.mute_mem_phone_num)
                    self.user_pool.cache_lock.release()

                    self.user_pool.cache_lock.acquire()
                    if self.is_mute:
                        if self.mute_mid in self.conf_obj.unmute_mid_list:
                            self.conf_obj.unmute_mid_list.remove(self.mute_mid)
                        self.conf_obj.mute_mid_list.append(self.mute_mid)
                    else:
                        if self.mute_mid in self.conf_obj.mute_mid_list:
                            self.conf_obj.mute_mid_list.remove(self.mute_mid)
                        self.conf_obj.unmute_mid_list.append(self.mute_mid)
                    self.user_pool.cache_lock.release()

                    self._logger_ar.debug("execute Mute: check result success! http.status_code == 200")
                    self.properly_executed = True
                    return True

                self.user_pool.cache_lock.acquire()
                if self.is_mute:
                    if self.mute_mid in self.conf_obj.unmute_mid_list:
                        self.conf_obj.unmute_mid_list.remove(self.mute_mid)
                    self.conf_obj.mute_mid_list.append(self.mute_mid)
                else:
                    if self.mute_mid in self.conf_obj.mute_mid_list:
                        self.conf_obj.mute_mid_list.remove(self.mute_mid)
                    self.conf_obj.unmute_mid_list.append(self.mute_mid)
                self.user_pool.cache_lock.release()

                self._logger_ar.debug("execute Mute: http.status_code == 200")
                self.properly_executed = True
                return True
            else:
                self._logger.error("Mute Fail!")
                if  self.check_result:
                    self._logger_ar.debug("execute Mute: check result fail! http.status_code == " + str(http_response.status_code))
                self._logger_ar.debug("execute Mute: http.status_code == " + str(http_response.status_code))
                return False
        except:
            self._logger.error("Return False because of except.")
            self._logger_ar.debug("execute Mute: except")
            self._logger.error(traceback.format_exc())
            return False
        finally:
            nowtime_str = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))
            filename = "/mnt/" + nowtime_str + ".png"
            objgraph.show_refs([self.user_pool], filename=filename)
            self._logger.debug("in_conf_mem_num_list: " + str(self.conf_obj.in_conf_mem_num_list))
            self._logger.debug("out_conf_mem_num_list: " + str(self.conf_obj.out_conf_mem_num_list))
            sleep_after = 0

            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]
            if not self.properly_executed:
                self._clean_up_when_fail()
            time.sleep(sleep_after)
            return self.properly_executed

    def _execute_http_request(self):
        self._logger.info("execute mute_member")
        url = Constant.CONFS_URL + "/" + str(self.attach_conf_id) + "/members/mute"
        method = 'POST'
        # 使用把参数列表中的groupshareid
        data = [{
                "mid": self.mute_mid,
                "mute": self.is_mute
            },]
        data = json.dumps(data)
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/members/mute",
                                        catch_response=False, headers=headers,
                                        data=data)
        r.close()
        return r

    def _clean_up_when_fail(self):
        if self.user_pool.cache_lock.locked():
            self.user_pool.cache_lock.release()

        if self.mute_mem_phone_num not in self.user_pool.in_conf_mem_phone_num_list:
            self.user_pool.cache_lock.acquire()
            self.user_pool.in_conf_mem_phone_num_list.appendleft(self.mute_mem_phone_num)
            self.user_pool.cache_lock.release()

        abnormal_interrupt = False
        if "abnormal_interrupt" in self.case_info_dict:
            abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

        if abnormal_interrupt:
            self.p_stop_signal.set()
            # False，设置终止整个测试信号
        else:
            pass

    def check_ismute_info(self):
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
            if str(member["mid"]) == str(self.mute_mid):
                now_ismute_status = True
                mute_status = member["mute"]
                break

        if not now_ismute_status:
            self._logger.error("Can not get the member information in the meeting info! mid:" + str(self.mute_mid))
            return False

        if except_ismute_status == mute_status:
            self._logger.info("check mute info success, " + "mid:" + str(self.mute_mid)
                              + " phone_num:" + str(self.mute_mem_phone_num)
                              + " except_ismute_status:" + str(except_ismute_status)
                              + " mute_status:" + str(mute_status))
            return True
        else:
            self._logger.info("check mute info failed, " + "mid:" + str(self.mute_mid)
                              + " phone_num:" + str(self.mute_mem_phone_num)
                              + " except_ismute_status:" + str(except_ismute_status)
                              + " mute_status:" + str(mute_status))
            return False


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
