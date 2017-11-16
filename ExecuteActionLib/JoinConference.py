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


class JoinConfAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.chairman_phone_num= None
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
            # self.conf_group_id = self.user_pool.group_id_list.pop()
            self.user_pool.cache_lock.release()

            self.conf_obj = self.user_pool.conf_id_obj_dict[self.conf_id]
            self.conf_group_id = self.conf_obj.group_id

            self._logger.info("aqf:this confid is: " + str(self.conf_id))
            self._logger.info("aqf:show aqf_test:******************************************")
            self._logger.info("aqf:self.user_pool.out_conf_list: " + str(self.conf_obj.out_conf_mem_num_list))
            self._logger.info("aqf:self.conf_group_id: " + str(self.conf_group_id))

            '''get all out conf list,and select join_caps'''
            self.conf_mem_phone_num_list = copy.deepcopy(self.conf_obj.out_conf_mem_num_list)
            self.conf_all_mem_phone_num_list = random.sample(self.conf_mem_phone_num_list, join_caps)

            # 所有会议成员的sip_number 不包括主席
            for conf_mem_phone_num in self.conf_all_mem_phone_num_list:
                """conf_mem_sip_number = str(
                                    self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num].user_info_dict["userID"]) + "00" """
                conf_mem_sip_number = str(int(str(
                        self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num].user_info_dict["userPhoneNum"])[
                        1:12]) - 11525100001 + 10010000019) + "00"
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

            for conf_mem_phone_num in self.conf_all_mem_phone_num_list:
                conf_mem_obj = self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num]
                conf_mem_obj.ws_client.add_handler(self._analyze_notify)

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


            time_out = 200
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

            for conf_mem_phone_num in self.conf_all_mem_phone_num_list:
                conf_mem_obj = self.user_pool.user_phone_num_obj_dict[conf_mem_phone_num]
                conf_mem_obj.ws_client.sub_handler(self._analyze_notify)


            self._logger.info("Sip caller is successful!")

            self._logger.info("aqf:输出**********************")

            self._logger.info("aqf:输出未入会列表" + str(self.user_pool.out_conf_mem_phone_num_list))
            self._logger.info("aqf:输出已入会列表" + str(self.user_pool.in_conf_mem_phone_num_list))

            self.user_pool.cache_lock.acquire()
            self.user_pool.conf_id_list.appendleft(self.conf_id)
            self.user_pool.cache_lock.release()
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
            self._logger.debug("aqf: print name:" + str(event.get("name", "")))
            self._logger.debug("aqf: print event_body:" + str(event.get("body", [])))

            if event_name == "mx.conf3.arrayNotify" :
                if "body" in event:
                    event_body = event.get("body", [])
                else:
                    event_body = event

                self._logger.debug("aqf: print 3event_body:" + str(event_body))

                if event.get("cid", "") == self.conf_id:
                    self._logger.debug("aqf: start do with mx.conf3.arrayNotify")
                    for sigle_event in event_body:
                        if sigle_event["name"] == "mx.conf3.member":
                            if kwargs["user_num"] not in self.listcc:
                                self.listcc.append(kwargs["user_num"])
                                self._logger.debug("aqf: print listcc " + str(self.listcc))
                            if sigle_event.get("body", {})["ol"] :
                                self._logger.debug("aqf: aaaaaaa " + str(kwargs["user_num"]))
                                if kwargs["user_num"] not in self.received_inconf_num_list:
                                    event_uid = sigle_event.get("body", {})["uid"]
                                    event_mid = sigle_event.get("body", {})["mid"]
                                    self._logger.debug("aqf: print kwargs "+ str(kwargs["user_num"]))
                                    self.received_inconf_num_list.append(kwargs["user_num"])
                                    self.conf_mid_map.update({str(event_uid): event_mid})
                                    self._logger.debug("Receive the add_mem notification, update the mid_map in the conf object.")
                                    self._logger.debug("aqf: print self.received_inconf_info " + str(self.received_inconf_num_list))
