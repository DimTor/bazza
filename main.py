from machine import Pin,I2C
from neopixel import NeoPixel
from MX1508 import *
from VL53L0X import *
from tcs34725 import *
from time import sleep_ms,sleep
import uasyncio as asio
import aioespnow
import network

i2c_bus = I2C(0, sda=Pin(16), scl=Pin(17))
tcs = TCS34725(i2c_bus)
tcs.gain(4)#gain must be 1, 4, 16 or 60
tcs.integration_time(50)
i2c_bus1 = I2C(1, sda=Pin(21), scl=Pin(22))
tof = VL53L0X(i2c_bus1)
NUM_OF_LED = 1
np = NeoPixel(Pin(23), NUM_OF_LED)
color=['Red','Yellow','White','Green','Black','Cyan','Blue','Magenta']
dir_move=['Stop','Forward','Left','Right','Reverse']
motor_L = MX1508(4, 2)
motor_R = MX1508(19, 18)
Sp=1023
Sp1=int(Sp*0.3)
Lt=60
alfa=0.8
debug=1

R_W_count,W_count,col_id,col_id_l,direct,di,dist,busy,busy_col,col_sel=0,0,0,0,0,0,500,0,0,5
R_m_pin = Pin(25, Pin.IN)
L_m_pin = Pin(35, Pin.IN)

motor_R.forward(Sp)
motor_L.forward(Sp)

# A WLAN interface must be active to send()/recv()
network.WLAN(network.STA_IF).active(True)
e = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support
e.active(True)
#peer = b'\xCC\xDB\xA7\x49\xC2\x24' #My 70B8F65B5844
#e.add_peer(peer)
#peer = b'\xCC\xDB\xA7\x49\xC2\x24' #ccdba749c224
#e.add_peer(peer)


def R_W_int(pin):
    global W_count,R_W_count
    W_count+=1
    R_W_count+=1
    print(R_W_count, W_count, 'R')
    
def L_W_int(pin):
    global W_count,L_W_count
    W_count-=1
    L_W_count+=1
    print(L_W_count, 'L')
   
R_m_pin.irq(trigger=Pin.IRQ_FALLING |Pin.IRQ_RISING , handler=R_W_int) #t    rigger=Pin.IRQ_FALLING | 
L_m_pin.irq(trigger=Pin.IRQ_FALLING |Pin.IRQ_RISING , handler=L_W_int)

async def synch(int_ms):
    while 1:
        await asio.sleep_ms(int_ms)
        if direct==0:
            if W_count>0:
                motor_R.forward(Sp1)
                motor_L.forward(Sp)
            elif W_count<0:
                motor_R.forward(Sp)
                motor_L.forward(Sp1)
            else:
                motor_R.forward(Sp)
                motor_L.forward(Sp)
        elif direct==1:
            if W_count>0:
                motor_R.forward(Sp1)
                motor_L.reverse(Sp)
            elif W_count<0:
                motor_R.forward(Sp)
                motor_L.reverse(Sp1)
            else:
                motor_R.forward(Sp)
                motor_L.reverse(Sp)
        elif direct==2:
            if W_count>0:
                motor_R.reverse(Sp1)
                motor_L.forward(Sp)
            elif W_count<0:
                motor_R.reverse(Sp)
                motor_L.forward(Sp1)
            else:
                motor_R.reverse(Sp)
                motor_L.forward(Sp)        
        elif direct==3:
            if W_count>0:
                motor_R.reverse(Sp1)
                motor_L.reverse(Sp)
            elif W_count<0:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp1)
            else:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp)
        elif direct==-1:
            motor_R.reverse(0)
            motor_L.reverse(0)

async def W_sp(int_ms):
    global di,direct,busy_col
    while 1:
        await asio.sleep_ms(int_ms)
        await color_det()
        await dist_det()
        if 150<dist<250:di=1
        elif dist<150:di=2
        else:di=0
        if (not busy) & (not busy_col):
            if di==1:
                if dist%2:
                    direct=1
                else:
                    direct=2
                await move(8)
            elif di==2:
                direct=3
                await move(16)
            else:
                direct=0
        if  col_id==4: #col_id_l==col_id &
            direct=3
            await move(4)
            direct=2
            await move(8)
        if  col_id==col_sel:#col_id_l==col_id &
            direct=-1
            busy_col=1
        else:
            motor_R.forward(Sp)
            motor_L.forward(Sp)
            busy_col=0
                      
async def move(turn):
    global R_W_count,busy
    busy=1
    R_W_count=0    
    while R_W_count<turn:   
        await asio.sleep_ms(0)
    busy=0

async def color_det():
    global col_id,col_id_l
    rgb=tcs.read(1)
    r,g,b,c =rgb[0],rgb[1],rgb[2], rgb[3]
    h,s,v=rgb_to_hsv(r*2,g,b)
    if c>3000:
        col_id=2
    elif c<2300:
        col_id = 4
    elif 0<h<20:
        col_id_l=col_id
        col_id=0
    elif 20<h<50:
        col_id_l=col_id
        col_id=1
    elif 150<h<180:
        col_id_l=col_id
        col_id=3
    elif 180<h<220:
        if c>2500:
            col_id_l=col_id
            col_id=5
        else:
            col_id_l=col_id
            col_id=6
    elif 241<h<350:
        col_id_l=col_id
        col_id=7 
    if debug:
        print('Color is {}. R:{} G:{} B:{} H:{:.0f} S:{:.0f} V:{:.0f}'.format(color[col_id],r,g,b,h,s,v))
            
async def dist_det():
    global dist
    tof.start()
    dist_l=dist
    dist=tof.read()-65
    tof.stop()
    dist=int(alfa*dist+(1-alfa)*dist_l)
    if debug:
        print('Distance is {}. W_count {}'.format(dist   ,W_count))
            
async def LED_cont(int_ms):
    while 1:
        await asio.sleep_ms(int_ms)
        if col_id==0:
            np[0]=(Lt,0,0)
        elif col_id==1:
            np[0]=(Lt,Lt,0)
        elif col_id==2:
            np[0]=(Lt,Lt,Lt)
        elif col_id==3:
            np[0]=(0,Lt,0)
        elif col_id==4:
            np[0]=(0,0,0)
            np.write()
            await asio.sleep_ms(300)
            np[0]=(Lt,0,0)
            np.write()
            await asio.sleep_ms(300)
        elif col_id==5:
            np[0]=(0,Lt,Lt)
        elif col_id==6:
            np[0]=(0,0,Lt) 
        elif col_id==7:
            np[0]=(Lt,0,Lt)
        np.write()
        
async def send(e, period):
    while 1:
        await e.asend(color[col_id]+' '+dir_move[1+direct]+' '+str(dist)) #
        await asio.sleep_ms(period)
        
async def resive(e,int_ms):
    global col_sel
    while 1:
        async for mac, msg in e:
            col_sel=int.from_bytes(msg,'big')-48
            #print(color[col_sel])
            await asio.sleep_ms(int_ms)
            
# define loop
loop = asio.get_event_loop()

#create looped tasks
loop.create_task(synch(1))
loop.create_task(W_sp(100))
loop.create_task(LED_cont(100))
loop.create_task(send(e,100))
loop.create_task(resive(e,100))
#loop run forever
loop.run_forever()
    