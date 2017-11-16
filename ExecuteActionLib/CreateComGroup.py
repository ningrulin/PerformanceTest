# coding:utf-8
from ExecuteActionLib.ExecuteAction import ExecuteAction
import logging
import time
import json
import traceback
from public.ConstantSet import Constant
from public.HttpClient import HttpClient
from public.GroupInfo import GroupInfo


class CreateComGroupAction(ExecuteAction):
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        super(ExecuteAction, self).__init__()
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self.executor_obj = None
        self.executor_phone_num = None
        self._logger = logging.getLogger(log_name)

    def _execute_action(self):
        try:
            # 出现异常或者失败的情况是否终止当前任务的标志
            abnormal_interrupt = True
            if "abnormal_interrupt" in self.case_info_dict:
                abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]

            self.user_pool.cache_lock.acquire()
            self.executor_phone_num = self.user_pool.online_user_phone_num_list.pop()
            self.executor_obj = self.user_pool.user_phone_num_obj_dict[self.executor_phone_num]
            self.user_pool.cache_lock.release()
            sleep_after = 0
            if "sleep_after" in self.case_info_dict:
                sleep_after = self.case_info_dict["sleep_after"]
            # 获取userset中的groupID
            http_response = self._execute_http_request()

            if http_response.status_code == 200:
                groupid = json.loads(http_response.text)["groupid"]
                this_group_mem_phone_num_list = []
                self.user_pool.cache_lock.acquire()
                # group_member_num = 0
                if "group_number" in self.case_info_dict:
                    group_member_num = self.case_info_dict["group_number"]
                    for i in range(group_member_num - 1):
                        this_group_mem_phone_num_list.append(self.user_pool.online_user_phone_num_list.pop())

                group_obj = GroupInfo(groupid, self.executor_phone_num, None, this_group_mem_phone_num_list)
                self.user_pool.group_mem_phone_num_list.extend(this_group_mem_phone_num_list)
                self.user_pool.group_id_list.append(groupid)
                self._logger.debug("groupid:"+str(groupid))
                self.user_pool.group_id_obj_dict.update({groupid: group_obj})

                for phone_num in this_group_mem_phone_num_list:
                    self.user_pool.user_phone_num_obj_dict[phone_num].attach_group_id = groupid

                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                for this_group_member_num in this_group_mem_phone_num_list:
                    self.user_pool.online_user_phone_num_list.appendleft(this_group_member_num)

                self.user_pool.cache_lock.release()
                self._logger.info("CreateCommonGroup Success!")
                self._logger.info("Sleep %s s after action!" % sleep_after)
                time.sleep(sleep_after)
                return True
            else:
                if self.user_pool.cache_lock.locked():
                    self.user_pool.cache_lock.release()
                self.user_pool.online_user_phone_num_list.appendleft(self.executor_phone_num)
                self.user_pool.cache_lock.release()
                self._logger.info("CreateCommonGroup Fail!")
                # False，设置终止整个进程信号
                if abnormal_interrupt:
                    self.p_stop_signal.set()
                    # False，设置终止整个进程信号
                time.sleep(sleep_after)
                return False
        except:
            if self.user_pool.cache_lock.locked():
                self.user_pool.cache_lock.release()
            self._logger.warning("CreateComGroup Return False because of except.")
            self._logger.warning(traceback.format_exc())
            abnormal_interrupt = True
            if "abnormal_interrupt" in self.case_info_dict:
                abnormal_interrupt = self.case_info_dict["abnormal_interrupt"]
            if abnormal_interrupt:
                self.p_stop_signal.set()
                # False，设置终止整个进程信号
            return False

    def _execute_http_request(self):
        self._logger.info("execute create_common_group")
        url = Constant.CREATE_GROUP_URL
        method = 'POST'
        data = {'name': 'Python',
                'invite': 'free',
                'members': [{'id': str(self.executor_obj.user_info_dict["userID"]), 'remark': 'test'}]
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
