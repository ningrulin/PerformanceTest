# -*- coding: utf-8 -*-
"""
@author:jiazhu
@time: 17/02/21 10:56
"""
from ExecuteActionLib import *
import logging


class ExecuteCase(object):
    """
    这段代码 用来执行一个具体的yaml文件中的case
    """
    def __init__(self, case_info_dict, user_pool, p_stop_signal, log_name="MXTest"):
        self.case_info_dict = case_info_dict
        self.user_pool = user_pool
        self.p_stop_signal = p_stop_signal
        self._logger = logging.getLogger(log_name)
        self.switch_case_dict = {
            "AddFriend": AddFriendAction,
            "AddMem2ConfNOSIpp": AddMem2ConfNOSIppAction,
            "ApplyFloor": ApplyFloorAction,
            "CreateComGroup": CreateComGroupAction,
            "CreateComGroup2": CreateComGroupAction2,
            "CreateConference": CreateConfAction,
            "CreateConference2": CreateConf2Action,
            "CreateConference6": CreateConf6Action,
            "CreateConference8": CreateConf8Action,
            "CreateConference9": CreateConf9Action,
            "EnableGroupShare": EnableGroupShareAction,
            "EndConference": EndConfAction,
            "EnablePPTShare": EnablePPTShareAction,
            #"GetContactList": GetContactListAction,
            "GetErinfo": GetErinfoAction,
            "GetGroupList": GetGroupListAction,
            "GetUserInfo": GetUserInfoAction,
            "GetConferenceInfo" : GetConferenceInfoAction,
            "GetSinfo": GetSinfoAction,
            "Modifyinfo": ModifyinfoAction,
            "AddMember": AddMemberAction,
            "KickMember": KickMemberAction,
            "JoinConference": JoinConfAction,
            "JoinConference2": JoinConf2Action,
            "JoinGroupByID": JoinGroupByIDAction,
            "Login": LoginAction,
            "LoginNoWS": LoginNoWSAction,
            "Logout": LogoutAction,
            "LogoutNoWS": LogoutNoWSAction,
            "V3GetDeviceInfo": V3GetDeviceInfoAction,
            "V3GetUserInfo": V3GetUserInfoAction,
            "V3Modifyinfo": V3ModifyinfoAction,
            "V3SearchContactInfo": V3SearchContactInfoAction,
            "ModUserInfo": ModUserInfoAction,
            "Mss": MssAction,
            "Mss2": Mss2Action,
            "MuteMember": MuteMemberAction,
            "UpdateStatus": UpdateStatusAction,
            "QueryConf": QueryConfAction,
            "ModifyConfState": ModifyConfAction
        }

    def execute_case(self):
        """
        测试用例解释器
        :param case_info_dict 测试用例具体dict格式信息
        :return:
        """
        self._logger.debug("execute_case:  "+str(self.case_info_dict))
        if isinstance(self.case_info_dict, dict):
            range_num = 1
            if "range" in self.case_info_dict:
                range_num = self.case_info_dict["range"]
            for i in xrange(0, range_num):
                if 'action' in self.case_info_dict:
                    if self.case_info_dict["action"] in self.switch_case_dict:
                        action_class = self.switch_case_dict[self.case_info_dict["action"]]
                        exe_obj = action_class(self.case_info_dict, self.user_pool, self.p_stop_signal)
                        exe_obj.run()
                    else:
                        self._logger.warning("Action 不存在！！！！！！！！")