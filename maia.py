#!/usr/bin/python
print("MAIA  MAritime Information Application for use with touch displays")
appver="232" # for displaying software version in the status window
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

gpioimport=False
OSplatform=(platform.system())
print("OSplatform = " + str(OSplatform))

if OSplatform=="Windows":
    workdir="C:\\"
elif OSplatform=="Linux": # Assuming RPi as hardware
    import RPi.GPIO as GPIO # used for dimming PiTFT display and controlling buzzer if installed with current display
    GPIO.setmode(GPIO.BCM)
    gpioimport=True
    print("gpioimport=True")
    try:
        import mypi #script to check hardware
        print("mypi installed")
    except:
        print("mypi not installed")

GPSUSB=True # If GPS is connected to display USB port and instrument data is fetched via UDP
display_brightness=80 # Default brightness percentage  %
displayRPi_brightness=200 # Default brightness for RPi 7" (0-255)

# Clock
counting=0 #Counter for stop watch
homise="hms" #hours - minutes - seconds interval
downcount=5 #default countdown time

#Racing
countdown=True #For deciding if counter goes down before race or up after start of race
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
but_text_bigsize=130
key_width=None #Keyboard buttons
key_height=None
posmode=True # black text n white back. Opposite if False
colorfor=None #"black"
colorback=None #"white"

#Voltages
VOL1=0
VOL2=0
VOL3=0

#Met variables
tempin=0
tempout=0
tempENGINE=0
pressure=0
altitude=0
seapressure=0
humidity=0

#GPS variables
latdep=0 #Position of departure
londep=0
latnow=0 #55.942508 #Current position in DEGDEC format
lonnow=0 #11.870814
latnowdms=0 #Current position in DMS format
lonnowdms=0
latdes=0 # Default position of destination if no GPS
londes=0
latdesdms=0
londesdms=0
latbef=0 #Last destination measured (for calculating trip distance)
lonbef=0
GPSNS="" #N or S
GPSEW="" #E or W
UTC=0 #Time in UTC format
UTCOS=0 # Time string formatted for OS time update when out of network
GPSdate=0 #Date received from GPS
latdegminmin=0
londegminmin=0
COG=0 #Course over ground
SOG=0 #Speed over ground
SOGmax=0 # Max speed at trip

#Seatalk 1 variables
DEP=0 #Depth
AWS=0 #Apparent wind speed
AWA=0 #Apparent wind angle
TSE=0 #Sea temperature
STW=0 #log: speed through water : $IIVHW
MAG=0 # Magnetic Compass heading : $IIVHW
AUTON=False # True if Auto pilot turned on
AUTONCOUNT=0 # Time out for auto pilot active
AUTSET=False # True if Auto pilot active
AUTSETCOUNT=0 # Time out for auto pilot auto setting
AUT=0 # Auto pilot heading
windknots=False # If wind data is transmitted as knots. Else m/s

# Calculated on basis of ST1 and GPSinfo
TWS=0 #True wind speed
TWSmax=0 # Max wind speed
TWD=0 #True wind direction

# UDP and MET commands
NMEAstring=None
UDPaddress=None
UDPupdatedef=5 # default time to wait for UDP string. If below 0 texts will be red
UDPupdate=UDPupdatedef # Counting time to wait for UDP string
metpng="met.png"
UDP_IP = ""
UDP_PORT = 2000

# Serial variable
port=None
ser=None

#metpng="smb://192.168.0.105/PiShare/met.png"

# Navigational calculations
dest="" # Name of destination
DTW=0 # Distance from current position to selected waypoint
BRG=0 # Bearing to destination
TIMEZ = 2 #Offsetting GPS UTC time to local timezone 1=winther EST; 2=summer EST
UTZ="timenow"# Local time UTC+TIMEZ
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
    global GPSUSB
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
    global GPSUSB
    if answer=="yes":
        GPSUSB=True
        serinit()
    else:
        GPSUSB=False
        setsave()
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
    global racecount,countdown,but_race_color,but_race_text,but_race,but_raceup,but_racedown,mode
    #= Race countdown form
    mode="race"
    window_race = Window(app, title="Race")
    window_race.tk.attributes("-fullscreen", True)
    window_race.text_size=but_text_size
    but_race = PushButton(window_race, command=window_race.hide, height=but_height-3, width="fill")
    but_raceup = PushButton(window_race, command=racedown, text="▼", width=11, height=but_height-2, align="right")
    but_racedown = PushButton(window_race, command=raceup, text="▲", width=11, height=but_height-2, align="left")
    countdown=True
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
    global counting,countdown,homise
    global UTC,GPSdate,SOG,COG,GPSNS,GPSEW,latnow,lonnow,latnowdms,lonnowdms,TTG,ETA,UTZ,UTCOS
    global mode, but_text_bigsize, but_text_medsize
    global tempin, tempout, pressure, altitude, seapressure,humidity
    global racecount,but_race_color,but_race_text,but_race,but_raceup,but_racedown,downcount
    global tripdistance,tripcount,triptime,latint,lonint,tripaver,tripinterval,latsec,lonsec,tripsecelapsed,tripsec
    global navlog,DTW,BRG,AVSlog,AVSlat,AVSlon,MAG
    global logfile_created,UDPupdate,colorfor,colorback
    global AUTSETCOUNT,AUTONCOUNT,AUTSET,AUTON,AUT

#   Updating single display depending on function selected in menus
    but_single.text=str(mode) # Show mode if there is no data
    counting=counting+1 #seconds
    UDPupdate-=1 #counting down UDP update if not reset by UDP loop
    AUTONCOUNT-=1 # time out for active auto pilot
    AUTSETCOUNT-=1 # time out of auto pilot in auto mode if no HSC sentences are recieved
    if AUTSETCOUNT <1:
        AUTSET=False
        AUT=0
    if AUTONCOUNT <1:
        AUTON=False
    ms=time.strftime("%M:%S", time.gmtime(counting)) #stop watch display as M+S
    #dm=time.strftime ("%A\n" + "%d " + "%B") #displaying the actual date

    if GPSdate!=0: #Functions that will only run when GPS is ready
 #       if logfile_created==False:
 #           log_create()
 #           logfile_created=True

        if AVSlog==False: # Functions running once when GPS is ready
            AVSlat=latnow
            AVSlon=lonnow
            UTCOS = "20" + str(GPSdate)[4:] + "-" + str(GPSdate)[2:4] + "-" + str(GPSdate)[0:2] + " " + str(UTC)[0:2] + ":" + str(UTC)[2:4] + ":" + str(UTC)[4:6] #UTC time formatted to use for OS clock
            if OSplatform=="Linux":
                timestring="20" + str(GPSdate)[4:6]+"-"+str(GPSdate)[2:4]+"-"+str(GPSdate)[0:2]+" "+str(UTC)[0:2]+":"+str(UTC)[2:4]+":"+str(UTC)[4:6]
                print("timestring: " + str(timestring))
                try:
                    subprocess.run(['sudo','date','-s',str(timestring)])
                    print("Date set to UTC")
                except:
                    print("timestring not set")
            but_dep_start.enabled=True
        AVSlog=True
        AVSupdate()
        if latdes != None:
            DTW=WPTdistance(latnow,lonnow,latdes,londes) #calculate distance to waypoint in nm if GPS is live and a destination is selected
            DTW=str(DTW)[0:4]
            if SOG>0:
                TTGsec=int((float(DTW))*3600/SOG)# Find Time-to-go in seconds. Replace SOG with AVS
            else:
                TTGsec=1
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
    if mode=="ALLDATA":
        but_single.text_size=int(but_text_medsize/2.8)
        SOGstring='{:3.1f}'.format(float(SOG)) #str(SOG)
        but_single.text = \
            "Date " + str(GPSdate) + " " + "UTC " + str(UTC)[0:2] + ":" + str(UTC)[2:4] + "\n" \
            + "POS " + str(latnowdms) + str(GPSNS) + " " + str(lonnowdms) + str(GPSEW) + "\n" \
            + "SOG " + str(SOGstring) + " "  + "COG " + str(COG) + "\n" \
            + "tIn " + str(tempin) + " tOut " + str(tempout)+ " tENG " +  '{:3.1f}'.format(float(tempENGINE)) + "\n" \
            + "hPa " + str(pressure) + " hum " + str(humidity) + " %"  + "\n" \
            + "AWS " + str(AWS) + " AWA " + str(int(AWA)).zfill(3) + " TWS " + '{:3.1f}'.format(TWS) + " TWD " + str(int(TWD)).zfill(3) + "\n" \
            + "DEPTH " + '{:3.1f}'.format(float(DEP)) + " STW " + '{:3.1f}'.format(float(STW)) + "\n" \
            + "Cons "+ str(VOL1) + " " + "Eng "+ str(VOL2) + " " + "Spare " + str(VOL3) 
    if mode=="tIN":
        #if BMP280import==True:
        #    tempin = '{:4.1f}'.format(measurebmp.get_temperature())
        but_single.text="tIN" + "\n" + str(tempin) + "°C"
    if mode=="hPa":
        but_single.text_size=int(but_text_bigsize/1.2)
        but_single.text="PRES" + "\n" + str(pressure) + " hPa"  
    if mode=="tOUT":
        #if DHT22import==True:
#            DHT_SENSOR = Adafruit_DHT.DHT22
#            DHT_PIN = 4
        #    humidity, tempout = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        #    tempout = '{:4.1f}'.format(tempout)
        but_single.text="tOUT" + "\n" + str(tempout) + "°C"
    if mode=="HUM":
        #if DHT22import==True:
#            DHT_SENSOR = Adafruit_DHT.DHT22
#            DHT_PIN = 4
        #    humidity, tempout = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        #    humidity = '{:2.0f}'.format(humidity)
        but_single.text="HUM" + "\n" + str(humidity) + " %"     
    if mode=="tENG":
        but_single.text="tENG" + "\n" + str(tempENGINE) + "°C"    
    if mode=="dash":
        dashboard_update()
    if mode=="gpsall":
        but_single.text_size=but_text_medsize-20
        SOGstring='{:3.1f}'.format(float(SOG)) #str(SOG)
        but_single.text=str(latnowdms)+ str(GPSNS) + "\n" + str(lonnowdms) + str(GPSEW) + "\n" + "Speed " + str(SOGstring) + "\n" + "Course " + str(COG)[0:3]
    if mode=="gpspos":
        but_single.text_size=but_text_medsize
        but_single.text=str(latnowdms) + str(GPSNS) + "\n" + str(lonnowdms) + str(GPSEW) 
    if mode=="SOG": # current speed in nm as fetched from GPS
        SOGstring=str('{:3.1f}'.format(float(SOG))) #str(SOG)
        but_single.text="SOG" + "\n" + SOGstring + " kts"
    if mode=="SOGmax": # current speed in nm as fetched from GPS
        SOGmaxstring=str('{:3.1f}'.format(float(SOGmax))) #str(SOG)
        but_single.text="SOGmax" + "\n" + SOGmaxstring + " kts"
    if mode=="TWSmax": # current speed in nm as fetched from GPS
        TWSmaxstring=str('{:3.1f}'.format(float(TWSmax))) #str(SOG)
        but_single.text="TWSmax" + "\n" + TWSmaxstring + " kts"
    if mode=="gpshead":
        if str(COG)[2:3]==".":
            but_single.text="COG" + "\n" + str(COG)[0:2] + "°"
        else:
            but_single.text="COG" + "\n" + str(COG)[0:3] + "°"
    if mode=="DEP": # current depth
        but_single.text="DEPTH" + "\n" + str('{:3.1f}'.format(float(DEP))) + " m" #str(DEP) 
    if mode=="TWS": # true wind speed
        but_single.text="TWS" + "\n" + str('{:3.1f}'.format(TWS)) + " m/s" #str(TWS)
    if mode=="TWD": # true wind angle
        but_single.text="TWD" + "\n"  + str(int(TWD)).zfill(3) + "°" #(TWD)
    if mode=="STW": # speed through water
        but_single.text="STW" + "\n" + str('{:3.1f}'.format(float(STW))) + " kts" #str(STW)
    if mode=="TSE": # sea temp
        but_single.text="tSea " + "\n" + str(TSE) + "°C"
    if mode=="VOL": # voltages
        but_single.text_size=int(but_text_medsize/1.6)
        but_single.text="Consume " + str(VOL1) + " V" + "\n" + "Engine " + str(VOL2) + " V" + "\n" + "Windlass " + str(VOL3) + " V"
    if mode=="VOL1": # Consume battery 
        but_single.text="Cons."+ "\n" + str(VOL1) + " V"
    if mode=="VOL2": # Engine battery 
        but_single.text="Engine"+ "\n" + str(VOL2) + " V"
    if mode=="MAG": # Compass heading
        try:
            MAG='{:3.0f}'.format(float(MAG))
        except:
            MAG=MAG
        but_single.text_size=int(but_text_medsize/1.1)
        but_single.text="COMPASS" + "\n" + str(MAG) + "°"
    if mode=="PILOT": # Auto pilot data
        try:
            AUT='{:3.0f}'.format(float(AUT))
        except:
            AUT=AUT
        but_single.text_size=int(but_text_medsize/1.2)
        but_single.text="Pilot on: " + str(AUTON) + "  " + "\n" + "Auto: " + str(AUTSET) + "  " + "\n" + "Heading " + str(AUT) + "°"
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
        but_single.text="UTC " + str(UTC[0:2]) + ":" + str(UTC[2:4]) + "\n" + "UTZ " + str(UTZ[0:2]) + ":" + str(UTZ[2:4])
    if mode=="utc":     
        but_single.text=UTC[0:2]+":"+UTC[2:4] #UTC hours and minutes separated by :
    if mode=="utz":
        but_single.text=UTZ[0:2]+":"+UTZ[2:4] #UTZ hours and minutes separated by :
    if mode=="date":
        but_single.text_size=but_text_medsize+40
        but_single.text=str(GPSdate)
#        but_single.text=str(dayname)+ "\n" + str(GPSdate)
    if mode=="DTW":
        but_single.text="DTW" + "\n" + str(DTW) + "nm" # Chopping off some small digits
    if mode=="navbear":
        but_single.text="BRG" + "\n" + str(int(BRG)).zfill(3) + "°"
    if mode=="navttg": #
        if len(TTG)>9:
            TTGarray=TTG.split(",")
            TTGtext="TTG" + "\n" + str(TTGarray [0]) + "\n" + str(TTGarray [1])
            but_single.text_size=but_text_medsize
        else:
            TTGtext=TTG
            but_single.text_size=but_text_medsize+20
        but_single.text=TTGtext
    if mode=="naveta": #  
        but_single.text_size=but_text_medsize
        but_single.text="ETA" + "\n" + (str(ETA)[:10] + "\n" + str(ETA)[11:19])
    if mode=="MOBnow": #
        but_single.text_size=but_text_medsize
        but_single.text="MOB" + "\n" + str(DTW)[0:5] + "\n" + str(BRG)
    if mode=="tripdist":
        but_single.text="TRIP" + "\n" + str(tripsecelapsed)[:3] + " nm"
    if mode=="triptime":
        tt=time.strftime("%H:%M:%S", time.gmtime(triptime)) #elapsed time as HMS
        but_single.text_size=but_text_medsize+20
        but_single.text=tt
    if mode=="tripaver":
        tripaver=3600*tripsecelapsed/triptime
        but_single.text="AVS kts" + "\n" + str(tripaver)[:4]
    if mode=="race":        
        if countdown==True:
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
            countdown=False      
#    if UDPupdate==0:
#        colorfor="red"
#        display_update()
#    if UDPupdate>0:
#        display_posneg("u")
    
# *******************   DISPLAY CONTROL  *******************

def display_adjust(bri):
    # function to adjust display brightness according to display type
    global display_brightness,displayRPi_brightness,pwm

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
            display_brightness+=10
        #subprocess.run(['sudo','sh','-c','echo "128" > /sys/class/backlight/rpi_backlight/brightness'])

    if bri=="-":
        if display_brightness>9:
            display_brightness-=10
            if display_brightness==0:
                display_brightness=1        
        #subprocess.run(['sudo','sh','-c','echo "50" > /sys/class/backlight/rpi_backlight/brightness'])
                
    if bri=="100":    
        display_brightness=100
        #subprocess.run(['sudo','sh','-c','echo "255" > /sys/class/backlight/rpi_backlight/brightness'])

    if screen_width==720:
        # print("assuming PiTFT 3.5'' display")
        pwm.ChangeDutyCycle(display_brightness)

    if screen_width==800:
        # print("assuming RPi 7'' display: 0<brightness<255")
        displayRPi_brightness=int(255*display_brightness/100)        
        subprocess.run(['sudo','sh','-c','echo ' + str(displayRPi_brightness) + ' > /sys/class/backlight/rpi_backlight/brightness'])
#        subprocess.run(['sudo','sh','-c','echo',str(displayRPi_brightness),' > /sys/class/backlight/rpi_backlight/brightness'])
        print("display_brightness " + str(display_brightness))
        print("displayRPi_brightness " + str(displayRPi_brightness))

    if screen_width>800:
        print("assuming HDMI display - no brightness adjustment possible")
        # Could possibly tweak colors instead

#    else:
#        print("Unknown display type - no brightness adjustment possible")

    setsave()

def display_update():
    # Update displays after color change (pos/neg)
    app.text_color=colorfor
    app.bg=colorback    
    '''
    window_avs.text_color=colorfor
    window_avs.bg=colorback
    window_countdown.text_color=colorfor
    window_countdown.bg=colorback
    window_GPS.text_color=colorfor
    window_GPS.bg=colorback
    window_key.text_color=colorfor
    window_key.bg=colorback
    window_wea.text_color=colorfor
    window_wea.bg=colorback
    window_wea_graph.text_color=colorfor
    window_wea_graph.bg=colorback
    window_des.text_color=colorfor
    window_des.bg=colorback
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
    window_dep.text_color=colorfor
    window_dep.bg=colorback
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
    #if n=="p": # if posneg is changed from panel
    display_update()
#    if n=="u": # function called from UDP check when signal is present (UDPupdate > 0)
#        display_update()
    setsave()

def PiTFT():
# Initializing PiTFT display brightness
    global pwm,gpioimport
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
#    COG_color="blue"
    COG_color=(153,80,240)
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
    UTCstring=("UTC " + str(UTC)[:2] + ":" + str(UTC)[2:4])
    dash_drawing.text(10, 10,compass_direction,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts
    dash_drawing.text(screen_centerX+circle_radius-2*inner_circle, 10,UTCstring,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts
    dash_drawing.text(10,screen_height-2*int(dash_drawing_text_size),dest,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts
    dash_drawing.text(10,screen_height-int(dash_drawing_text_size),ETAstring,color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner texts
    dash_drawing.text(screen_centerX+circle_radius-2*inner_circle,screen_height-int(dash_drawing_text_size),"Compass " + str(MAG)[:3],color=dash_drawing_text_color,size=int(dash_drawing_text_size/2)) # Set compass corner text = Magnetic compass

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
#    drawing_angles=[BRG,COG,(COG+AWA),TWD] #used for north up????
    AWD=COG+AWA #Apparant compass direction
    if AWD>=360:
        AWD=AWD-360
    drawing_angles=[BRG,COG,AWD,TWD]
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
    #window_wea_graph.show()
    #window_wea_graph.when_clicked=window_wea_graph.hide()

    #metpng = curl -O graphurl
    #metpng = curl -O http://192.168.0.105/met.png
    #metpng = curl -O 192.168.0.105/met.png

# *****************   Navigation   ****************************

def serinit():
    # Serial setup
    global port, ser, GPSUSB
    if GPSUSB==True:
        try:
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
            print("ser= " + str(ser))
        except:
            GPSUSB=False
            print("no serial connection. GPSUSB=" + str(GPSUSB))
    setsave()

def GPSread():
    # read and split GPS data from serial port or UDP
    # format:  $GPRMC,225446,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3,E*68
    global UTC,GPSdate,COG,GPSNS,GPSEW,SOG,SOGmax
    global ser,gpsdata,UTZ,UTZhours,TIMEZ,UTCOS,GPSNS,GPSEW,dayname,UDPupdate,daynumber
    global latnow,lonnow,latnowdms,lonnowdms,londegminmin,latdegminmin
    if GPSUSB==True:  # Fetch GPS data from USB instead of UDP
        gpsdata = ser.readline().decode('ascii', errors='replace') #wait for each full line        
    else:   # Fetch GPS data from UDP instead of USB
        gpsdata=NMEAstring
    if len(str(gpsdata))>8:
        header = gpsdata[3:6] # slicing out the header information (3 letters needed)
        UDPupdate=UDPupdatedef # resetting the UDP timer to default value
    else:
        header="1234567890"
    #print(header)
    if header=="RMC": # the line containing the needed information like position, time and speed etc....
        RMCarray=gpsdata.split(",") #make array according to comma-separation in string
        UTC=(RMCarray [1])
        GPSdate=(RMCarray [9])
        try:
            SOG=float(RMCarray [7]) # knots
        except:
            SOG=0
            print("SOG error")
#        SOG='{:3.1f}'.format(float(RMCarray [7])) #str(SOG)
        #if SOG>SOGmax:
        #    SOGmax=SOG
        if RMCarray [8]!="":
            COG=float(RMCarray [8])
        else:
            COG=0
        latdegminmin=(RMCarray [3])
        GPSNS=(str(RMCarray [4]))
        latnow=dmm2dec(latdegminmin,GPSNS) #current latitude converted to decimal format
        londegminmin=(RMCarray [5])                
        GPSEW=(str(RMCarray [6]))
        lonnow=dmm2dec(londegminmin,GPSEW) #current longitude converted to decimal format
        latnowdms=dec2dms(float(latnow)) #current position converted to dms format
        lonnowdms=dec2dms(float(lonnow))
        UTZhours=TIMEZ+float(UTC[0:2])
        if UTZhours>23:
            UTZhours=UTZhours-24
        UTZhours=int(UTZhours)
        UTZ=str(UTZhours).zfill(2)+str(UTC)[2:4]
        
        monthname=calendar.month_abbr[int((GPSdate)[2:4])]
        daynames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
#        daynumber=calendar.weekday((int(str(GPSdate)[4:])),int(str(GPSdate)[2:4]),int(str(GPSdate)[0:2]))
#        dayname=daynames[daynumber]

            #Check system clocks:   timedatectl status           
            #Format example: sudo date --set="2015-09-30 10:05:59"            
#            UTCOS = "20" + str(GPSdate)[4:] + "-" + str(GPSdate)[2:4] + "-" + str(GPSdate)[0:2] + " " + str(UTZ)[0:2] + ":" + str(UTC)[2:4] + ":" + str(UTC)[4:6] #Local time formatted to use for OS clock
#            subprocess.Popen(["sudo", "date", "-s", UTCOS])
#            os.system("sudo date -s " % str(UTCOS))
            # subprocess('sudo time --set' % UTCOS)
            # os.system('sudo date -u %s' % UTCOS)
            #os.system('sudo hwclock --set --date=' % UTCOS)
#            os.system('sudo hwclock --systohc') #Set hardware clock

def UDPread():
    global NMEAstring,tempin,tempout,tempENGINE,pressure,humidity,UDPaddress,TWSmax,SOGmax,MAG
    global DEP,TWS,TWD,TSE,STW,AWA,AWS,AUT #Seatalk1
    global VOL1,VOL2,VOL3
    global AUT,AUTSET,AUTSETCOUNT,AUTON,AUTONCOUNT # Autopilot values

    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #reuse socket if program is opened after crash
        sock.bind((UDP_IP, UDP_PORT))
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        UDPaddress=addr[0]
        NMEAstring = str(data)[2:] 
        try:
            but_udp.text=NMEAstring
        except:
            print("error? but_udp.text=NMEAstring ")
        header = NMEAstring[3:6] # slicing out the header information (3 letters needed to identify string)
        #if header=="RMC":
        #    print(NMEAstring)  
        if header=="WEA":
            WEAarray=NMEAstring.split(",") #make array according to comma-separation in string
            #print(WEAarray)
            #print(UDPaddress)  
            try:
                tempin='{:3.1f}'.format(float(WEAarray[1]))
                tempout='{:3.1f}'.format(float(WEAarray[2]))
                pressure='{:3.0f}'.format(float(WEAarray[3]))
                humidity='{:2.0f}'.format(float(WEAarray[4]))
                tempENGINE='{:2.0f}'.format(float(WEAarray[5]))
            except:
                print("WEA read problem")
        if header=="DBT":
            DBTarray=NMEAstring.split(",") #DBT - Depth Below Transducer
            try:
                DEP='{:3.1f}'.format(float(DBTarray[3]))
            except:
                DEP=DBTarray[3]
#        if header=="MWV":
#           MWVarray=NMEAstring.split(",") #make array according to comma-separation in string
        if header=="VOL":
            VOLarray=NMEAstring.split(",") #VOL - Voltage inputs
            try:
                VOL1='{:3.1f}'.format(float(VOLarray[1]))
                VOL2='{:3.1f}'.format(float(VOLarray[2]))
                VOL3='{:3.1f}'.format(float(VOLarray[3]))
            except:
                VOL1=VOLarray[1]
                VOL2=VOLarray[2]
                VOL3=VOLarray[3]
                
        if header=="VWR":
            VWRarray=NMEAstring.split(",") #VWR - Relative Wind Speed and Angle
            try:
                AWA=float(VWRarray[1]) # Wind angle to bow magnitude in degrees
                AWB=VWRarray[2] # Wind direction Left/Right of bow
            except:
                AWA=1
                AWB="R"
                print("AWA/AWB error")
            if AWB=="R":
                AWA=AWA
            else:
                AWA=-AWA
            try:
                if windknots==True:
                    AWS=float(VWRarray[3])*0.514444 # Apparent wind speed (knots) converted to Meters Per Second
                else:
                    AWS=float(VWRarray[3])
                if AWS<1: # Avoid zeros
                    AWS=1
            except:
                print("could not read AWS from VWR string")
            #Calculating True wind
            AWA_rad=math.radians(AWA) # convert angle deg to radians
            if AWA_rad<0.1: # Avoid cos(0)
                AWA_rad=0.1
            SOGms=SOG*0.514444 #Speed over ground in m/s
            try:
                TWS=math.sqrt(math.pow(AWS,2)+math.pow(SOGms,2)-2*AWS*SOGms*math.cos(AWA_rad)) # True wind speed
            except:
                TWS=1
                print("TWS errror")
            #if TWS>TWSmax:
            #    TWSmax=TWS
            if TWS<0.1: #Avoid 0 division 
                TWS=0.1
            try:
                if AWB=="R":
                    TWD=math.degrees(math.acos((AWS*math.cos(AWA_rad)-SOGms)/TWS)) # True wind direction (compass)
                else:
                    TWD=math.degrees(-math.acos((AWS*math.cos(AWA_rad)-SOGms)/TWS))
            except ValueError:
                TWD=1
#            TWD=COG+TWD
            if TWD<0:
                TWD=360+TWD
            if TWD>=360:
                TWD=TWD-360
        if header=="MTW":
            MTWarray=NMEAstring.split(",") #MTW - Mean Temperature of Water
            try:
                TSE=MTWarray[1] #Sea temp
            except:
                print("No TSE in array")
        if header=="VHW": #VHW - Water speed and heading
            VHWarray=NMEAstring.split(",") #make array according to comma-separation in string
            MAG=VHWarray[3] # Magnetic compass heading
            try:
                STW=float(VHWarray[5])
            except ValueError:
                STW=0
        if header=="HDM": # HDM="$IIHDM,222.,M" # Heading - Magnetic - Auto pilot. Only broadcasted if turned on.
            HDMarray=NMEAstring.split(",")
            AUTON=True
            AUTONCOUNT=10
        if header=="HSC": # HSC="$IIHSC,,,333.,M" # Heading Steering Command. Auto pilot heading. Only broadcasted in AUTO mode.
            AUTSET=True
            AUTSETCOUNT=10
            HSCarray=NMEAstring.split(",")
            AUT=HSCarray[3]
        if header=="MAX": # Max values
            MAXarray=NMEAstring.split(",")
            TWSmax=MAXarray[1]
            SOGmax=MAXarray[2]
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
    global tripcount,triptime,latint,lonint,latnow,lonnow,latdep,londep,triplog,but_dep_00,but_dep_10,tripdistance,latsec,lonsec,tripsecelapsed,tripstart,navlog
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
    but_dep_start.disable()
    but_dep_start.text_color="red"
    but_dep_stop.enable()
    log_create()
    
def trip_stop():
    global tripdistance,tripcount,triptime,latint,lonint,latnow,lonnow,but_dep_00,but_dep_10,triplog

    #Stop trip
    triplog=False
    but_dep_start.enable()
    but_dep_start.text_color=colorfor
    but_dep_stop.disable()
#    but_dep_stop = PushButton(window_dep, command=trip_start, text="START", width=but_width, height=but_height, grid=[0,1])

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
    log_header = ["Date","UTC","UTZ", "SOG","SOGmax","STW","COG","tripdistance","triptime(min)","latdep","londep","Latitude","Longitude","latdes","londes","destination","tempin","tempout","humidity","HPa","AWA","AWS","TWD","TWS","TWSmax","BRG","DTW","Depth","SEA"]
    if OSplatform=="Linux":
        logname='/home/pi/' + str(GPSdate) + "-" + str(UTZ) + '.csv'
    else:
        logname='C:\\Users\\bonde\\Dropbox\\Code\\Python\\MAIA\\' +  "-" + str(UTZ) + '.csv' 
    with open(logname,"w") as f:
        f.write(",".join(str(value) for value in log_header)+ "\n")
    print ("New log created: " + str(logname))

def log_update(): # save data to logfile
    #global tempin,tempout,pressure,humidity
    logtripdis= '{:4.1f}'.format(tripdistance)
    logtriptime= triptime/60
    log_data = [GPSdate,UTC,UTZ, SOG,SOGmax,STW,COG,logtripdis,logtriptime,latdep,londep,latnow,lonnow,latdes,londes,dest,tempin,tempout,humidity,pressure,AWA,AWS,TWD,TWS,TWSmax,BRG,DTW,DEP,TSE]
    with open(logname,"a") as f:
        f.write(",".join(str(value) for value in log_data)+ "\n")

def setsave():
    # Saving current settings
    with open("maia.csv","w") as m:
        m.write("TIMEZ" + "=" + str(TIMEZ) + '\n') 
        m.write("display_brightness" + "=" + str(display_brightness) + '\n') 
        m.write("posmode" + "=" + str(posmode) + '\n') 
        m.write("GPSUSB" + "=" + str(GPSUSB) + '\n') 
        m.write("triplog" + "=" + str(triplog) + '\n')       
        if GPSUSB==True:
            but_settings_30.text_color="green"
        else:
            but_settings_30.text_color="red"
            
def setload():
    global TIMEZ,display_brightness,posmode,GPSUSB,triplog
    try:        
        with open('maia.csv', encoding="latin-1", newline='') as csvfile: # Open CSV file with settings
            settingsfile = list(csv.reader(csvfile, delimiter='=')) # Create list from csv file
        print("settingsfile: " + str(settingsfile))
        TIMEZ=int(settingsfile[0][1])
        print("TIMEZ loaded: " + str(TIMEZ))
        display_brightness=int(settingsfile[1][1])
        #pwm.ChangeDutyCycle(display_brightness)
        print("display_brightness loaded: " + str(display_brightness))
        posmodestr=str(settingsfile[2][1])
        if posmodestr=="True":
            posmode=True
        else:
            posmode=False
        print("posmode loaded: " + str(posmode))
        GPSUSBstr=str(settingsfile[3][1])
        if GPSUSBstr=="True":
            GPSUSB=True
            serinit()
        else:
            GPSUSB=False
        print("GPSUSB mode loaded: " + str(GPSUSB))

        UTZ_set(0)
        display_adjust("z")
        display_posneg("z")

    except:
        print("no settings file ")

# **************** Hardware detect ***************************

def getSerial():
  # Extract serial from cpuinfo file
  mycpuserial = "Error"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:6]=='Serial':
        mycpuserial = line[10:26]
    f.close()
  except:
    mycpuserial = "Error"

  return mycpuserial

def getRevision():
  # Extract board revision from cpuinfo file
  myrevision = "Error"
  try:
    f = open('/proc/cpuinfo','r')
    for line in f:
      if line[0:8]=='Revision':
        myrevision = line[11:-1]
    f.close()
  except:
    myrevision = "Error"

  return myrevision

def getModel():
  # Extract Pi Model string
  try:
    mymodel = open('/proc/device-tree/model').readline()
  except:
    mymodel = "Error"

  return mymodel

def getEthName():
  # Get name of Ethernet interface
  try:
    for root,dirs,files in os.walk('/sys/class/net'):
      for dir in dirs:
        if dir[:3]=='enx' or dir[:3]=='eth':
          interface=dir
  except:
    interface="None"
  return interface
  
def getMAC(interface='eth0'):
  # Return the MAC address of named Ethernet interface
  try:
    line = open('/sys/class/net/%s/address' %interface).read()
  except:
    line = "None"
  return line[0:17]
  
def getIP(interface='eth0'):
  # Read ifconfig.txt and extract IP address
  try:
    filename = 'ifconfig_' + interface + '.txt'
    os.system('ifconfig ' + interface + ' > /home/pi/' + filename)
    f = open('/home/pi/' + filename, 'r')
    line = f.readline() # skip 1st line
    line = f.readline() # read 2nd line
    line = line.strip()
    f.close()

    if line.startswith('inet '):
      a,b,c = line.partition('inet ')
      a,b,c = c.partition(' ')
      a=a.replace('addr:','')
    else:
      a = 'None'

    return a

  except:
    return 'Error'

def getCPUtemp():
  # Extract CPU temp
  try:
    temp = subprocess.check_output(['vcgencmd','measure_temp'])
    temp = temp[5:-3]
  except:
    temp = '0.0'
  temp = '{0:.2f}'.format(float(temp))
  return str(temp)

def getGPUtemp():
  # Extract GPU temp
  try:
    temp = subprocess.check_output(['cat','/sys/class/thermal/thermal_zone0/temp'])
    temp = float(temp)/1000
  except:
    temp = 0.0
  temp = '{0:.2f}'.format(temp)
  return temp

def getRAM():
  # free -m
  output = subprocess.check_output(['free','-m'])
  lines = output.splitlines()
  line  = str(lines[1])
  ram = line.split()
  # total/free  
  return (ram[1],ram[3])

def getDisk():
  # df -h
  output = subprocess.check_output(['df','-h'])
  lines = output.splitlines()
  line  = str(lines[1])
  disk  = line.split()
  # total/free
  return (disk[1],disk[3])

def getCPUspeed():
  # Get CPU frequency
  try:
    output = subprocess.check_output(['vcgencmd','get_config','arm_freq'])
    lines = output.splitlines()
    line  = lines[0]
    freq = line.split('=')
    freq = freq[1]
  except:
    freq = '0'
  return freq

def getUptime():
  # uptime
  # tupple uptime, 5 min load average
  return 0

def getPython():
  # Get current Python version
  # returns string
  pythonv = platform.python_version()
  return pythonv

def getSPI():
  # Check if SPI bus is enabled
  # by checking for spi_bcm2### modules
  # returns a string
  spi = "False"
  try:
    c=subprocess.Popen("lsmod",stdout=subprocess.PIPE)
    gr=subprocess.Popen(["grep" ,"spi_bcm2"],stdin=c.stdout,stdout=subprocess.PIPE)
    output = gr.communicate()[0]
    if output[:8]=='spi_bcm2':
      spi = "True"
  except:
    pass
  return spi

def getI2C():
  # Check if I2C bus is enabled
  # by checking for i2c_bcm2### modules
  # returns a string
  i2c = "False"
  try:
    c=subprocess.Popen("lsmod",stdout=subprocess.PIPE)
    gr=subprocess.Popen(["grep" ,"i2c_bcm2"],stdin=c.stdout,stdout=subprocess.PIPE)
    output = gr.communicate()[0]
    if output[:8]=='i2c_bcm2':
      i2c = "True"
  except:
    pass
  return i2c

def getBT():
  # Check if Bluetooth module is enabled
  # returns a string
  bt = "False"
  try:
    c=subprocess.Popen("lsmod",stdout=subprocess.PIPE)
    gr=subprocess.Popen(["grep" ,"bluetooth"],stdin=c.stdout,stdout=subprocess.PIPE)
    output = gr.communicate()[0]
    if output[:9]=='bluetooth':
      bt = "True"
  except:
    pass
  return bt

# ********************************  Exiting ***************************************

def quitting():
#    if gpioimport==True:
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
        try:
            status_list_column.append(getModel()[:15])
            status_list_column.append(getModel()[15:])
        except:
            status_list_column.append("model failed")            
        try:
            status_list_column.append(platform.platform()[:15])
            status_list_column.append(platform.platform()[15:30])
            status_list_column.append(platform.platform()[30:])
        except:
            status_list_column.append("platform failed")            
        status_list_column.append("rev " + getRevision())
        status_list_column.append("ser" + getSerial()[:10])
        status_list_column.append("" + getSerial()[10:])
        status_list_column.append("python " + platform.python_version())

        status_list_column=status_list_center
        status_list_column.clear()
        status_list_column.append("SPI " + getSPI())
        status_list_column.append("I2C " + getI2C())
        status_list_column.append("NETWORK ")
        status_list_column.append("Bluetooth " + getBT())
        status_list_column.append("LAN " + getEthName())
        status_list_column.append("" + getMAC())
        status_list_column.append("ip " + getIP())
        status_list_column.append("WiFi:")
        status_list_column.append("" + getMAC('wlan0'))
        status_list_column.append("ip " + getIP('wlan0'))

        status_list_column=status_list_right 
        status_list_column.clear()
        status_list_column.append("CPUt " + getCPUtemp())
        status_list_column.append("GPUt " + getGPUtemp())
        status_list_column.append("ram" + str(getRAM()))
        status_list_column.append("dsk" + str(getDisk()))
        status_list_column.append("CPUspeed " + getCPUspeed())
        status_list_column.append("uptime " + str(getUptime()))
    window_status.text_size=but_text_size-16
    window_status.show()

def menu_status_soft():
    # Updating the status window with fresh data from app
    # Max 14 items in each row
    status_list_column=status_list_left # Column for reading hardware data with mypi
    status_list_column.clear()
    status_list_column.append("app ver. " + str(appver))
    status_list_column.append("GPS data" )
    status_list_column.append("Speed " + str(SOG))
    status_list_column.append("Course " + str(COG))
    status_list_column.append("Date " + str(GPSdate))
    status_list_column.append("UTC " + str(UTC)[0:6])
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
    status_list_column.append("GPS USB " + str(GPSUSB))
#    status_list_column.append("BMP280 " + str(BMP280import))
    status_list_column.append("TTG " + str(TTG))
    status_list_column.append("TWSmax " + str(TWSmax)[0:4])
    status_list_column.append("AVS01 " + str(AVS01))
    status_list_column.append("AVS10 " + str(AVS10))
    status_list_column.append("AVS30 " + str(AVS30))
    status_list_column.append("AVS60 " + str(AVS60))
    status_list_column.append("AVSlog " + str(AVSlog))
    status_list_column.append("SOGmax " + str(SOGmax))
    status_list_column.append(str(VOL1) + " " + str(VOL2) + " " + str(VOL3))

    window_status.text_size=but_text_size-16
    window_status.show()

#display_posneg("z")

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
    but_height=int(screen_height/150)
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

# UDP data menu
window_udp = Window(app, title="UDP")
window_udp.tk.attributes("-fullscreen", True)
but_udp = PushButton(window_udp, command=window_udp.hide, text=str(mode), width="fill", height="fill")
but_udp.text_size=int(but_text_size/2)
window_udp.hide()

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
but_system_20 = PushButton(window_system, command=window_udp.show, text="UDP", width=but_width+1, height=but_height, grid=[2,0])
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
window_countdown = Window(app, title="Countdown", layout="grid")
window_countdown.tk.attributes("-fullscreen", True)
window_countdown.text_size=but_text_size
window_countdown.hide()
but_countdown_00 = PushButton(window_countdown, command=downcounter, args=["05"], text="05", width=but_width, height=but_height, grid=[0,0])
but_countdown_10 = PushButton(window_countdown, command=downcounter, args=["10"], text="10", width=but_width, height=but_height, grid=[1,0])
but_countdown_20 = PushButton(window_countdown, command=downcounter, args=["man"], text="man", width=but_width+1, height=but_height, grid=[2,0])
but_countdown_01 = PushButton(window_countdown, command=downcounter, args=["12"], text="12", width=but_width, height=but_height, grid=[0,1])
but_countdown_11 = PushButton(window_countdown, command=downcounter, args=["15"], text="15", width=but_width, height=but_height, grid=[1,1])
but_countdown_21 = PushButton(window_countdown, command=window_countdown.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

window_timer = Window(app, title="Timers", layout="grid")
window_timer.tk.attributes("-fullscreen", True)
window_timer.text_size=but_text_size
window_timer.hide()
but_timer_00 = PushButton(window_timer, lambda:single_show("time"), text="Time", width=but_width, height=but_height, grid=[0,0])
but_timer_10 = PushButton(window_timer, lambda:single_show("date"), text="Date", width=but_width, height=but_height, grid=[1,0])
but_timer_20 = PushButton(window_timer, command=racing, text="Race", width=but_width+1, height=but_height, grid=[2,0])
but_timer_01 = PushButton(window_timer, command=window_countdown.show, text="Count", width=but_width, height=but_height, grid=[0,1])
but_timer_11 = PushButton(window_timer, lambda:single_show("stop"), text="Stop", width=but_width, height=but_height, grid=[1,1])
but_timer_21 = PushButton(window_timer, command=window_timer.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

'''
window_wea_graph = Window(app, title="Meterologic graphs")
window_wea_graph.tk.attributes("-fullscreen", True)
window_wea_graph.hide()
but_wea=PushButton(window_wea_graph, command=window_wea_graph.hide, image=metpng)
'''
# 4x3 Menu for settings
window_settings = Window(app, title="settings", layout="grid")
window_settings.tk.attributes("-fullscreen", True)
window_settings.text_size=but_text_size
window_settings.hide()

if screen_width>800:
    but_set_width=int(screen_width/150)
    but_set_heigth=int(screen_height/200)
else:
    but_set_width=int(screen_width/130)
    but_set_heigth=int(screen_height/170)

but_settings_00 = PushButton(window_settings, command=window_display.show, text="DIS", width=but_set_width, height=but_set_heigth, grid=[0,0])
but_settings_10 = PushButton(window_settings, command=window_avs.show, text="AVS", width=but_set_width, height=but_set_heigth, grid=[1,0])
but_settings_20 = PushButton(window_settings, lambda:wpt_nav("del"), text="WPT", width=but_set_width, height=but_set_heigth, grid=[2,0])
but_settings_30 = PushButton(window_settings, command=ynmenu, args=["connect gps"], text="GPS", width=but_set_width, height=but_set_heigth, grid=[3,0])
but_settings_01 = PushButton(window_settings, command=window_utz.show, text="ZONE", width=but_set_width, height=but_set_heigth, grid=[0,1])
but_settings_11 = PushButton(window_settings, text="UNIT", width=but_set_width, height=but_set_heigth, grid=[1,1])
but_settings_21 = PushButton(window_settings, lambda:single_show("ALLDATA"), text="ALL", width=but_set_width, height=but_set_heigth, grid=[2,1])
but_settings_31 = PushButton(window_settings, command=window_settings.hide, text="◄", width=but_set_width, height=but_set_heigth, grid=[3,1])
but_settings_02 = PushButton(window_settings, command=window_settings.hide, text="◄", width=but_set_width, height=but_set_heigth, grid=[0,2])
but_settings_12 = PushButton(window_settings, command=window_settings.hide, text="◄", width=but_set_width, height=but_set_heigth, grid=[1,2])
but_settings_22 = PushButton(window_settings, command=window_settings.hide, text="◄", width=but_set_width, height=but_set_heigth, grid=[2,2])
but_settings_32 = PushButton(window_settings, command=window_settings.hide, text="◄", width=but_set_width, height=but_set_heigth, grid=[3,2])

# Menu for selecting service features
window_service = Window(app, title="Service", layout="grid")
window_service.tk.attributes("-fullscreen", True)
window_service.text_size=but_text_size
window_service.hide()
but_service_00 = PushButton(window_service, command=window_system.show, text="SYS", width=but_width, height=but_height, grid=[0,0])
but_service_10 = PushButton(window_service, command=window_settings.show, text="SET", width=but_width, height=but_height, grid=[1,0])
but_service_20 = PushButton(window_service, text=" ", width=but_width+1, height=but_height, grid=[2,0])
but_service_01 = PushButton(window_service, command=window_timer.show, text="TIME", width=but_width, height=but_height, grid=[0,1])
but_service_11 = PushButton(window_service, lambda:single_show("ALLDATA"), text="ALL", width=but_width, height=but_height, grid=[1,1])
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
window_des = Window(app, title="Navigation", layout="grid")
window_des.tk.attributes("-fullscreen", True)
window_des.text_size=but_text_size
window_des.hide()
but_des_00 = PushButton(window_des, lambda:wpt_nav("nav"), text="WPT", width=but_width, height=but_height, grid=[0,0])
but_des_10 = PushButton(window_des, lambda:single_show("DTW"), text="DTW", width=but_width, height=but_height, grid=[1,0])
but_des_20 = PushButton(window_des, lambda:single_show("navbear"), text="BRG", width=but_width+1, height=but_height, grid=[2,0])
but_des_01 = PushButton(window_des, lambda:single_show("navttg"), text="TTG", width=but_width, height=but_height, grid=[0,1])
but_des_11 = PushButton(window_des, lambda:single_show("naveta"), text="ETA", width=but_width, height=but_height, grid=[1,1])
but_des_21 = PushButton(window_des, command=window_des.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Trip function
window_dep = Window(app, title="Trip control", layout="grid")
window_dep.tk.attributes("-fullscreen", True)
window_dep.text_size=but_text_size
window_dep.hide()
but_dep_00 = PushButton(window_dep, lambda:single_show("tripdist"), text="DIS", width=but_width, height=but_height, grid=[0,0])
but_dep_10 = PushButton(window_dep, lambda:single_show("triptime"), text="TIME", width=but_width, height=but_height, grid=[1,0])
but_dep_20 = PushButton(window_dep, lambda:single_show("tripaver"), text="AVS", width=but_width+1, height=but_height, grid=[2,0])
but_dep_start = PushButton(window_dep, command=trip_start, text="START", width=but_width, height=but_height, grid=[0,1])
but_dep_stop = PushButton(window_dep, command=trip_stop, text="STOP", width=but_width, height=but_height, grid=[1,1], enabled=False)
but_dep_21 = PushButton(window_dep, command=window_dep.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# -------------   NOW  GROUP    -------------------
# Engine
window_eng = Window(app, title="Engine data", layout="grid")
window_eng.tk.attributes("-fullscreen", True)
window_eng.text_size=but_text_size
window_eng.hide()
but_eng_00 = PushButton(window_eng, lambda:single_show("tCO"), text="tCO", width=but_width, height=but_height, grid=[0,0])
but_eng_10 = PushButton(window_eng, lambda:single_show("tENG"), text="tENG", width=but_width, height=but_height, grid=[1,0])
but_eng_20 = PushButton(window_eng, lambda:single_show("tEXH"), text="tEXH", width=but_width+1, height=but_height, grid=[2,0]) 
but_eng_01 = PushButton(window_eng, lambda:single_show("RPM"), text="RPM", width=but_width, height=but_height, grid=[1,1])
but_eng_11 = PushButton(window_eng, lambda:single_show("HRS"), text="HRS", width=but_width, height=but_height, grid=[0,1])
but_eng_21 = PushButton(window_eng, command=window_eng.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Levels
window_lev = Window(app, title="Engine data", layout="grid")
window_lev.tk.attributes("-fullscreen", True)
window_lev.text_size=but_text_size
window_lev.hide()
but_lev_00 = PushButton(window_lev, lambda:single_show("VOL1"), text="CON", width=but_width, height=but_height, grid=[0,0])
but_lev_10 = PushButton(window_lev, lambda:single_show("VOL2"), text="ENG", width=but_width, height=but_height, grid=[1,0])
but_lev_20 = PushButton(window_lev, lambda:single_show("WLS"), text="WLS", width=but_width+1, height=but_height, grid=[2,0]) 
but_lev_01 = PushButton(window_lev, lambda:single_show("FUE"), text="FUE", width=but_width, height=but_height, grid=[1,1])
but_lev_11 = PushButton(window_lev, lambda:single_show("WAT"), text="WAT", width=but_width, height=but_height, grid=[0,1])
but_lev_21 = PushButton(window_lev, command=window_lev.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Weather Station
window_wea = Window(app, title="Meterologics", layout="grid")
window_wea.tk.attributes("-fullscreen", True)
window_wea.text_size=but_text_size
window_wea.hide()
but_wea_00 = PushButton(window_wea, lambda:single_show("tIN"), text="tIN", width=but_width, height=but_height, grid=[0,0])
but_wea_10 = PushButton(window_wea, lambda:single_show("tOUT"), text="tOUT", width=but_width, height=but_height, grid=[1,0])
but_wea_20 = PushButton(window_wea, lambda:single_show("TWS"), text="WIND", width=but_width+1, height=but_height, grid=[2,0]) 
but_wea_01 = PushButton(window_wea, lambda:single_show("HUM"), text="HUM", width=but_width, height=but_height, grid=[1,1])
but_wea_11 = PushButton(window_wea, lambda:single_show("hPa"), text="hPa", width=but_width, height=but_height, grid=[0,1])
but_wea_21 = PushButton(window_wea, command=window_wea.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Seatalk1 converted to NMEA -- Secondary ST1 window
window_ST1_2 = Window(app, title="ST1 control 2", layout="grid")
window_ST1_2.tk.attributes("-fullscreen", True)
window_ST1_2.text_size=but_text_size
window_ST1_2.hide()
but_ST1_2_00 = PushButton(window_ST1_2, lambda:single_show("TWSmax"), text="TWSmax", width=but_width, height=but_height, grid=[0,0])
but_ST1_2_10 = PushButton(window_ST1_2, lambda:single_show("PILOT"), text="PILOT", width=but_width, height=but_height, grid=[1,0])
but_ST1_2_20 = PushButton(window_ST1_2, text=" ", width=but_width+1, height=but_height, grid=[2,0])
but_ST1_2_01 = PushButton(window_ST1_2, lambda:single_show("MAG"), text="COM", width=but_width, height=but_height, grid=[0,1])
but_ST1_2_11 = PushButton(window_ST1_2, lambda:single_show("TSE"), text="SEA", width=but_width, height=but_height, grid=[1,1])
but_ST1_2_21 = PushButton(window_ST1_2, window_ST1_2.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# Seatalk1 converted to NMEA -- Main ST1 window
window_ST1_1 = Window(app, title="ST1 control", layout="grid")
window_ST1_1.tk.attributes("-fullscreen", True)
window_ST1_1.text_size=but_text_size
window_ST1_1.hide()
but_ST1_1_00 = PushButton(window_ST1_1, lambda:single_show("STW"), text="STW", width=but_width, height=but_height, grid=[0,1])
but_ST1_1_10 = PushButton(window_ST1_1, lambda:single_show("TWS"), text="TWS", width=but_width, height=but_height, grid=[1,0])
but_ST1_1_20 = PushButton(window_ST1_1, lambda:single_show("TWD"), text="TWD", width=but_width+1, height=but_height, grid=[2,0])
but_ST1_1_01 = PushButton(window_ST1_1, lambda:single_show("DEP"), text="DPT", width=but_width, height=but_height, grid=[0,0])
but_ST1_1_11 = PushButton(window_ST1_1, command=window_ST1_2.show, text="MORE", width=but_width, height=but_height, grid=[1,1])
but_ST1_1_21 = PushButton(window_ST1_1, window_ST1_1.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# GPS 
window_GPS = Window(app, title="GPS control", layout="grid")
window_GPS.tk.attributes("-fullscreen", True)
window_GPS.text_size=but_text_size
window_GPS.hide()
but_GPS_00 = PushButton(window_GPS, lambda:single_show("SOG"), text="SOG", width=but_width, height=but_height, grid=[0,0])
but_GPS_10 = PushButton(window_GPS, lambda:single_show("gpshead"), text="COG", width=but_width, height=but_height, grid=[1,0])
but_GPS_20 = PushButton(window_GPS, lambda:single_show("gpspos"), text="POS", width=but_width+1, height=but_height, grid=[2,0])
but_GPS_01 = PushButton(window_GPS, lambda:single_show("gpsall"), text="ALL", width=but_width, height=but_height, grid=[0,1])
but_GPS_11 = PushButton(window_GPS, lambda:single_show("SOGmax"), text="MAX", width=but_width, height=but_height, grid=[1,1])
but_GPS_21 = PushButton(window_GPS, window_GPS.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# NOW menu
window_now = Window(app, title="NOW data", layout="grid")
window_now.tk.attributes("-fullscreen", True)
window_now.text_size=but_text_size
window_now.hide()
but_now_00 = PushButton(window_now, command=window_GPS.show, text="GPS", width=but_width, height=but_height, grid=[0,0])
but_now_10 = PushButton(window_now, command=window_wea.show, text="WEA", width=but_width, height=but_height, grid=[1,0])
but_now_20 = PushButton(window_now, command=window_ST1_1.show, text="INS", width=but_width+1, height=but_height, grid=[2,0]) 
but_now_01 = PushButton(window_now, command=window_lev.show, text="LEV", width=but_width, height=but_height, grid=[0,1])
but_now_11 = PushButton(window_now, command=window_eng.show, text="ENG", width=but_width, height=but_height, grid=[1,1])
but_now_21 = PushButton(window_now, command=window_now.hide, text="◄", width=but_width+1, height=but_height, grid=[2,1])

# -----------   MAIN MENU   -------------------

# App = Main Menu
#app.text_size=but_text_size
app.tk.attributes("-fullscreen", True)
but_main_00 = PushButton(app, command=window_dep.show, text="DEP", width=but_width, height=but_height, grid=[0,0])
but_main_10 = PushButton(app, command=window_now.show, text="NOW", width=but_width, height=but_height, grid=[1,0])
but_main_20 = PushButton(app, command=window_des.show, text="DES",  width=but_width+1, height=but_height, grid=[2,0])
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

U = threading.Thread(target=UDPread)
U.start()

display_update()
setload()
serinit()
#display_adjust("z")
app.repeat(1000, timer_update)  # Schedule call to update timer every 1 sec
#if serimport==True:
app.repeat(1000, GPSread) #read data from GPS 1/1 sec

#Run the application
app.display()

# Installation and configuration notes at https://github.com/jbonde/MAIA/blob/master/installation

#EOF
