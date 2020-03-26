#coding=utf-8
import threading
import queue
import time
import re
import subprocess
import conf
import adblib
import traceback
allevents=list()
sendedevents=list()
event = list()
def parseEvent(content,serial):
    device=conf.devices.get(serial,[])
    timestamp=re.findall('\d+\.\d{6}',content)
    e_FINGER=re.findall('BTN_TOUCH',content)
    e_event = re.findall('UP|DOWN', content)
    px=re.findall('ABS_MT_POSITION_X', content)
    x=re.findall('0000\w{4}', content)
    py = re.findall('ABS_MT_POSITION_Y', content)
    y = re.findall('0000\w{4}', content)

    if timestamp:
        stime=timestamp[0]
        if e_FINGER:
            event.append(e_event[0])
        if px:
            ix=int(x[0], 16)
            conver_x = round(float(ix) / device.get('display')[0], 3)
            event.append(ix)
        if py:
            iy=int(y[0], 16)
            conver_y = round(float(iy) / device.get('display')[1], 3)
            event.append(iy)
    return   event
# print allevent
# allevent=['DOWN',  '0000013f', '0000038d',  'UP', 'DOWN',  '000003eb', '000000aa',  'UP',  'DOWN', '000001ee', '000006a1', '000001ed', '00000691','UP']
def getevent(content,serial):
    eventdata= parseEvent(content,serial)
    new_evt=eventdata
    num = 0
    for index, value in enumerate(eventdata):
        cnt = eventdata.count('DOWN')
        if value == 'DOWN':
            num += 1
        if num == cnt:
            new_evt = eventdata[index:]
            break
    return     new_evt

# print getevent(log)
# import adbutils
# d=adbutils.Adb()
# print d.shell('getevent')

def changeevent(event):

    try:
        option = list()
        if len(event)==4:
            option.append({"click":[event[1],event[2]]})
        elif len(event)>4:
            option.append({"swipe": [event[1], event[2],event[-3], event[-2]]})
        else:
            raise(ValueError,'解析数据异常')
        return option
    except:
        print('data error %s' % event)
        return [{"click":[0,0]}]


def sendEvent(event,rec_serial,d_serials,swipetime=1000):
    cmd=''
    rec_d=conf.devices.get(rec_serial, [])
    init_top = rec_d.get('top', 0)
    for seri in d_serials:
        d_info=conf.devices.get(seri, [])
        d_top=d_info.get('top',0)
        dx=d_info.get('display')[0]
        dy=d_info.get('display')[1]
        eventtype=list(event[0].keys())[0]
        args=event[0].get(eventtype,[])
        diff_top=d_top-init_top
        new_xy=list()
        #转换成10进制坐标
        for index,arg in enumerate(args):
            if index%2==0:
                new_xy.append(int(arg))
            elif index%2==1:
                new_xy.append(int(arg)+diff_top)
        if eventtype=='click':
            cmd='adb -s %s shell input tap %s %s'%(seri,new_xy[0],new_xy[1])
        elif eventtype=='swipe':
            cmd='adb -s %s shell input swipe %s %s %s %s %s'%(seri,new_xy[0],new_xy[1],new_xy[2],new_xy[3],swipetime)
        popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)


def Des_Devices(rec_dev):
    devices=adblib.getdevices()
    devices.remove(rec_dev)
    return devices





def getEventLog(q,serial):
    cmd = 'adb -s %s exec-out getevent -tl'%(serial)
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    for line in iter(popen.stdout.readline, b''):
        line=line.decode('utf-8')
        event = getevent(line,serial)
        if re.findall('UP', line) and re.findall('BTN_TOUCH', line):
            touch_option=changeevent(event)
            q.put(touch_option)
    popen.stdout.close()
    popen.wait()





class RecordEvent(threading.Thread):
    """消费线程"""
    def __init__(self, t_name, queue,recode_serial):
        self.queue = queue
        self.rec_d=recode_serial
        threading.Thread.__init__(self, name=t_name)
    def run(self):
        getEventLog(self.queue , self.rec_d)


class DispatchToDevice(threading.Thread):
    """消费线程"""
    def __init__(self, t_name, queue,recode_serial,d_serials):
        self.queue = queue
        self.rec_d=recode_serial
        self.d_s=d_serials
        threading.Thread.__init__(self, name=t_name)

    def run(self):
        while True:
            try:
                queue_val = self.queue.get()
                print(' get events: %s'%(queue_val))
                sendEvent(queue_val, self.rec_d,self.d_s)
            except Exception:
                print(traceback.format_exc())
                break;
if __name__=="__main__":
    threads = []
    recode_serial='66c0c42c'
    q=queue.Queue()
    devices=Des_Devices(recode_serial)
    p_thread=RecordEvent('record_thread',q,recode_serial)
    p_thread.start()
    for index,d in enumerate(devices):
        print('待测试设备名称：',conf.devices.get(d).get('name'))
        d_thread = DispatchToDevice('replay_event', q,  recode_serial,devices)
        d_thread.start()
        threads.append(d_thread)
    p_thread.join()
    for thd in threads:
        thd.join()











