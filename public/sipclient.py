#!/usr/bin/python

import random
import socket
import sys
import fcntl
import os
import signal
import struct
import subprocess
import time
from threading import Thread
from multiprocessing import Process



if len(sys.argv) < 3:
    print "usage: sdpclient HOST PORT VOICEBRIDGE(optional) INPUT_VIDEO_PATH(optional)"
    sys.exit()
else:
    REMOTE_HOST = sys.argv[1]
    REMOTE_PORT = int(sys.argv[2])
    VOICE_BRIDGE = sys.argv[3] if sys.argv[3].isdigit() else "72013"
    INPUT_VIDEO_PATH = sys.argv[4] if sys.argv[4] else "video.mp4"


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def terminate_process(process):
    try:
        os.kill(process.pid,signal.SIGTERM)
    except:
        print "EXCEPTION when terminating process"

def signal_handler(signal, frame):
        global p1,p2,s
        sendByeMessage(CLIENT_TAG,SERVER_TAG,s)
        s.close()
        terminate_process(p1)
        terminate_process(p2)
        print 'Exiting...'
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler) #ctrl-c (-2)
signal.signal(signal.SIGTERM, signal_handler)

BUFFER_SIZE = pow(2,12)
#NETWORK_INTERFACE = 'eth0'
NETWORK_INTERFACE = 'br0'
#NETWORK_INTERFACE = 'wlan0'
#NETWORK_INTERFACE = 'p5p1'
LOCAL_HOST = get_ip_address(NETWORK_INTERFACE)
LOCAL_SDP_PORT= random.randint(5000,5200)
LOCAL_ADDRESS = (LOCAL_HOST, LOCAL_SDP_PORT)
ADDRESS = (REMOTE_HOST,REMOTE_PORT)
#VOICE_BRIDGE = "72013"
AUDIO_SAMPLE_RATE = 8000
AUDIO_CODEC_NAME = "G722/"+str(AUDIO_SAMPLE_RATE)
VIDEO_CODEC_ID = 96
VIDEO_CODEC_NAME = "H264"
#VIDEO_ENCODER_NAME = "libx264"
VIDEO_ENCODER_NAME = "libopenh264"
AUDIO_CODEC_ID = 9
CLIENT_TAG = str(random.randint(10000000,99999999))
SERVER_TAG = ""
CALL_ID = str(random.randint(10000000,99999999))+"@"+LOCAL_HOST
LOCAL_VIDEO_PORT = random.randint(20000,21000)
REMOTE_VIDEO_PORT = 0
LOCAL_AUDIO_PORT = random.randint(5300,6000)
REMOTE_AUDIO_PORT = 0
VIDEO_ADDRESS = (REMOTE_HOST,REMOTE_VIDEO_PORT)
FFMPEG_PATH = "/usr/local/bin/ffmpeg"
CALLERNAME = "sip-client" #must be url-encoded
USER_AGENT = "Polycom QDX 6000 (rev 0.6.4)"
#INPUT_VIDEO_PATH = "video.mp4"
VIDEO_RESOLUTION={
    'qvga':'320x240',
    'vga':'640x480',
    'hd':'1280x720',
    'fullhd':'1920x1080'
}

#Socket local
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
#s.connect(ADDRESS)

#INVITE MESSAGE#
SDP_CONTENT="""v=0\r
o="""+CALLERNAME+""" 0 0 IN IP4 """+LOCAL_HOST+"""\r
s=Session SIP/SDP\r
c=IN IP4 """+LOCAL_HOST+"""\r
t=0 0\r
a=recvonly\r
m=audio """+str(LOCAL_AUDIO_PORT)+""" RTP/AVP """+str(AUDIO_CODEC_ID)+""" 8 18 0 111\r
a=rtpmap:0 PCMU/8000/1\r
a=rtpmap:8 PCMA/8000/1\r
c=IN IP4 """+LOCAL_HOST+"""\r
m=video """+str(LOCAL_VIDEO_PORT)+""" RTP/AVP """+str(VIDEO_CODEC_ID)+"""\r
a=rtpmap:"""+str(VIDEO_CODEC_ID)+""" """+VIDEO_CODEC_NAME+"""/90000/1\r"""

SDP_HEADER = """INVITE sip:"""+VOICE_BRIDGE+"""@"""+REMOTE_HOST+""" SIP/2.0\r
Via: SIP/2.0/UDP """+LOCAL_HOST+""":"""+str(LOCAL_SDP_PORT)+""";branch="""+str(random.randint(10000000,99999999))+"""\r
Max-Forwards: 70\r
To:  <sip:"""+VOICE_BRIDGE+"""@"""+REMOTE_HOST+""">\r
From: \""""+CALLERNAME+"""\" <sip:"""+VOICE_BRIDGE+"""@"""+LOCAL_HOST+""">;tag="""+CLIENT_TAG+"""\r
Call-ID: """+CALL_ID+"""\r
CSeq: 1 INVITE\r
Session-Expires: 3600\r
Contact: <sip:"""+VOICE_BRIDGE+"""@"""+LOCAL_HOST+""":"""+str(LOCAL_SDP_PORT)+""">\r
User-Agent: """+USER_AGENT+"""\r
Content-Type: application/sdp\r
Content-Length:""" +str(len(SDP_CONTENT))+"\r\n\r\n"

SDP_MESSAGE_INVITE=SDP_HEADER+SDP_CONTENT
print "SDP Message: ", SDP_MESSAGE_INVITE

def getTransactionFields(message):
    tag = ""
    branch = ""
    callid = ""
    remote_video_port = ""
    remote_audio_port = ""

    if message == "":
        return message
    else:
        for line in message.splitlines():
            if "To:" in line:
                remote_tag=line.split(";",1)[1].replace("tag=","")
            elif "Via" in line:
                branch=line.split(";",1)[1].replace("branch=","")
            elif "Call-ID" in line:
                callid=line.split(":",1)[1].strip()
            elif "video" in line:
                remote_video_port=line.split()[1].strip()
            elif "audio" in line:
                remote_audio_port=line.split()[1].strip()

    return remote_tag,branch,callid,int(remote_video_port),int(remote_audio_port)


def messageOk(str):
    if "OK" in str:
        return True
    else:
        return False

def createAckMessage(client_tag,server_tag,transaction_branch, call_id):
    message = """ACK sip:"""+VOICE_BRIDGE+"""@"""+REMOTE_HOST+""":"""+str(REMOTE_PORT)+""";transport=udp SIP/2.0\r
Via: SIP/2.0/UDP """+LOCAL_HOST+""":"""+str(LOCAL_SDP_PORT)+""";rport;branch="""+transaction_branch+"""\r
Max-Forwards: 70\r
To: <sip:"""+VOICE_BRIDGE+"""@"""+REMOTE_HOST+""">;tag="""+ server_tag +"""\r
From:  <sip:"""+LOCAL_HOST+"""> ;tag="""+client_tag+"""\r
Call-ID: """+call_id+"""\r
CSeq: 1 ACK\r
Contact: <sip:"""+VOICE_BRIDGE+"""@"""+LOCAL_HOST+""":"""+str(LOCAL_SDP_PORT)+""">\r
Expires: 120\r
User-Agent: """+USER_AGENT+"""\r
Content-Length: 0\r\n\r\n"""
    return message

#Bye Message and handler
def sendByeMessage(client_tag,server_tag,socket):
    BYE_BRANCH = str(random.randint(10000000,99999999))
    SDP_MESSAGE_BYE = """BYE sip:"""+VOICE_BRIDGE+"""@"""+REMOTE_HOST+""":"""+str(REMOTE_PORT)+""";transport=udp SIP/2.0\r
Via: SIP/2.0/UDP """+LOCAL_HOST+""":"""+str(LOCAL_SDP_PORT)+""";rport;branch="""+BYE_BRANCH+"""\r
Max-Forwards: 70\r
To: <sip:"""+VOICE_BRIDGE+"""@"""+REMOTE_HOST+""">;tag="""+ server_tag +"""\r
From:  <sip:"""+LOCAL_HOST+"""> ;tag="""+client_tag+"""\r
Call-ID: """+CALL_ID+"""\r
CSeq: 2 BYE\r
User-Agent: """+USER_AGENT+"""\r
Content-Length: 0\r\n\r\n"""
    BUFFER = bytearray(SDP_MESSAGE_BYE)
    s.sendto(BUFFER,ADDRESS)

##

BUFFER = bytearray(SDP_MESSAGE_INVITE)
s.bind(LOCAL_ADDRESS)


def startAudioStream():
    global p1
    FFMPEG_AUDIO_CALL = [FFMPEG_PATH,'-re','-i' ,INPUT_VIDEO_PATH,'-vn','-ac', '1', '-acodec',AUDIO_CODEC_NAME.split("/",1)[0].lower(),'-ar',str(AUDIO_SAMPLE_RATE*2),'-af','volume=0.5','-f','rtp','-payload_type',str(AUDIO_CODEC_ID),"rtp://"+REMOTE_HOST+":"+str(REMOTE_AUDIO_PORT)+"?localport="+str(LOCAL_AUDIO_PORT)]
    p1 = subprocess.Popen(FFMPEG_AUDIO_CALL)
    print "[DEBUG] Calling ffmpeg with the command line: ", " ".join(FFMPEG_AUDIO_CALL)

def startVideoStream():
    global p2

    #CIF
    #resolutions = ['128x96','176x144','256x192','352x240','352x288','704x480','704x576','1408x1152','528x384']
    #QVGA
    #resolutions = ['160x120','320x240','360x240','400x240','640x480']
    #for r in resolutions:
    profiles = [
        ('main','1.0'),
        ('main','1.3'),
        ('main','1.1'),
        ('main','1.2'),
        ('main','1.3'),
        ('main','2.0'),
        ('main','2.1'),
        ('main','2.2'),
        ('main','3.0'),
        ('main','3.1'),
        ('main','3.2'),
        ('main','4.0'),
        ('main','4.1'),
        ('main','4.2')
    ]
    profiles=[('baseline','1.3')]
    for p in profiles:
        FFMPEG_VIDEO_CALL = [
            FFMPEG_PATH,
            #'-ignore_loop','0', #for images
            #'-loop','1',
            '-re',
            #'-r','15',
            '-i',INPUT_VIDEO_PATH,
            #'-i','/home/mario/bbb-stuff/back.png',
            #'-i','/home/mario/bbb-stuff/mconf-videoconf-logo.mp4',
            '-s',VIDEO_RESOLUTION['hd'], #720x480 made polycom crash
            #'-filter:v','crop='+VIDEO_RESOLUTION.split("x")[0]+':'+VIDEO_RESOLUTION.split("x")[1]+':0:0',
            #'-force_key_frames','expr:gte(t,n_forced)',
            #'-b:v','1024k',
            '-maxrate','1024k',
            '-bufsize','1024k',
            '-g','1', #GOP
            #'-aspect','16:9',
            #'-keyint_min','10',
            #'-q:v','1',
            #'-crf','40',
            #'-loglevel','verbose',
            #'-loglevel','quiet',
	    #'-qscale','1',
            '-vcodec',VIDEO_ENCODER_NAME,
            '-profile:v', p[0],
            #'-vf','drawtext=fontfile=/usr/share/fonts/truetype/freefont/FreeSerif.ttf:text=mario:x='+VIDEO_RESOLUTION.split("x")[0]+'-20:y='+VIDEO_RESOLUTION.split("x")[1]+':fontcolor=white:fontsize=30',
            #'-level', p[1],
            #'-preset','ultrafast',
            #'-movflags','frag_keyframe+empty_moov',
            #'-x264-params','slice-max-size=1024',
            #'-ps','1024', #RTP payload size (not needed for h264_mode0)
            '-slice_mode','dyn',
            '-max_nal_size','1024',
	    #'-allow_skip_frames','true',
            #'-b:v','100k',
	    '-r','15',
            '-an',
            '-rtpflags','h264_mode0',
            '-f', 'rtp',
            '-payload_type', str(VIDEO_CODEC_ID),
            "rtp://"+REMOTE_HOST+":"+str(REMOTE_VIDEO_PORT)+"?localport="+str(LOCAL_VIDEO_PORT)#+"\\&pkt_size=1024"

        ]
        p2 = subprocess.Popen(FFMPEG_VIDEO_CALL)
        print "[DEBUG] Calling ffmpeg with the command line: ", " ".join(FFMPEG_VIDEO_CALL)
        #time.sleep(20)
        #p2.terminate()
        #p2.wait()



#INVITE
s.sendto(BUFFER,ADDRESS)
global p1,p2
while True:
    try:


        data,addr = s.recvfrom(1800)
        print "Received MESSAGE:", data
        #raw_input("press a key to continue...")

        if messageOk(data):
            SERVER_TAG,ACK_BRANCH , CALLID, REMOTE_VIDEO_PORT , REMOTE_AUDIO_PORT = getTransactionFields(data)
            SDP_MESSAGE_ACK = createAckMessage(CLIENT_TAG, SERVER_TAG,ACK_BRANCH, CALLID)
            print "Sending Message: ", SDP_MESSAGE_ACK
            BUFFER = bytearray(SDP_MESSAGE_ACK)
            s.sendto(BUFFER,ADDRESS)

            startAudioStream()
            startVideoStream()

        time.sleep(0.1)
    except socket.error:
        print "Socket Error: Leaving!"
        s.close()
        sys.exit(1)

