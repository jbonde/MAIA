# MAIA Marine server: Handling sensor data transmitted via UDP to use for MAIA application
appversion=105

import os
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

print ("appversion " + str(appversion))
OSplatform=(platform.system())
print("OSplatform = " + str(OSplatform))

buzzer = LED(21) # pin 40

try:
    from bmp280 import BMP280
    print ("BMP280 imported")
except ImportError:
    print ("BMP280 import error")

# Initializing MCP3008 chip
MCP3008=False

try:
    from smbus2 import SMBus
    bus = SMBus(1)
    measurebmp = BMP280(i2c_dev=bus)
    print ("SMbus imported")
    # Open SPI bus
    spi = spidev.SpiDev()
    spi.open(0,0)
    spi.max_speed_hz=1000000
    MCP3008=True
except ImportError:
    from smbus import SMBus
    print ("no SMbus")
    MCP3008=False

try:
    import Adafruit_DHT
    DHT_SENSOR = Adafruit_DHT.DHT22
    DHT_PIN = 26
except ImportError:
    print ("No DHT sensor attached")

# NMEA string
gpsdata="No GPS attached" # string carrying the gps information
metdata="$GPWEA,0.0,0.0,0000,0.0,0.0," # string carrying the meteorological information (temps, humidity and pressure)
nmeadata="00000" # string with NMEA sentences from Autohelm
nmearead="No nmea"
NMEAstring=None

# Counters
udpcounter=0
metcounter=0
csvcounter=0

#metdata=[]
tempin=None
pressure=None
humidity=None
tempout=None

# Initialize 18B20 sensors
temperature = 0 # Temp of the 18B20 sensors
t18B20=0
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
foldernumber=0

# AUTOHELM SEATALK 1 INSTRUMENTS
#Strings
DBT="$IIDBT,0.00,f,0.00,M,," # Depth Below Transducer
VHW="$IIVHW,,,0.00,N,," #Water speed and heading
VWR="$IIVWR,0.00,R,0.00,N,,,," #Relative Wind Speed and Angle
MTW="$IIMTW,0.00,C" #Mean Temperature of Water
VOL="$IIVOL,0.00,0.00,0.00,V"#Analogue readings of voltage

# Instrument Variables
DEP=0 #Depth
TWS=0 #True wind speed
TWSmax=0 # Max wind speed
TWD=0 #True wind direction
TWA=0 #True wind angle to COG
AWS=0 #Apparent wind speed
AWA=0 #Apparent wind angle
TSE=0 #Sea temperature
STW=0 #log: speed through water

# GPS
GPSstring=None
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
COG=0
GPSNS=None #N or S
GPSEW=None #E or W
UTC=None #Time in UTC format
UTCOS=None # Time string formatted for OS time update when out of network
GPSdate=210101 #Date received from GPS
SOGmax=0 # Max speed at trip

# Define MC3008 analogue channels
consume_battery = 0
engine_battery  = 1
spare_battery  = 2

# LOG FILE
log_data = []
logname='/home/pi/csv/' + 'time' + '.csv' # name will change according to time for each new file created
logfile_created=False # Is log file created when GPS Date is received?
log_update=60 #seconds between each log update
log_header = ["Date","UTC","UTZ", "SOG","SOGmax","COG","tripdistance",
            "triptime(min)","latdep","londep","Latitude","Longitude",
            "latdes","londes","destination","tempin","tempout","humidity",
            "HPa","AWA","AWS","TWD","TWS","TWSmax","BRG","DTW","Depth","SEA"]


#SERIAL SETUP
port1 = "/dev/ttyUSB0"  # USB serial (Adafruit GPS etc)
port2 = "/dev/ttyUSB1"  # USB serial (Adafruit GPS etc)
port3 = "/dev/ttyACM0"  # RPi with BS-708 receiver at USB port
port4 = "/dev/ttyACM1"  # RPi with BS-708 receiver at USB port
port5 = "/dev/ttyAMA0"  # RPi Zero GPIO PIN 10
port6 = "/dev/ttyS0"    # RPi 3 + Zero PIN 10
serialGPS=False # Check if GPS is available at serial port
portGPS=port3
portNMEA = port6

baudGPS=9600 # baudrate for GPS port
baudNMEA=4800 # baudrate for NMEA 
porttimeout=1

# Setting up GPS at USB connector
try:
    serGPS = serial.Serial(portGPS, baudrate = baudGPS, timeout=porttimeout)
    serialGPS=True
    print("GPS connection OK at USB connector")
except:
    print("no USB GPS connection")
    serialGPS=False

# Setting up NMEA input at GPIO
try:
    sernmea = serial.Serial(portNMEA, baudrate = baudNMEA, timeout=porttimeout)
    print("Serial connection for NMEA ready at GPIO pin 15 with baudrate " + str(baudNMEA))
except:
    print("no serial connection for NMEA")

#UDP SETUP
UDPaddress='255.255.255.255'
UDPport=2000

# Reading SPI data from MCP3008 chip
def ReadChannel(channel):
    adc = spi.xfer2([1,(8+channel)<<4,0])
    data = ((adc[1]&3) << 8) + adc[2]
    return data
 
# Converting data to voltage level,
def ConvertVolts(data,places):
  volts = (data * 24) / float(1023)
  volts = round(volts,places)
  return volts

def ReadVolts():
    global VOL
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

def NMEAread():
    global nmeadata,DBT,VHW,VWR,MTW,TWS,TWSmax,NMEAstring
    # Read NMEA0183 serial instrument data from Autohelm converter
    NMEAstring = sernmea.readline().decode('ascii', errors='replace')
    print(NMEAstring)
    if len(str(NMEAstring))>8:
        header = NMEAstring[3:6] # slicing out the header information (3 letters needed)
        if header=="DBT": 
            DBT=NMEAstring
        if header=="VHW": 
            VHW=NMEAstring
        if header=="VWR": 
            VWR=NMEAstring
            VWRarray=NMEAstring.split(",") #make array according to comma-separation in string
            TWS=(VWRarray [1])
            if TWS>TWSmax:
                TWSmax=TWS  
        if header=="MTW": 
            MTW=NMEAstring

def GPSread():
    global GPSstring,gpsdata,NMEAstring
    global UTC,GPSdate,GPSspeed,COG,GPSNS,GPSEW,SOG,COG,SOGmax
    global gpsdata,UTZ,UTZhours,TIMEZ,UTCOS,GPSNS,GPSEW,dayname,UDPupdate,daynumber

    # Check if GPS info is sent to the serial port
    SERstring = sernmea.readline().decode('ascii', errors='replace')
    if serialGPS==True: # Read GPS from USB instead
        SERstring = serGPS.readline().decode('ascii', errors='replace')
        #print ("GPS data: " + str(gpsread))

    header = SERstring[3:6]
    if header=="RMC": # the line containing the needed information like position, time and speed etc....
        RMCarray=GPSstring.split(",") #make array according to comma-separation in string
        UTC=(RMCarray [1])
        GPSdate=(RMCarray [9])
        SOG=(float(RMCarray [7])) # knots
        if SOG>SOGmax:
            SOGmax=SOG
        if RMCarray [8]!="":
            COG=(float(RMCarray [8]))
        else:
            COG=0
        log_create()

def UDPmessage():
    metbytes = str.encode(metdata)
    gpsbytes = str.encode(gpsdata)
    DBTbytes = str.encode(DBT)
    VHWbytes = str.encode(VHW)
    VWRbytes = str.encode(VWR)
    MTWbytes = str.encode(MTW)
    VOLbytes = str.encode(VOL)
    
    udp = socket(AF_INET, SOCK_DGRAM)
    udp.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    udp.sendto(metbytes, (UDPaddress, UDPport))
    print ("Weather data sent:" +str(metdata))
    sleep(0.1)
    udp.sendto(gpsbytes, (UDPaddress, UDPport))
    print ("GPS data sent:" +str(gpsdata))
    sleep(0.1)
    udp.sendto(VOLbytes, (UDPaddress, UDPport))
    print ("VOLTAGE data sent:" +str(VOLbytes))
    udp.sendto(DBTbytes, (UDPaddress, UDPport))
    print ("DEPTH data sent:" +str(DBTbytes))
    udp.sendto(VHWbytes, (UDPaddress, UDPport))
    print ("LOG SPEED data sent:" +str(VHWbytes))
    udp.sendto(VWRbytes, (UDPaddress, UDPport))
    print ("WIND data sent:" +str(VWRbytes))
    udp.sendto(MTWbytes, (UDPaddress, UDPport))
    print ("SEA TEMP data sent:" +str(MTWbytes))

def metsensors():
    # Reading data from meteorological sensors BMP280 and DHT22
    global metdata,tempin,pressure,humidity,tempout
    try:
        tempin = '{:4.1f}'.format(measurebmp.get_temperature())
        print ("indoor temp deg C: " + str(tempin))
        pressure = '{:4.0f}'.format(measurebmp.get_pressure())
        print ("pressure HPa: " + str(pressure))
    except:
        print("BMP error")
    try:
        humidity, tempout = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
        tempout = '{:4.1f}'.format(tempout)
        print ("outdoor temp deg C: " + str(tempout))
        humidity = '{:2.0f}'.format(humidity)
        print ("humidity %: " + str(humidity))
    except:
        print("DHT error")
    metdata = "$GPWEA," + str(tempin) + "," + str(tempout) + "," + str(pressure) + "," + str(humidity) + "," + str(t18B20) + "," + " "  
    print (metdata)

def metcsv():
    # update csv file with readings
    print("csv updated")

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
	  ["ELMA", "28-000009130002", "Elma", "Elma test sensor", "27", "Z"]
    
def TermoRead():
    #Compare the two arrays in order to know which sensors to use
    global t18B20
    for i in range(len(deviceIDs)):
        a=deviceIDs[i]
        TermoFile(i)
        for t in range(len(TempIDs)):             
            b=TempIDs[t][1]
            if a==b:
                temperature=TermoSplit()
                print (str(TempIDs[t][0]) + " ID " + str(TempIDs[t][1]))
                print (str(TempIDs[t][3]) + " " + str(temperature) + " deg C")
                t18B20=temperature

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
        temp_c = float(temp_string) / 1000.0
        #temp_f = temp_c * 9.0 / 5.0 + 32.0
        temperature=temp_c
        return temp_c #, temp_f

def TermoFile(n):
    # Set path to sensor file
    global device_file
    device_folder = glob.glob('28*')[n]
    #print("device ID")
    #print(device_folder)
    device_file = device_folder + '/w1_slave'

def log_create():
    global logname,logfile_created
    #Creating new file after GPS time is received and inserting header
    if logfile_created==False:
        if OSplatform=="Linux":
            logname='/home/pi/' + str(GPSdate) + "-" + str(UTC) + '.csv'
        else:
            logname='C:\\Users\\bonde\\Dropbox\\Code\\Python\\MAIA\\' + "MAIAserver" + '.csv' 
        with open(logname,"w") as f:
            f.write(",".join(str(value) for value in log_header)+ "\n")
        print ("New log created: " + str(logname))
        logfile_created=True
        log_update()

def log_update(): # save data to logfile
    global log_data
    #global tempin,tempout,pressure,humidity
    if logfile_created==True:       
        log_data = [GPSdate,UTC,"UTZ", GPSspeed,SOGmax,COG,"logtripdis",
            "logtriptime",latdep,londep,latnow,lonnow,latdes,londes,
            "dest",tempin,tempout,humidity,pressure,AWA,AWS,TWD,TWS,TWSmax,"BRG","DTW",DEP,TSE]
        with open(logname,"a") as f:
            f.write(",".join(str(value) for value in log_data)+ "\n")

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

base_dir = '/sys/bus/w1/devices/'
os.chdir(base_dir)
print("directory changed to")
print(base_dir)
print("Detecting 18B20 devices ")
deviceIDs=glob.glob('28*')
print ("Total amount of tested sensors: " + str(len(TempIDs)))
print ("Amount of attached temp sensors: " + str(len(deviceIDs)))
print ("ID of attached sensors: " + str(deviceIDs))

while True:
    csvcounter+=1
    metcounter+=1
    NMEAread()
    sleep(0.2)
    GPSread()
    sleep(0.2)
    if metcounter==20:
        metsensors()
        TermoRead()
        ReadVolts()
        metcounter=0
    if csvcounter==log_update:
        log_update()
        csvcounter=0
    UDPmessage()
    sleep(0.6)
    #print(nmearead)

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