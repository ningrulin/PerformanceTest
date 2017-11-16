#!/usr/bin/env python
"""
handle sip register task.

"""
from Commander import Commander,CommanderMap
import time
import threading
from Logger import Logger
from SipMqConstants import SipMqConstants
class SipRegisterMap():
    instance = None
    mutex = threading.Lock()

    def __init__(self):
        self.sip_register_map={}
        pass

    @staticmethod
    def get_instance():
        if (SipRegisterMap.instance == None):
            SipRegisterMap.mutex.acquire()
            if (SipRegisterMap.instance == None):
                Logger.debug('sip register map not init, initing..')
                SipRegisterMap.instance = SipRegisterMap()
            else:
                Logger.debug('sip register map inited')
            SipRegisterMap.mutex.release()
        else:
            Logger.debug('sip register map is init, return..')

        return SipRegisterMap.instance
    def get_sip_register(self,id,protocol='udp'):
        if id in self.sip_register_map.keys():
            Logger.debug('in get_sip_register, sip register found,return ')
            return self.sip_register_map[id]
        else:
            Logger.debug('in get_sip_register, sip register not found,return new instance')
            sip_register=SipRegister(id,protocol)
            self.sip_register_map[id]=sip_register
            return sip_register
    def release_sip_register(self,id):
        if id in self.sip_register_map.keys():
            self.sip_register_map[id].release()
            return True
        else:
            Logger.error('in release_sip_register, sip register not found')
            return False
class SipRegister(object):
    def release(self):
        self.commander.stop_receive()
    def reg_reply_callback(self,msg):
        msgdic = eval(msg.body)
        if msgdic['cmd'] == 'reg' and msgdic['reply_id']==self.id:
            if msgdic['result'] is True:
                # success
                Logger.debug("SIP REGISTER SUCCESS! id is "+self.id)
                self.reg_caller_port=msgdic['caller_port']
                self.reg_callee_port=msgdic['callee_port']
                Logger.debug("in reg_reply_callback, caller_port is "+self.reg_caller_port+", callee_port is "+self.reg_callee_port)
            elif msgdic['result'] is False:
                Logger.error("SIP REGISTER FAILED!! id is "+self.id)
            self.result = msgdic['result']
            self.signal.set()
        else:
            pass
            # other's me
            # Logger.debug( "in reg_reply_callback, receive unrelated msg")
    def __init__(self, id,sip_protocol = 'udp'):
        self.protocol = sip_protocol
        self.reg_caller_port=None
        self.reg_callee_port=None
        self.signal = threading.Event()
        self.id=id
        self.commander=CommanderMap.get_instance().get_commander(id)
        self.result=None
    '''
    Register a set of sip numbers, with same host/password
    '''
    def register_users_with_same_config(self, sip_numbers_caller,sip_numbers_callee, host, password, caps, reg_duration):
        Logger.debug('in register user, commander is '+str(self.commander))
        content = {'cmd': 'reg', 'host':host,'protocol':self.protocol,'caps':caps,'call_duration':reg_duration,'msgid':self.id,'data': {'caller_list':sip_numbers_caller, 'callee_list':sip_numbers_callee,'password':password}}
        # #result = {'cmd': 'reg', 'result': True}
        # t1 = threading.Thread(target=self.commander.start_receive)
        # t1.start()
        time.sleep(1) #need sleep between receive and send or there will be mq error
        self.commander.send_cmd(str(content),self.id,self.reg_reply_callback)
        Logger.debug("in reg user, start to wait reply.")
        self.signal.wait(int(reg_duration)+5)
        # self.signal.wait(30)
        self.signal = threading.Event()
        if self.result is None or self.result is False:
            Logger.error('register failed,id is'+self.id)
            return False,None,None
        else:
            Logger.debug('register success! port is '+str(self.reg_caller_port)+', '+str(self.reg_callee_port))
            self.result=False
            return True,self.reg_caller_port,self.reg_callee_port
    '''
    Register a set of sip numbers, use different host/password.
    You should read domain/password from every user object
    '''
    def register_users(self,user_set):
        pass

if __name__ == '__main__':
    reg = SipRegister('201','192.168.5.201')
    pass