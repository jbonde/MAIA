# MAIA Marine server: Handling sensor data transmitted via UDP to use for MAIA application
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
from bmp280 import BMP280
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus
bus = SMBus(1)
measurebmp = BMP280(i2c_dev=bus)
import Adafruit_DHT
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

gpsdata="No GPS attached" # string carrying the gps information
metdata=None # string carrying the meteorological information
nmeadata=None # string with NMEA sentences from Autohelm
udpcounter=0
metcounter=0
csvcounter=0

metdata=[]
tempin=None
pressure=None
humidity=None
tempout=None

# 18B20 sensors
temperature = 0 # Temp of the 18B20 sensors
t18B20=0
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
foldernumber=0

DBT=None #Depth Below Transducer
VHW=None #Water speed and heading
VWR=None #Relative Wind Speed and Angle
MTW=None #Mean Temperature of Water
DBT="$IIDBT,0076.5,f,0121.2,M,," # Depth Below Transducer
VHW="$IIVHW,,,01.23,N,," #Water speed and heading
VWR="$IIVWR,070.,R,19.2,N,,,," #Relative Wind Speed and Angle
MTW="$IIMTW,12.3,C" #Mean Temperature of Water
# Serial and UDP communication
port1 = "/dev/ttyUSB0"  # USB serial (Adafruit GPS etc)
port2 = "/dev/ttyUSB1"  # USB serial (Adafruit GPS etc)
port = "/dev/ttyACM0"  # RPi with BS-708 receiver at USB port
port4 = "/dev/ttyACM1"  # RPi with BS-708 receiver at USB port
port5 = "/dev/ttyAMA0"  # RPi Zero PIN 10
port6 = "/dev/ttyS0"    # RPi 3 + Zero PIN 10

serialGPS=False # Check if GPS is available at serial port
try:
    portbaud=9600 # baudrate
    porttimeout=1
    ser = serial.Serial(port, baudrate = portbaud, timeout=porttimeout)
    serialGPS=True
except:
    print("no serial connection")
    serialGPS=False

UDPaddress='255.255.255.255'
UDPport=2000

def NMEAmessage():
    global nmeadata
    #NMEA string captured from Autohelm
    nmeadata=str(DBT)+str(VHW)+str(VWR)+str(MTW)

def UDPmessage():
    metbytes = str.encode(metdata)
    gpsbytes = str.encode(gpsdata)
    nmeabytes = str.encode(nmeadata)
    DBTbytes = str.encode(DBT)
    VHWbytes = str.encode(VHW)
    VWRbytes = str.encode(VWR)
    MTWbytes = str.encode(MTW)
    
    udp = socket(AF_INET, SOCK_DGRAM)
    udp.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    udp.sendto(metbytes, (UDPaddress, UDPport))
    print ("Weather data sent:" +str(metdata))
    sleep(0.1)
    udp.sendto(gpsbytes, (UDPaddress, UDPport))
    print ("gps sent:" +str(gpsdata))
    sleep(0.1)

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
    sleep(0.1)
    csvcounter+=1
    metcounter+=1
    if metcounter==20:
        metsensors()
        TermoRead()
        NMEAmessage()
        metcounter=0
        UDPmessage()
    if serialGPS==True:
        gpsread = ser.readline().decode('ascii', errors='replace')
        #print ("GPS data: " + str(gpsread))
        header = gpsread[3:6]
        if header=="RMC":
            gpsdata=gpsread
            #print ("GPS data: " + str(gpsread))

'''
# Installation notes
Enable 1-wire connection in raspi-config
Show ID of connected devices from command prompt:

sudo modprobe w1-gpio
sudo modprobe w1-therm
ls /sys/bus/w1/devices/ | grep -e "28-"
cd /sys/bus/w1/devices
ls 

pip3 install Adafruit_DHT
pip3 install BMP280
'''