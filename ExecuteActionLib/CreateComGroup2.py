# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.GroupInfo import GroupInfo


class CreateComGroupAction2(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self.properly_executed = False
        self._logger = logging.getLogger(log_name)

    def _execute_action(self):
        try:
            self.user_pool.cache_lock.acquire()
            self.executor_phone_num = self.user_pool.online_user_phone_num_list.pop()
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            # group_member_num = 0
            this_group_mem_phone_num_list = []
            self.this_group_mem_userID_list = [{'id': str(self.executor_obj.user_info_dict["userID"]), 'remark': 'owner'}]
            if "group_number" in self.case_info_dict:
                group_member_num = self.case_info_dict["group_number"]
                for i in range(group_member_num - 1):
                    group_member_num = self.user_pool.online_user_phone_num_list.pop()
                    this_group_mem_phone_num_list.append(group_member_num)
                    group_mem_obj = self.user_pool.user_phone_num_obj_dict[group_member_num]
                    self.this_group_mem_userID_list.append(
                            {'id': str(group_mem_obj.user_info_dict["userID"]), 'remark': 'member'})
            self.user_pool.cache_lock.release()

            http_response = self._execute_http_request()

            if http_response.status_code == 200:
                groupid = json.loads(http_response.text)["groupid"]
                self.user_pool.cache_lock.acquire()
                group_obj = GroupInfo(groupid, self.executor_phone_num, None, this_group_mem_phone_num_list)
                self.user_pool.group_mem_phone_num_list.extend(this_group_mem_phone_num_list)
                self.user_pool.group_id_list.append(groupid)
                self._logger.debug("groupid:"+str(groupid))
                self.user_pool.group_id_obj_dict.update({groupid: group_obj})

                for phone_num in this_group_mem_phone_num_list:
                    self.user_pool.user_phone_num_obj_dict[phone_num].attach_group_id = groupid

                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.online_user_phone_num_list.extendleft(this_group_mem_phone_num_list)

                self.user_pool.cache_lock.release()
                self._logger.info("CreateComGroup Success!")
                self.properly_executed = True
                return True
            else:
                self._logger.info("CreateComGroup Fail!")
                # False，设置终止整个进程信号
                return False
        except:
            self._logger.error("CreateComGroup Return False because of except.")
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
        self._logger.info("execute create_common_group")
        url = Constant.CREATE_GROUP_URL
        method = 'POST'
        data = {'name': 'Python',
                'invite': 'free',
                'members': self.this_group_mem_userID_list
                }
        headers = {'authorization': self.executor_obj.user_info_dict["basicToken"],
                   "Content-Type": "application/json; charset=utf-8"}
        execute_http_client = HttpClient(url)
        r = execute_http_client.request(method=method, url=url, name="/group/create/group",
                                        catch_response=False, headers=headers,
                                        data=json.dumps(data))
        """返回执行成功，并携带groupid"""
        self._logger.info("=======================" + str(r.text))
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
            # False，设置终止整个测试信号
        else:
            self.user_pool.cache_lock.acquire()
            if self.executor_phone_num not in self.user_pool.online_user_phone_num_list:
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
            self.user_pool.cache_lock.release()
