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
import random
import uuid


class JoinConf2Action(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.chairman_phone_num= None
        self.chair_obj = None
        self.group_obj = None
        self.conf_id = None
        self.conf_mid_map = {}
        self.all_conf_mem_info_dict = []
        self.conf_mem_phone_num_list = []
        self.conf_mem_sip_number_list = []
        self.all_in_conf_mem_sip_number_list = []
        self.all_in_conf_mem_phone_number_list = []
        self.action_resource_lock = threading.Lock()
        self.received_call_notify_num_list = []
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)
        self.media_type = True
        self.received_inconf_num_list = []
        self.flag = False
        self.listcc = []

    def _execute_action(self):
        try:
            reg_callee_caps = 10
            if "reg_callee_caps" in self.case_info_dict:
                reg_callee_caps = self.case_info_dict["reg_callee_caps"]

            if "with_media" in self.case_info_dict:
                self.media_type = self.case_info_dict["with_media"]

            join_caps = 2
            if "join_caps" in self.case_info_dict:
                join_caps = self.case_info_dict["join_caps"]

            self.user_pool.cache_lock.acquire()
            '''get confid'''
            self.conf_id=self.user_pool.conf_id_list.pop()
            self.user_pool.cache_lock.release()

            self.conf_obj = self.user_pool.conf_id_obj_dict[self.conf_id]
            self.conf_group_id = self.conf_obj.group_id
            self.chairman_phone_num = self.conf_obj.conf_chair_phone_num

            self._logger.info("aqf:this confid is: " + str(self.conf_id))
            self._logger.info("aqf:show aqf_test:******************************************")
            self._logger.info("aqf:self.user_pool.out_conf_mem_phone_num_list: " + str(self.user_pool.out_conf_mem_phone_num_list))
            self._logger.info("aqf:self.user_pool.in_conf_mem_phone_num_list: " + str(self.user_pool.in_conf_mem_phone_num_list))
            self._logger.info("aqf:self.conf_group_id: " + str(self.conf_group_id))

            '''get all out conf list,and select join_caps'''
            self.conf_mem_phone_num_list = copy.deepcopy(self.user_pool.out_conf_mem_phone_num_list)
            self.conf_all_mem_phone_num_list = random.sample(self.conf_mem_phone_num_list, join_caps)
            self._logger.info(
                "aqf:self.conf_all_mem_phone_num_list: " + str(self.conf_all_mem_phone_num_list))

            # 所有会议成员的sip_number 不包括主席
            for conf_mem_phone_num in self.conf_all_mem_phone_num_list:
                conf_mem_sip_number = str(
                    self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num].user_info_dict["userID"]) + "00"
                # 所有会议成员的sip_number 不包括主席
                self.conf_mem_sip_number_list.append(conf_mem_sip_number)
                mem_info_dict = {
                    "uid": self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num].user_info_dict["userID"],
                    "name": self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num].user_info_dict["commName"],
                    "basicToken": self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num].user_info_dict["basicToken"]
                }

                #发起会议接口需要携带所有会议成员（包括主席）的信息
                self.all_conf_mem_info_dict.append(mem_info_dict)

            self._logger.info("aqf:显示入会的成员号码" + str(self.conf_all_mem_phone_num_list))
            self._logger.info("aqf:显示入会的成员SIP号码"+str(self.conf_mem_sip_number_list))


            # 所有会议成员的sip_number 包括主席
            #:aqf:发起主动入会的成员列表

            in_conf_mem_num = len(self.conf_all_mem_phone_num_list)
            sip_reg_callee_timeout = in_conf_mem_num // reg_callee_caps + 3

            UUID = uuid.uuid1()
            # sip 注册，对应会议群中所有成员
            sip_reg = SipRegisterMap.get_instance().get_sip_register(str(self.conf_group_id)+"_"+str(UUID), SipMqConstants.SIP_REG_SERVER)

            #主叫列表
            #caller_sip_number_list = []
            #caller_sip_number_list.append(conf_chairman_sip_number)
            caller_sip_number_list = copy.deepcopy(self.conf_mem_sip_number_list)

            sip_reg_flag, caller_port, callee_port = \
                sip_reg.register_users_with_same_config(caller_sip_number_list,
                                                        [], SipMqConstants.SIP_REG_SERVER,
                                                        SipMqConstants.SIP_PASSWORD,reg_callee_caps,sip_reg_callee_timeout)
            self._logger.info("aqf:***********start reg********************")
            if not sip_reg_flag:
                self._logger.error("aqf:sip registration failed!")
                return False

            self._logger.info("aqf:he calling port and the called port are: %s,%s" % (str(caller_port), str(callee_port)))

            self.chair_obj = self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num]
            self.chair_obj.ws_client.add_handler(self._analyze_notify)

            #r = self._execute_http_request()
            # todo XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX50个并发发送HTTP消息---OK
            self._logger.info("aqf:start send sip list")
            self._logger.info("aqf:conf_all_mem_phone_num_list: "+ (str(self.conf_all_mem_phone_num_list)))
            #join_signal = threading.Event()

            self._logger.info("aqf test***********************************")
            self._logger.info("mem_info_dict: " + (str( self.user_pool.user_phone_num_obj_dict)))
            join_signal = threading.Event()

            for join_user in self.all_conf_mem_info_dict:
                http_user_send = self._class_execute_http_request(self._logger, join_user, self.conf_id, join_signal)
                http_user_send.start()

            join_signal.set()

            self._logger.info("start send sipp, join the conf")

            # 先拉起被叫
            # sip 被叫流程
            # 如果是一个人的会议就不需要被叫流程了
            sipcall = SipCallMap.get_instance().get_sip_call(str(self.conf_group_id)+"_"+str(UUID))

            # 主叫
            if not sipcall.make_call(caller_sip_number_list, str(self.conf_id),
                                     SipMqConstants.SIP_MEDIA_SERVER, SipMqConstants.SIP_PASSWORD, caller_port,10000,10,5, self.media_type):
                self._logger.error("Sip caller failed!")
                return False


            time_out = 100
            while time_out:
                self.action_resource_lock.acquire()
                if len(self.received_inconf_num_list) == len(self.conf_all_mem_phone_num_list):
                    self.action_resource_lock.release()
                    print "break"
                    break
                self.action_resource_lock.release()
                time.sleep(1)
                time_out -= 1

            if len(self.received_inconf_num_list) == len(self.conf_all_mem_phone_num_list):
                self.flag = True

            self.chair_obj.ws_client.sub_handler(self._analyze_notify)

            self._logger.info("Sip caller is successful!")

            self.user_pool.cache_lock.acquire()
            self.user_pool.conf_id_list.appendleft(self.conf_id)
            self.user_pool.cache_lock.release()

            #删除已入会的成员
            self.user_pool.cache_lock.acquire()
            for user_name in self.conf_all_mem_phone_num_list:
                self._logger.info("aqf:delete:" + str(user_name))
                self.user_pool.out_conf_mem_phone_num_list.remove(user_name)
            self.user_pool.cache_lock.release()
            #添加已入会的
            self.user_pool.cache_lock.acquire()
            self.user_pool.in_conf_mem_phone_num_list.extend(self.conf_all_mem_phone_num_list)
            #self._logger.info("conf_mid_map:" + str(self.conf_mid_map))
            self.user_pool.conf_id_obj_dict[self.conf_id].mid_map.update(self.conf_mid_map)
            self.user_pool.conf_id_obj_dict[self.conf_id].in_conf_mem_num_list = copy.deepcopy(self.user_pool.in_conf_mem_phone_num_list)
            self.user_pool.conf_id_obj_dict[self.conf_id].out_conf_mem_num_list = copy.deepcopy(self.user_pool.out_conf_mem_phone_num_list)
            self.user_pool.conf_id_obj_dict[self.conf_id].unmute_mid_list.extend(self.conf_all_mem_phone_num_list)
            self.user_pool.conf_id_obj_dict[self.conf_id].mute_mid_list = []
            self.user_pool.cache_lock.release()

            self._logger.info("aqf:输出**********************")

            self._logger.info("aqf:输出未入会列表" + str(self.user_pool.out_conf_mem_phone_num_list))
            self._logger.info("aqf:输出已入会列表" + str(self.user_pool.in_conf_mem_phone_num_list))
            if self.flag:
                self._logger.debug("Join conference is successfully!")
            else :
                self._logger.debug("Join conference is failed!")
            self.properly_executed = True

        except:
            self._logger.error("Return False because of except.")
            self._logger.error(traceback.format_exc())

        finally:
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]

            """if not self.properly_executed:
                self._clean_up_when_fail()"""

            time.sleep(sleep_after)
            return self.properly_executed

    class _class_execute_http_request(threading.Thread):
        def __init__(self,_logger, userinfo, confid, join_signal):
            threading.Thread.__init__(self)
            self.user_info = userinfo
            self._logger = _logger
            self.confid = confid
            self.join_signal = join_signal

        def run(self):
            self.join_signal.wait()
            self._logger.info("execute join_conference")
            # self._logger.info("execute create_conference")
            url = Constant.CONFS_URL + "/" + str(self.confid) + "/members/join"  # v3
            method = 'POST'
            data = {"uid": self.user_info["uid"],
                    "name": self.user_info["name"],
                    "vs": 2
                    }
            headers = {'authorization': self.user_info["basicToken"],
                       "Content-Type": "application/json; charset=utf-8"}
            execute_http_client = HttpClient(url)
            r = execute_http_client.request(method=method, url=url, name="/members/join", catch_response=False,
                                            headers=headers,
                                            data=json.dumps(data))
            if r.status_code != 200:
                self._logger.warning("aqf: http fail! "+ str(r.text))
                self._logger.error("aqf:Join conf fail!")

    def _analyze_notify(self, **kwargs):
        if "message" in kwargs:
            json_data = json.loads(kwargs["message"])
            event = json_data.get("event", {})
            event_name = event.get("name", "")
            self._logger.debug("aqf: print name event:" + str(event))
            self._logger.debug("aqf: print name:" + str(event.get("name", "")))
            self._logger.debug("aqf: print event_body:" + str(event.get("body", [])))

            if event_name == "mx.conf3.arrayNotify" and event.get("cid", "") == self.conf_id and kwargs["user_num"] == self.chairman_phone_num:
                event_body = event.get("body", [])
                self._logger.debug("aqf: print 3event_body:" + str(event_body))
                for sigle_event in event_body:
                    if sigle_event["name"] == "mx.conf3.member":
                        self._logger.debug("aqf: self.received_inconf_num_list " + str(self.received_inconf_num_list))
                        event_uid = sigle_event.get("body", {})["uid"]
                        event_mid = sigle_event.get("body", {})["mid"]
                        if event_uid not in self.received_inconf_num_list and sigle_event.get("body", {})["ol"]:
                            self.received_inconf_num_list.append(kwargs["user_num"])
                            self.conf_mid_map.update({str(event_uid): event_mid})
                            self._logger.debug(
                                "Receive the add_mem notification, update the mid_map in the conf object.")
                            self._logger.debug("aqf: print self.received_inconf_info " + str(
                                self.received_inconf_num_list))
                        else:
                            pass

                        #if kwargs["user_num"] not in self.received_inconf_num_list and sigle_event.get("body", {})["ol"]:



    def _clean_up_when_fail(self):
        """
        当测试执行失败后，执行该操作
        :return:
        """
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
