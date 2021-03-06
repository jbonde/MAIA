# MAIA - a MAritime Information Application

MAIA is a Raspberry Pi maritime information and utility tool to be installed on board as a supplement to plotters or mobile navigation devices in order to optimize overview of yacht data from instruments and GPS but also for providing additional information and features. The system consists of a server that picks up and transmits data and a display client that can run on as many units as desired on board.

The client software is designed for small touch screens and all menus provide an intuitive user interface which enables quick and easy access to information during sailing through a simple layout that is clearly visible even on the smallest screens. So for those carrying older instruments on board and use tablets for navigation, the MAIA system might add the extra overview and flexibility that new and expensive systems have.

In order to use the system on Raspberry Pi touch displays like PiTFT 3.5" or the official RPi 7" and to ensure smooth operation in rough seas, the amount of items in menus are kept to a minimum comprising 6 choices in a 3x2 matrix. All information displayed is primarily one value at a time, but some options are also provided for condensed views if readable on the current display configuration. When data is displayed the screen works as a full size button and touching the screen will revert to the last menu.

When switching on the system a matrix menu presents 6 choices:
* Actions and information related to departure
* Overview of actual position
* Data related to the destination
* Dashboard that comprises most live data 
* MOB (Man Over Board) function
* Access to the sub menus

## Functionality
DEP (Departure) include Trip Start and Trip Stop functions. Other functions displays Distance Covered, Trip time, Average Speed and Max Speed. A digital log is automatically enabled when the trip is started so all data are saved at short intervals in a format that can be uploaded directly to Google Maps or used in spreadsheets for further analysis.

NOW shows information about actual Position such as GPS-Coordinates, Speed and Heading

DES (Destination) features a Waypoint selector/editor and shows distance/bearing to selected waypoint. There is also a time calculator showing estimated Time-To-Go and ETA.

DASH will take you to the dashboard which is coded in a "B&G" style with a left and right column showing live data from instruments. The center is a compass rose with four coloured lines representing COG, BRG, TWD and AWA. AWA will change color between red and green according to angle. Tapping the display will change the view from "North-up" to "Course-up".

MOB. A "Man Over Board" button is placed centrally in the Main menu in order to have fast registration of coordinates in an emergency situation.

The * (sub menu)  section gives access to the Timer- and Race modules and Weather data from the temperature, air pressure and humidity sensors as well as system information. Settings can also be reached from this section eg if you would like a layout with black background or dim the display during night passages.

For further insight to the general flow and sub-menus please check MAIA_functionality.pdf and the MAIA.pdf flowcharts

## Data acquisition
Instrument data are acquired and submitted from the MAIA server (see MAIAserver.py) or any other device capable of broadcasting standard NMEA-sentences via UDP. For full data feed the MAIAserver with weather sensors is required and for this a non-standard NMEA header "WEA" is used for transmitting data from sensors (temperature, humidity and pressure). The data can picked up by clients from a standard LAN of your choice in order to service as many display configurations as desired on board.

## Testing
The MAIA application can be tested by running MAIAsimulator.py on a separate RPi connected to same LAN. This will take you on a virtual but realistic trip around the Danish island Anholt in a fairly stable westerly breeze. If a trip is started in MAIA at the same time as launching the simulator you can after some time fetch a date/time stamped CSV-file which can be uploaded directly to Google maps for testing the log data that was recorded. A full trip around the island takes 6 hours (check the screen shot MAIA_simulator.png). So if desired you can set up two RPi's right away and get a grasp of how it works as long as they are on the same network. But please read the installation notes first. 

## Disclaimer
MAIA should never be used as the primary navigation tool as it is a supplement to proven marine products on the market. Some features still need to be tested in live environments so use of the system is by own responsibility and developers have no liabilities for any errors and problems related to the MAIA system.
Some features have not yet been tested like the server board and analogue inputs used for battery monitoring etc. 
