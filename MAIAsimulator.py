# Data simulator for MAIA - sending a virtual trip to UDP port simulating GPS and instruments on board
import time, datetime
from datetime import datetime, timedelta
import socket
from socket import *
from threading import Thread
from time import sleep
import math
import random

UDPaddress='255.255.255.255'
UDPport=2000

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

# Start position as decimal (Google) angles
lat=56.71418 # Just outside Anholt harbour
lon=11.50685 # 
latprev=lat
lonprev=lon
dist=0
bear=0
variation=0.000015 #Change in position beween each update (app 5 knots)
looptime=0 #keep track on how much time each loop takes in sec
submitperiod=1 # time (sec) between UDP messages

#Start data
COG=0 # Default Course Over Ground 
SOG=3 # Default Speed Over Ground 
TWD=255 # True wind direction used for finding AWA
TWA=-90 # Angle between course and true wind
TWS=10 # True wind speed (m/s) used for AWS
AWA=1 # Apparent wind angle
AWD="R" #Apparent wind direction (left/right)
AWS=1 #Apparent wind speed
AWAcos=None
SOGup=True #Increase speed
SOGmax=9 #Max speed
SOGmin=3 #Min speed
AWSup=True
AWSmax=25 #Max wind velocity knots
AWSmin=1 #Max wind velocity knots
depth=4.5
STW=1 # Speed through water

# MET data
tempin=18.3
pressure=1003
humidity=78
tempout=22.3

# Convert m/s to knots
TWS=TWS/0.514444

def UDPmessage(UDPstring):
    UDPbytes = str.encode(UDPstring)
    udp = socket(AF_INET, SOCK_DGRAM)
    udp.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    udp.sendto(UDPbytes, (UDPaddress, UDPport))
    #print ("UDP sent (" + str(UDPport) + ")" + str(UDPstring))


def true2apparent():
    global AWS,AWA,AWS,AWD,AWAcos,TWA
    # Finding apparent wind speed based on TWD, TWS, course and speed
    TWA=abs(COG-TWD)
    if TWA>180:
        if COG>TWD: 
            AWD="R"
        else:
            AWD="L" 
        TWA=360-TWA
    else:
        if COG>TWD: 
            AWD="L"
        else:
            AWD="R"
    TWA_rad=math.radians(TWA)
    TWD_rad=math.radians(TWD)
    if TWA_rad==0:
        TWA_rad=0.1 # Avoid COS zero 
    AWS=math.sqrt(math.pow(TWS,2)+math.pow(SOG,2)+2*TWS*SOG*math.cos(TWA_rad))
    if AWS<=0:
        AWS=0.1 
        print("Avoiding zero division")
    # Finding apparent wind angle based on TWD, course and speed  
    AWAcos=((TWS*math.cos(TWA_rad)+SOG)/AWS)
    if AWAcos>1:
        AWAcos=AWAcos-int(AWAcos)
    if AWAcos<-1:
        AWAcos=AWAcos+abs(int(AWAcos))
    AWArad=math.acos(AWAcos)
    AWA=math.degrees(AWArad)
    
def WPTcourse(lat1,lon1,lat2,lon2):
    # calculate course to selected waypoint from current position

    lat1rad=math.radians(float(lat1)) # convert to radians
    lon1rad=math.radians(float(lon1)) # convert to radians
    lat2rad=math.radians(float(lat2)) # convert to radians
    lon2rad=math.radians(float(lon2)) # convert to radians

    y = math.sin(lon2rad-lon1rad) * math.cos(lat2rad)
    x = math.cos(lat1rad)*math.sin(lat2rad) - math.sin(lat1rad)*math.cos(lat2rad)*math.cos(lon2rad-lon1rad)
    cors = math.atan2(y, x)

    course=math.degrees(cors)
    course=(course+360) % 360
    course=str(course)
    course=course[0:4]
    return(course)

def dec2dmm(angle):
    # convert degree decimal positions to DegreesMinutes.Minutes
    posangle=float(angle) #converts to number format
    posangle=abs(posangle) #converts to positive (if negative) format
    degint=math.floor(posangle)
    degree=str(degint).zfill(2)
    minutesdec=posangle-float(degree)
    minutes=minutesdec*600000000000
    return(str(degree) + str(minutes)[:2] + "." + str(minutes)[2:6])

def newpos():
    global latprev,lat,lonprev,lon
    # Find the new position on basis of last position, course and speed
    COGrad=math.radians(float(COG))
    lat=latprev+math.cos(COGrad)*distance/60
    lon=lonprev+math.sin(COGrad)*distance/60
    #print("New position " + str(lat) + "," +str(lon))

while True:
    datenow=str(datetime.now())[2:4] + str(datetime.now())[5:7]  + str(datetime.now())[8:10]      
    timenow=str(datetime.now())[11:13] + str(datetime.now())[14:16] + str(datetime.now())[17:19]
    latdms=dec2dmm(lat)
    londms=dec2dmm(lon)
    distance=SOG*looptime/3600
    looptime=0

    ''' # Following prints can be activated for extra testing:
    print("Distance since last update: " + str(distance))
    print("Input values: ")
    print("SOG: " + str(SOG))
    print("COG: " + str(COG))
    print("TWS: " + str(TWS))
    print("TWD: " + str(TWD))
    print("Calculated values: ")
    print("TWA: " + str(TWA))
    print("AWAcos: " + str(AWAcos))
    print("AWA: " + str(AWA))
    print("AWD: " + str(AWD))
    print("AWS: " + str(AWS))
    ''' 
    newpos()

    # Create GPS position
    latprev=lat
    lonprev=lon
    RMC="$GPRMC,"+timenow+",A," + str(latdms) +",N," + str(londms)+ ",E,"+str('{:3.1f}'.format(SOG))+","+str('{:3.1f}'.format(COG))+","+datenow+",004.3,E*68"

    # Speed and TWS adjustments before next GPS update
    if SOGup==True:
        SOG=SOG+0.01
        TWS=TWS-0.01
    else:
        SOG=SOG-0.01
        TWS=TWS+0.01
    if SOG>=SOGmax:
        SOGup=False
    if SOG<=SOGmin:
        SOGup=True

    # Course adjustments before next GPS update (set for a 360 deg turn)
    COG=COG+0.1
    if COG>360:
        COG=0

    # Send Wind data
    true2apparent()
    VWR="$IIVWR," + str(abs(AWA)) + "," + str(AWD) + "," + str(AWS) + ",N,,,," #Relative Wind Speed and Angle
    
    # Wind speed adjustments before next update
    if AWSup==True:
        AWS=AWS+0.1
    else:
        AWS=AWS-0.1
    if AWS>=AWSmax:
        AWSup=False
    if AWS<=AWSmin:
        AWSup=True

    # Create depth info
    if SOGup==True:
        depth=depth+0.1
    else:
        depth=depth-0.1
    DBT="$IIDBT,0076.5,f,"+str(depth)+",M,," # Depth Below Transducer

    # Create other instrument data
    STW=abs(SOG-random.randint(0, 3)) #Make a random adjustment for current
    VHW="$IIVHW,,,"+str(STW)+",N,," # Water speed and heading
    WEA = "$GPWEA," + str(tempin) + "," + str(tempout) + "," + str(pressure) + "," + str(humidity) + "," + " " 
    UDPsentences=[RMC,DBT,VHW,VWR,MTW,WEA]
    for nmea in range(len(UDPsentences)):
        UDPmessage(UDPsentences[nmea])
        print(str(UDPsentences[nmea]))
        sleep(submitperiod)
        looptime=looptime+submitperiod # for calculating distance since last position
    