#!/usr/bin/python
# Maritime application for use with touch displays
# Installation and configuration guide at https://github.com/jbonde/MAIA/blob/master/installation

from guizero import App, Text, PushButton, Window, ListBox, Box, Picture, Drawing
import os
import time, datetime
from time import sleep
from datetime import datetime, timedelta
import calendar
import subprocess
import csv
import math
import threading
import socket
import platform

OSplatform=(platform.system())
print("OSplatform = " + str(OSplatform))
gpioimport=False
if OSplatform=="Windows":
    workdir="C:\\"
elif OSplatform=="Linux": # Assuming RPi as hardware
    import RPi.GPIO as GPIO # used for dimming PiTFT display and controlling buzzer if installed with current display
    GPIO.setmode(GPIO.BCM)
    gpioimport=True
    try:
        import mypi #script to check hardware
    except:
        print("mypi not installed")

appver="1.5.0" # for displaying software version in the status window
UDPmode=True # fetching sensor and GPS data via UDP if True
SERmode=True # If GPS is connected to display and instrument data is fetched via UDP
display_brightness=100 # BRIGHTNESS percentage %

# Clock
counting=0 #Counter for stop watch
homise="hms" #hours - minutes - seconds interval
downcount=5 #default countdown time

#Racing
racecountdown=True #For deciding if counter goes down before race or up after start of race
racecount=0 #Counter for race countdow
but_race_text=None
but_race="05:00"
but_race_color="red"

# GUI
mode=" " #Modes are pushed from buttons in the menus and used in
wptscrolling=1 #index navigation
wptindex=0 #Default index number for waypoint list box
dashCourseUp=False # Dashboard has Course (COG) up if True. North Up if False   

# Menu and text properties
but_width=7 #Standard width of push buttons. Total width of 7+7+8=22 matches a 4.5" PiTFT display
but_height=4
but_text_size=35
but_text_medsize=80
but_text_bigsize=150
key_width=None #Keyboard buttons
key_height=None
posmode=True # black text n white back. Opposite if False
colorfor=None #"black"
colorback=None #"white"

#Met variables
tempin=None
tempout=None
pressure=None
altitude=None
seapressure=None
humidity=None

#GPS variables
latdep=None #Position of departure
londep=None
latnow=None #55.942508 #Current position in DEGDEC format
lonnow=None #11.870814
latnowdms=None #Current position in DMS format
lonnowdms=None
latdes=None # Default position of destination if no GPS
londes=None
latdesdms=None
londesdms=None
latbef=None #Last destination measured (for calculating trip distance)
lonbef=None
GPSspeed=0
GPScourse=0
GPSNS=None #N or S
GPSEW=None #E or W
GPSUTC=None #Time in UTC format
UTCOS=None # Time string formatted for OS time update when out of network
GPSdate=190101 #Date received from GPS
latdegminmin=None
londegminmin=None
GPSsim=False #GPS simulator mode

#Seatalk 1 variables
DEP=0 #Depth
TWS=0 #True wind speed
TWSmax=0 # Max wind speed
TWD=0 #True wind direction
TWA=0 #True wind angle to COG
AWS=0 #Apparent wind speed
AWA=0 #Apparent wind angle
TSE=0 #Sea temperature
STW=0 #log: speed through water

#GPS data
COG=0 #Course over ground
SOG=0 #Speed over ground

# UDP and MET commands
UDPstring=None
UDPaddress=None
UDPupdatedef=5 # default time to wait for UDP string. If below 0 texts will be red
UDPupdate=UDPupdatedef # Counting time to wait for UDP string
metpng="met.png"
UDP_IP = ""
UDP_PORT = 2000

# Serial setup
if SERmode==True:
    import serial
    # Serial communication with GPS and/or NMEA0183 input
    port1 = "/dev/ttyUSB0"  # USB serial (Adafruit GPS etc)
    port2 = "/dev/ttyUSB1"  # USB serial (Adafruit GPS etc)
    port = "/dev/ttyACM0"  # RPi4 or RPi0 with BS-708 receiver at USB port
    port4 = "/dev/ttyACM1"  # RPi with BS-708 receiver at USB port
    port5 = "/dev/ttyAMA0"  # RPi Zero PIN 10
    port6 = "/dev/ttyS0"    # RPi 3 + Zero PIN 10
    portbaud=9600 # Baudrate: 9600 for GPS, 4800 for NMEA0183
    porttimeout=1
    ser = serial.Serial(port, baudrate = portbaud, timeout=porttimeout)

#metpng="smb://192.168.0.105/PiShare/met.png"

# Navigational calculations
dest="" # Name of destination
DTW=0 # Distance from current position to selected waypoint
BRG=0 # Bearing to destination
TIMEZ = 2 #Offsetting GPS UTC time to local timezone 1=winther EST; 2=summer EST
UTZ=str(0)# Local time UTC+TIMEZ
TTG=0 # Time-to-go
ETA=0 # Expected time of arrival
navlog=[] #log list used for AVS summarizing distance covered each minute
for w in range (60):
    navlog.append(0) #create 60 items covering one hour
AVSlat=0
AVSlon=0
AVS01=None
AVS10=None
AVS30=None
AVS60=None
AVSlog=False #If the AVS log is activated
AVScount=0 #Counter used for activating AVS calc
AVSinterval=60 # The interval between each calc. Default 60 sec
AVSmode="AUTO" # selecting which AVS value to use for TTG etc.
AVS=None # The average speed depending on mode selected

# Trip
tripdistance=None # elapsed distance since start
triptime=None  # elapsed time
tripcount=0 #counting seconds between each update
tripsecelapsed=0 # elapsed trip distance counted by seconds
tripstart=str(datetime.now()) # Time when trip was started
tripaver=None #Average speed on trip
tripaver10=None #Average speed last 10 minutes
tripaver30=None #Average speed last 30 minutes
tripaver60=None #Average speed last 60 minutes
tripinterval=60 # how many seconds between each log update
latint=None # position since last tripinterval was reached
lonint=None
latsec=None #Updating tripdistance every seconds used for live updating the single display
lonsec=None
triplog=False # If triplog is active
TTGsec=0 # time to go in seconds

# Log file
log_header = []
log_data = []
logname='/home/pi/csv/' + 'time' + '.csv' # name will change according to time for each new file created
logfile_created=False

pwm=None # Pulse width modulation for controlling PiTFT brightness if used

# ****************    Interaction widgets  *******************************

# YES/NO interaction
def ynmenu(ynaction):
    global mode
    mode=ynaction
    window_ynmenu.bg=colorback
    window_ynmenu.text_color=colorfor
    text_ynmenu.value = "Do you really want to " + str(ynaction) + " ?"
    window_ynmenu.show()

def yesaction(): # Action to be performed if YES button is clicked
    global SERmode
    if mode=="quit":
        quitting()
    if mode=="reboot":
        reboot()
    if mode=="delete the waypoint":
        wpt_delete()
    if mode=="connect gps":
        SERgps("yes")
    
def noaction(): # Action to be performed if NO button is clicked
    if mode=="connect gps":
        SERgps("no")
    else:
        window_ynmenu.hide()

def SERgps(answer):
    global SERmode
    if answer=="yes":
        SERmode=True
    else:
        SERmode=False
    window_ynmenu.hide()

# Show single data  
def single_show(button_clicked):
    global mode, counting
    # Generic function opening all windows with a single data feed
    mode=str(button_clicked)
    print("mode = " + str(mode))
    if mode=="stop":
        counting=0
    but_single.text=" "
    but_single.text_size=but_text_bigsize
    window_single.show()

def single_hide():
    #resetting Single Window to default settings
    global mode
    if mode=="BO":
        display_adjust("off")
    else:
        mode=" "
    but_single.text_size=but_text_bigsize # reset properties
    but_single.text_color=colorfor
    but_single.text=" "
    window_single.hide()

# Keyboards
def keyboard(txt): #handling keyboard inputs
    global dest,mode,nums,londes,latdes
    keys=key_input.value #read text in box
    if txt=="OK":
        txt=""
        if mode=="wptnew":
            mode="wptnewlat"
            londes=0
            latdes=0
#            num_title.value="Latitude (deg.dec)"
            num_input.value=""
#            nums=None
            numboard("")
#            window_num.show()
        window_key.hide()
    if txt=="del":
        txt=""
        if len(keys)>0:
            namelen=len(keys)-1
            keys=keys[:namelen]
    else:
        keys=keys+txt #add the new character and update box
    key_input.value=keys
    if mode=="wptnew":
        dest=keys
   
def numboard(txt): #handling numboard inputs
    global londes,latdes,mode,list_wpts, wptlist,downcount
    nums=num_input.value #read text in box
    window_num.show()
    if txt=="OK":
        if mode=="wptnewlon":
            londes=float(nums)
            list_wpts.append(dest) # add new destination to list box
            wptlist.append(dest) # add new destination to box-array
            wpts.append([dest,latdes,londes]) # add new destination to wpt-array
            # Insert function here to update CSV-file from wpt-array
            with open('waypoints.csv',"a") as f:
                f.write(str(dest) + "," + str(latdes) + "," + str(londes) + "\n")
            nums=""
            window_num.hide()
        if mode=="wptnewlat":
            latdes=float(nums)
            mode="wptnewlon"
#            num_title.value="Longitude (deg.dec)"
            #window_num.show()
        if mode=="down":
            downcount=int(float(nums)*60)
            single_show(mode)
            window_num.hide()
        #else:
        #    window_num.hide()
        nums=""
        txt=""
    if txt=="del":
        txt=""
        if len(nums)>0:
            namelen=len(nums)-1
            nums=nums[:namelen]
    else:
        nums=nums+txt #add the new character and update box
    num_input.value=nums
    if mode=="wptnewlat":
        num_title.value="Latitude (deg.dec)"
        #latdes=float(nums)
    if mode=="wptnewlon":
        num_title.value="Longitude (deg.dec)"
        #londes=float(nums)
    if mode=="down":
        num_title.value="Countdown"
#        single_show(mode)
#        window_num.hide()   

# *************************   TIMERS   *********************************

def UTZ_set(zone): #Adjusting time difference according to UTC
    global TIMEZ
    TIMEZ=TIMEZ+zone
    text_utz.value="Time difference to UTC = " + str(TIMEZ)
    setsave()
    #window_utz.show()

def downcounter(t):
    global downcount, mode
    mode="down"
    if t=="man":
#        window_num.show()
        numboard("")
    else:
        downcount=int(t)*60
        single_show(mode)

def racing():
    global racecount,racecountdown,but_race_color,but_race_text,but_race,but_raceup,but_racedown,mode
    #= Race countdown form
    mode="race"
    window_race = Window(app, title="Race")
    window_race.tk.attributes("-fullscreen", True)
    window_race.text_size=but_text_size
    but_race = PushButton(window_race, command=window_race.hide, height=but_height-3, width="fill")
    but_raceup = PushButton(window_race, command=racedown, text="▼", width=11, height=but_height-2, align="right")
    but_racedown = PushButton(window_race, command=raceup, text="▲", width=11, height=but_height-2, align="left")
    racecountdown=True
    racecount=300 #start race timer at 5 mins
    but_race.text=" "
    window_race.show()

def racedown():
    global racecount
    racemin=int(time.strftime("%M", time.gmtime(racecount)))
    racecount=(racemin*60)+1
    
def raceup():
    global racecount
    racemin=int(time.strftime("%M", time.gmtime(racecount)))+1
    print(racemin)
    racecount=racemin*60+1
    
def timer_update():
    global counting,racecountdown,homise
    global GPSUTC,GPSdate,GPSspeed,GPScourse,GPSNS,GPSEW,latnow,lonnow,latnowdms,lonnowdms,TTG,ETA,UTZ,UTCOS
    global mode, but_text_bigsize, but_text_medsize
    global tempin, tempout, pressure, altitude, seapressure,humidity
    global racecount,but_race_color,but_race_text,but_race,but_raceup,but_racedown,downcount
    global tripdistance,tripcount,triptime,latint,lonint,tripaver,tripinterval,latsec,lonsec,tripsecelapsed,tripsec
    global navlog,DTW,BRG,AVSlog,AVSlat,AVSlon
    global logfile_created,UDPupdate,colorfor,colorback

#   Updating single display depending on function selected in menus
    but_single.text=str(mode) # Show mode if there is no data
    counting=counting+1 #seconds
    UDPupdate-=1 #counting down UDP update if not reset by UDP loop
    ms=time.strftime("%M:%S", time.gmtime(counting)) #stop watch display as M+S
    #dm=time.strftime ("%A\n" + "%d " + "%B") #displaying the actual date

    if latnow != None: #Functions that will only run when GPS is ready
 #       if logfile_created==False:
 #           log_create()
 #           logfile_created=True

        if AVSlog==False: # Functions running once when GPS is ready
            AVSlat=latnow
            AVSlon=lonnow
            UTCOS = "20" + str(GPSdate)[4:] + "-" + str(GPSdate)[2:4] + "-" + str(GPSdate)[0:2] + " " + str(GPSUTC)[0:2] + ":" + str(GPSUTC)[2:4] + ":" + str(GPSUTC)[4:6] #UTC time formatted to use for OS clock
            if OSplatform=="Linux":
                subprocess.Popen(["sudo", "date", "-s", UTCOS])
            but_trip_start.enabled=True
        AVSlog=True
        AVSupdate()
        if latdes != None:
            DTW=WPTdistance(latnow,lonnow,latdes,londes) #calculate distance to waypoint in nm if GPS is live and a destination is selected
            DTW=str(DTW)[0:4]
            TTGsec=int((float(DTW))*3600/GPSspeed)# Find Time-to-go in seconds. Replace GPSspeed with AVS
            TTG=str(timedelta(0,TTGsec))
            BRG=float(WPTbearing(latnow,lonnow,latdes,londes)) #calculate bearing to waypoint
            timenow=datetime.now()
            ETA=timenow+timedelta(0,TTGsec)
            
        if triplog==True:
            tripsec=float(WPTdistance(latnow,lonnow,latsec,lonsec))
            tripsecelapsed=tripsec+tripsecelapsed
            latsec=latnow
            lonsec=lonnow
            tripcount=tripcount+1
            triptime=triptime+1 #elapsed total time in secs
            if tripcount==tripinterval:
                tripdelta=WPTdistance(latnow,lonnow,latint,lonint)
                tripdistance=tripdistance+float(tripdelta)
                latint=latnow
                lonint=lonnow
                log_update() # append current log data to log file
                tripcount=0
    if mode=="tIN":
        #if BMP280import==True:
        #    tempin = '{:4.1f}'.format(measurebmp.get_temperature())
        but_single.text=str(tempin) # + " °C"
    if mode=="hPa":
        #if BMP280import==True:
        #    pressure = '{:4.0f}'.format(measurebmp.get_pressure())
        but_single.text=str(pressure) # + " hPa"  
    if mode=="tOUT":
        #if DHT22import==True:
#            DHT_SENSOR = Adafruit_DHT.DHT22
#            DHT_PIN = 4
        #    humidity, tempout = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        #    tempout = '{:4.1f}'.format(tempout)
        but_single.text=str(tempout) # + " °C"
    if mode=="HUM":
        #if DHT22import==True:
#            DHT_SENSOR = Adafruit_DHT.DHT22
#            DHT_PIN = 4
        #    humidity, tempout = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        #    humidity = '{:2.0f}'.format(humidity)
        but_single.text=str(humidity) + " %"     
    if mode=="dash":
        dashboard_update()
    if mode=="gpsall":
        but_single.text_size=but_text_medsize-20
        but_single.text=str(latnowdms)+ str(GPSNS) + "\n" + str(lonnowdms) + str(GPSEW)  + "\n" + "Speed " + str(GPSspeed) + "\n" + "Course " + str(GPScourse)
    if mode=="gpspos":
        but_single.text_size=but_text_medsize
        but_single.text=str(latnowdms) + str(GPSNS) + "\n" + str(lonnowdms) + str(GPSEW) 
    if mode=="gpsspeed": # current speed in nm as fetched from GPS
        but_single.text=str(GPSspeed)
    if mode=="gpshead":
        if str(GPScourse)[2:3]==".":
            but_single.text=str(GPScourse)[0:2]
        else:
            but_single.text=str(GPScourse)[0:3]
    if mode=="DEP": # current depth
        but_single.text='{:3.1f}'.format(float(DEP)) #str(DEP)
    if mode=="TWS": # true wind speed
        but_single.text='{:3.1f}'.format(TWS) #str(TWS)
    if mode=="TWD": # true wind angle
        but_single.text=str(int(TWD)).zfill(3) #(TWD)
    if mode=="STW": # speed through water
        but_single.text='{:3.1f}'.format(float(STW)) #str(STW)
    if mode=="TSE": # sea temp
        but_single.text=str(TSE)
    if mode=="stop":
        but_single.text=ms
    if mode=="down":
        doc=time.strftime("%H:%M:%S", time.gmtime(abs(downcount))) # make the counter positive so it counts up after 0 and convert to time format
        if downcount<0:
            but_single.text_color="red"
        else:
            but_single.text_color=colorfor
        if downcount<3600:
            doc=time.strftime("%M:%S", time.gmtime(abs(downcount)))
        but_single.text=str(doc)
        downcount-=1
    if mode=="time":     
        but_single.text_size=but_text_medsize
        but_single.text="UTC " + GPSUTC[0:2] + ":" + GPSUTC[2:4] + "\n" + "UTZ " + UTZ[0:2] + ":" + UTZ[2:4]
    if mode=="utc":     
        but_single.text=GPSUTC[0:2]+":"+GPSUTC[2:4] #UTC hours and minutes separated by :
    if mode=="utz":
        but_single.text=UTZ[0:2]+":"+UTZ[2:4] #UTZ hours and minutes separated by :
    if mode=="date":
        but_single.text_size=but_text_medsize+40
        but_single.text=str(dayname)+ "\n" + str(GPSdate)
    if mode=="DTW":
        but_single.text=str(DTW)[0:5] # Chopping off some small digits
    if mode=="navbear":
        but_single.text=str(int(BRG)).zfill(3)
    if mode=="navttg": #
        if len(TTG)>9:
            TTGarray=TTG.split(",")
            TTGtext=str(TTGarray [0]) + "\n" + str(TTGarray [1])
            but_single.text_size=but_text_medsize
        else:
            TTGtext=TTG
            but_single.text_size=but_text_medsize+20
        but_single.text=TTGtext
    if mode=="naveta": #  
        but_single.text_size=but_text_medsize
        but_single.text=(str(ETA)[:10] + "\n" + str(ETA)[11:19])
    if mode=="MOBnow": #
        but_single.text_size=but_text_medsize
        but_single.text="MOB" + "\n" + str(DTW)[0:5] + "\n" + str(BRG)
    if mode=="tripdist":
        but_single.text=str(tripsecelapsed)[:5]
    if mode=="triptime":
        tt=time.strftime("%H:%M:%S", time.gmtime(triptime)) #elapsed time as HMS
        but_single.text_size=but_text_medsize+20
        but_single.text=tt
    if mode=="tripaver":
        tripaver=3600*tripsecelapsed/triptime
        but_single.text=str(tripaver)[:4]
    if mode=="race":        
        if racecountdown==True:
            racecount=racecount-1
            but_race.text_size=but_text_bigsize
            but_race.text_color="red"
            but_race_text=time.strftime("%M:%S", time.gmtime(racecount))
            but_race.text=but_race_text
        else:      
            racecount=racecount+1
            but_race.height="fill"
            but_raceup.visible=False
            but_racedown.visible=False
            but_race.text_color="green"
            but_race_text=time.strftime("%M:%S", time.gmtime(racecount))
            but_race.text=but_race_text
        if racecount==0:
            racecountdown=False      
#    if UDPupdate==0:
#        colorfor="red"
#        display_update()
#    if UDPupdate>0:
#        display_posneg("u")
    
# *******************   DISPLAY CONTROL  *******************
def display_on():
    global display_brightness
    display_brightness=70
    #pwm.ChangeDutyCycle(display_brightness)
    setsave()

def display_adjust(bri):
    # function to adjust display brightness according to display type
    global display_brightness,pwm

    if bri=="on":
        display_brightness=70
    
    if bri=="off":
        if display_brightness>0:
            display_brightness=0
        else:
            display_brightness=70
        single_show("BO")
        
    if bri=="+":
        if display_brightness<91:
            if display_brightness==1:
                display_brightness=10
            display_brightness=display_brightness+10

    if bri=="-":
        if display_brightness>9:
            display_brightness=display_brightness-10
            if display_brightness==0:
                display_brightness=1        
                
    if bri=="100":    
        display_brightness=100

    if screen_width==720:
        print("assuming PiTFT 3.5'' display")
        pwm.ChangeDutyCycle(display_brightness)

    if screen_width==800:
        print("assuming RPi 7'' display: 0<brightness<255")
        RPibrightness=int(255*display_brightness/100)        
        #subprocess.run(['sudo','sh','-c','echo "128" > /sys/class/backlight/rpi_backlight/brightness'])
        subprocess.run(['sudo','sh','-c','echo ' + str(RPibrightness) + ' > /sys/class/backlight/rpi_backlight/brightness'])
#        subprocess.run(['sudo','sh','-c','echo ', "128", ' > /sys/class/backlight/rpi_backlight/brightness'])

    if screen_width==1920:
        print("assuming HDMI display - no adjustment of brightness possible")

#    else:
#        print("assuming other display - no adjustment of brightness possible")

    setsave()

def display_update():
    # Update displays after color change (pos/neg)
    app.text_color=colorfor
    app.bg=colorback    
    '''
    window_avs.text_color=colorfor
    window_avs.bg=colorback
    window_racecountdown.text_color=colorfor
    window_racecountdown.bg=colorback
    window_GPS.text_color=colorfor
    window_GPS.bg=colorback
    window_key.text_color=colorfor
    window_key.bg=colorback
    window_met.text_color=colorfor
    window_met.bg=colorback
    window_met_graph.text_color=colorfor
    window_met_graph.bg=colorback
    window_nav.text_color=colorfor
    window_nav.bg=colorback
    window_num.text_color=colorfor
    window_num.bg=colorback
    window_service.text_color=colorfor
    window_service.bg=colorback
    window_settings.text_color=colorfor
    window_settings.bg=colorback
    window_single.text_color=colorfor
    window_single.bg=colorback
    window_status.text_color=colorfor
    window_status.bg=colorback
    window_system.text_color=colorfor
    window_system.bg=colorback    
    window_trip.text_color=colorfor
    window_trip.bg=colorback
    window_timer.text_color=colorfor
    window_timer.bg=colorback
    window_utz.text_color=colorfor
    window_utz.bg=colorback
    window_wpts.text_color=colorfor
    window_wpts.bg=colorback
'''

def display_posneg(n):
    global posmode,colorfor,colorback
    if n=="p":
        if posmode==False:
            posmode=True
        else:
            posmode=False
    if posmode==True:
        colorfor="black"
        colorback="white"
    else:
        colorfor="white"
        colorback="black"
    if n=="p": # if posneg is changed from panel
        display_update()
#    if n=="u": # function called from UDP check when signal is present (UDPupdate > 0)
#        display_update()
    setsave()

def PiTFT():
# Initializing PiTFT display brightness
    global pwm
    if gpioimport==True:
        try:
            #Setting STMPE control 'not active' as the STMPE GPIO overrides the PWM output on PIN 18.
            subprocess.run(['sudo','sh','-c','echo "0" > /sys/class/backlight/soc\:backlight/brightness']) 
            GPIO.setup(18, GPIO.OUT) # Set pin 18 as output pin
            pwm = GPIO.PWM(18, 100) # Set PWM to pin 18 and cycling frequency to 100
            pwm.start(display_brightness)
        except:
            print("RPi.GPIO import error")
            gpioimport=False

##############################################################################################################

def window_dash_click():
    global mode,dashCourseUp
    if dashCourseUp==False:
        dashCourseUp=True
        dashboard_update()
    else:
        dashCourseUp=False
        window_dash.hide()

def dashboard():
    global mode,drawing_angle_offset,dashCourseUp
    #Updating the dashboard    
    dashCourseUp=False
    mode="dash"
    window_dash.show()
    dashboard_update() # for immediate update of the Dashboard

def dashboard_update():
    # Function called from the timer to update values in the dashboard window once per second

    BRG_color="cyan"
    COG_color="blue"
    TWD_color="orange"
    if AWA>=0:
        AWA_color="green"
    else:
        AWA_color="red"
    
    dash_text_value_color=colorfor #"black"
    dash_text_title_color=colorfor #"blue"
    dash_drawing_text_size=int(screen_height/25)
    XYoffset=int(dash_drawing_text_size/2)
    dash_drawing_text_color=colorfor
    dash_circle_color="grey"
    inner_circle=int(screen_height/12)    
    dash_text_title_AWA.value="AWA"
    dash_text_title_AWA.text_color=dash_text_title_color
    dash_text_title_AWA.text_size = dash_box_text_small

    dash_text_value_AWA.value=str(int(float(abs(AWA)))).zfill(3)
    dash_text_value_AWA.text_color=AWA_color
    dash_text_value_AWA.text_size = dash_box_text_large

    dash_text_title_AWS.value="AWS"
    dash_text_title_AWS.text_color=dash_text_title_color
    dash_text_title_AWS.text_size = dash_box_text_small

    dash_text_value_AWS.value='{:3.1f}'.format(AWS)
    dash_text_value_AWS.text_color=dash_text_value_color
    dash_text_value_AWS.text_size = dash_box_text_large

    dash_text_title_BRG.value="BRG"
    dash_text_title_BRG.text_color=dash_text_title_color
    dash_text_title_BRG.text_size = dash_box_text_small

    dash_text_value_BRG.value=str(int(float(BRG))).zfill(3)
    dash_text_value_BRG.text_color=BRG_color
    dash_text_value_BRG.text_size = dash_box_text_large

    dash_text_title_COG.value="COG"
    dash_text_title_COG.text_color=dash_text_title_color
    dash_text_title_COG.text_size = dash_box_text_small
 
    dash_text_value_COG.value=str(int(COG)).zfill(3)
    dash_text_value_COG.text_color=COG_color
    dash_text_value_COG.text_size = dash_box_text_large

    dash_text_title_DEP.value="DEPTH"
    dash_text_title_DEP.text_color=dash_text_title_color
    dash_text_title_DEP.text_size = dash_box_text_small

    dash_text_value_DEP.value='{:3.1f}'.format(float(DEP))
    dash_text_value_DEP.text_color=dash_text_value_color
    dash_text_value_DEP.text_size = dash_box_text_large

    dash_text_title_DTW.value="DTW"
    dash_text_title_DTW.text_color=dash_text_title_color
    dash_text_title_DTW.text_size = dash_box_text_small

    if float(DTW)<1000:
        dash_text_value_DTW.value='{:3.1f}'.format(float(DTW))
    else:
        dash_text_value_DTW.value=str(DTW)[:4]
    dash_text_value_DTW.text_color=dash_text_value_color
    dash_text_value_DTW.text_size = dash_box_text_large

    dash_text_title_SOG.value="SOG"
    dash_text_title_SOG.text_color=dash_text_title_color
    dash_text_title_SOG.text_size = dash_box_text_small

    dash_text_value_SOG.value='{:3.1f}'.format(float(SOG))
    dash_text_value_SOG.text_color=dash_text_value_color
    dash_text_value_SOG.text_size = dash_box_text_large

    dash_text_title_STW.value="STW"
    dash_text_title_STW.text_color=dash_text_title_color
    dash_text_title_STW.text_size = dash_box_text_small

    dash_text_value_STW.value='{:3.1f}'.format(float(STW))
    dash_text_value_STW.text_color=dash_text_value_color
    dash_text_value_STW.text_size = dash_box_text_large

    dash_text_title_TWD.value="TWD"
    dash_text_title_TWD.text_color=dash_text_title_color
    dash_text_title_TWD.text_size = dash_box_text_small

    dash_text_value_TWD.value=str(int(float(TWD))).zfill(3)
    dash_text_value_TWD.text_color=TWD_color
    dash_text_value_TWD.text_size = dash_box_text_large

    dash_text_title_TWS.value="TWS"
    dash_text_title_TWS.text_color=dash_text_title_color
    dash_text_title_TWS.text_size = dash_box_text_small

    dash_text_value_TWS.value='{:3.1f}'.format(TWS)
    dash_text_value_TWS.text_color=dash_text_value_color
    dash_text_value_TWS.text_size = dash_box_text_large

    screen_centerX=screen_width/2-dash_column_width
    screen_centerY=screen_height/2
    dash_drawing_width=screen_width-2*dash_column_width
    dash_drawing_heigth=screen_height

    # Adjust for screen format and resolution
    if dash_drawing_width>dash_drawing_heigth:
        circle_radius=(screen_height/2) #400
    else:
        circle_radius=dash_drawing_width/2
    
    dash_drawing.clear() # wipe screen before drawing update
    dash_drawing.oval(screen_centerX-circle_radius, screen_centerY-circle_radius, screen_centerX+circle_radius, screen_centerY+circle_radius, color=dash_circle_color, outline=True)
    dash_drawing.oval(screen_centerX-circle_radius+inner_circle, screen_centerY-circle_radius+inner_circle, screen_centerX+circle_radius-inner_circle, screen_centerY+circle_radius-inner_circle, color=colorback, outline=True)

    # Print text based on COG angle used for course up display
    compass_direction=""
    if dashCourseUp==True:
        drawing_angle_offset=COG #Offset angle in degrees = COG Used for Course Up mode
        compass_direction="Course up"
    else:
        drawing_angle_offset=0 # North up
        compass_direction="North up"
    ETAstring=("ETA " + str(ETA)[:10] + " " + str(ETA)[11:16])
    UTCstring=("UTC " + str(GPSUTC)[:2] + ":" + str(GPSUTC)[2:4])
    dash_drawing.text(10, 10,compass_direction,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts
    dash_drawing.text(screen_centerX+circle_radius-2*inner_circle, 10,UTCstring,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts
    dash_drawing.text(10,screen_height-2*int(dash_drawing_text_size),dest,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts
    dash_drawing.text(10,screen_height-int(dash_drawing_text_size),ETAstring,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts

    # Create compass
    compass_corner=["N","W","S","E"]
    for V in range(len(compass_corner)):
        drawing_angle_offset_rad=math.radians(90+float(drawing_angle_offset)) # convert angle deg to radians and rotate sin/cos relation 90 degrees counter clockwise so north is up
        CompassX=math.cos(drawing_angle_offset_rad)*(circle_radius-inner_circle+2*XYoffset)
        CompassY=math.sin(drawing_angle_offset_rad)*(circle_radius-inner_circle+2*XYoffset)
        # Print a line from center and to compass corner
        dash_drawing.line(screen_centerX,screen_centerY,screen_centerX+CompassX,screen_centerY-CompassY, color=dash_circle_color, width=2) 
        # Print the compass corners in the compass ring
        dash_drawing.text(screen_centerX+CompassX-XYoffset, screen_centerY-CompassY-1.5*XYoffset,compass_corner[V],color=dash_drawing_text_color,size=dash_drawing_text_size) # Set compass corner texts
        drawing_angle_offset=drawing_angle_offset+90 # Change angle for next compass corner

    # Paint colored lines for all known directions
    drawing_angles=[BRG,COG,(COG+AWA),TWD]
    drawing_angle_colors=[BRG_color, COG_color, AWA_color, TWD_color]
    for a in range(len(drawing_angles)):
        angle_rad=math.radians(90+drawing_angle_offset-float(drawing_angles[a])) # convert angle deg to radians
        X=math.cos(angle_rad)*circle_radius
        Y=math.sin(angle_rad)*circle_radius
        dash_drawing.line(screen_centerX,screen_centerY,screen_centerX+X,screen_centerY-Y, color=drawing_angle_colors[a], width=5)

#def metgraph():
    #global metpng
    #metpng="met.png"
#    metpng="//192.168.0.105/PiShare/met.png"
    #graphurl = "http://" + str(UDPaddress) + "/met.png" 
    #metpicture.show()
    #window_met_graph.show()
    #window_met_graph.when_clicked=window_met_graph.hide()

    #metpng = curl -O graphurl
    #metpng = curl -O http://192.168.0.105/met.png
    #metpng = curl -O 192.168.0.105/met.png

# *****************   Navigation   ****************************
        
def GPSread():
    # read and split GPS data from serial port or UDP
    # format:  $GPRMC,225446,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3,E*68
    global GPSUTC,GPSdate,GPSspeed,GPScourse,GPSNS,GPSEW,SOG,COG
    global ser,gpsdata,UTZ,UTZhours,TIMEZ,UTCOS,GPSNS,GPSEW,dayname,UDPupdate,daynumber
    global latnow,lonnow,latnowdms,lonnowdms,londegminmin,latdegminmin
    if SERmode==True:  # Fetch GPS data from USB
        gpsdata = ser.readline().decode('ascii', errors='replace') #wait for each full line        
    else:   # Fetch GPS data from UDP
        gpsdata=UDPstring
    if len(str(gpsdata))>8:
        header = gpsdata[3:6] # slicing out the header information (3 letters needed)
        UDPupdate=UDPupdatedef #resetting the UDP timer to default value
    else:
        header="1234567890"
    #print(header)
    if header=="RMC": # the line containing the needed information like position, time and speed etc....
        RMCarray=gpsdata.split(",") #make array according to comma-separation in string
        GPSUTC=(RMCarray [1])
        GPSdate=(RMCarray [9])
        GPSspeed=(float(RMCarray [7])) # knots
        SOG=GPSspeed
        if RMCarray [8]!="":
            GPScourse=(float(RMCarray [8]))
        else:
            GPScourse=0
        COG=GPScourse
        latdegminmin=(RMCarray [3])
        GPSNS=(str(RMCarray [4]))
        latnow=dmm2dec(latdegminmin,GPSNS) #current latitude converted to decimal format
        londegminmin=(RMCarray [5])                
        GPSEW=(str(RMCarray [6]))
        lonnow=dmm2dec(londegminmin,GPSEW) #current longitude converted to decimal format
        latnowdms=dec2dms(float(latnow)) #current position converted to dms format
        lonnowdms=dec2dms(float(lonnow))
        UTZhours=TIMEZ+float(GPSUTC[0:2])
        if UTZhours>23:
            UTZhours=UTZhours-24
        UTZhours=int(UTZhours)
        UTZ=str(UTZhours).zfill(2)+str(GPSUTC)[2:4]
        
        monthname=calendar.month_abbr[int((GPSdate)[2:4])]
        daynames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
#        daynumber=calendar.weekday((int(str(GPSdate)[4:])),int(str(GPSdate)[2:4]),int(str(GPSdate)[0:2]))
#        dayname=daynames[daynumber]

            #Check system clocks:   timedatectl status           
            #Format example: sudo date --set="2015-09-30 10:05:59"            
#            UTCOS = "20" + str(GPSdate)[4:] + "-" + str(GPSdate)[2:4] + "-" + str(GPSdate)[0:2] + " " + str(UTZ)[0:2] + ":" + str(GPSUTC)[2:4] + ":" + str(GPSUTC)[4:6] #Local time formatted to use for OS clock
#            subprocess.Popen(["sudo", "date", "-s", UTCOS])
#            os.system("sudo date -s " % str(UTCOS))
            # subprocess('sudo time --set' % UTCOS)
            # os.system('sudo date -u %s' % UTCOS)
            #os.system('sudo hwclock --set --date=' % UTCOS)
#            os.system('sudo hwclock --systohc') #Set hardware clock

def UDPread():
    global UDPstring,tempin,tempout,pressure,humidity,UDPaddress,TWSmax
    global DEP,TWS,TWD,TWA,TSE,STW,AWA,AWS #Seatalk1

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #reuse socket if program is opened after crash
        sock.bind((UDP_IP, UDP_PORT))
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        UDPaddress=addr[0]
        UDPstring = str(data)[2:] 
        header = UDPstring[3:6] # slicing out the header information (3 letters needed)
        #if header=="RMC":
        #    print(UDPstring)  
        if header=="WEA":
            WEAarray=UDPstring.split(",") #make array according to comma-separation in string
            #print(WEAarray)
            #print(UDPaddress)  
            tempin=(WEAarray [1])
            tempout=(WEAarray [2])
            pressure=(WEAarray [3])
            humidity=(WEAarray [4])
        if header=="DBT":
            DBTarray=UDPstring.split(",") #DBT - Depth Below Transducer
            DEP='{:3.1f}'.format(float(DBTarray[3]))
#        if header=="MWV":
#           MWVarray=UDPstring.split(",") #make array according to comma-separation in string
        if header=="VWR":
            VWRarray=UDPstring.split(",") #VWR - Relative Wind Speed and Angle
            AWA=float(VWRarray[1]) # Wind angle to bow magnitude in degrees
            AWD=VWRarray[2] # Wind direction Left/Right of bow
            if AWD=="R":
                AWA=AWA
            else:
                AWA=-AWA
            #AWA='{:3.1f}'.format(AWA)
            AWS=float(VWRarray[3])*0.514444 # Apparent wind speed (knots) changed to Meters Per Second
            if AWS<0.1:
                AWS=0.1
            #Calculating True wind
            AWA_rad=math.radians(AWA) # convert angle deg to radians
            if AWA_rad==0: # Avoid cos(0)
                AWA_rad=0.1
            SOGms=SOG*0.514444 #Speed over ground in m/s
            TWS=math.sqrt(math.pow(AWS,2)+math.pow(SOGms,2)-2*AWS*SOGms*math.cos(AWA_rad)) # True wind speed
            if TWS>TWSmax:
                TWSmax=TWS
            if TWS<0.1: #Avoid 0 division 
                TWS=0.1
            if AWD=="R":
                TWA=math.degrees(math.acos((AWS*math.cos(AWA_rad)-SOGms)/TWS)) # True wind direction (compass)
            else:
                TWA=math.degrees(-math.acos((AWS*math.cos(AWA_rad)-SOGms)/TWS))
            TWD=COG+TWA
            if TWD<0:
                TWD=360+TWD
            if TWD>=360:
                TWD=TWD-360
            #print("AWA_rad "+str(AWA_rad))            
            #print("AWA "+str(AWA))            
            #print("TWA "+str(TWA))            
            #print("TWD "+str(TWD))
        if header=="MTW":
            MTWarray=UDPstring.split(",") #MTW - Mean Temperature of Water
            TSE=float(MTWarray[1]) #Sea temp
        if header=="VHW":
            VHWarray=UDPstring.split(",") #make array according to comma-separation in string
            STW=(VHWarray[3])

def wpt_nav(wpt_mode):
    # Show Waypoint selector when WPT button is clicked in Navigation menu
    global wptindex,wpts,wptlist,wptscsv,dest,list_wpts,wpts_text_index,latdesdms,latNS,londesdms,lonEW
    dirpath = os.getcwd()
    with open('waypoints.csv', encoding='utf-8') as csvfile: #Open CSV file with waypoints. r is 'raw string' before the path
        list_wpts.clear() #Clearing the box for old wpts each time page is loaded
        wpts = list(csv.reader(csvfile)) #create array with waypoints read from csv file
#        wpts=wptscsv #sort the array alphabetically???
        for w in range (len(wpts)):
            list_wpts.append(wpts[w][0]) #load first column in to the list box
    wptlist=list_wpts.items #Create a support array only with the items loaded to the list box (column 0 in the CSV file)in order to look up index numbers etc
    if dest !="":
        wpts_text_index.value=dest + " " + str(latdesdms) + str(latNS) + " " + str(londesdms) + str(lonEW) #Show destination info at top of menu
    if wpt_mode=="nav": # If called from DEP menu
        but_wpts_edit.text="NEW" # change text in button
        wpts_text_index.value="Select destination"
    if wpt_mode=="del": # If called from SET menu
        but_wpts_edit.text="DEL" # change text in button
        wpts_text_index.value="Delete waypoint"
    window_wpts.show()

def wpt_edit(): # Control button text according to choice in order to create new or delete waypoint
    global mode
    if but_wpts_edit.text=="NEW":
        mode="wptnew"
        key_title.value="New waypoint"
        key_input.value="" # Delete old text if any
        window_key.show()
    if but_wpts_edit.text=="DEL":
        mode="wptdel"
        ynmenu("delete the waypoint")
        
def wpt_delete(): #Delete waypoint
    but_wpts_edit.text=="DEL"
    wptindex=wptlist.index(dest)
#    print(wptindex)
#    print(wpts)
#    print(len(wptlist))
    print("Deleted " + str(wpts[wptindex]))   
    del wpts[wptindex]
    # Write updated array to file
    with open('waypoints.csv', "w", encoding='utf-8') as f:
        for w in range(len(wptlist)-1):
            f.write(str(wpts[w][0]) + "," + str(wpts[w][1]) + "," + str(wpts[w][2]) +"\n")
    window_wpts.hide()
    window_ynmenu.hide()

def wpt_new(): # New waypoint
    but_wpts_edit.text=="NEW"

def destination(): #Select waypoint
    # Find lon+lat when destination is clicked in list box
    global wptindex,latdes,londes,latdesdms, wpts, wptlist, dest,list_wpts,wpts_text_index,latdesdms,latNS,londesdms,lonEW
    dest=list_wpts.value #Destination = the waypoint currently selected
    wptindex=wptlist.index(dest) #determines index number in support array for use in list box to select the selected destinations position
    # print (dest + " = index " + str(wptindex))
    latdes=(wpts[wptindex][1]) #Looks up corresponding latitude as DEGDEC in array
    latdesdms=dec2dms(latdes) #make a dms-version
    londes=(wpts[wptindex][2]) #Looks up corresponding longitude as DEGDEC in array
    londesdms=dec2dms(londes) #make a dms-version
    quadrant()
    wpts_text_index.value=dest + " " + str(latdesdms) + str(latNS) + " " + str(londesdms) + str(lonEW) #Show destination info at top of menu    

def quadrant():
    #Determine which quadrant we are going to
    global latNS,lonEW
    latNS="S" #Default Southern hemisphere = negative number
    if float(latdes)>0:
        latNS="N"
    lonEW="W" #Default western = negative number
    if float(londes)>0:
        lonEW="E"

def MOB():
    global mode,dest,latdes,londes,latNS,lonEW
    #Man Over Board
    mode="MOBnow"
    dest ="MOB"
    latdes=latnow
    londes=lonnow
    quadrant()
    single_show("MOBnow")
    
def trip_start():
    global tripcount,triptime,latint,lonint,latnow,lonnow,latdep,londep,triplog,but_trip_00,but_trip_10,tripdistance,latsec,lonsec,tripsecelapsed,tripstart,navlog
    #Start trip
    triptime=0
    tripcount=0
    tripdistance=0
    tripsecelapsed=0
    latint=latnow
    lonint=lonnow
    latsec=latnow
    lonsec=lonnow
    latdep=latnow
    londep=lonnow
    tripstart=str(datetime.now())
    triplog=True
    but_trip_start.disable()
    but_trip_start.text_color="red"
    but_trip_stop.enable()
    log_create()
    
def trip_stop():
    global tripdistance,tripcount,triptime,latint,lonint,latnow,lonnow,but_trip_00,but_trip_10,triplog

    #Stop trip
    triplog=False
    but_trip_start.enable()
    but_trip_start.text_color=colorfor
    but_trip_stop.disable()
#    but_trip_stop = PushButton(window_trip, command=trip_start, text="START", width=but_width, height=but_height, grid=[0,1])

def wptscroll(y): #Control scrolling in waypoint list box with up+down buttons
    global wptindex, wpts, wptlist, wptscrolling
    wptscrolling = wptscrolling+y
    if wptscrolling>len(wpts):
        wptscrolling=len(wpts)
    if wptscrolling<0:
        wptscrolling=0       
    list_wpts._listbox.tk.see(wptscrolling)
    # print ("mouse scroll")

def dec2dms(angle):
    # convert deg.dec positions (Google map format) to Degree/Minutes/Seconds
    posangle=float(angle) #converts to number format
    posangle=abs(posangle) #converts to positive (if negative) format
    degint=math.floor(posangle)
    degdeg=str(degint).zfill(2)
    degint=float(degdeg)
    posdec=posangle-degint
    posmin=posdec*60
    minint=math.floor(posmin)
    possec=posmin-minint
    possec=possec*60*10000
    possec=str(possec)[:2]
    return(str(degdeg) + "°" + str(minint)+ "'" + str(possec) + "''")

def dmm2dec(dmm,nsew):
    # convert received GPS positions DegreesMinutes.Minutedecimals (DDDMM.MMMM) to deg.dec positions
        if dmm=="":
            dmm=0.0 # used while waiting for GPS to inject a string
        dmm=str(dmm)
        dmmsplit=dmm.split(".") #number left of . are deg+min. Right of . are minute decimals
        posdegmin=dmmsplit[0] # first row=deg+mins
        posdegminlength=len(posdegmin)# 4 or 5 numbers: latitude always 4 numbers (DDMM) and longitude always 5 (DDDMM)
        posmindec=0
        posdeg2dec=0
        if posdegminlength==4: # it's a latitude (nsew=N or nsew=S)
                posdeg2dec=float(posdegmin[0:2])
                posmindec=float(dmm[2:])
        if posdegminlength==5: # it's a longitude (nsew=E or nsew=W)
                posdeg2dec=float(posdegmin[0:3])
                posmindec=float(dmm[3:])
        posmin2dec=float(posmindec)/60 # convert minutes to decimal
        posdec=posdeg2dec+posmin2dec#+posmindec2dec       
        if nsew=="S" or nsew=="W":
                posdeg=posdeg*(-1)
        return (posdec)
  
def WPTdistance(lat1,lon1,lat2,lon2):
    # calculate distance between two coordinates in degrees

    lat1rad=math.radians(float(lat1)) # convert to radians
    lon1rad=math.radians(float(lon1)) # convert to radians
    lat2rad=math.radians(float(lat2)) # convert to radians
    lon2rad=math.radians(float(lon2)) # convert to radians

    latdelta = abs(lat1rad-lat2rad)
    londelta = abs(lon1rad-lon2rad)
    R = 6371000 # Earth radius in meters
    a=math.sin(latdelta/2) * math.sin(latdelta/2) + math.cos(lat1rad) * math.cos(lat2rad) * math.sin(londelta/2) * math.sin(londelta/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c #in meters
    distance = distance/1852 # Convert to nautical miles
    return(distance)

def WPTbearing(lat1,lon1,lat2,lon2):
    # calculate bearing to selected waypoint from current position

    lat1rad=math.radians(float(lat1)) # convert to radians
    lon1rad=math.radians(float(lon1)) # convert to radians
    lat2rad=math.radians(float(lat2)) # convert to radians
    lon2rad=math.radians(float(lon2)) # convert to radians

    y = math.sin(lon2rad-lon1rad) * math.cos(lat2rad)
    x = math.cos(lat1rad)*math.sin(lat2rad) - math.sin(lat1rad)*math.cos(lat2rad)*math.cos(lon2rad-lon1rad)
    brng = math.atan2(y, x)

    bearing=math.degrees(brng)
    bearing=(bearing+360) % 360
    bearing=str(bearing)
    bearing=bearing[0:3]
    return(bearing)

def AVSupdate():
    global AVSlog,AVSlat,AVSlon,AVS01,AVS10,AVS30,AVS60,navlog,AVScount,AVSinterval
    AVScount=AVScount+1
    # calculating average speeds according to intervals: 1, 10, 30 and 60 minutes
    if AVScount==AVSinterval:
        navleg=WPTdistance(latnow,lonnow,AVSlat,AVSlon)
        navlog.pop(59)
        navlog.insert(0, navleg)    
        AVS01=float(navlog[0])*60
        navlog10=0
        for d in range (10):
            navlog10=navlog10+float(navlog[d])
        AVS10=navlog10*6
        navlog30=0
        for d in range (30):
            navlog30=navlog30+float(navlog[d])
        AVS30=navlog30*2
        navlog60=0
        for d in range (60):
            navlog60=navlog60+float(navlog[d])
        AVS60=navlog60
        AVSlat=latnow
        AVSlon=lonnow
        AVScount=0

def AVSreset():
    # Resetting AVS values in navlog
    navlog=[] # empty navlog
    for w in range (60):
        navlog.append(0) # create 60 empty items 

def log_create():
    global logname
    #Creating new file after GPS time is received and inserting header
    log_header = ["Date","UTC","UTZ", "SOG","COG","tripdistance","triptime(min)","latdep","londep","Latitude","Longitude","latdes","londes","destination","tempin","tempout","humidity","HPa","AWA","AWS","TWD","TWS","BRG","DTW","Depth","SEA"]
    if OSplatform=="Linux":
        logname='/home/pi/' + str(GPSdate) + "-" + str(UTZ) + '.csv'
    else:
        logname='C:\\Users\\bonde\\Dropbox\\Code\\Python\\MAIA\\' + str(daynumber) + "-" + str(UTZ) + '.csv' 
    with open(logname,"w") as f:
        f.write(",".join(str(value) for value in log_header)+ "\n")
#    print ("New log created: " + str(logname))

def log_update(): # save data to logfile
    global tempin,tempout,pressure,humidity
    logtripdis= '{:4.1f}'.format(tripdistance)
    if UDPmode==False:
        tempin = '{:4.1f}'.format(measurebmp.get_temperature())
        pressure = '{:4.0f}'.format(measurebmp.get_pressure())
        if DHT22import==True:
            humidity, tempout = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        humidity= '{:4.1f}'.format(humidity)
        tempout= '{:4.1f}'.format(tempout)
    logtriptime= triptime/60
    log_data = [GPSdate,GPSUTC,UTZ, GPSspeed,GPScourse,logtripdis,logtriptime,latdep,londep,latnow,lonnow,latdes,londes,dest,tempin,tempout,humidity,pressure,AWA,AWS,TWD,TWS,BRG,DTW,DEP,TSE]
    with open(logname,"a") as f:
        f.write(",".join(str(value) for value in log_data)+ "\n")

def setsave():
    with open("maia.csv","w") as m:
        m.write("TIMEZ" + "=" + str(TIMEZ)) 
        m.write("display_brightness" + "=" + str(display_brightness)) 
        m.write("posmode" + "=" + str(posmode)) 

def setload():
    global TIMEZ,display_brightness,posmode
    try:        
        with open('maia.csv', encoding="latin-1", newline='') as csvfile: # Open CSV file with settings
            settingsfile = list(csv.reader(csvfile, delimiter='=')) # Create list from csv file
#            maiasettings=[]
#            for m in maiasettings[0]:
#                maiasettings.append(str(settingsfile[0][i]))
        TIMEZ=int(settingsfile[0][1])
        UTZ_set(0)
        print("TIMEZ loaded: " + str(TIMEZ))
        display_brightness=int(settingsfile[0][2])
        #pwm.ChangeDutyCycle(display_brightness)
        print("display_brightness loaded: " + str(display_brightness))
        posmodestr=str(settingsfile[0][2])
        if posmodestr=="True":
            posmode=True
        else:
            posmode=False
        display_posneg("z")
        print("posmode loaded: " + str(posmode))

    except:
        print("no settings file ")


# ********************************  Exiting ***************************************

def quitting():
    if gpioimport==True:
        GPIO.cleanup()
    window_system.hide()
    app.destroy()

def reboot():
    if gpioimport==True:
        GPIO.cleanup()
    window_system.hide()
    app.hide()
    os.system('sudo shutdown -r now')
        
# *******************************  MENUS  *******************************************

def menu_status_hard():
    # Updating the status window with fresh data about hardware status
    # Max 14 items in each row
    status_list_column=status_list_left # Column for reading hardware data with mypi
    status_list_column.clear()
    status_list_column.append("time " + str(datetime.now())[:10])
    status_list_column.append("" + str(datetime.now())[11:19])
    status_list_column.append("res " + str(screen_width) + "x" + str(screen_height))
    if OSplatform=="Linux": 
        status_list_column.append(mypi.getModel()[:15])
        status_list_column.append(mypi.getModel()[15:])
        status_list_column.append(mypi.platform.platform()[:15])
        status_list_column.append(mypi.platform.platform()[15:30])
        status_list_column.append(mypi.platform.platform()[30:])
        status_list_column.append("rev " + mypi.getRevision())
        status_list_column.append("ser" + mypi.getSerial()[:10])
        status_list_column.append("" + mypi.getSerial()[10:])
        status_list_column.append("python " + mypi.platform.python_version())

        status_list_column=status_list_center
        status_list_column.clear()
        status_list_column.append("SPI " + mypi.getSPI())
        status_list_column.append("I2C " + mypi.getI2C())
        status_list_column.append("NETWORK ")
        status_list_column.append("Bluetooth " + mypi.getBT())
        status_list_column.append("LAN " + mypi.getEthName())
        status_list_column.append("" + mypi.getMAC())
        status_list_column.append("ip " + mypi.getIP())
        status_list_column.append("WiFi:")
        status_list_column.append("" + mypi.getMAC('wlan0'))
        status_list_column.append("ip " + mypi.getIP('wlan0'))

        status_list_column=status_list_right 
        status_list_column.clear()
        status_list_column.append("CPUt " + mypi.getCPUtemp())
        status_list_column.append("GPUt " + mypi.getGPUtemp())
        status_list_column.append("ram" + str(mypi.getRAM()))
        status_list_column.append("dsk" + str(mypi.getDisk()))
        status_list_column.append("CPUspeed " + mypi.getCPUspeed())
        status_list_column.append("uptime " + str(mypi.getUptime()))
    window_status.text_size=but_text_size-16
    window_status.show()

def menu_status_soft():
    # Updating the status window with fresh data from app
    # Max 14 items in each row
    status_list_column=status_list_left # Column for reading hardware data with mypi
    status_list_column.clear()
    status_list_column.append("app ver. " + str(appver))
    status_list_column.append("GPS data" )
    status_list_column.append("Speed " + str(GPSspeed))
    status_list_column.append("Course " + str(GPScourse))
    status_list_column.append("Date " + str(GPSdate))
    status_list_column.append("UTC " + str(GPSUTC)[0:6])
    status_list_column.append("Zone " + str(TIMEZ))
    status_list_column.append("UTZ " + str(UTZ)[0:4])
    status_list_column.append("latgps " + str(latdegminmin))
    status_list_column.append("longps " + str(londegminmin))
    status_list_column.append("latdec " + str(latnow))
    status_list_column.append("londec " + str(lonnow))
    status_list_column.append("Lat " + str(latnowdms) + str(GPSNS))
    status_list_column.append("Lon " + str(lonnowdms) + str(GPSEW))

    status_list_column=status_list_center
    status_list_column.clear()
    status_list_column.append("TRIP" )
    status_list_column.append("Start " + tripstart[:10])
    status_list_column.append("" + tripstart[11:19])
    status_list_column.append("Interval " + str(tripinterval))
    status_list_column.append("Distance " + str(tripdistance)[0:4])
    status_list_column.append("Dest " + str(dest))
    status_list_column.append("lat " + str(latdes))
    status_list_column.append("lon " + str(londes))
    status_list_column.append("depa " + str(latdep))
    status_list_column.append("depo " + str(londep))
    status_list_column.append("log= " + str(triplog))
    status_list_column.append("UTCOS= ")
    status_list_column.append(str(UTCOS)[0:11])
    status_list_column.append(str(UTCOS)[11:])

#    status_list_column.append("tripcount " + str(tripcount))
    
    status_list_column=status_list_right 
    status_list_column.clear()
    #status_list_column.append("serimport " + str(serimport))
    status_list_column.append("ser port " + str(port))
    status_list_column.append("UDPport " + str(UDP_PORT))
    status_list_column.append("gpioimport " + str(gpioimport))
#    status_list_column.append("BMP280 " + str(BMP280import))
    status_list_column.append("TTG " + str(TTG))
    status_list_column.append("TWSmax " + str(TWSmax)[0:4])
    status_list_column.append("AVS01 " + str(AVS01))
    status_list_column.append("AVS10 " + str(AVS10))
    status_list_column.append("AVS30 " + str(AVS30))
    status_list_column.append("AVS60 " + str(AVS60))
    status_list_column.append("AVSlog " + str(AVSlog))

    window_status.text_size=but_text_size-16
    window_status.show()

display_posneg("z")

app = App(title="Marine control panel", layout="grid")#, width=480, height=320)
app.tk.attributes("-fullscreen", True)
#app.tk.configure(cursor='none')
screen_width = app.tk.winfo_screenwidth()
screen_height = app.tk.winfo_screenheight()
if screen_width==720: #PiTFT is 720x480
    PiTFT()
but_width=int(screen_width/95)
if screen_height<=1000:
    but_height=int(screen_height/100)
if screen_height>1000:
    but_height=int(screen_height/130)
#if screen_width>780: 
#    but_width=8
RES=str(screen_width) + " x " + str(screen_height)
print("Resolution is " + str(RES))

# Single data menu
window_single = Window(app, title="single")
window_single.tk.attributes("-fullscreen", True)
but_single = PushButton(window_single, command=single_hide, text=str(mode), width="fill", height="fill")
but_single.text_size=but_text_bigsize
window_single.hide()

# Yes/No menu
window_ynmenu = Window(app, title="ynmenu")
window_ynmenu.tk.attributes("-fullscreen", True)
window_ynmenu.bg=colorback
window_ynmenu.text_color=colorfor
window_ynmenu.hide()
ynbut_width=int(screen_width/65)
text_ynmenu = Text(window_ynmenu, text="?", width="fill", size=but_text_size)
but_ynmenu = PushButton(window_ynmenu, command=yesaction, text="YES", width=ynbut_width, height=but_height, align="left")
but_ynmenu.text_size=but_text_size
but_ynmenu.text_color=but_race_color
but_noynmenu = PushButton(window_ynmenu, command=noaction, text="NO", width=ynbut_width, height=but_height, align="right")
but_noynmenu.text_size=but_text_size

#Keypad
window_key = Window(app, title="Keypad")
window_key.tk.attributes("-fullscreen", True)
window_key.text_size=but_text_size
window_key.hide()
box_key_title = Box(window_key, width="fill", align="top")
key_title = Text(box_key_title, text="Title")
key_title.text_size=but_text_size
box_key_input = Box(window_key, width="fill", align="top")
key_input = Text(box_key_input, align="left")
key_input.text_size=but_text_size
key_width=int(screen_width/300)
key_height=int(screen_height/800)
box_keys1 = Box(window_key, width="fill", align="top")
box_keys = box_keys1 # Helps moving lines with buttons for other configurations
but_key_A = PushButton(box_keys, lambda:keyboard("A"),text="A", width=key_width, height=key_height, align="left")
but_key_B = PushButton(box_keys, lambda:keyboard("B"),text="B", width=key_width, height=key_height, align="left")
but_key_C = PushButton(box_keys, lambda:keyboard("C"),text="C", width=key_width, height=key_height, align="left")
but_key_D = PushButton(box_keys, lambda:keyboard("D"),text="D", width=key_width, height=key_height, align="left")
but_key_E = PushButton(box_keys, lambda:keyboard("E"),text="E", width=key_width, height=key_height, align="left")
but_key_F = PushButton(box_keys, lambda:keyboard("F"),text="F", width=key_width, height=key_height, align="left")
but_key_G = PushButton(box_keys, lambda:keyboard("G"),text="G", width=key_width, height=key_height, align="left")
but_key_H = PushButton(box_keys, lambda:keyboard("H"),text="H", width=key_width, height=key_height, align="left")

box_keys2 = Box(window_key, width="fill", align="top")
box_keys = box_keys2
but_key_I = PushButton(box_keys, lambda:keyboard("I"),text="I", width=key_width, height=key_height, align="left")
but_key_J = PushButton(box_keys, lambda:keyboard("J"),text="J", width=key_width, height=key_height, align="left")
but_key_K = PushButton(box_keys, lambda:keyboard("K"),text="K", width=key_width, height=key_height, align="left")
but_key_L = PushButton(box_keys, lambda:keyboard("L"),text="L", width=key_width, height=key_height, align="left")
but_key_M = PushButton(box_keys, lambda:keyboard("M"),text="M", width=key_width, height=key_height, align="left")
but_key_N = PushButton(box_keys, lambda:keyboard("N"),text="N", width=key_width, height=key_height, align="left")
but_key_O = PushButton(box_keys, lambda:keyboard("O"),text="O", width=key_width, height=key_height, align="left")
but_key_P = PushButton(box_keys, lambda:keyboard("P"),text="P", width=key_width, height=key_height, align="left")

box_keys3 = Box(window_key, width="fill", align="top")
box_keys = box_keys3
but_key_Q = PushButton(box_keys, lambda:keyboard("Q"),text="Q", width=key_width, height=key_height, align="left")
but_key_R = PushButton(box_keys, lambda:keyboard("R"),text="R", width=key_width, height=key_height, align="left")
but_key_S = PushButton(box_keys, lambda:keyboard("S"),text="S", width=key_width, height=key_height, align="left")
but_key_T = PushButton(box_keys, lambda:keyboard("T"),text="T", width=key_width, height=key_height, align="left")
but_key_U = PushButton(box_keys, lambda:keyboard("U"),text="U", width=key_width, height=key_height, align="left")
but_key_V = PushButton(box_keys, lambda:keyboard("V"),text="V", width=key_width, height=key_height, align="left")
but_key_W = PushButton(box_keys, lambda:keyboard("W"),text="W", width=key_width, height=key_height, align="left")
but_key_X = PushButton(box_keys, lambda:keyboard("X"),text="X", width=key_width, height=key_height, align="left")

box_keys4 = Box(window_key, width="fill", align="top")
box_keys = box_keys4
but_key_del = PushButton(box_keys, lambda:keyboard("del"),text="<", width=key_width, height=key_height, align="left")
but_key_Y = PushButton(box_keys, lambda:keyboard("Y"),text="Y", width=key_width, height=key_height, align="left")
but_key_Z = PushButton(box_keys, lambda:keyboard("Z"),text="Z", width=key_width, height=key_height, align="left")
but_key_at = PushButton(box_keys, lambda:keyboard("Æ"),text="Æ", width=key_width, height=key_height, align="left")
but_key_at = PushButton(box_keys, lambda:keyboard("Ø"),text="Ø", width=key_width, height=key_height, align="left")
but_key_dot = PushButton(box_keys, lambda:keyboard("Å"),text="Å", width=key_width, height=key_height, align="left")
but_key_dot = PushButton(box_keys, lambda:keyboard("del"),text="<", width=key_width, height=key_height, align="left")
but_key_ok = PushButton(box_keys, lambda:keyboard("OK"),text="OK", width=key_width, height=key_height, align="left")

#numpad
window_num = Window(app, title="numpad")
window_num.tk.attributes("-fullscreen", True)
window_num.text_size=but_text_size
window_num.hide()
box_num_title = Box(window_num, width="fill", align="top")
num_title = Text(box_num_title, text="Title")
num_title.text_size=but_text_size
box_num_input = Box(window_num, width="fill", align="top")
num_input = Text(box_num_input, align="left")
num_input.text_size=but_text_size #35
num_width=int(screen_width/180) #4
num_height=int(screen_height/250) #2
box_nums1 = Box(window_num, width="fill", align="top")
box_nums = box_nums1 # Helps moving lines with buttons for other configurations
but_num_0 = PushButton(box_nums, lambda:numboard("0"),text="0", width=num_width, height=num_height, align="left")
but_num_1 = PushButton(box_nums, lambda:numboard("1"),text="1", width=num_width, height=num_height, align="left")
but_num_2 = PushButton(box_nums, lambda:numboard("2"),text="2", width=num_width, height=num_height, align="left")
but_num_3 = PushButton(box_nums, lambda:numboard("3"),text="3", width=num_width, height=num_height, align="left")
but_num_4 = PushButton(box_nums, lambda:numboard("4"),text="4", width=num_width, height=num_height, align="left")

box_nums2 = Box(window_num, width="fill", align="top")
box_nums = box_nums2
but_num_5 = PushButton(box_nums, lambda:numboard("5"),text="5", width=num_width, height=num_height, align="left")
but_num_6 = PushButton(box_nums, lambda:numboard("6"),text="6", width=num_width, height=num_height, align="left")
but_num_7 = PushButton(box_nums, lambda:numboard("7"),text="7", width=num_width, height=num_height, align="left")
but_num_8 = PushButton(box_nums, lambda:numboard("8"),text="8", width=num_width, height=num_height, align="left")
but_num_9 = PushButton(box_nums, lambda:numboard("9"),text="9", width=num_width, height=num_height, align="left")

box_nums3 = Box(window_num, width="fill", align="top")
box_nums = box_nums3
but_num_min = PushButton(box_nums, lambda:numboard("-"),text="-", width=num_width, height=num_height, align="left")
but_num_dot = PushButton(box_nums, lambda:numboard("."),text=".", width=num_width, height=num_height, align="left")
but_num_del = PushButton(box_nums, lambda:numboard("del"),text="<", width=num_width, height=num_height, align="left")
but_num_ok = PushButton(box_nums, lambda:numboard("OK"),text="OK", width=num_width*2, height=num_height, align="left")

# Computer status - collects all information in one window
window_status = Window(app, title="status")
window_status.tk.attributes("-fullscreen", True)
window_status.hide()
status_list_box_width=240
status_list_left=ListBox(window_status, command=window_status.hide, width=status_list_box_width, height="fill", align="left")
status_list_center=ListBox(window_status, command=window_status.hide, width=status_list_box_width, height="fill", align="left")
status_list_right=ListBox(window_status, command=window_status.hide, width=status_list_box_width, height="fill", align="left")

# Dashboard with all info
window_dash = Window(app, title="Dashboard")
window_dash.tk.attributes("-fullscreen", True)
window_dash.tk.configure(cursor='none')
window_dash.hide()
window_dash.when_clicked=window_dash_click

dash_column_width=int(screen_width/5.3)
dash_box_width=dash_column_width #150
dash_box_heigth=int(screen_height/5) #95
dash_box_text_large=int(screen_height/11) #44
dash_box_text_small=int(screen_height/34) #14
dash_text_title_align="top"
dash_text_value_align="top"

dash_box_left = Box(window_dash, width=dash_column_width, height="fill", align="left",border=0, layout="auto")
dash_box_right = Box(window_dash, width=dash_column_width, height="fill", align="right",border=0, layout="auto")
dash_box_center = Box(window_dash, width="fill", height="fill", layout="auto")
dash_drawing = Drawing(dash_box_center, width="fill", height="fill")

dash_box=dash_box_left
dash_box_STW = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_STW = Text(dash_box_STW, text="STW", align=dash_text_title_align)
dash_text_value_STW = Text(dash_box_STW, text=" ", align=dash_text_value_align)

dash_box_SOG = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_SOG = Text(dash_box_SOG, text="SOG", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_SOG = Text(dash_box_SOG, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box_COG = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_COG = Text(dash_box_COG, text="COG", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_COG = Text(dash_box_COG, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box_BRG = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_BRG = Text(dash_box_BRG, text="BRG", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_BRG = Text(dash_box_BRG, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box_DTW = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_DTW = Text(dash_box_DTW, text="DTW", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_DTW = Text(dash_box_DTW, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box=dash_box_right
dash_box_AWS = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_AWS = Text(dash_box_AWS, text="AWS", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_AWS = Text(dash_box_AWS, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box_TWS = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_TWS = Text(dash_box_TWS, text="TWS", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_TWS = Text(dash_box_TWS, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box_AWA = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_AWA = Text(dash_box_AWA, text="AWA", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_AWA = Text(dash_box_AWA, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box_TWD = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_TWD = Text(dash_box_TWD, text="TWD", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_TWD = Text(dash_box_TWD, text=" ", align=dash_text_value_align, size=dash_box_text_large)

dash_box_DEP = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
dash_text_title_DEP = Text(dash_box_DEP, text="DEP", align=dash_text_title_align, size=dash_box_text_small)
dash_text_value_DEP = Text(dash_box_DEP, text=" ", align=dash_text_value_align, size=dash_box_text_large)

# Sea temp:
#dash_box_TSE = Box(dash_box, width=dash_box_width, height=dash_box_heigth, align=dash_text_title_align,border=1)
#dash_text_title_TSE = Text(dash_box_TSE, text="tSEA", align=dash_text_title_align, size=dash_box_text_small)
#dash_text_value_TSE = Text(dash_box_TSE, text=" ", align=dash_text_value_align, size=dash_box_text_large)

# Display settings
window_display = Window(app, title="display", layout="grid")
window_display.tk.attributes("-fullscreen", True)
window_display.text_size=but_text_size
window_display.hide()
but_display_00 = PushButton(window_display, command=display_adjust, args=["-"], text="-", width=but_width, height=but_height, grid=[0,0])
but_display_10 = PushButton(window_display, command=display_adjust, args=["+"], text="+", width=but_width, height=but_height, grid=[1,0])
if gpioimport==False:
    but_display_10.text_color="red"
but_display_20 = PushButton(window_display, command=display_posneg, args=["p"], text="posneg", width=but_width+1, height=but_height, grid=[2,0])
but_display_01 = PushButton(window_display, command=display_adjust, args=["off"], text="Off", width=but_width, height=but_height, grid=[0,1])
but_display_11 = PushButton(window_display, command=display_adjust, args=["100"], text="100%", width=but_width, height=but_height, grid=[1,1])
but_display_21 = PushButton(window_display, command=window_display.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# AVS settings
window_avs = Window(app, title="system", layout="grid")
window_avs.tk.attributes("-fullscreen", True)
window_avs.text_size=but_text_size
window_avs.hide()
but_avs_01 = PushButton(window_avs, lambda:single_show("AVS: 01"), text="01", width=but_width, height=but_height, grid=[0,0])
but_avs_10 = PushButton(window_avs, lambda:single_show("AVS: 10"), text="10", width=but_width, height=but_height, grid=[1,0])
but_avs_auto = PushButton(window_avs, lambda:single_show("AVS: AUTO"), text="AUTO", width=but_width+1, height=but_height, grid=[2,0])
but_avs_30 = PushButton(window_avs, lambda:single_show("AVS: 30"), text="30", width=but_width, height=but_height, grid=[0,1])
but_avs_60 = PushButton(window_avs, lambda:single_show("AVS: 60"), text="60", width=but_width, height=but_height, grid=[1,1])
but_avs_hide = PushButton(window_avs, command=window_avs.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# System functions
window_system = Window(app, title="system", layout="grid")
window_system.tk.attributes("-fullscreen", True)
window_system.text_size=but_text_size
window_system.hide()
but_system_00 = PushButton(window_system, command=menu_status_hard, text="HW", width=but_width, height=but_height, grid=[0,0])
but_system_10 = PushButton(window_system, command=menu_status_soft, text="SW", width=but_width, height=but_height, grid=[1,0])
but_system_20 = PushButton(window_system, command=ynmenu, args=["connect gps"], text="GPS", width=but_width+1, height=but_height, grid=[2,0])
but_system_01 = PushButton(window_system, command=ynmenu, args=["quit"], text="QUIT", width=but_width, height=but_height, grid=[0,1])
but_system_11 = PushButton(window_system, command=ynmenu, args=["reboot"], text="REBOOT", width=but_width, height=but_height, grid=[1,1])
but_system_21 = PushButton(window_system, command=window_system.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# UTZ selection
window_utz = Window(app, title="UTZ selector")
window_utz.tk.attributes("-fullscreen", True)
window_utz.text_size=but_text_size
window_utz.hide()
box_utz_title = Box(window_utz, width="fill", align="top")
text_utz = Text(box_utz_title, text="Time difference to UTC = " + str(TIMEZ), height=but_height-3, align="left")
text_utz.text_size=but_text_size
box_utz_sel = Box(window_utz, width="fill", align="bottom")
but_utz_minus = PushButton(box_utz_sel, lambda:UTZ_set(-1), text="-", width=but_width, height=but_height, align="left")
but_utz_plus = PushButton(box_utz_sel, lambda:UTZ_set(1), text="+", width=but_width, height=but_height, align="left")
but_utz_hide = PushButton(box_utz_sel, command=window_utz.hide, text="◄", width=but_width+1, height=but_height, align="left")

# Time and timers
window_racecountdown = Window(app, title="Countdown", layout="grid")
window_racecountdown.tk.attributes("-fullscreen", True)
window_racecountdown.text_size=but_text_size
window_racecountdown.hide()
but_racecountdown_00 = PushButton(window_racecountdown, command=downcounter, args=["05"], text="05", width=but_width, height=but_height, grid=[0,0])
but_racecountdown_10 = PushButton(window_racecountdown, command=downcounter, args=["10"], text="10", width=but_width, height=but_height, grid=[1,0])
but_racecountdown_20 = PushButton(window_racecountdown, command=downcounter, args=["man"], text="man", width=but_width+1, height=but_height, grid=[2,0])
but_racecountdown_01 = PushButton(window_racecountdown, command=downcounter, args=["12"], text="12", width=but_width, height=but_height, grid=[0,1])
but_racecountdown_11 = PushButton(window_racecountdown, command=downcounter, args=["15"], text="15", width=but_width, height=but_height, grid=[1,1])
but_racecountdown_21 = PushButton(window_racecountdown, command=window_racecountdown.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

window_timer = Window(app, title="Timers", layout="grid")
window_timer.tk.attributes("-fullscreen", True)
window_timer.text_size=but_text_size
window_timer.hide()
but_timer_00 = PushButton(window_timer, lambda:single_show("time"), text="Time", width=but_width, height=but_height, grid=[0,0])
but_timer_10 = PushButton(window_timer, lambda:single_show("date"), text="Date", width=but_width, height=but_height, grid=[1,0])
but_timer_20 = PushButton(window_timer, command=racing, text="Race", width=but_width+1, height=but_height, grid=[2,0])
but_timer_01 = PushButton(window_timer, command=window_racecountdown.show, text="Count", width=but_width, height=but_height, grid=[0,1])
but_timer_11 = PushButton(window_timer, lambda:single_show("stop"), text="Stop", width=but_width, height=but_height, grid=[1,1])
but_timer_21 = PushButton(window_timer, command=window_timer.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Weather Station
window_met = Window(app, title="Meterologics", layout="grid")
window_met.tk.attributes("-fullscreen", True)
window_met.text_size=but_text_size
window_met.hide()
but_met_00 = PushButton(window_met, lambda:single_show("tIN"), text="tIN", width=but_width, height=but_height, grid=[0,0])
but_met_10 = PushButton(window_met, lambda:single_show("tOUT"), text="tOUT", width=but_width, height=but_height, grid=[1,0])
but_met_20 = PushButton(window_met, text=" ", width=but_width+1, height=but_height, grid=[2,0])
but_met_01 = PushButton(window_met, lambda:single_show("hPa"), text="hPa", width=but_width, height=but_height, grid=[0,1])
but_met_11 = PushButton(window_met, lambda:single_show("HUM"), text="HUM", width=but_width, height=but_height, grid=[1,1])
but_met_21 = PushButton(window_met, command=window_met.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])
'''
window_met_graph = Window(app, title="Meterologic graphs")
window_met_graph.tk.attributes("-fullscreen", True)
window_met_graph.hide()
but_met=PushButton(window_met_graph, command=window_met_graph.hide, image=metpng)
'''
# Menu for settings 
window_settings = Window(app, title="settings", layout="grid")
window_settings.tk.attributes("-fullscreen", True)
window_settings.text_size=but_text_size
window_settings.hide()
but_settings_00 = PushButton(window_settings, command=window_display.show, text="DISP", width=but_width, height=but_height, grid=[0,0])
but_settings_10 = PushButton(window_settings, command=window_avs.show, text="AVS", width=but_width, height=but_height, grid=[1,0])
but_settings_20 = PushButton(window_settings, lambda:wpt_nav("del"), text="WPT", width=but_width+1, height=but_height, grid=[2,0])
but_settings_01 = PushButton(window_settings, command=window_utz.show, text="ZONE", width=but_width, height=but_height, grid=[0,1])
but_settings_11 = PushButton(window_settings, text="UNIT", width=but_width, height=but_height, grid=[1,1])
but_settings_21 = PushButton(window_settings, command=window_settings.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Menu for selecting service features
window_service = Window(app, title="Service", layout="grid")
window_service.tk.attributes("-fullscreen", True)
window_service.text_size=but_text_size
window_service.hide()
but_service_00 = PushButton(window_service, command=window_system.show, text="SYS", width=but_width, height=but_height, grid=[0,0])
but_service_10 = PushButton(window_service, command=window_settings.show, text="SET", width=but_width, height=but_height, grid=[1,0])
but_service_20 = PushButton(window_service, command=window_key.show, text="KEY", width=but_width+1, height=but_height, grid=[2,0])
but_service_01 = PushButton(window_service, command=window_timer.show, text="TIME", width=but_width, height=but_height, grid=[0,1])
but_service_11 = PushButton(window_service, command=window_met.show, text="WEA", width=but_width, height=but_height, grid=[1,1])
but_service_21 = PushButton(window_service, command=window_service.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])
#if BMP280import==False:
 #   but_service_11.text_color="red"
    
# Waypoints
window_wpts = Window(app, title="waypoints")
window_wpts.tk.attributes("-fullscreen", True)
window_wpts.text_size=but_text_size
window_wpts.hide()
box_wpts_title = Box(window_wpts, width="fill", align="top")
wpts_text_index= Text(box_wpts_title, text="Select destination", height=but_height-3, align="left")
wpts_text_index.text_size=but_text_size
#box_wpts = Box(window_wpts, align="left")

list_wpts = ListBox(window_wpts, command=destination, width=330, height=415, align="left")
#list_wpts.text_color=(0, 0, 100)
box_wpts_arrows = Box(window_wpts, align="left")
but_wpts_up = PushButton(box_wpts_arrows, lambda:wptscroll(-6), text="▲", width=but_width-3, height=but_height-1, align="top")
but_wpts_down = PushButton(box_wpts_arrows, lambda:wptscroll(6), text="▼", width=but_width-3, height=but_height-1, align="top")
box_wpts_buts = Box(window_wpts, height="fill", align="left")
but_wpts_edit = PushButton(box_wpts_buts, command=wpt_edit, text=" ", width=but_width, height=but_height-2,align="top")
but_wpts = PushButton(box_wpts_buts, command=window_wpts.hide, text="◄", width=but_width, height=but_height,align="top")

# Navigate and select destination
window_nav = Window(app, title="Navigation", layout="grid")
window_nav.tk.attributes("-fullscreen", True)
window_nav.text_size=but_text_size
window_nav.hide()
but_nav_00 = PushButton(window_nav, lambda:wpt_nav("nav"), text="WPT", width=but_width, height=but_height, grid=[0,0])
but_nav_10 = PushButton(window_nav, lambda:single_show("DTW"), text="DTW", width=but_width, height=but_height, grid=[1,0])
but_nav_20 = PushButton(window_nav, lambda:single_show("navbear"), text="BRG", width=but_width+1, height=but_height, grid=[2,0])
but_nav_01 = PushButton(window_nav, lambda:single_show("navttg"), text="TTG", width=but_width, height=but_height, grid=[0,1])
but_nav_11 = PushButton(window_nav, lambda:single_show("naveta"), text="ETA", width=but_width, height=but_height, grid=[1,1])
but_nav_21 = PushButton(window_nav, command=window_nav.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Trip function
window_trip = Window(app, title="Trip control", layout="grid")
window_trip.tk.attributes("-fullscreen", True)
window_trip.text_size=but_text_size
window_trip.hide()
but_trip_00 = PushButton(window_trip, lambda:single_show("tripdist"), text="DIS", width=but_width, height=but_height, grid=[0,0])
but_trip_10 = PushButton(window_trip, lambda:single_show("triptime"), text="TIME", width=but_width, height=but_height, grid=[1,0])
but_trip_20 = PushButton(window_trip, lambda:single_show("tripaver"), text="AVS", width=but_width+1, height=but_height, grid=[2,0])
but_trip_start = PushButton(window_trip, command=trip_start, text="START", width=but_width, height=but_height, grid=[0,1])
but_trip_stop = PushButton(window_trip, command=trip_stop, text="STOP", width=but_width, height=but_height, grid=[1,1], enabled=False)
but_trip_21 = PushButton(window_trip, command=window_trip.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Seatalk converted to NMEA
window_ST1 = Window(app, title="ST1 control", layout="grid")
window_ST1.tk.attributes("-fullscreen", True)
window_ST1.text_size=but_text_size
window_ST1.hide()
but_ST1_00 = PushButton(window_ST1, lambda:single_show("DEP"), text="DPT", width=but_width, height=but_height, grid=[0,0])
but_ST1_10 = PushButton(window_ST1, lambda:single_show("TWS"), text="TWS", width=but_width, height=but_height, grid=[1,0])
but_ST1_20 = PushButton(window_ST1, lambda:single_show("TWD"), text="TWD", width=but_width+1, height=but_height, grid=[2,0])
but_ST1_01 = PushButton(window_ST1, lambda:single_show("STW"), text="STW", width=but_width, height=but_height, grid=[0,1])
but_ST1_11 = PushButton(window_ST1, lambda:single_show("TSE"), text="Tsea", width=but_width, height=but_height, grid=[1,1])
but_ST1_21 = PushButton(window_ST1, window_ST1.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# GPS 
window_GPS = Window(app, title="GPS control", layout="grid")
window_GPS.tk.attributes("-fullscreen", True)
window_GPS.text_size=but_text_size
window_GPS.hide()
but_GPS_00 = PushButton(window_GPS, lambda:single_show("gpsspeed"), text="SOG", width=but_width, height=but_height, grid=[0,0])
but_GPS_10 = PushButton(window_GPS, lambda:single_show("gpshead"), text="COG", width=but_width, height=but_height, grid=[1,0])
but_GPS_20 = PushButton(window_GPS, lambda:single_show("gpspos"), text="POS", width=but_width+1, height=but_height, grid=[2,0])
but_GPS_01 = PushButton(window_GPS, lambda:single_show("gpsall"), text="ALL", width=but_width, height=but_height, grid=[0,1])
but_GPS_11 = PushButton(window_GPS, command=window_ST1.show, text="INS", width=but_width, height=but_height, grid=[1,1])
#but_GPS_11 = PushButton(window_GPS, command=MOB, text="MOB", width=but_width, height=but_height, grid=[1,1])
but_GPS_21 = PushButton(window_GPS, window_GPS.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# App = Main Menu
#app.text_size=but_text_size
app.tk.attributes("-fullscreen", True)
but_main_00 = PushButton(app, command=window_trip.show, text="DEP", width=but_width, height=but_height, grid=[0,0])
but_main_10 = PushButton(app, command=window_GPS.show, text="NOW", width=but_width, height=but_height, grid=[1,0])
but_main_20 = PushButton(app, command=window_nav.show, text="DES",  width=but_width+1, height=but_height, grid=[2,0])
but_main_01 = PushButton(app, command=dashboard, text="DASH", width=but_width, height=but_height, grid=[0,1])
but_main_11 = PushButton(app, command=MOB, text="MOB", width=but_width, height=but_height, grid=[1,1])
but_main_21 = PushButton(app, command=window_service.show, text="⦿", width=but_width+1, height=but_height, grid=[2,1])
# Need to set text size of each app button instead of the generic command so it is not inherited on other windows
but_main_00.text_size=but_text_size
but_main_10.text_size=but_text_size
but_main_20.text_size=but_text_size
but_main_01.text_size=but_text_size
but_main_11.text_size=but_text_size
but_main_21.text_size=but_text_size

if UDPmode==True:
    U = threading.Thread(target=UDPread)
    U.start()
display_update()
setload()
app.repeat(1000, timer_update)  # Schedule call to update timer every 1 sec
#if serimport==True:
app.repeat(1000, GPSread) #read data from GPS 1/1 sec

#Run the application
app.display()

# Installation and configuration notes at https://github.com/jbonde/MAIA/blob/master/installation


#EOF
