#!/usr/bin/env python
"""
sip register agent. running with sipp

"""
from Agent import Agent
import subprocess,time
from SipUtil import SipUtil
import csv,os,re,commands
import traceback,threading
from Logger import Logger
from SipMqConstants import SipMqConstants
from socket import *
import Utils as Utils
from Logger import Logger
#port pool used for sipp
sip_port_list = []
def init_sip_port_list(list2):
    for i in range(SipRegAgent.MIN_SIP_PORT,SipRegAgent.MAX_SIP_PORT):
        list2.append(i)
media_port_list = []
def init_media_port_list(list2):
    for i in range(SipRegAgent.MIN_MEDIA_PORT,SipRegAgent.MAX_MEDIA_PORT):
        if i%3 ==0:
            list2.append(i)
confid_pid_map_lock=threading.Lock()
sip_port_list_lock=threading.Lock()
media_port_list_lock=threading.Lock()
plock=threading.Lock()
def add_port_to_sip_port_list(port):
    sip_port_list_lock.acquire()
    sip_port_list.append(port)
    sip_port_list_lock.release()
def pop_sip_port_list(i):
    sip_port_list_lock.acquire()
    port=sip_port_list.pop(i)
    sip_port_list_lock.release()
    return port
def add_port_to_media_port_list(port):
    media_port_list_lock.acquire()
    media_port_list.append(port)
    media_port_list_lock.release()
def pop_media_port_list(i):
    media_port_list_lock.acquire()
    port=media_port_list.pop(i)
    media_port_list_lock.release()
    return port
def write_reg_csv(userlist,password,file_appendix_name):
    heardname = 'SEQUENTIAL'
    file_name = SipMqConstants.SIP_XML_PATH+'users_reg_'+file_appendix_name+'.csv'
    with open(file_name, 'w+') as f:
        f.write(heardname + '\n')
        for i in range(len(userlist)):
            cc = userlist[i] + ";[authentication username=" + userlist[i] + " password=" + password + "]\n"
            f.write(cc)
        f.close()
    return file_name
def write_caller_csv(userlist,password,confid,file_appendix_name):
    heardname = 'SEQUENTIAL'
    filename = SipMqConstants.SIP_XML_PATH+'users_caller_'+file_appendix_name+'.csv'
    with open(filename, 'w+') as f:
        f.write(heardname + '\n')
        for i in range(len(userlist)):
            cc = userlist[i] + ";" + confid + ";[authentication username=" + userlist[i] + " password="+password+"];"+userlist[i][:-2]+"\n"
            f.write(cc)
        f.close()
    return filename
def readcsv(cmdinfo,pid,port):
    if cmdinfo == 'reg':
        cc = "uac_reg"
    elif cmdinfo == 'callee':
        cc = "uac_callee"
    elif cmdinfo == 'caller':
        cc = "uac_caller"
    filename = SipMqConstants.SIP_XML_PATH + cc + "_" + str(pid) + "_.csv"
    with open(filename, 'rb') as csvfile:
        reader = csv.reader(csvfile)
        for i, rows in enumerate(reader):
            if i == 0:
                row1 = rows
        row2 = rows
    dic = {}
    d = len(row1)
    a = row1[0]
    tup1 = a.split(';')
    tup2 = row2[0].split(';')
    for j in range(len(tup2)):
        dic[tup1[j]] = tup2[j]
    log= 'result: '+'analyzing file name is '+filename+'. port is '+str(port)+' cmd is '+str(cmdinfo)+', success count is '+str(dic['SuccessfulCall(C)'])+', fail count is '+str(dic['FailedCall(C)'])
    Logger.getLogger().debug(log)
    return dic['SuccessfulCall(C)'], dic['FailedCall(C)']


def get_sipp_pid_list():
    (status, output) = commands.getstatusoutput('ps -ef|grep sipp')
    #print output
    outinfo=output.split('root')
    pid_list=[]
    for i in range(len(outinfo)):
        p=re.compile('.*sipp -i.*')
        sipp_line=p.search(outinfo[i])
        if sipp_line:
            p2 = re.compile('(\t|\s){1,10}\d{1,5}(\t|\s){1,10}')
            pid=p2.search(sipp_line.group())
            if pid:
                pid_list.append(pid.group().strip())
    return pid_list
def sip_reg_users(host,userlist,password,caps,side,id,duration):
    # generate cmd
    # reg_port = get_available_sip_port()
    # media_port = get_available_media_port()
    # reg_file = write_reg_csv(userlist, password, side+'_' + str(reg_port))
    # cmd = "sipp  -i " + SipUtil.get_local_ip() + " -p " + str(reg_port) + " -m "+str(len(userlist))+" -mp " + str(
    #     media_port) + " -inf " + reg_file + " -sf "+SipMqConstants.SIP_XML_PATH+"uac_reg.xml " + host + " -r " + str(caps) + " -rp 1000 -aa -trace_stat -fd 4 -trace_err"
    #
    # Logger.debug('in sip_reg_users, '+side+" cmd is : " + cmd + ';')
    #
    # # execute reg for caller.
    # p_reg = subprocess.Popen(cmd.split(), shell=False)
    # Logger.debug(
    #     'for id ' + id + ',caller port ' + str(reg_port) + 'pid is ' + str(p_reg.pid))
    # if reg_port is None:
    #     Logger.error('reg failed. port not found')
    # Logger.debug(
    #     'for id ' + id + ',port ' + str(reg_port) + 'pid is ' + str(p_reg.pid))
    # time.sleep(int(duration))
    # # os.system("kill 9 " + str(p_reg.pid))
    # p_reg.communicate()

    ok = False
    max_test = 3
    test = 0
    start = time.time()
    p_caller_reg=None
    caller_reg_port=None
    caller_media_port=None
    caller_reg_file=None
    # to ensure sipp is successfully running ,check until the port assigned to sipp is occupied by the right process.
    while not ok and test < max_test:
        Logger.debug('in caller ' + id + ' trying ' + str(test) + ' times')
        test += 1
        plock.acquire()
        caller_reg_port = get_available_sip_port()
        caller_media_port = get_available_media_port()
        caller_reg_file = write_reg_csv(userlist, password,
                                        'caller_' + str(caller_reg_port))
        caller_cmd = "sipp  -i " + SipUtil.get_local_ip() + " -p " + str(caller_reg_port) + " -m " + str(
            len(userlist)) + " -mp " + str(
            caller_media_port) + " -inf " + caller_reg_file + " -sf " + SipMqConstants.SIP_XML_PATH + "uac_reg.xml " + \
                     host + " -r " + str(caps) + " -rp 1000 -aa -trace_stat -fd 4 -trace_err"
        Logger.debug("caller cmd is : " + caller_cmd)
        p_caller_reg = subprocess.Popen(caller_cmd.split(), shell=False)
        if is_process_alive(p_caller_reg) or os.path.exists(
                                        SipMqConstants.SIP_XML_PATH + "uac_reg_" + str(p_caller_reg.pid) + "_.csv"):
            ok = True
        else:  # if process dead, return ports
            Logger.debug("aqf: add to caller_reg_media_port!")
            add_port_to_sip_port_list(caller_reg_port)
            add_port_to_media_port_list(caller_media_port)
            Logger.debug("aqf: add to caller_reg_media_port is ok!")
        plock.release()
    end = time.time()
    Logger.debug('totol open caller process cost time ' + str(end - start))
    p_caller_reg.communicate()

    suc_reg, fail_reg = readcsv('reg', p_caller_reg.pid, caller_reg_port)
    media_port_list.append(caller_media_port)
    return suc_reg,fail_reg,caller_reg_port,str(p_caller_reg.pid),caller_reg_file
def sip_reg_handler(msg):
    try:#print traceback, this is running in a sub thread
        msgdic=eval(msg.body)
        reply_msg='default'
        # start = time.time()
        # caller_reg_port = get_available_sip_port()
        # callee_reg_port = get_available_sip_port()
        # caller_media_port = get_available_media_port()
        # callee_media_port = get_available_media_port()
        # end = time.time()
        # Logger.debug('arrange port cost time: ' + str(end - start))
        Logger.debug('received cmd, msgdic is '+str(msgdic))
        if msgdic['cmd'] == 'reg':
            #TODO: this is nasty, need refactor. if there's only caller, just do caller.
            if len(msgdic['data']['callee_list'])==0:
                suc_caller,fail_caller,port,pid,regfile=sip_reg_users(host=msgdic['host'],userlist=msgdic['data']['caller_list'],password=msgdic['data']['password'],caps=msgdic['caps'],side='caller',id=msgdic['msgid'],duration=msgdic['call_duration'])
                if int(suc_caller) == len(msgdic['data']['caller_list']):
                    #os.remove(SipMqConstants.SIP_XML_PATH + "uac_reg_" + pid + "_.csv")
                    #os.remove(regfile)
                    reply_msg = {'cmd': 'reg', 'result': True, 'reply_id': msgdic['msgid'],'caller_port':str(port),'callee_port':'65536'}
                else:
                    reply_msg = {'cmd': 'reg', 'result': False, 'reply_id':msgdic['msgid']}
            else: #cmd with caller and callee
                #generate cmd
                caller_list=msgdic['data']['caller_list']
                callee_list=msgdic['data']['callee_list']


                ok=False
                max_test=3
                test=0
                start = time.time()
                caller_reg_file=None
                callee_reg_file=None
                #to ensure sipp is successfully running ,check until the port assigned to sipp is occupied by the right process.
                while not ok and test<max_test:
                    Logger.debug('in caller ' + msgdic['msgid'] + ' trying ' + str(test) + ' times')
                    test+=1
                    plock.acquire()
                    caller_reg_port = get_available_sip_port()
                    caller_media_port = get_available_media_port()
                    caller_reg_file = write_reg_csv(caller_list, msgdic['data']['password'],
                                                    'caller_' + str(caller_reg_port))
                    caller_cmd="sipp  -i "+SipUtil.get_local_ip()+" -p "+ str(caller_reg_port)+" -m "+str(len(caller_list))+" -mp "+str(caller_media_port)+" -inf "+caller_reg_file+" -sf "+SipMqConstants.SIP_XML_PATH+"uac_reg.xml "+msgdic['host']+" -r "+str(msgdic['caps'])+" -rp 1000 -aa -trace_stat -fd 4 -trace_err"
                    Logger.debug("caller cmd is : " + caller_cmd)
                    p_caller_reg = subprocess.Popen(caller_cmd.split(),shell=False)
                    if is_process_alive(p_caller_reg.pid) or os.path.exists(SipMqConstants.SIP_XML_PATH + "uac_reg_" + str(p_caller_reg.pid) + "_.csv"):
                        ok=True
                    else: #if process dead, return ports
                        Logger.debug("aqfa: add to caller_reg_media_port is ok!")
                        add_port_to_sip_port_list(caller_reg_port)
                        add_port_to_media_port_list(caller_media_port)
                    plock.release()
                end = time.time()
                Logger.debug('totol open caller process cost time '+str(end-start))

                ok = False
                test = 0
                start = time.time()
                # to ensure sipp is successfully running ,check until the port assigned to sipp is occupied by the right process.
                while not ok and test < max_test:
                    Logger.debug('in callee '+msgdic['msgid']+' trying '+str(test)+' times')
                    test += 1
                    plock.acquire()
                    callee_reg_port = get_available_sip_port()
                    callee_media_port = get_available_media_port()
                    callee_reg_file = write_reg_csv(callee_list, msgdic['data']['password'],
                                                    'callee_' + str(callee_reg_port))
                    callee_cmd = "sipp  -i " + SipUtil.get_local_ip() + " -p " + str(callee_reg_port) + " -m " + str(
                        len(callee_list)) + " -mp " + str(
                        callee_media_port) + " -inf " + callee_reg_file + " -sf " + SipMqConstants.SIP_XML_PATH + "uac_reg.xml " + \
                                 msgdic['host'] + " -r " + str(
                        msgdic['caps']) + " -rp 1000 -aa -trace_stat -fd 4 -trace_err"
                    Logger.debug("callee cmd is : " + callee_cmd)
                    p_callee_reg = subprocess.Popen(callee_cmd.split(), shell=False)
                    if is_process_alive(p_callee_reg.pid) or os.path.exists(SipMqConstants.SIP_XML_PATH + "uac_reg_" + str(p_callee_reg.pid) + "_.csv"):
                        ok = True
                    else:  # if process dead, return ports
                        Logger.debug("aqfb: add to caller_reg_media_port is ok!")
                        add_port_to_sip_port_list(callee_reg_port)
                        add_port_to_media_port_list(callee_media_port)
                    plock.release()
                end = time.time()
                Logger.debug('totol open callee process cost time ' + str(end - start))


                Logger.debug('for id '+msgdic['msgid']+',caller port '+str(caller_reg_port)+'pid is '+str(p_caller_reg.pid))
                if caller_reg_port is None:
                    Logger.error('reg caller failed. port not found')
                Logger.debug('for id ' + msgdic['msgid'] + ',callee port ' + str(callee_reg_port) + 'pid is ' + str(p_callee_reg.pid))
                if callee_reg_port is None:
                    Logger.error('reg callee failed. port not found')
                #so many log to debug the problem 'hang on p_caller_reg.communicate()'
                # time.sleep(int(msgdic['call_duration']))
                # Logger.debug("in reg ,after sleep.")
                p_caller_reg.communicate()
                p_callee_reg.communicate()
                Logger.debug("in reg, after communicate")
                suc_caller, fail_caller = readcsv(msgdic['cmd'], p_caller_reg.pid,caller_reg_port)
                suc_callee, fail_callee = readcsv(msgdic['cmd'], p_callee_reg.pid,callee_reg_port)
                time.sleep(1)# maybe sipp is not done yet, so return port a little later
                media_port_list.append(caller_media_port)
                media_port_list.append(callee_media_port)
                # if int(fail_caller) < 3 and int(suc_caller) > len(caller_list) and int(fail_callee) < 3 and int(suc_callee) > len(callee_list):
                if int(suc_caller) == len(caller_list) and int(suc_callee) == len(callee_list):
                    #os.remove(SipMqConstants.SIP_XML_PATH + "uac_reg_" + str(p_caller_reg.pid) + "_.csv")
                    #os.remove(SipMqConstants.SIP_XML_PATH + "uac_reg_" + str(p_callee_reg.pid) + "_.csv")
                    #os.remove(caller_reg_file)
                    #os.remove(callee_reg_file)
                    reply_msg = {'cmd': 'reg', 'result': True, 'reply_id': msgdic['msgid'],'caller_port':str(caller_reg_port),'callee_port':str(callee_reg_port)}
                else:
                    reply_msg = {'cmd': 'reg', 'result': False, 'reply_id':msgdic['msgid']}
        #cmd is to make callee ready
        elif msgdic['cmd'] == 'callee':
            # replace audio pcap
            apcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/') + SipMqConstants.SIP_AUDIO_PCAP_FILE.replace(r'/',
                                                                                                                  r'\/')
            vpcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/') + SipMqConstants.SIP_VIDEO_PCAP_FILE.replace(r'/',
                                                                                                                  r'\/')
            replace_pcap = '''sed -ri 's/play_pcap_audio=".*"/play_pcap_audio="''' + apcap + '''"/g' ''' + SipMqConstants.SIP_XML_PATH + '''/uac_callee.xml'''
            Logger.debug('in callee, replace pcap out is ' + replace_pcap)
            out = commands.getoutput(replace_pcap)
            Logger.debug('in callee, replace pcap out is ' + out)
            # replace_video pcap
            replace_pcap = '''sed -ri 's/play_pcap_video=".*"/play_pcap_video="''' + vpcap + '''"/g' ''' + SipMqConstants.SIP_XML_PATH + '''/uac_callee.xml'''
            out = commands.getoutput(replace_pcap)
            Logger.debug('in callee, replace pcap out is ' + out)
            max_test = 3
            ok = False
            test = 0
            start = time.time()
            # to ensure sipp is successfully running ,check until the port assigned to sipp is occupied by the right process.
            while not ok and test < max_test:
                Logger.debug('in callee call ' + msgdic['msgid'] + ' trying ' + str(test) + ' times')
                test += 1
                plock.acquire()
                callee_call_media_port = get_available_media_port()
                cc = "sipp  -i " + SipUtil.get_local_ip() + " -p " + msgdic['callee_port'] + " -mp "+str(callee_call_media_port)+" -sf " + SipMqConstants.SIP_XML_PATH + "uac_callee.xml " + msgdic['host'] + " -r " + str(msgdic['caps']) + " -rp 1000 -l " + str(msgdic['callee_number']) + " -trace_err"
                Logger.getLogger().debug("in callee call , cmd is : " + cc)
                p = subprocess.Popen(cc.split(), shell=False)
                if is_process_alive(p.pid) or os.path.exists(SipMqConstants.SIP_XML_PATH + "uac_callee_" + str(
                        p.pid) + "_.csv"):
                    ok = True
                else:  # if process dead, return ports
                    Logger.debug("aqfc: add to caller_reg_media_port is ok!")
                    add_port_to_media_port_list(callee_call_media_port)
                plock.release()
            end = time.time()
            Logger.debug('totol open callee call process cost time ' + str(end - start))
            SipRegAgent.confid_sippid_map.append({'confid': msgdic['confid'], 'sippid': p.pid})
            reply_msg = {'cmd': 'callee', 'result': True, 'reply_id': msgdic['msgid']}










            # cc="sipp  -i "+SipUtil.get_local_ip()+" -p "+msgdic['callee_port']+" -sf "+SipMqConstants.SIP_XML_PATH+"uac_callee.xml "+msgdic['host']+" -r "+str(msgdic['caps'])+" -rp 1000 -l "+str(msgdic['callee_number'])+" -trace_err"
            # Logger.getLogger().debug("in callee, cmd is : " + cc)
            #
            # # replace audio pcap
            # apcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/')+SipMqConstants.SIP_AUDIO_PCAP_FILE.replace(r'/', r'\/')
            # vpcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/') + SipMqConstants.SIP_VIDEO_PCAP_FILE.replace(r'/',r'\/')
            # replace_pcap = '''sed -ri 's/play_pcap_audio=".*"/play_pcap_audio="''' + apcap + '''"/g' '''+SipMqConstants.SIP_XML_PATH+'''/uac_callee.xml'''
            # Logger.debug('in callee, replace pcap out is ' + replace_pcap)
            # out = commands.getoutput(replace_pcap)
            # Logger.debug('in callee, replace pcap out is ' + out)
            # # replace_video pcap
            # replace_pcap = '''sed -ri 's/play_pcap_video=".*"/play_pcap_video="''' + vpcap  + '''"/g' '''+SipMqConstants.SIP_XML_PATH+'''/uac_callee.xml'''
            # out = commands.getoutput(replace_pcap)
            # Logger.debug('in callee, replace pcap out is ' + out)
            # p = subprocess.Popen(cc.split(),shell=False)
            # SipRegAgent.confid_sippid_map.append({'confid': msgdic['confid'], 'sippid': p.pid})
            # reply_msg = {'cmd': 'callee', 'result': True, 'reply_id': msgdic['msgid']}
        #cmd is to make call
        elif msgdic['cmd'] == 'caller':
            xml_file = SipMqConstants.SIP_XML_PATH + 'uac_caller.xml'
            if msgdic['with_media'] == False:
                xml_file = SipMqConstants.SIP_XML_PATH + 'uac_caller_nomedia.xml'
            write_caller_csv(msgdic['data']['userlist'], msgdic['data']['password'], msgdic['confid'],
                             msgdic['caller_port'])
            # replace call duration
            replace_call_duration = '''sed -ri 's/pause milliseconds="[0-9]{1,5}"/pause milliseconds="''' + str(
                msgdic['call_duration']) + '''"/g' ''' + xml_file
            out = commands.getoutput(replace_call_duration)
            Logger.debug('in caller, replace duration out is ' + out)
            # replace audio pcap
            apcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/') + SipMqConstants.SIP_AUDIO_PCAP_FILE.replace(r'/',
                                                                                                                  r'\/')
            vpcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/') + SipMqConstants.SIP_VIDEO_PCAP_FILE.replace(r'/',
                                                                                                                  r'\/')
            replace_pcap = '''sed -ri 's/play_pcap_audio=".*"/play_pcap_audio="''' + apcap + '''"/g' ''' + SipMqConstants.SIP_XML_PATH + '''/uac_caller.xml'''
            out = commands.getoutput(replace_pcap)
            Logger.debug('in caller, replace pcap out is ' + out)
            # replace_video pcap
            replace_pcap = '''sed -ri 's/play_pcap_video=".*"/play_pcap_video="''' + vpcap + '''"/g' ''' + SipMqConstants.SIP_XML_PATH + '''/uac_caller.xml'''
            out = commands.getoutput(replace_pcap)
            Logger.debug('in caller, replace pcap out is ' + out)

            max_test = 3
            ok = False
            test = 0
            start = time.time()
            # to ensure sipp is successfully running ,check until the port assigned to sipp is occupied by the right process.
            while not ok and test < max_test:
                Logger.debug('in caller call ' + msgdic['msgid'] + ' trying ' + str(test) + ' times')
                test += 1
                plock.acquire()
                caller_call_media_port = get_available_media_port()
                cc = "sipp  -i " + SipUtil.get_local_ip() + " -p " + msgdic[
                    'caller_port'] + " -mp "+str(caller_call_media_port)+" -inf " + SipMqConstants.SIP_XML_PATH + "users_caller_" + msgdic[
                         'caller_port'] + ".csv -sf " + xml_file + " " + msgdic['host'] + " -m " + str(
                    len(msgdic['data']['userlist'])) + " -r " + str(msgdic['caps']) + " -rp 1000 -l " + str(
                    len(msgdic['data']['userlist'])) + " -trace_err"

                Logger.getLogger().debug("in caller call, cmd is : " + cc)
                p = subprocess.Popen(cc.split(), shell=False)
                if is_process_alive(p.pid) or os.path.exists(SipMqConstants.SIP_XML_PATH + "uac_caller_" + str(
                        p.pid) + "_.csv"):
                    ok = True
                else:  # if process dead, return ports
                    Logger.debug("aqfd: add to caller_reg_media_port is ok!")
                    add_port_to_media_port_list(caller_call_media_port)
                plock.release()
            end = time.time()
            Logger.debug('totol open caller call process cost time ' + str(end - start))

            SipRegAgent.confid_sippid_map.append({'confid': msgdic['confid'], 'sippid': p.pid})
            reply_msg = {'cmd': 'caller', 'result': True, 'reply_id': msgdic['msgid']}






            # xml_file=SipMqConstants.SIP_XML_PATH+'uac_caller.xml'
            # if msgdic['with_media'] == False:
            #     xml_file=SipMqConstants.SIP_XML_PATH+'uac_caller_nomedia.xml'
            # write_caller_csv(msgdic['data']['userlist'],msgdic['data']['password'],msgdic['confid'],msgdic['caller_port'])
            # #replace call duration
            # replace_call_duration='''sed -ri 's/pause milliseconds="[0-9]{1,5}"/pause milliseconds="'''+str(msgdic['call_duration'])+'''"/g' '''+xml_file
            # out= commands.getoutput(replace_call_duration)
            # Logger.debug('in caller, replace duration out is '+out)
            # #replace audio pcap
            # apcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/') + SipMqConstants.SIP_AUDIO_PCAP_FILE.replace(r'/',r'\/')
            # vpcap = SipMqConstants.SIP_XML_PATH.replace(r'/', r'\/') + SipMqConstants.SIP_VIDEO_PCAP_FILE.replace(r'/',r'\/')
            # replace_pcap = '''sed -ri 's/play_pcap_audio=".*"/play_pcap_audio="''' + apcap + '''"/g' '''+SipMqConstants.SIP_XML_PATH+'''/uac_caller.xml'''
            # out = commands.getoutput(replace_pcap)
            # Logger.debug('in caller, replace pcap out is ' + out)
            # #replace_video pcap
            # replace_pcap = '''sed -ri 's/play_pcap_video=".*"/play_pcap_video="''' + vpcap + '''"/g' '''+SipMqConstants.SIP_XML_PATH+'''/uac_caller.xml'''
            # out = commands.getoutput(replace_pcap)
            # Logger.debug('in caller, replace pcap out is ' + out)
            #
            # cc="sipp  -i "+SipUtil.get_local_ip()+" -p "+msgdic['caller_port']+" -inf "+SipMqConstants.SIP_XML_PATH+"users_caller_"+msgdic['caller_port']+".csv -sf "+xml_file+" "+msgdic['host']+" -m "+str(len(msgdic['data']['userlist']))+ " -r "+str(msgdic['caps'])+" -rp 1000 -l "+str(len(msgdic['data']['userlist']))+" -trace_err"
            # Logger.getLogger().debug("in caller, cmd is : " + cc)
            # p = subprocess.Popen(cc.split(),shell=False)
            # SipRegAgent.confid_sippid_map.append({'confid': msgdic['confid'], 'sippid': p.pid})
            # reply_msg = {'cmd': 'caller', 'result': True, 'reply_id': msgdic['msgid']}
        elif msgdic['cmd'] == 'endconf'or msgdic['cmd']=='end_sipp':
            Logger.getLogger().debug("in endconf, sipp list is "+str(SipRegAgent.confid_sippid_map))
            try:
                Logger.getLogger().debug("in endconf, sipp list len is " + str(len(SipRegAgent.confid_sippid_map)))
            except:
                Logger.getLogger().debug("in endconf, exception")
            sipp_pid_list=get_sipp_pid_list()
            # remove_conf_in_list(msgdic['confid',SipRegAgent.confid_sip_port_list])
            i=0
            # find pid and kill, return used port to port_list
            confid_pid_map_lock.acquire()
            while i<len(SipRegAgent.confid_sippid_map):
                Logger.getLogger().debug("confid "+SipRegAgent.confid_sippid_map[i]['confid']+" corresponding sip pid is "+str(SipRegAgent.confid_sippid_map[i]['sippid']))
                #kill only when recv endconf&& confid is specified or kill all sipp process
                if msgdic['cmd']=='endconf' and str(msgdic['confid']) == str(SipRegAgent.confid_sippid_map[i]['confid']) or msgdic['cmd']=='end_sipp':
                    Logger.getLogger().debug('kill cmd is '+"kill 9 " + str(SipRegAgent.confid_sippid_map[i]['sippid']))
                    ports=get_port_with_pid(str(SipRegAgent.confid_sippid_map[i]['sippid']))
                    os.system("kill 9 " + str(SipRegAgent.confid_sippid_map[i]['sippid']))
                    if len(ports) >0:
                        Logger.debug('returning port: '+str(ports)+' to port_list')
                        return_ports_to_sip_port_list(ports)
                    SipRegAgent.confid_sippid_map.pop(i)
                    i=i-1 #-1 to prevent skipping next element
                i=i+1
            confid_pid_map_lock.release()
            if len(sipp_pid_list)==0:
                if msgdic['cmd']=='end_sipp':
                    reply_msg = {'cmd': msgdic['cmd'], 'result': True, 'reply_id': msgdic['msgid']}
                else:
                    reply_msg = {'cmd': msgdic['cmd'], 'result': False, 'reply_id': msgdic['msgid']}
            else:
                reply_msg = {'cmd': msgdic['cmd'], 'result': True, 'reply_id': msgdic['msgid']}
        else:
            reply_msg = {'cmd': 'errinfo', 'result': False, 'reply_id': msgdic['msgid']}
        Logger.debug("out of case")
        SipRegAgent.agt.sendBackMsg(str(reply_msg))
    except:
        Logger.getLogger().debug(traceback.format_exc())

# def get_conf_in_list(confid,conf_list):
#     for item in conf_list:
#         if confid == item['confid']:
#             return confid
# def remove_conf_in_list(confid,conf_list):
#     i = 0
#     while i < len(conf_list):
#         if confid == str(conf_list[i]['confid']):
#             conf_list.pop(i)
#             i = i - 1  # -1 to prevent skipping next element
#         i = i + 1

def get_port(out,remote_host):
    '''
    get sip port number according to sipp output
    :param out:
    :param remote_host:
    :param remote_port:
    :return:
    '''
    line_pattern = re.compile('\n.*'+remote_host)
    port_line_m = line_pattern.search(out)
    if port_line_m is None:
        Logger.getLogger().error('in get_port, ' +remote_host+'not found')
        return None
    port_pattern = re.compile(r'(\s|\t){1,4}\d{4,5}(\t|\s){1,4}')
    m = port_pattern.search(port_line_m.group())
    if m is None:
        Logger.error('in get_port, sipp local port not found')
        return None
    else:
        return m.group().strip()
def callback_running_in_sub_thread(msg):
    #pre_alloc_port_version
    # start = time.time()
    # caller_reg_port = get_available_sip_port()
    # callee_reg_port = get_available_sip_port()
    # caller_media_port = get_available_media_port()
    # callee_media_port = get_available_media_port()
    # end = time.time()
    # Logger.debug('arrange port cost time: ' + str(end - start))
    # t1 = threading.Thread(target=sip_reg_handler,args=(msg,caller_reg_port,callee_reg_port,caller_media_port,callee_media_port))
    # t1.start()
    t1 = threading.Thread(target=sip_reg_handler,args=(msg,))
    t1.start()
class SipRegAgent(object):
    confid_sippid_map=[]
    confid_sip_port_list=[]
    agt=None
    MIN_SIP_PORT=35001
    MAX_SIP_PORT=40000
    MIN_MEDIA_PORT=9999
    MAX_MEDIA_PORT=14998
    def __init__(self):
        pass
    def start(self,host='localhost',mquser=SipMqConstants.MQ_USER,mqpwd=SipMqConstants.MQ_PASSWORD):
        SipRegAgent.agt = Agent(host,mquser,mqpwd,receive_callback=callback_running_in_sub_thread)
        SipRegAgent.agt.start_receive()
def is_port_used2(port):
    # reg pattern for IP:port
    sk=socket(AF_INET,SOCK_DGRAM)
    iport=int(port)
    try:
        sk.bind((SipUtil.get_local_ip(),iport))
    except:
        Logger.debug(traceback.format_exc())
        Logger.debug('port in use.port is:'+str(port))
        return True
    sk.close()
    return False
# def is_port_used(port):
#     # reg pattern for IP:port
#     start = time.time()
#     out=commands.getoutput('netstat -tunlp')
#     end = time.time()
#     Logger.debug('is_port_used cost time1: ' + str(end - start))
#     p = re.compile("(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d{2,5}")
#     end = time.time()
#     Logger.debug('is_port_used cost time2: ' + str(end - start))
#     ip_port_list=p.findall(out)
#     end = time.time()
#     Logger.debug('is_port_used cost time3: ' + str(end - start))
#     used_port=[]
#     for item in ip_port_list:
#         used_port.append(item.split(':')[1])
#     end=time.time()
#     Logger.debug('is_port_used cost time: ' + str(end - start))
#     if str(port) in used_port:
#         return True
#     return False
def get_available_sip_port():
    length=len(sip_port_list)
    result=None
    for i in range(0,length):
        if not is_port_used2(sip_port_list[i]):
            result=pop_sip_port_list(i)
            break
        else:
            pop_sip_port_list(i)
    return result
def get_available_media_port():
    length=len(media_port_list)
    result=None
    for i in range(0,length):
        if not is_port_used2(media_port_list[i]):
            result=pop_media_port_list(i)
            break
        else:
            pop_media_port_list(i)
    return result
def get_port_with_pid(pid):
    out=commands.getoutput('netstat -tunlp|grep sipp')
    p=re.compile('\n.*'+str(pid)+'/sipp')
    lines=p.findall(out)
    p2 = re.compile("(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d{2,5}")
    ip_port_list = p2.findall(str(lines))
    ports=[]
    for item in ip_port_list:
        ports.append(item.split(':')[1])
    return ports

def return_ports_to_sip_port_list(ports):
    for port in ports:
        if (int(port) not in sip_port_list) and (port >= SipRegAgent.MIN_SIP_PORT and port<SipRegAgent.MAX_SIP_PORT):
            add_port_to_sip_port_list(int(port))


def is_process_alive(pid):
    spid=str(pid)
    out=commands.getoutput('ps '+spid)
    if out.find(spid) == -1:
        return False
    elif out.find('defunct')!=-1:
        return False
    return True

if __name__ == '__main__':
    nowtime_str = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))
    print nowtime_str
    #LINUX
    DebugLogPath = Utils.create_folder("TestResult/DebugLog/")
    ResultLogPath = Utils.create_folder("TestResult/HttpResult/")

    #WINDOWS
    """DebugLogPath = Utils.create_folder("TestResult\\DebugLog\\")
    ResultLogPath = Utils.create_folder("TestResult\\HttpResult\\")"""
    debug_log_file = DebugLogPath + nowtime_str + "_sip_Debug.log"
    result_log_file = ResultLogPath + nowtime_str + "_sip.log"

    logger = Utils.create_debug_logger("MXTest", debug_log_file)
    logger_db = Utils.create_http_result_logger("Result", result_log_file)

    try:
        init_sip_port_list(sip_port_list)
        init_media_port_list(media_port_list)
        agent=SipRegAgent()
        print 'Sip Agent is running...'
        agent.start(SipMqConstants.MQ_LOCAL_SERVER, SipMqConstants.MQ_USER, SipMqConstants.MQ_PASSWORD)
    except:
        Logger.getLogger().debug(traceback.format_exc())
    # cc = "sipp -i 192.168.5.87  -inf /mnt/aqf/sipxml/users_caller.csv -sf /mnt/aqf/sipxml/uac_caller.xml 192.168.5.201:6650 -r 10 -rp 1000 -l 50 -d 25000 -aa "
    # p = subprocess.Popen(cc.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    # for i in range (1,100):
    #     print p.stdout.readline()
    # out='Call-rate(length)   Port   Total-time  Total-calls  Remote-host\n10.0(25000 ms)/1.000s\t5060\t1.00 s           10  192.168.5.201:6650(UDP)'
    # get_port(out,'192.168.5.201:6650')
