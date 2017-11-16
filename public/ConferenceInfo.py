# coding:utf-8


class ConferenceInfo(object):
    def __init__(self, group_id, conf_id, conf_chair, conf_mem_num_list,
                 out_conf_mem_num_list, in_conf_mem_num_list, conf_mid_map):
        self.group_id = group_id
        self.conf_id = conf_id
        self.conf_chair_phone_num = conf_chair
        self.mem_num_list = []
        self.mem_num_list.extend(conf_mem_num_list)
        self.in_conf_mem_num_list = []
        self.in_conf_mem_num_list.extend(in_conf_mem_num_list)
        self.out_conf_mem_num_list = []
        self.out_conf_mem_num_list.extend(out_conf_mem_num_list)

        """{str(notify_userID): notify_conferMemberID}"""
        self.mid_map = conf_mid_map
        self.mute_mid_list = []
        self.mute_mid_list.extend(conf_mem_num_list)
        self.unmute_mid_list = []
