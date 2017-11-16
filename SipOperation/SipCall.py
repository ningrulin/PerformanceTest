#!/usr/bin/env python
"""
sip caller. start sip call. use when start a new conf or join a exist conf

"""
from Commander import *
import time,threading

class SipCallMap(object):
    instance = None
    mutex = threading.Lock()

    def __init__(self):
        self.sip_call_map={}
        pass

    @staticmethod
    def get_instance():
        if (SipCallMap.instance == None):
            SipCallMap.mutex.acquire()
            if (SipCallMap.instance == None):
                Logger.debug('sip call map not init, initing..')
                SipCallMap.instance = SipCallMap()
            else:
                Logger.debug('sip call map inited')
            SipCallMap.mutex.release()
        else:
            Logger.debug('sip call map is init, return..')

        return SipCallMap.instance
    def get_sip_call(self,id,protocol='udp'):
        if id in self.sip_call_map.keys():
            Logger.debug('in get_sip_call, sip call found,return ')
            return self.sip_call_map[id]
        else:
            Logger.debug('in get_sip_call, sip call not found,return new instance')
            sip_call=SipCall(id,protocol)
            self.sip_call_map[id]=sip_call
            return sip_call
    def release_sip_call(self,id):
        if id in self.sip_call_map.keys():
            self.sip_call_map[id].release()
            return True
        else:
            Logger.error('in release_sip_call, sip call not found')
            return False

class SipCall(object):

    msgid=None
    def __init__(self,id,protocol='udp'):
        self.protocol=protocol
        self.id=id
        self.commander = CommanderMap.get_instance().get_commander(id)
        self.caller_signal = threading.Event()
        self.callee_signal = threading.Event()
        self.confend_signal = threading.Event()
        self.end_sipp_signal = threading.Event()
        self.make_call_result = None
        self.callee_result = None
        self.end_conf_result = None
        self.end_all_sipp_result=None
        pass
    def release(self):
        self.commander.stop_receive()

    def callback_running_in_sub_thread(self,msg):
        t1 = threading.Thread(target=self.call_reply_callback, args=(msg,))
        t1.start()
    def call_reply_callback(self,msg):
        msgdic = eval(msg.body)
        if msgdic['cmd'] == 'caller' and msgdic['reply_id'] == self.id:
            if msgdic['result'] is True:
                # success
                Logger.debug("SIP MAKE CALL SUCCESS! id is "+self.id)
            else:
                Logger.error("SIP MAKE CONF CALL FAILED!!id is "+self.id)
            self.make_call_result = msgdic['result']
            self.caller_signal.set()
        elif msgdic['cmd'] == 'callee' and msgdic['reply_id'] == self.id:
            if msgdic['result'] is True:
                # success
                Logger.debug('SIP MAKE CALLEE READY SUCCESS! commader is ' + str(self.commander) + ', id is ' + self.id + ' thread id is ' + str(threading.current_thread().ident))
            else:
                Logger.error("SIP MAKE CALLEE READY FAILED!!")
            self.callee_result = msgdic['result']
            self.callee_signal.set()
        elif msgdic['cmd'] == 'endconf'and msgdic['reply_id'] == self.id:
            if msgdic['result'] is True:
                # success
                Logger.debug("END SIPP SUCCESS!")
            else:
                Logger.error("END SIPP FAILED!!")
            self.end_conf_result = msgdic['result']
            self.confend_signal.set()
        elif msgdic['cmd'] == 'end_sipp' and msgdic['reply_id'] == self.id:
            if msgdic['result'] is True:
                # success
                Logger.debug("END ALL SIPP SUCCESS!")
            else:
                Logger.error("END ALL SIPP FAILED!!")
            self.end_all_sipp_result = msgdic['result']
            self.end_sipp_signal.set()
        else:
            #other msg.ignore
            Logger.debug('in call_reply_callback, receive other msg. msg is '+str(msg.body))
            pass
    def make_call(self,sipnumber_list,conf_id,host,password,caller_port,call_duration,caps,timeout,with_media=True):
        '''
        initiate calls with sipnumber_list.
        :param sipnumber_list:
        :param conf_id:
        :param host:
        :param password:
        :param call_duration: the duration of a call.
        :param caps:
        :param timeout: enter fail process if no reply from agent in timeout seconds
        :return:True if success, else False
        '''
        command={'cmd':'caller','host':host,'data':{'userlist':sipnumber_list,'password':password},'confid':conf_id,'caps':caps,'call_duration':call_duration,'caller_port':caller_port,'msgid':self.id,'with_media':with_media}
        #sipp -i 172.31.1.196  -p 5083 -inf /home/mx/sipxml/users_call_same_conference.csv -sf /mnt/aqf/sipxml/uac_confer_no_authentication_av_media.xml 172.31.1.133:6650 -r 10 -rp 1000 -l 50  -aa
        SipCall.msgid=self.commander.send_cmd(str(command),self.id,self.callback_running_in_sub_thread)
        self.caller_signal.wait(timeout)
        self.caller_signal = threading.Event()
        if self.make_call_result is None or self.make_call_result is False:
            Logger.error('caller failed, commader is '+str(self.commander))
            self.make_call_result=False
            return False
        else:
            Logger.debug( 'caller success!')
            self.make_call_result=False
            return True
        pass
    def get_callee_ready(self,confid,callee_numbers,host,caps,callee_port,call_duration,timeout):
        '''
        get sip callee ready
        :param confid: confid
        :param callee_numbers: numbers of callee
        :param host: sip server,ip:port
        :param caps: caps
        :param callee_port:
        :param call_duration: how long the test will going
        :param timeout: enter fail process if no reply from agent in timeout seconds
        :return:True if success, else False
        '''
        command={'cmd':'callee','host':host,'caps':caps,'call_duration':call_duration,"callee_number":callee_numbers,'confid':confid,'callee_port':callee_port,'msgid':self.id}
        SipCall.msgid=self.commander.send_cmd(str(command),self.id,self.callback_running_in_sub_thread)
        self.callee_signal.wait(timeout)
        self.callee_signal=threading.Event()
        if self.callee_result is None or self.callee_result is False:
            Logger.error('make callee ready failed, commader is '+str(self.commander)+'id is '+self.id+' thread id is ' +str(threading.current_thread().ident))
            self.callee_result = False
            return False
        else:
            Logger.debug('make callee ready success! commader is '+str(self.commander)+'id is '+self.id+' thread id is ' +str(threading.current_thread().ident))
            self.callee_result = False
            return True
        pass
    def end_sipp_conf(self, confid, timeout=5):
        '''
        end a sipp process
        :param confid:
        :param timeout: enter fail process if no reply from agent in timeout seconds
        :return: True if success, else False
        '''
        command={'cmd':'endconf','confid':confid,'msgid':self.id}
        SipCall.msgid=self.commander.send_cmd(str(command),self.id,self.callback_running_in_sub_thread)
        self.confend_signal.wait(timeout)
        self.confend_signal = threading.Event()
        if self.end_conf_result is None or self.end_conf_result is False:
            Logger.error('end sipp failed, commader is '+str(self.commander))
            self.end_conf_result=False
            return False
        else:
            Logger.debug('end sipp success!')
            self.end_conf_result=False
            return True
        pass
    def end_all_sipp(self,timeout=5):
        '''
        end all sipp process
        :param timeout: enter fail process if no reply from agent in timeout seconds
        :return: True if success, else False
        '''
        command={'cmd':'end_sipp','msgid':self.id}
        SipCall.msgid=self.commander.send_cmd(str(command),self.id,self.callback_running_in_sub_thread)
        self.end_sipp_signal.wait(timeout)
        self.end_sipp_signal = threading.Event()
        if self.end_all_sipp_result is None or self.end_all_sipp_result is False:
            Logger.error('end all sipp failed, commader is '+str(self.commander))
            self.end_all_sipp_result=False
            return False
        else:
            Logger.debug('end all sipp success!')
            self.end_all_sipp_result=False
            return True
        pass
