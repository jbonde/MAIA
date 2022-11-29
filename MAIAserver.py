# MAIA Maritime server: Handling sensor data transmitted via UDP to use for MAIA application
appversion=198

import os
import sys
import glob
import time
from time import sleep
import serial
import socket
from socket import *
from threading import Thread
import time
from time import sleep
import spidev
from gpiozero import LED, Button
import platform
import math
import subprocess
import logging
import datetime
from datetime import datetime
from datetime import date

#time_string = "Hour Min 21 June, 2018"
#time_now = time.strptime(time_string, "%H %M %d %B, %Y")
#time_now = time.strptime("%a %b %d %H:%M:%S ")
time_local = time.localtime() # get struct_time
time_now = time.strftime("%Y%m%d_%H%M%S", time_local)

#sys.stdout = open('/home/pi/logconsole.txt', 'w') #send console text to file instead of display

def log_error(TheError): #file with error logs
    try:
        with open("/home/pi/logerror.txt","a") as f:
            f.write(str(time_now) + ": " + str(TheError) + "  "   +  "\n")
            f.close
        print("logerror.txt updated " + str(time_now) + ": " + str(TheError))
    except:
        print("logerror.txt failed " + str(time_now) + ": " + str(TheError))

log_error (" ") # make some space after previous log
log_error ("MAIA Maritime server version " + str(appversion))
OSplatform=(platform.system())
log_error("OSplatform = " + str(OSplatform))
log_error ('Argument List: ' + str(sys.argv))
try:
    log_error ('passed value: ' + str(sys.argv[1]))
except:
    log_error("no arguments passed")

buzzer = LED(21) # pin 40

try:
    from bmp280 import BMP280
    log_error ("BMP280 imported")
except ImportError:
    log_error("BMP280 import error")

# Initializing MCP3008 chip for voltage readings
MCP3008=False

try:
    from smbus2 import SMBus
    bus = SMBus(1)
    measurebmp = BMP280(i2c_dev=bus)
    log_error ("SMbus imported for BMP280")
    # Open SPI bus
    spi = spidev.SpiDev()
    spi.open(0,0)
    spi.max_speed_hz=1000000
    MCP3008=True
except ImportError:
    from smbus import SMBus
    log_error ("no SMbus for BMP280")
    MCP3008=False
try:
    import Adafruit_DHT
    DHT_SENSOR = Adafruit_DHT.DHT22
    DHT_PIN = 26
    log_error ("DHT sensor attached")
except ImportError:
    log_error("No DHT sensor attached")

# NMEA string
gpsdata="No GPS attached" # string carrying the gps information
nmeadata="nmeadata" # string with NMEA sentences from Autohelm
nmearead="No nmea"
NMEAstring=None

# Counters
udpcounter=0
VOLcounter=0
CSVcounter=0

#WEA=[]
tBMP280=None #tENG
tENGmax=0
pressure=None
presMAX=0
humidity=None
humMAX=0
tDHT22=None #tIN
tINmax=0

# Initialize 18B20 sensors
temperature = 0 # Temp of the 18B20 sensors
t18B20=0 # Outdoor temp
tOUTmax=0
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
foldernumber=0

# AUTOHELM SEATALK 1 INSTRUMENTS
# Standard NMEA0183 strings
DBT="$IIDBT,0.00,f,0.00,M,," # Depth Below Transducer
VHW="$IIVHW,,,111.,M,00.00,N,," # heading (magnetic compass) and water speed 
VWR="$IIVWR,0.00,R,0.00,N,,,," #Relative Wind Speed and Angle
MTW="$IIMTW,0.00,C" #Mean Temperature of Water
HDM="$IIHDM,222.,M" # Heading - Magnetic - Only broadcasted if Auto pilot power is turned on.
HSC="$IIHSC,,,333.,M" # Heading Steering Command. Auto pilot heading. Only broadcasted in AUTO mode.

# Preferred NMEA0183 string from GPS
RMC="$GPRMC,hhmmss,A,4916.45,N,12311.12,W,000.5,054.7,yymmdd,020.3,E*68" # Sample GPS string 

# Custom NMEA0183 strings from sensors etc
VOL="$IIVOL,VOL1,VOL2,VOL3,VOL4,VOL5,VOL6,V"# Analogue readings of voltage. To be expanded with level sensors
WEA="$GPWEA,tIN,tOUT,pressure,humidity,tENGINEroom," # string carrying the meteorological information (temps, humidity and pressure)
MAX="$GPMAX,TWSmax,SOGmax,STWmax,DEPmax,tOUTmax,tINmax,tENGmax,presMAX,humMAX,vol1MAX,vol2MAX,vol3MAX,," # Max values measured since boot

#Seatalk 1 variables
DEP=0 #Depth
DEPmax=0
AWS=0 #Apparent wind speed
AWSmax=0
AWA=0 #Apparent wind angle
TSE=0 #Sea temperature
STW=0 #log: speed through water : $IIVHW
STWmax=0
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

# GPS
GPSstring=None
#GPS variables
SOG=0
SOGmax=0 # Max speed at trip
COG=0
GPSNS=None #N or S
GPSEW=None #E or W
UTC=None #Time in UTC format
UTCOS=None # Time string formatted for OS time update when out of network
GPSdate=None #Date received from GPS<
latnow=0 #55.942508 #Current position in DEGDEC format
lonnow=0 #11.870814
latdec=0
londec=0

log_error("system time " + str(time_now))

# Define MC3008 analogue channels
consume_battery = 0
engine_battery  = 1
spare_battery  = 2

# LOG FILE
logdir='/home/pi/csv/'
dir = os.path.join(str(logdir))
if not os.path.exists(dir):
    os.mkdir(dir)
log_data = []
logname=str(logdir) + 'time' + '.csv' # Logfile with all data when powered on. Name will change according to time for each new file created
lognow=str(logdir) + 'time' + '.csv' # Logfile with current data. Will be exchanged at interval time. name will change according to time for each new file created
logfile_created=False # Is log file created when GPS Date is received?

#SERIAL SETUP
port1 = "/dev/ttyUSB0"  # USB serial (Adafruit GPS etc)
port2 = "/dev/ttyUSB1"  # USB serial (Adafruit GPS etc)
port3 = "/dev/ttyACM0"  # RPi with BS-708 receiver at USB port
port4 = "/dev/ttyACM1"  # RPi with BS-708 receiver at USB port
port5 = "/dev/ttyAMA0"  # RPi Zero GPIO PIN 10
port6 = "/dev/ttyS0"    # RPi 3 + Zero PIN 10
serialGPS=False # Check if GPS is available at serial port
portGPS=port3 #RPiZ in boat
#portGPS=port4 #RPi model 4
portNMEA = port5

baudGPS=9600 # baudrate for GPS port
baudNMEA=4800 # baudrate for NMEA 
porttimeout=1

#UDP SETUP
UDPaddress='255.255.255.255'
UDPport=2000
UDPtimeout=1
UDPbusy=False #Pausing operations while submitting UDP

# Setting up GPS at USB connector
try:
    serGPS = serial.Serial(portGPS, baudrate = baudGPS, timeout=porttimeout)
    serialGPS=True
    log_error("GPS connection OK at USB connector")
except:
    serialGPS=False
    log_error("no USB GPS connection")

# Setting up NMEA input at GPIO
try:
    sernmea = serial.Serial(portNMEA, baudrate = baudNMEA, timeout=porttimeout)
    log_error("Serial connection for NMEA ready at GPIO 15 pin 10 with baudrate " + str(baudNMEA))
except:
    log_error("no serial connection for NMEA")

# Reading SPI data from MCP3008 chip
def ReadChannel(channel):
    adc = spi.xfer2([1,(8+channel)<<4,0])
    data = ((adc[1]&3) << 8) + adc[2]
    return data
 
# Converting data to voltage level,
def ConvertVolts(data,places):
    try:
        volts = float((data * 23) / 1023)
        volts = round(volts,places)
    except:
        volts=0
        log_error("volts not float")
    return volts

def ReadVolts():
    global VOL
    try:
        if MCP3008==True:
            consume = ReadChannel(consume_battery)
            consume_volts = ConvertVolts(consume,2)

            # Read voltage of engine battery
            engine = ReadChannel(engine_battery)
            engine_volts = ConvertVolts(engine,2)
            
            # Read voltage of spare battery
            spare = ReadChannel(spare_battery)
            spare_volts = ConvertVolts(spare,2)
        else:
            consume_volts=0
            engine_volts=0
            spare_volts=0
        VOL="$IIVOL," + str(consume_volts) + "," + str(engine_volts) +"," + str(spare_volts) + ",V"
        if UDPbusy==False:
            UDPsubmit(VOL)
    except:
        log_error("Can't read voltage"  + str(time_now))

def NMEAread():
    global nmeadata,DBT,VHW,VWR,MTW,HDM,HSC # Standard NMEA strings
    global AWSmax,NMEAstring,gpsdata,RMC,VOL,WEA,DEPmax,AWD,TWSmax,MAG
    global NMEAstring,tempin,tempout,tempENGINE,pressure,humidity,UDPaddress,TWSmax,SOGmax,STWmax
    global DEP,TWS,TWD,TSE,STW,AWA,AWS,AUT #Seatalk1
    global VOL1,VOL2,VOL3
    global AUT,AUTSET,AUTSETCOUNT,AUTON,AUTONCOUNT # Autopilot values

    # Read NMEA0183 serial instrument data from Autohelm converter
    try:
        NMEAstring = sernmea.readline().decode('ascii', errors='replace')
    except:
        log_error("NMEA read error " + str(time_now))
    if len(str(NMEAstring))>8:
        header = NMEAstring[3:6] # slicing out the header information (3 letters needed)
        if header=="DBT": # DEPTH
            DBTarray=NMEAstring.split(",") #DBT - Depth Below Transducer
            try:
                DEP=DEP
                if DBTarray[3]!="":
                    DEP=DBTarray[3]
            except:
                log_error("DBT array error")
            try:
                if float(DEP)>DEPmax:
                    DEPmax=float(DEP)
            except:
                log_error("DEPmax error")
            DBT=NMEAstring
            if UDPbusy==False:
                UDPsubmit(DBT)
        if header=="VHW": 
            VHWarray=NMEAstring.split(",") #make array according to comma-separation in string
            try:
                MAG=VHWarray[3] # Magnetic compass heading
                STW=0
                if VHWarray[5]!="":
                   STW=float(VHWarray[5])
                   if STW>STWmax:
                    STWmax=STW
            except ValueError:
                log_error("STW error")
            VHW=NMEAstring
            if UDPbusy==False:
                UDPsubmit(VHW)
        if header=="VWR": # WIND DATA
            VWR=NMEAstring
            VWRarray=NMEAstring.split(",") #make array according to comma-separation in string
            try:
                AWA=float(VWRarray[1]) # Wind angle to bow magnitude in degrees
                AWD=VWRarray[2] # Wind direction Left/Right of bow
                if AWD=="R":
                    AWA=AWA
                else:
                    AWA=-AWA
            except:
                log_error("AWA error")
            try:
                AWS=float(VWRarray[3])*0.514444 #(if knots)
            except:
                log_error("AWS not float")
                
            if AWS>AWSmax:
                AWSmax=AWS  
            # Calculate true wind
            AWA_rad=math.radians(AWA) # convert angle deg to radians
            if AWA_rad==0: # Avoid cos(0)
                AWA_rad=0.1            
            SOGms=SOG*0.514444 #Speed over ground in m/s
            TWS=math.sqrt(math.pow(AWS,2)+math.pow(SOGms,2)-2*AWS*SOGms*math.cos(AWA_rad)) # True wind speed
            if TWS>TWSmax:
                TWSmax=TWS
            if TWS<0.1: #Avoid 0 division 
                TWS=0.1
            try:
                if AWD=="R":
                    TWD=math.degrees(math.acos((AWS*math.cos(AWA_rad)-SOGms)/TWS)) # True wind direction (compass)
                else:
                    TWD=math.degrees(-math.acos((AWS*math.cos(AWA_rad)-SOGms)/TWS))
            except:
                TWD=1
                log_error("TWD error")
            if TWD<0:
                TWD=360+TWD
            if TWD>=360:
                TWD=TWD-360
            # Create new NMEA0183 (not standardized) wind string with the addition of calculated wind speed and direction
            VWR="$IIVWR," + str(abs(AWA)) + "," + str(AWD) + "," + str(AWS) + ",N," + str(TWD) + "," + str(TWS) + ",," #Relative and true Wind Speed and Angle
            if UDPbusy==False:
                UDPsubmit(VWR)
        if header=="MTW": # Sea temp (not working)
            MTW=NMEAstring
            if UDPbusy==False:
                UDPsubmit(MTW)
        if header=="HDM": # HDM="$IIHDM,222.,M" # Heading - Magnetic - Auto pilot. Only broadcasted if turned on.
            HDM=NMEAstring
            if UDPbusy==False:
                UDPsubmit(HDM)
            AUTON=True
            AUTONCOUNT=20
        if header=="HSC": # HSC="$IIHSC,,,333.,M" # Heading Steering Command. Auto pilot heading. Only broadcasted in AUTO mode.
            AUTSET=True
            AUTSETCOUNT=20
            HSCarray=NMEAstring.split(",")
            HSC=NMEAstring
            try:
                AUT=HSCarray[3]
            except:
                log_error("AUT array error")        
                
            if UDPbusy==False:
                UDPsubmit(HSC)
        # The following is not provided as instrument NMEA0183 data - only for testing with simulator
        if header=="RMC": # Information from GPS @ USB connector
            RMC=NMEAstring
            RMCsplit(NMEAstring)
            if UDPbusy==False:
                UDPsubmit(RMC)
        if header=="VOL": # Voltage inputs from 3008
            VOL=NMEAstring
            if UDPbusy==False:
                UDPsubmit(VOL)
        if header=="WEA": # Met sensor inputs from DHT22, BMP280 and 18B20
            WEA=NMEAstring
            if UDPbusy==False:
                UDPsubmit(WEA)

def GPSread():
    global RMC
    if serialGPS==True: # Read GPS from USB instead
        gpsdata = serGPS.readline().decode('ascii', errors='replace')
        header = gpsdata[3:6]
        if header=="RMC": # the line containing the needed information like position, time and speed etc....
            RMCsplit(gpsdata)
            RMC=str(gpsdata) # for UDP use
            if UDPbusy==False:
                UDPsubmit(RMC)
            if logfile_created==False:
                if UTC!="":
                    if GPSdate!="":
                        #  set RPi date and time to GPS “sudo date -s 'YYYY-MM-DD HH:MM:SS'“
                        GPSdatetimestring="20" + str(GPSdate)[4:6]+"/"+str(GPSdate)[2:4]+"/"+str(GPSdate)[0:2]+" "+str(UTC)[0:2]+":"+str(UTC)[2:4]+":"+str(UTC)[4:6]
                        log_error(GPSdatetimestring)
                        try:
                            subprocess.call(['sudo','date','-s',str(GPSdatetimestring)])
                            log_error("Date and time set to UTC")
                        except:
                            log_error("could not set time from GPS")
                        log_create()

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

def RMCsplit(RMCstring):
    global UTC,GPSdate,COG,SOG,COG,SOGmax,latnow,lonnow,latdec,londec
    RMCarray=RMCstring.split(",") #make array according to comma-separation in string
    try:
        latnow=RMCarray [3]
        latNSEW=RMCarray [4]
        lonnow=RMCarray [5]
        lonNSEW=RMCarray [6]
    except:
        log_error("lat lon error")
    #convert positions to decimal
    try:
        latdec=dmm2dec(latnow,latNSEW)
        londec=dmm2dec(lonnow,lonNSEW)
    except:
        log_error("Dec pos error")
    try:
        UTC=(RMCarray[1])[0:6]
        GPSdate=RMCarray [9]
    except:
        log_error("UTC/Date array error")
    try:
        SOG=float(RMCarray [7]) # knots
    except:
        SOG=0
        log_error("SOG not float")
    if SOG>SOGmax:
        SOGmax=SOG
    COG=0
    try:
        if RMCarray [8]!="":
            COG=float(RMCarray [8])
    except:
        COG=0
        log_error("COG not float")

def myping(host):
    try:
        response = os.system("ping -c 1 " + host)
        if response == 0:
            return True
        else:
            return False
    except:
        log_error("ping not possible") 

def MAXvalues():
    global MAX
#    MAX="$GPMAX,TWSmax,SOGmax,STWmax,DEPmax,tOUTmax,tINmax,tENGmax,presMAX,humMAX,vol1MAX,vol2MAX,vol3MAX,," # Max values measured since boot
    MAX="$GPMAX,"+str(TWSmax)+","+str(SOGmax)+","+str(STWmax)+","+str(DEPmax)+","+str(tOUTmax)+","+str(tINmax)+","+str(tENGmax)+","+str(presMAX)+","+str(humMAX)+",,," # Max values measured since boot
    if UDPbusy==False:
        UDPsubmit(MAX)

def UDPsubmit(UDPstring):
    global UDPbusy

    #if myping("192.168.0.1")==True:
    UDPbusy=True
    UDPencoded = str.encode(UDPstring + "\n")
    try:
        UDPsocket = socket(AF_INET, SOCK_DGRAM)
        UDPsocket.settimeout(.02)
#        print("udp.timeout " + str(udp.timeout))
        #print ("IP: " + str(udp.getsockname()[0]))
        UDPsocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        UDPsocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        UDPsocket.sendto(UDPencoded, (UDPaddress, UDPport))
    except UDPsocket.timeout:
        log_error("UDP timeout")
        #continue
    except OSError:
        log_error("OSError")
    finally:
        UDPsocket.close
    #except OSError:
    #   udp.close
#     log_error("UDP submit error " + str(e))
    UDPbusy=False

def weasensors():
    while True:
        # Loop rReading data from meteorological sensors 18B20, BMP280 and DHT22
        global WEA,tBMP280,pressure,humidity,tDHT22,t18B20,tOUTmax,tINmax,tENGmax,presMAX,humMAX

        try:
            tBMP280 = '{:4.1f}'.format(measurebmp.get_temperature())
            if float(tBMP280)>tENGmax:
                tENGmax=float(tBMP280)
            pressure = '{:4.0f}'.format(measurebmp.get_pressure())
            if float(pressure)>presMAX:
                presMAX=float(pressure)
        except:
            log_error("BMP error")
        try:
            humidity, tDHT22 = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
#            tDHT22 = '{:4.1f}'.format(tDHT22)
            if float(tDHT22)>tINmax:
                tINmax=float(tDHT22)
            if float(humidity)>humMAX:
                humMAX=float(humidity)
        except:
            log_error("DHT error")
        try:
            for i in range(len(deviceIDs)):
                for i in range(len(deviceIDs)):
                    a=deviceIDs[i]
                    TermoFile(i)
                    for t in range(len(TempIDs)):             
                        b=TempIDs[t][1]
                        if a==b:
                            temperature=TermoSplit()
                            #print (str(TempIDs[t][0]) + " ID " + str(TempIDs[t][1]))
                            #print (str(TempIDs[t][3]) + " " + str(temperature) + " deg C")
                            t18B20=temperature 
                            if t18B20>tOUTmax:
                                tOUTmax=t18B20
        except:
            log_error("18B22 error")

        WEA="$GPWEA," + str(tDHT22) + "," + str(t18B20) + "," + str(pressure) + "," + str(humidity) + "," + str(tBMP280) + "," + " "  
        if UDPbusy==False:
            UDPsubmit(WEA)
        sleep(300)

#Array with information about all tested sensors incl. color code, sensor ID, spreadsheet name, function and spreadsheet cell
TempIDs = ["BLACK", "28-000005b16567", "out", "Outside temperature", "16", "X"],\
	  ["BLANK", "28-000009140d56", "out2", "Outside temperature2", "27", "X"], \
	  ["BROWN", "28-000005b226ae", "water", "Water tank temp", "17", "A"], \
	  ["RED", "28-000005b217e2", "radf", "Radiators forward temp", "18", "B"],\
	  ["ORANGE", "28-000005b23020", "radr", "Radiators return temp", "19", "C"],\
	  ["YELLOW", "28-000005b21d0d", "heatf", "Received power heating temp", "20", "D"], \
	  ["GREEN", "28-000005b1b646", "heatr", "Returned power heating temp", "21", "E" ],\
	  ["BLUE", "28-000005b1d70e", "floorf", "Floor heating forward temp", "22", "F"], \
	  ["PURPLE", "28-000005b217eb", "floorr", "Floor heating return temp", "23", "G"],\
	  ["RED", "28-000005b22544", "dining", "Dining Room", "24", "X"],\
	  ["ORANGE", "28-000005b1725b", "living", "Living Room", "25", "X"],\
	  ["LOST BROWN", "28-000005b1a9e9", "xx", "xx", "26", "X"],\
	  ["ELMA", "28-000009130002", "Elma", "Elma sensor", "27", "Z"]
    
def TermoRead():
    #Compare the two arrays in order to know which sensors to use
    global t18B20,tOUTmax
    for i in range(len(deviceIDs)):
        a=deviceIDs[i]
        TermoFile(i)
        for t in range(len(TempIDs)):             
            b=TempIDs[t][1]
            if a==b:
                temperature=TermoSplit()
                #print (str(TempIDs[t][0]) + " ID " + str(TempIDs[t][1]))
                #print (str(TempIDs[t][3]) + " " + str(temperature) + " deg C")
                t18B20=temperature 
                if t18B20>tOUTmax:
                    tOUTmax=t18B20

def TermoRaw():
    # Read data from the sensor
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def TermoSplit():
    # Split data from sensor and find temperature in Celcius
    global temperature
    lines = TermoRaw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = TermoRaw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        try:
            temperature = float(temp_string) / 1000.0
        except:
            temperature=0
            log_error("temp not float")
        return temperature #, temp_f

def TermoFile(n):
    # Set path to sensor file
    global device_file
    device_folder = glob.glob('28*')[n]
    #print("device ID")
    #print(device_folder)
    device_file = device_folder + '/w1_slave'

#    MAX="$GPMAX,TWSmax,SOGmax,STWmax,DEPmax,tOUTmax,tINmax,tENGmax,presMAX,humMAX,vol1MAX,vol2MAX,vol3MAX,," # Max values measured since boot

log_header = ["Date","UTC","Lat","Lon","Lat Dec","Lon Dec","SOG","SOGmax","STW","STWmax","COG","tOUT","tOUTmax","tIN","tINmax","tENG","tENGmax","humidity","humMAX","Air pressure","MAX pressure","AWA","AWS","TWD","TWS","TWSmax","Depth","tSEA","MAG COMP","A.PILOT ON","A.PILOT ENABL","A. PILOT HEADING"] 
def log_create():
    global logname,lognow,logfile_created
    #Creating new file after GPS time is received and inserting header
    if logfile_created==False:
        if OSplatform=="Linux":
            logname='/home/pi/' + str(GPSdate)[4:6] + str(GPSdate)[2:4] + str(GPSdate)[0:2] + "-" + str(UTC) + '.csv'
            lognow='/home/pi/' + "lognow" + '.csv'
        else:
            logname='C:\\Users\\bonde\\Dropbox\\Code\\Python\\MAIA\\' + str(time_now) + '.csv' 
            lognow='C:\\Users\\bonde\\Dropbox\\Code\\Python\\MAIA\\' + "lognow" + '.csv'             
        with open(logname,"w") as f:
            f.write(",".join(str(value) for value in log_header) + "\n")
        with open(lognow,"w") as g:
            g.write(",".join(str(value) for value in log_header) + "\n")
        log_error ("New log created: " + str(logname))
        log_error ("New lognow created: " + str(lognow))
        logfile_created=True
        log_update()
        buzzer.on()
        sleep(1)
        buzzer.off()

def log_update(): # save data to logfile
    global log_data,log_header
    #global tBMP280,tDHT22,pressure,humidity
    if logfile_created==True: 
        try:    
            # log_header = ["Date","UTC","Lat","Lon","Lat Dec","Lon Dec","SOG","SOGmax","STW","STWmax","COG","tOUT","tOUTmax","tIN","tINmax","tENG","tENGmax","humidity","humMAX","Air pressure","MAX pressure","AWA","AWS","TWD","TWS","TWSmax","Depth","tSEA","MAG COMP","A.PILOT ON","A.PILOT ENABL","A. PILOT HEADING"]
            log_data = [GPSdate,UTC,latnow,lonnow,latdec,londec,str(SOG)[:5],SOGmax,STW,STWmax,COG,t18B20,tOUTmax,tDHT22,tINmax,tBMP280,tENGmax,humidity,humMAX,pressure,presMAX,AWA,AWS,int(TWD),'{:4.1f}'.format(TWS),TWSmax,DEP,TSE,MAG,AUTON,AUTSET,AUT]
            with open(logname,"a") as f:
                f.write(",".join(str(value) for value in log_data)+ "\n")
        except:
            log_error("log failed to update")
            
        try:    
            with open(lognow,"w") as f:
                f.write(",".join(str(value) for value in log_header)+ "\n")
                f.write(",".join(str(value) for value in log_data)+ "\n")
        except:
            log_error("lognow failed to update")

def log_website():
    l = open('/home/pi/csv/lognow.csv', 'w')
    for i in range(len(log_header)): #Order data vertically
        l.write(str(log_header[i])+ "," + str(log_data[i]) + "\n")
    #  l.write(str(header) + "\n" + str(log_data))
    l.close()


buzzer.on()
sleep(0.2)
buzzer.off()
sleep(0.2)
buzzer.on()
sleep(0.2)
buzzer.off()

try:
    base_dir = '/sys/bus/w1/devices/'
    os.chdir(base_dir)
    log_error("directory changed to")
    log_error(base_dir)
    log_error("Detecting 18B20 devices ")
    deviceIDs=glob.glob('28*')
    log_error ("Total amount of tested sensors: " + str(len(TempIDs)))
    log_error ("Amount of attached temp sensors: " + str(len(deviceIDs)))
    log_error ("ID of attached sensors: " + str(deviceIDs))
except:
    log_error("no 18B20 devices")

w=Thread(target=weasensors)
w.start()

#ipadress=socket(getaddrinfo)
#print(ipadress)

while True:
    CSVcounter+=1
    VOLcounter+=1

    #For use with auto pilot:
    AUTONCOUNT-=1
    if AUTONCOUNT==0:
        AUTON=False
    AUTSETCOUNT-=1
    if AUTSETCOUNT==0:
        AUTSET=False

    # Read inputs from devices other than met sensors (which read in a thread)
    try:
        NMEAread()
    except:
        log_error("NMEAread call error")
    sleep(.05)
    try:
        GPSread()
    except:
        log_error("GPSread call error")
    sleep(.05)
    if VOLcounter==100:
        try:
            ReadVolts()
        except:
            log_error("ReadVolts call error")
        VOLcounter=0
    MAXvalues()
    if logfile_created==True:
        if CSVcounter==600:
            log_update()
            CSVcounter=0
    

'''
# Installation notes
Enable i2c connection in sudo raspi-config
Enable 1-wire connection in sudo raspi-config

Enable SPI Interface
lsmod | grep spi_
check using :
sudo apt-get install -y python-dev python3-dev
cd ~
git clone https://github.com/Gadgetoid/py-spidev.git
cd py-spidev
sudo python setup.py install
sudo python3 setup.py install
cd ~

Show ID of connected devices from command prompt:

sudo modprobe w1-gpio
sudo modprobe w1-therm
ls /sys/bus/w1/devices/ | grep -e "28-"
cd /sys/bus/w1/devices
ls 

sudo pip3 install Adafruit_DHT
sudo pip3 install BMP280
sudo pip3 install smbus2

AUTORUN, EDIT:
sudo nano /home/pi/.bashrc
sudo python3 /home/pi/MAIAserver.py

'''