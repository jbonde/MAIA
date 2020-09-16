# MAIA
Stands for MAritime Information Application

MAIA is a maritime information and utility tool to be installed as a supplement to plotters or mobile navigation devices in order to optimize access and readability for critical yacht data. The software is targeted for small touch screens and all menus are designed with an intuitive user interface which enables quick and easy access to information during sailing through a simple layout that is visible everywhere in a standard cockpit.

As for using the system on smaller displays for Raspberry Pi's like PiTFT 3.5" or the official RPi 7" the amount of items in menus are kept to a minimum comprising 6 choices in a 3x2 matrix. All information displayed is primarily one value at a time, but there are options for selecting more information if the user can read it on the current display.

When switching on the system the top line menu presents 3 categories:
* Actions and information related to departure
* Overview of actual position
* Data related to the destination

Bottom line har direct selection of the Dashboard that comprises most live data but also fast access to a MOB (Man Over Board) function. Finally access to the sub menus is done in the last cell in matrix.

Functionality

Departure include Trip Start and Trip Stop functions. Other functions displays Distance Covered, Trip time, Average Speed and Max Speed. A digital log is automatically enabled when the trip is started. It saves all data at short intervals in a format that can be used in spreadsheets for further analysis.

NOW shows information about actual Position such as GPS-Coordinates, Speed and Heading

Destination features a Waypoint selector/editor and shows distance/bearing to selected waypoint. There is also a time calculator showing estimated Time-To-Go and ETA.

The sub menu section gives access to the Timer- and Race modules but also a meteorological function presenting data from the temperature, air pressure and humidity sensors. System information, battery status and settings can also be reached from this section.

The MAIA application is prepared for connecting sensors in engine room (temperature and RPM) and the system can be expanded also to handle input from a NMEA0183 bus in order to show data from depth and wind sensors etc
