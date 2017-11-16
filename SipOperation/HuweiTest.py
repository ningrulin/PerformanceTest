#coding:utf-8

import re,commands,time,threading
import traceback
from socket import *
def get_sipp_pid_list(output):
    print 'in get_sipp_pid_list, output of ps -ef|grep sipp is '+output
    #print output
    outinfo=output.split('root')
    pid_list=[]
    print 'len is '+str(len(outinfo))
    for i in range(len(outinfo)):
        print "-----------------------------"
        print outinfo[i]
        p=re.compile('.*sipp -i.*')
        sipp_line=p.search(outinfo[i])
        if sipp_line:
            p2 = re.compile('(\t|\s){1,10}\d{1,5}(\t|\s){1,10}')
            pid=p2.search(sipp_line.group())
            if pid:
                print 'pid is '+str(pid.group().strip())
                pid_list.append(pid.group().strip())
    return pid_list

def get_port_with_pid(pid):
    out=commands.getoutput('netstat -tunlp|grep sipp')
    p=re.compile('\n.*'+str(pid)+'/sipp')
    lines=p.findall(out)
    p2 = re.compile("(?:[0-9]{1,3}\.){3}[0-9]{1,3}:\d{2,5}")
    ip_port_list = p2.findall(str(lines))
    ports=[]
    for item in ip_port_list:
        print item
        ports.append(item.split(':')[1])
    return ports

def is_port_used2(port):
    # reg pattern for IP:port
    start = time.time()
    sk=socket(AF_INET,SOCK_DGRAM)
    iport=int(port)
    try:
        sk.bind(('172.18.16.190',iport))
    except:
        print traceback.format_exc()
        print 'port in use'
        return True
    print 'listening port '+str(port)
    sk.close()
    end = time.time()
    print 'is_port_used cost time: ' + str(end - start)
    return False
def is_process_alive(pid):
    spid=str(pid)
    out=commands.getoutput('ps '+spid)
    if out.find(spid) == -1:
        return False
    elif out.find('defunct')!=-1:
        return False
    return True
if __name__ == '__main__':
#     out='''root      98413  98405  2 21:00 pts/7    00:00:00 sipp -i 192.168.5.87 -p 5061 -sf /mnt/aqf/sipxml/uac_callee.xml 192.168.5.201:6650 -r 10 -rp 1000 -l 9 -aa -trace_stat
# root      98421  98405  1 21:00 pts/7    00:00:00 sipp -i 192.168.5.87 -p 5060 -inf /mnt/aqf/sipxml/users_caller.csv -sf /mnt/aqf/sipxml/uac_caller.xml 192.168.5.201:6650 -r 10 -rp 1000 -l 1 -aa -trace_stat
# root      98457  98405  0 21:01 pts/7    00:00:00 sh -c { ps -ef|grep sipp; } 2>&1
# root      98459  98457  0 21:01 pts/7    00:00:00 grep sipp'''
#     ss=get_sipp_pid_list(out)
#     print ss
#     out='''udp        0      0 0.0.0.0:8888            0.0.0.0:*                           50905/sipp
# udp        0      0 0.0.0.0:8889            0.0.0.0:*                           52654/sipp
# udp   214272      0 192.168.5.87:6000       0.0.0.0:*                           50905/sipp
# udp   213888      0 192.168.5.87:6001       0.0.0.0:*                           52654/sipp
# udp    81536      0 192.168.5.87:6002       0.0.0.0:*                           50905/sipp
# udp        0      0 192.168.5.87:6003       0.0.0.0:*                           52654/sipp
# udp        0      0 192.168.5.87:5060       0.0.0.0:*                           50905/sipp
# udp        0      0 192.168.5.87:5061       0.0.0.0:*                           52654/sipp '''

    # t1 = threading.Thread(target=is_port_used2, args=('6000',))
    # t1.start()
    # t2 = threading.Thread(target=is_port_used2, args=('6000',))
    # t2.start()
    # t3 = threading.Thread(target=is_port_used2, args=('6000',))
    # t3.start()
    # t4 = threading.Thread(target=is_port_used2, args=('6000',))
    # t4.start()
    import subprocess
    cmd1='sipp  -i 172.18.16.190 -p 15672 -mp 10345 -inf /root/PerformanceTest/SipOperation/sipxml/users_reg_caller_35081.csv -sf /root/PerformanceTest/SipOperation/sipxml/uac_reg.xml 172.18.16.187:6650 -r 10 -rp 1000 -aa -trace_stat -fd 4 -trace_err'
    cmd2='sipp  -i 172.18.16.190 -p 25672 -mp 10345 -inf /root/PerformanceTest/SipOperation/sipxml/users_reg_caller_35081.csv -sf /root/PerformanceTest/SipOperation/sipxml/uac_reg.xml 172.18.16.187:6650 -r 10 -rp 1000 -aa -trace_stat -fd 4 -trace_err'
    p=subprocess.Popen(cmd1.split(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    print is_process_alive(p.pid)
    p.communicate()


