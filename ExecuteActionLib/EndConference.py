# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
from SipOperation.SipCall import *
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
import logging
import time
import traceback
import uuid


class EndConfAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.properly_executed = False
        self.conf_id = None
        self._logger = logging.getLogger(log_name)

    def _execute_action(self):
        try:
            self.user_pool.cache_lock.acquire()
            self.conf_id = self.user_pool.conf_id_list.pop()
            self.conf_obj = self.user_pool.conf_id_obj_dict[self.conf_id]
            self.chairman_phone_num = self.conf_obj.conf_chair_phone_num
            self._logger.info(str(self.chairman_phone_num))
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.chairman_phone_num]
            self.user_pool.cache_lock.release()

            r = self._execute_http_request()

            if r.status_code != 204:
                self.user_pool.cache_lock.acquire()
                self.user_pool.conf_id_list.append(self.conf_id)
                self.user_pool.cache_lock.release()
                self._logger.warning("End meeting failed!")
                return False

            self.user_pool.cache_lock.acquire()
            # 将版本号置为0
            self._logger.debug("in_conf_mem_num_list: "+str(self.conf_obj.in_conf_mem_num_list))
            self._logger.debug("out_conf_mem_num_list: " + str(self.conf_obj.out_conf_mem_num_list))
            for in_conf_mem_num in self.conf_obj.in_conf_mem_num_list:
                self.user_pool.user_phone_num_obj_dict[in_conf_mem_num].conf_mss_v = 0
            for out_conf_mem_num in self.conf_obj.out_conf_mem_num_list:
                self.user_pool.user_phone_num_obj_dict[out_conf_mem_num].conf_mss_v = 0

            # self.user_pool.conf_id_list.remove(self.conf_id)
            conf_mem_phone_num_list = self.conf_obj.mem_num_list
            for conf_mem_phone_num in conf_mem_phone_num_list:
                self.user_pool.conf_mem_phone_num_list.remove(conf_mem_phone_num)
                self.user_pool.conf_all_mem_phone_num_list.remove(conf_mem_phone_num)
            self.user_pool.conf_chair_phone_num_list.remove(self.chairman_phone_num)
            self.user_pool.conf_all_mem_phone_num_list.remove(self.chairman_phone_num)

            del self.user_pool.conf_id_obj_dict[self.conf_id]
            self._logger.info("DELETE " + str(self.conf_id))
            self.user_pool.cache_lock.release()

            UUID = uuid.uuid1()
            sip_end_call = SipCallMap.get_instance().get_sip_call(str(self.conf_obj.group_id)+"_"+str(UUID))
            sip_end_call.end_sipp_conf(str(self.conf_id))
            # sip_end_call.release()
            self._logger.debug("end_sipp")
            self._logger.info("end conference success.")

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

    def _execute_http_request(self):
        self._logger.info("execute end_conference")
        method = 'DELETE'
        url = Constant.CONFS_URL + "/" + self.conf_id
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url,
                                        name="end_conference", catch_response=False, headers=headers)
        return r

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
            if self.conf_id is not None:
                self.user_pool.cache_lock.acquire()
                if self.conf_id in self.user_pool.conf_id_list:
                    self.user_pool.conf_id_list.remove(self.conf_id)

                if self.conf_id in self.user_pool.conf_id_obj_dict:
                    del self.user_pool.conf_id_obj_dict[self.conf_id]

                for in_conf_mem_phone_num in self.conf_obj.in_conf_mem_num_list:
                    if in_conf_mem_phone_num in self.user_pool.in_conf_mem_phone_num_list:
                        self.user_pool.in_conf_mem_phone_num_list.remove(in_conf_mem_phone_num)
                for out_conf_mem_phone_num in self.user_pool.out_conf_mem_num_list:
                    if out_conf_mem_phone_num in self.user_pool.out_conf_mem_phone_num_list:
                        self.user_pool.out_conf_mem_phone_num_list.remove(out_conf_mem_phone_num)

                for conf_mem_phone_num in self.conf_obj.mem_num_list:
                    if conf_mem_phone_num in self.user_pool.conf_mem_phone_num_list:
                        self.user_pool.conf_mem_phone_num_list.remove(conf_mem_phone_num)
                    if conf_mem_phone_num in self.user_pool.conf_all_mem_phone_num_list:
                        self.user_pool.conf_all_mem_phone_num_list.remove(conf_mem_phone_num)
                if self.chairman_phone_num in self.user_pool.conf_chair_phone_num_list:
                    self.user_pool.conf_chair_phone_num_list.remove(self.chairman_phone_num)
                if self.chairman_phone_num in self.user_pool.conf_all_mem_phone_num_list:
                    self.user_pool.conf_all_mem_phone_num_list.remove(self.chairman_phone_num)

                self.user_pool.cache_lock.release()
