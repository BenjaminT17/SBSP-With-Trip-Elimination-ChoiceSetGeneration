# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 19:14:37 2019

@author: tomha021
"""

###############################################################################
import datetime
import os
from haversine import haversine

###############################################################################
##########          Initialize blank lists to store GTFS TXT Info     #########
############################################################################### 
inputGTFSPath = r"E:\DallasData\GTFS"
outputFastTripFilePath=r"E:\DallasData\DatFiles"
print('\nInput GTFS Data Path: %s\nOutput FastTrips .dat Data Path: %s' %(inputGTFSPath,outputFastTripFilePath))

calendar = []
trips = []
routes = []
stopTimes = []
stops = []
shapes = []

year=2015
month=10
day=13
date = year*10000 + month*100 + day
dayOfWeek = datetime.date(year, month, day).isoweekday() #Generates what day of the week date is on (Monday=0, Tues.=1 etc.)

###############################################################################
##########            Load GTFS Info into Lists From Above            #########  
############################################################################### 
inFile = open(os.path.join(inputGTFSPath, "calendar.txt"),"r")
for tmpIn in inFile:
    calendar = calendar + [tmpIn[:-1].split(",")]
service = [c[0] for c in calendar if (c[dayOfWeek]=='1')]     #Only get service Ids/Trip ID's that occur on specified day of week
inFile.close()
print('\nFinished Calendar')


#### READ TRIPS FILE
inFile = open(os.path.join(inputGTFSPath,"trips.txt"),"r")
inFile.seek(0) 
tripFileHeaders = inFile.readline().split(',')
for index, value in enumerate(tripFileHeaders):                 #Get correct indicies from trip txt file for when writing corresponding .dat file
    if 'route' in value and 'id' in value:
        tripFileRouteIDIndex = index 
    elif 'trip' in value and 'id' in value:
        tripFileTripIDIndex = index
    elif 'direction' in value and 'id' in value:
        tripFileDirectionIDIndex = index 
    elif 'shape' in value and 'id' in value:
        tripFileShapeIDIndex = index        
inFile.seek(0)                                              #Return to top of file
for tmpIn in inFile:
    if tmpIn[:-1].split(",")[1] in service:                 #Check if trip ID occurs on the specified day of week (denoted by service ID)
        trips = trips + [tmpIn[:-1].split(",")]

routeIds = set([t[0] for t in trips])
inFile.close()
print('Finished Trips')


#### READ ROUTES FILE
inFile = open(os.path.join(inputGTFSPath,"routes.txt"),"r")
inFile.seek(0) 
routeFileHeaders = inFile.readline().split(',')
for index, value in enumerate(routeFileHeaders):              #Get correct indicies from route txt file for when writing corresponding .dat file
    if 'route' in value and 'id' in value:
        routeFileRouteIDIndex = index 
    elif 'agency' in value and 'id' in value:
        routeFileAgencyIndex = index
    elif 'route' in value and 'short' in value and 'name' in value:
        routeFileRouteShortNameIndex = index 
    elif 'route' in value and 'long' in value and 'name' in value:
        routeFileRouteLongNameIndex = index   
    elif 'route' in value and 'type' in value:
        routeFileRouteTypeIndex = index 
inFile.seek(0)                                              #Return to top of file
for tmpIn in inFile:
    if tmpIn[:-1].split(",")[0] in routeIds:                #Make sure the given route is a valid route that occurs on the studied trips selected above
        routes = routes + [tmpIn[:-1].split(",")]
inFile.close()
print('Finished Routes')


#### READ STOP TIMES FILE
inFile = open(os.path.join(inputGTFSPath,"stop_times.txt"),"r")
inFile.seek(0) 
stopTimesFileHeaders = inFile.readline().split(',')
for index, value in enumerate(stopTimesFileHeaders):              #Get correct indicies from route txt file for when writing corresponding .dat file
    if 'trip' in value and 'id' in value:
        stopTimesTripIDIndex = index 
    elif 'arrival' in value and 'time' in value:
        stopTimesArrivalTimeIndex = index
    elif 'departure' in value and 'time' in value:
        stopTimesDepartureTimeIndex = index
    elif 'stop' in value and 'id' in value :
        stopTimesStopIDIndex = index   
    elif 'stop' in value and 'sequence' in value:
        stopTimesStopSequenceIndex = index 
inFile.seek(0)    
tmpTrip = ''; exclude = 0; i=0
for tmpIn in inFile:   
    i=i+1
    if i%100000==0: print ('Currently at stop time row;', i)
    tmpList = tmpIn[:-1].split(",")
    if tmpList[0]==tmpTrip and exclude==1:
        continue
    if tmpList[0]==tmpTrip and exclude==0:
        stopTimes = stopTimes + [tmpList]
        continue
    if tmpList[0] in [t[2] for t in trips]: #If trip ID in stoptimes.txt matches trip ID from trips.txt append stop times
        stopTimes = stopTimes + [tmpList]
        tmpTrip=tmpList[0]
        exclude=0
    else:
        tmpTrip=tmpList[0]
        exclude=1
inFile.close()
stopIds = set([st[stopTimesStopIDIndex] for st in stopTimes]) #Column of stopID's in stopTimes file


#### READ STOPS FILE
inFile = open(os.path.join(inputGTFSPath,"stops.txt"),"r")
inFile.seek(0) 
stopFileHeaders = inFile.readline().split(',')
for index, value in enumerate(stopFileHeaders):              #Get correct indicies from route txt file for when writing corresponding .dat file
    if 'stop' in value and 'id' in value:
        stopFileStopIDIndex = index 
    elif 'stop' in value and 'name' in value:
        stopFileStopNameIndex = index
    elif 'stop' in value and 'desc' in value:
        stopFileStopDescriptionIndex = index
    elif 'stop' in value and 'lat' in value :
        stopFileStopLatitudeIndex = index   
    elif 'stop' in value and 'lon' in value:
        stopFileStopLongitudeIndex = index 
inFile.seek(0)    
for tmpIn in inFile:
    if tmpIn[:-1].split(",")[0] in stopIds:     #If stop ID is included in StopTimes from above then append to stop list
        stops = stops + [tmpIn[:-1].split(",")]
inFile.close()

print ("%i trips, %i routes, %i stop times, %i stops!" %(len(trips), len(routes), len(stopTimes), len(stops)))


###############################################################################
##########       Create new output .dat Files from lists above        #########
############################################################################### 
#### Write Output Stop File
outFile = open(os.path.join(outputFastTripFilePath,"ft_input_stops.dat"),"w")
outFile.write("stopId\tstopName\tstopDesciption\tLatitude\tLongitude\tcapacity\n")
for s in stops:
    outFile.write(str(s[stopFileStopIDIndex]+'\t'+s[stopFileStopNameIndex]+'\t'+s[stopFileStopDescriptionIndex]+'\t'+s[stopFileStopLatitudeIndex]+'\t'+s[stopFileStopLongitudeIndex]+'\t'+'100'+'\n'))
outFile.close()


#### Write Output Routes File
outFile = open(os.path.join(outputFastTripFilePath,"ft_input_routes.dat"),"w")
outFile.write("routeId\tagency\trouteShortName\trouteLongName\trouteType\n")
for r in routes:
    outFile.write(str(r[routeFileRouteIDIndex]+'\t'+r[routeFileAgencyIndex]+'\t'+r[routeFileRouteShortNameIndex]+'\t'+r[routeFileRouteLongNameIndex]+'\t'+r[routeFileRouteTypeIndex]+'\n'))
outFile.close()


#### Write Output Trips File
outFile = open(os.path.join(outputFastTripFilePath,"ft_input_trips.dat"),"w")
outFile.write("tripId\trouteId\ttype\tstartTime\tcapacity\tshapeId\tdirectionId\n")
for t in trips:
    _type = [r[routeFileRouteTypeIndex] for r in routes if r[routeFileRouteIDIndex]==t[tripFileRouteIDIndex]][0]
    startTime = min([st[stopTimesDepartureTimeIndex] for st in stopTimes if st[stopTimesTripIDIndex]==t[tripFileTripIDIndex]])                     #If trip ID's ,atch get stop time
    startTime = startTime.split(":")[0]+startTime.split(":")[1]+startTime.split(":")[2]
    capacity = 60
    outFile.write(str(t[tripFileTripIDIndex]+'\t'+t[tripFileRouteIDIndex]+'\t'+_type+'\t'+startTime+'\t'+str(capacity)+'\t'+t[tripFileShapeIDIndex]+'\t'+t[tripFileDirectionIDIndex]+'\n'))
outFile.close()


#### Write Output Stop Times File
outFile = open(os.path.join(outputFastTripFilePath,"ft_input_stopTimes.dat"),"w")
outFile.write("tripId\tarrivalTime\tdepartureTime\tstopId\tsequence\n")
for st in stopTimes:
    outFile.write(str(st[stopTimesTripIDIndex]+'\t'+st[stopTimesArrivalTimeIndex].split(":")[0]+st[stopTimesArrivalTimeIndex].split(":")[1]+st[stopTimesArrivalTimeIndex].split(":")[2]+'\t'+st[stopTimesDepartureTimeIndex].split(":")[0]+st[stopTimesDepartureTimeIndex].split(":")[1]+st[stopTimesDepartureTimeIndex].split(":")[2]+'\t'+st[stopTimesStopIDIndex]+'\t'+st[stopTimesStopSequenceIndex]+'\n'))
outFile.close()

print ("Done!\n Now create transfer link files")

###############################################################################
##########           Create fast trips transfer input file            #########
############################################################################### 
outFile = open(os.path.join(outputFastTripFilePath,"ft_input_transfers.dat"), "w+")
outFile.write("fromStop\ttoStop\tdist\ttime\n")
k=0
for i in range(len(stops)):   
    tmpLat1 = float(stops[i][stopFileStopLatitudeIndex] )
    tmpLon1 = float(stops[i][stopFileStopLongitudeIndex])
    temp1 = (tmpLat1, tmpLon1)
    
    for j in range(len(stops)):
        if i == j:
            continue
        tmpLat2 = float(stops[j][stopFileStopLatitudeIndex])
        tmpLon2 = float(stops[j][stopFileStopLongitudeIndex])
        temp2 = (tmpLat2, tmpLon2)
        tmpDist = haversine(temp1, temp2, unit='mi')
        tmpDist = max(tmpDist,0.001)
        if tmpDist <= 0.1: #Set walking distance for transfers in miles
            k = k + 1
            tmpStop1 = stops[i][stopFileStopIDIndex]
            tmpStop2 = stops[j][stopFileStopIDIndex]
            tmpTime = (tmpDist / 3.0) * 60
            strOut = str(tmpStop1) + "\t" + str(tmpStop2) + "\t" + str(round(tmpDist,3)) + "\t" + str(round(tmpTime,2)) + "\n"
            outFile.write(strOut)
    if i%1000==0:
        print('Stop', i, 'of', len(stops))  
        
outFile.close()
print( k, "transfers!")
print( "Done!")
