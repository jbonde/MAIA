# MAIA server acquiring sensor, GPS and/or NMEA data. Transmit via UDP to use for MAIA application
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

# Serial communication with GPS and/or NMEA0183 input
port1 = "/dev/ttyUSB0"  # USB serial (Adafruit GPS etc)
port2 = "/dev/ttyUSB1"  # USB serial (Adafruit GPS etc)
port = "/dev/ttyACM0"  # RPi with BS-708 receiver at USB port
port4 = "/dev/ttyACM1"  # RPi with BS-708 receiver at USB port
port5 = "/dev/ttyAMA0"  # RPi Zero PIN 10
port6 = "/dev/ttyS0"    # RPi 3 + Zero PIN 10
portbaud=9600 # Baudrate: 9600 for GPS, 4800 for NMEA0183
porttimeout=1
ser = serial.Serial(port, baudrate = portbaud, timeout=porttimeout)

# UDP communication
UDPaddress='255.255.255.255'
UDPport=2000

#Weather station
WEA=[]
tempin=None
pressure=None
humidity=None
tempout=None

# Standard NMEA string received directly from GPS connected to USB-port or via NMEA0183
RMC="225446,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3,E*68"
'''
           225446       Time of fix 22:54:46 UTC
           A            Navigation receiver warning A = OK, V = warning
           4916.45,N    Latitude 49 deg. 16.45 min North
           12311.12,W   Longitude 123 deg. 11.12 min West
           000.5        Speed over ground, Knots
           054.7        Course Made Good, True
           191194       Date of fix  19 November 1994
           020.3,E      Magnetic variation 20.3 deg East
           *68          mandatory checksum
'''
# Standard NMEA strings received from Autohelm ST1 instruments via NMEA converter
DBT="$IIDBT,0076.5,f,0121.2,M,," # Depth Below Transducer
VHW="$IIVHW,,,01.23,N,," #Water speed and heading
VWR="$IIVWR,070.,R,19.2,N,,,," #Relative Wind Speed and Angle
MTW="$IIMTW,12.3,C" #Mean Temperature of Water

# Non standard NMEA string containg data from weather station
WEA="$GPWEA,tempin,tempout,pressure,humidity," 

def UDPmessage(UDPstring):
    UDPbytes = str.encode(UDPstring)   
    udp = socket(AF_INET, SOCK_DGRAM)
    udp.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    udp.sendto(UDPbytes, (UDPaddress, UDPport))
    print ("UDPbytes sent:" +str(UDPbytes))

def WeatherSensors():
    # Read data from weather sensors BMP280 and DHT22
    global WEA,tempin,pressure,humidity,tempout
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
    WEA = "$GPWEA," + str(tempin) + "," + str(tempout) + "," + str(pressure) + "," + str(humidity) + "," + " " 
    print (WEA)

while True:
    WeatherSensors()
    sleep(0.5)
    UDPmessage(WEA)
    sleep(0.5)
    gpsread = ser.readline().decode('ascii', errors='replace')
    #print ("GPS data: " + str(gpsread))
    header = gpsread[3:6]
    if header=="RMC":
        RMC=gpsread
        UDPmessage(RMC)
    sleep(0.5)
