# coding:utf-8


class GroupInfo(object):
    def __init__(self, _group_id=None, group_owner_phone_num=None, _share_id=None, group_mem_phone_num_list=[]):
        self.group_id = _group_id
        self.group_owner_phone_num = group_owner_phone_num
        self.share_id = _share_id
        self.group_mem_phone_num_list = group_mem_phone_num_list
        self.is_in_conf = False
        self.conf_id = None
        self.in_group_mem_list = []
        self.out_group_mem_list = []
