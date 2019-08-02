# -*- coding: utf-8 -*-
"""
Created on Fri Aug  2 14:26:24 2019

@author: tomha021
Modified from SBSP code written by Alireza Khani (2013)
"""

################################################################################################
################################################################################################
################################################################################################

import time, heapq, os
import osmnx as ox                                                                 #First must install from conda (conda install -c conda-forge osmnx)
import networkx as nx
import datetime
from pathlib import Path
from collections import defaultdict
import demandInputFileGeneration                                            #Previously created file used to generate zone and demand files. MUST RUN THIS FIRST          
from anytree import Node as treeNode                                               #Need to rename node as treeNode else conflict with transit node class defined below
import csv
from haversine import haversine


#Below needed to bypass error (b'no arguments in initialization list') related to osmnx
os.environ["PROJ_LIB"] =r"[USER PATH]\AppData\Local\Continuum\anaconda3\Library\share"
ox.config(log_file=True, log_console=True, use_cache=True)

inputDataLocation = r"[INPUT Path To Fast-Trips Formated Files]"
OBSFilePath= r'[Path to Folder Containing On Board Survey]\Survey.csv'

desiredDayOfTheWeekInt    = 1
desiredBeginningMonthInt  = 9
desiredEndMonthInt        = 12
###############################################################################
#############            FIND INDEX LABELS IN OBSurvey             ############
############################################################################### 
####SPECIFY WHAT EACH HEADER IS
passengerIDHeader                         = 'Passenger'
accessModeDescriptionHeader               = 'ACCESS_MODE'
egressModeDescriptionHeader               = 'EGRESS_MODE'
surveyedDateHeader                        = 'DATE'
surveyedTimeMinPastMidnight_NoRangeHeader = 'surveyMinPastMidnight'            #If surveyed time is given as a range use first minute of range
surveyedRouteHeader                       = 'ROUTE_SURVEYED'
AMOrPMIndicatorHeader                     = 'timePeriod'
numberOfTransfersBeforeSurveyHeader       = 'TRANSFERS_FROM_CODE'
ifTransferFrom_FirstRouteTakenHeader      = 'TRANSFER_FROM_FIRST_ROUTE'
ifTransferFrom_SecondRouteTakenHeader     = 'TRANSFER_FROM_SECOND_ROUTE'
ifTransferFrom_ThirdRouteTakenHeader      = 'TRANSFER_FROM_THIRD_ROUTE'
numberOfTransfersAfterSurveyHeader        = 'TRANSFERS_TO_CODE'
ifTransferTo_FirstRouteTakenHeader        = 'TRANSFER_TO_FIRST_ROUTE'
ifTranfserTo_SecondRouteTakenHeader       = 'TRANSFER_TO_SECOND_ROUTE'
ifTranfserTo_ThirdRouteTakenHeader        = 'TRANSFER_TO_THIRD_ROUTE'
originLatitudeCoordinateHeader            = 'ORIGIN_LAT'
originLongitudeCoordinateHeader           = 'ORIGIN_LON'
destinationLaitudeCoordinateHeader        = 'DESTIN_LAT'
destinationLongitudeCoordinateHeader      = 'DESTIN_LON'


#Populate index varaibles with correct index in OBSurvey
with open(OBSFilePath) as inputOBSFile:   
    inputOBSFile.seek(0) 
    obsHeaders = inputOBSFile.readline().split("\n")[0].split(',')
    for index, colHeader in enumerate(obsHeaders):
        #print(index,colHeader)
        if passengerIDHeader ==colHeader:
            passengerIDIndex = index
        elif accessModeDescriptionHeader == colHeader:
            accessModeIndex = index
        elif egressModeDescriptionHeader == colHeader:
            egressModeIndex = index    
        elif surveyedDateHeader in colHeader:
            surveyDateIndex = index        
        elif numberOfTransfersBeforeSurveyHeader == colHeader:
            transfersBeforeSurveyCountIndex = index 
        elif ifTransferFrom_FirstRouteTakenHeader == colHeader:
            firstRouteBeforeTransferIndex = index 
        elif ifTransferFrom_SecondRouteTakenHeader == colHeader:
            secondRouteBeforeTransferRouteIndex = index 
        elif ifTransferFrom_ThirdRouteTakenHeader == colHeader:
            thirdRouteBeforeTransferRouteIndex = index 
        elif numberOfTransfersAfterSurveyHeader == colHeader:
            transfersAfterSurveyCountIndex = index 
        elif ifTransferTo_FirstRouteTakenHeader == colHeader:
            firstRouteAfterTransferIndex = index               
        elif ifTranfserTo_SecondRouteTakenHeader == colHeader:
            secondRouteAfterTransferIndex = index    
        elif ifTranfserTo_ThirdRouteTakenHeader == colHeader:
            thirdRouteAfterTransferIndex = index                
        elif surveyedRouteHeader == colHeader:
            survyedRouteIndex = index 
        elif surveyedTimeMinPastMidnight_NoRangeHeader == colHeader:
            surveyedTimeMinPastMidnightIndex = index  
        elif originLatitudeCoordinateHeader == colHeader:
            originLatIndex = index  
        elif originLongitudeCoordinateHeader == colHeader:
            originLonIndex = index              
        elif destinationLaitudeCoordinateHeader == colHeader:
            destLatIndex = index              
        elif destinationLongitudeCoordinateHeader == colHeader:
            destLonIndex = index              
        elif AMOrPMIndicatorHeader == colHeader:
            amOrPmIndex = index  
            
###############################################################################
#######        DETERMINE ANALYSIS DATES IN SURVEY (TUESDAYS)          #########    
############################################################################### 
dates = []
uniqueTuesdays = []
with open(OBSFilePath) as obsFile:
    reader = csv.reader(obsFile)
    next(reader) #Skip header
    for row in reader:
        dates.append(row[surveyDateIndex])

for dateString in list(set(dates)):
    year = int(dateString.split('/')[2])
    month = int(dateString.split('/')[0])
    day = int(dateString.split('/')[1])
    dayOfWeek = datetime.date(year, month, day).isoweekday() #Generates what day of the week date is on (Monday=0, Tues.=1 etc.)
    
    if dayOfWeek == desiredDayOfTheWeekInt and month >= desiredBeginningMonthInt and month<= desiredEndMonthInt:
        uniqueTuesdays.append(dateString)

uniqueTuesdays = [datetime.datetime.strptime(ts, "%m/%d/%Y") for ts in uniqueTuesdays]
uniqueTuesdays.sort()
uniqueTuesdays = [datetime.datetime.strftime(ts, "%#m/%#d/%Y") for ts in uniqueTuesdays]     #Where pound is to remove leading zeros
validDates = uniqueTuesdays       
                 
###############################################################################
#############                   DEFINE CLASSES                     ############    
############################################################################### 
class Zone: #from ft_input_zones.dat file
    def __init__(self, _tmpIn):
        self.lat = float(_tmpIn[1])
        self.long = float(_tmpIn[2])
        self.accessNode=''
        self.egressNode=''
        
class Stop: #From ft_input_stops.dat file
    def __init__(self, _tmpIn):
        self.lat = float(_tmpIn[3])
        self.long = float(_tmpIn[4])
        self.nodes = []                                                                 #Node ID formed in readSchedule composed of: (tripId+","+seq+","+stopId)

class Trip: #From ft_input_trips.dat file
    def __init__(self, _tmpIn):
        self.route = _tmpIn[1]
        self.type = _tmpIn[2]

class Node:#From ft_input_stop_times.dat file
    def __init__(self, _tmpIn): 
        self.trip = _tmpIn[0]
        self.seq = int(_tmpIn[4])                                                       #Sequence in trip
        self.stop = _tmpIn[3]
        if _tmpIn[0]=="access" or _tmpIn[0]=="egress":
            self.meanTime = _tmpIn[2]
        else: 
            self.meanTime = (int(_tmpIn[2])//10000)*60.0 + int(_tmpIn[2])%10000//100    # Convert departure time into min 
        self.last = 0                                                                   #Denotes is node is the first or a last on route
        self.outLinks = []
        self.inLinks = []
        self.labels = (999999.0, 999999.0)                                              #time, cost
        self.preds = ("","")                                                            #Previous node
        
class Link: #From ft_input_stop_times.dat and ft_input_transfers.dat (also from assignment function with access and egress)
    def __init__(self, _from, _to, _by, _time):
        self.fromNode = _from
        self.toNode = _to
        self.trip = _by
        self.time = _time
        self.passengers = []

class Passenger: #From ft_input_demand.dat
    def __init__(self, _tmpIn):
        self.origin = _tmpIn[1]
        self.destination = _tmpIn[2]
        self.PDT = float(_tmpIn[6])                                                     #Input file sets PDT to be on-hour (or half hour if between 6-7pm)
        self.path = []
        self.pathCost = 999999
        self.travelTime =999999
        self.startTime = 999999
        self.accessWalkTime = 999999
        self.ivtTime = []
        self.transferTimes = []
        self.egressWalkTime = 999999
        self.boardStops = ''
        self.alightStops = ''
        self.travelStartTime=''
        self.travelEndTime=''
        self.accessWtTime=''
        self.transferWtTime=[]
        
###############################################################################
#############           DEFINE "READ" FUNCTIONS                    ############
###############################################################################   
#All of these functions read existing data and put into a usable format
        
def readZones(inputZoneDataPath, zoneSet):
    '''
    PURPOSE: Populate outputZoneDict with zoneID as key and lat lon as values
    
    Input: 
            inputZoneDataPath:  zone dat file path              (String)
            zoneSet:            dictionary of zone objects      (Dictionary)
            
    NOTE: Input Zone Data must have columns with order zoneId, zoneLat, zoneLon
    
    Output:
            ZONE OBJECTS
    '''
    inZoneFile = open(inputZoneDataPath)
    zoneTmpIn = inZoneFile.readline().strip().split("\t")
    for row in inZoneFile:
        zoneTmpIn = row.strip().split("\t")
        zoneId = zoneTmpIn[0]
        zoneSet[zoneId] = Zone(zoneTmpIn)                                       #ZoneId=Dictionary Key
    inZoneFile.close()
    #print (len(zoneSet), "zones")
    return[len(zoneSet)]
#--
def readStops(inputStopsDataPath, stopSet):
    '''
    PURPOSE: Populate outputStopDict with stopID as key and lat lon as values
    
    Input: 
            inputStopDataPath:      stop dat file path              (String)
            stopSet:                dictionary of stop objects      (Dictionary)
            
    NOTE: Input Stops Data must have column1=stopID, column3=lat, column4=lon as defined in class above
    
    Output:
            STOP OBJECTS
    '''
    inStopsFile = open(inputStopsDataPath)
    stopTmpIn = inStopsFile.readline().strip().split("\t")
    for row in inStopsFile:
        stopTmpIn = row.strip().split("\t")
#        if stopTmpIn[0] != '56021':                                             #Make sure to exclude "fake" LRT stop at switching junction as it crosses over between USBank and Cedar Riv.
#            stopSet[stopTmpIn[0]] = Stop(stopTmpIn)
        stopSet[stopTmpIn[0]] = Stop(stopTmpIn)
    inStopsFile.close()
    #print (len(stopSet), "stops")
#--
def readTrips(inputTripsDataPath, tripSet):
    '''
    PURPOSE: Populate outputTripDict with tripID as key and routeID, routeType as values
    
    Input: 
            inputTripDataPath:      trip dat file path              (String)
            tripSet:                dictionary of trip objects      (Dictionary)
            
    NOTE: Input Trips Data must have column1=routeID, column2=type as defined in class above where indicies start at 0     
    
    Output:
            TRIP OBJECTS
    '''
    inTripsFile = open(inputTripsDataPath)
    tripsTmpIn = inTripsFile.readline().strip().split("\t")
    for row in inTripsFile:
        tripsTmpIn = row.strip().split("\t")
        tripSet[tripsTmpIn[0]] = Trip(tripsTmpIn)
    inTripsFile.close()
    #print (len(tripSet), "trips")
#--
def readSchedule(inputStopTimesDataPath, nodeSet, stopSet, linkSet): 
    '''
    PURPOSE: Large function which populates the node lists inside the stop, zone, and trip classes
             Also populates link dictionary with transit links 
    Input: 
            stopTimesInputFilePath:     stopTimes dat file path              (String)
            nodeSet:                    dictionary of node objects           (Dictionary)
            stopSet:                    dictionary of stop objects           (Dictionary)
            linkSet:                    dictionary of link objects           (Dictionary)
            
    Output:
            NODE OBJECTS
            TRANSIT LINK OBJECTS
    '''
    inStopTimesFile = open(inputStopTimesDataPath)
    stopTimesTmpIn = inStopTimesFile.readline().strip().split("\t")
    prevNodeId = ""                                                             #No previous node ID to the first node all other prevNodeId's assigned below
    for row in inStopTimesFile:
        stopTimesTmpIn = row.strip().split("\t")
        tripId = stopTimesTmpIn[0]
        stopId = stopTimesTmpIn[3]
        seq = stopTimesTmpIn[4]
        
#        if stopId != '56021':                                                   #Again don't want LRT transfer switch point as it isn't a stop
#            nodeId = '%s,%s,%s' %(tripId, seq, stopId)                          #Create node id and append to nodeDict with ID as key
#            nodeSet[nodeId] = Node(stopTimesTmpIn)
#            stopSet[stopId].nodes.append(nodeId)                                #Append nodes to node attribute of correlated stopID in pre-existing stopDict
        
        nodeId = '%s,%s,%s' %(tripId, seq, stopId)
        nodeSet[nodeId] = Node(stopTimesTmpIn)
        stopSet[stopId].nodes.append(nodeId)                                #Append nodes to node attribute of correlated stopID in pre-existing stopDict
                    
        #For the first stop of a given set where it hasn't come frome a previous node, denote as the end of a trip
        if int(seq) == 1 and prevNodeId != "":
            nodeSet[prevNodeId].last = 1
            
        #For all stops not the first stop for a given trip, the linkID is a string composed of the tripID and the number of stops removed from the beginning of the trip
        if int(seq)>1:
            
            #Create a record in linkDict for each of these stops listing with key value "trip, seqFromStart"
            linkId = tripId+","+str(int(seq)-1)
            linkSet[linkId] = Link(prevNodeId, nodeId, tripId, 0)               #Sets the time to be 0 as default
            
            #For each node assign outgoing and incoming links
            nodeSet[prevNodeId].outLinks.append(linkId)
            nodeSet[nodeId].inLinks.append(linkId)
            
        prevNodeId = nodeId
    inStopTimesFile.close()
    
    #print (len(nodeSet), "nodes")
    #print (len(linkSet), "transit links")
#--
def readWaitingTransfer(stopSet, nodeSet, tripSet, linkSet, timeWindow):
    '''
    PURPOSE: Populates link dictionary with waiting transfer (same stop) links
    
    stopSet:                dictionary of stop objects                  (Dictionary)
    nodeSet:                dictionary of node objects                  (Dictionary)
    tripSet:                dictionary of trip objects                  (Dictionary)
    linkSet:                dictionary of link objects                  (Dictionary)
    timeWindow:             Acceptable min to be waiting to transfer    (int)
            
    Output:
            WAITING TRANSFER LINKS
    '''
    for s in stopSet:
        for n1 in stopSet[s].nodes:
            for n2 in stopSet[s].nodes:                                             #Need both n1 and n2 to get the list of stops twice
                
                #Only create waiting transfer if transfer stop is the same, and if the routes are not the same
                #Can't transfer to last node of trip because the route doesn't go anywhere from there
                #Can't transfer from first node of trip because the trip hasn't even begun yet
                if (n1!=n2) and (nodeSet[n1].seq!=1) and (nodeSet[n2].last!=1) and (nodeSet[n1].stop==nodeSet[n2].stop) and (tripSet[nodeSet[n1].trip].route!=tripSet[nodeSet[n2].trip].route):
                    
                    #IF departure time of transfered TO stop is after the arrival time at the first routes stop plus some constant time (>2 for reliability)
                    #AND the second route's bus departs within the desired time window
                    #THEN create transfer link
                    if (nodeSet[n2].meanTime>=(nodeSet[n1].meanTime)) and ((nodeSet[n2].meanTime-nodeSet[n1].meanTime)<timeWindow):
                        linkId = "transfer"+","+str(len(linkSet)+1)
                        linkSet[linkId] = Link(n1, n2, "waitingtransfer", 0)
                        nodeSet[n1].outLinks.append(linkId)
                        nodeSet[n2].inLinks.append(linkId)
   # print (len(linkSet), "transit + waitingtransfer links")
#-
def readTransferLinks(inputTransferDataPath, stopSet, nodeSet, tripSet, linkSet, timeWindow):
    '''
    PURPOSE: Adds walking transfer links (where stop number changes) to linkDictionary
                Also adds these transfer links to the "outLinks" and "inLinks" of the
                associated node in the nodeDictionary
    Input: 
            transfersInputDataPath:     transferLinks dat file path          (String)
            stopSet:                    dictionary of stop objects           (Dictionary)
            nodeSet:                    dictionary of node objects           (Dictionary)
            tripSet:                    dictionary of trip objects           (Dictionary)
            linkSet:                    dictionary of link objects           (Dictionary)
            timeWindow:                 Max. wait time for any trip part     (int)
    Output:
            WALKING TRANSFER LINKS          
    '''    
    inFile = open(inputTransferDataPath)
    tmpIn = inFile.readline().strip().split("\t")
    for row in inFile:
        tmpIn = row.strip().split("\t")
        
        #Get nodes associated with "from" and "to" directions for a particular stopID
#        if tmpIn[0] != '56021' and tmpIn[1] != '56021':                                     #Still don't want stops to be associated with the LRT switching pt
#            fromNodes = stopSet[tmpIn[0]].nodes
#            toNodes = stopSet[tmpIn[1]].nodes
        fromNodes = stopSet[tmpIn[0]].nodes
        toNodes = stopSet[tmpIn[1]].nodes        
        # Create walking transfer links
        for n1 in fromNodes:
            for n2 in toNodes:
                
                #Same process as in above read schedule function
                if (nodeSet[n1].seq!=1) and (nodeSet[n2].last!=1) and (tripSet[nodeSet[n1].trip].route!=tripSet[nodeSet[n2].trip].route):
                    
                    #IF departure time of transferred TO stop is occurs after the arrival time of the first bus+ the time it takes to walk between the two routes and a buffer time
                    #AND The departure of the 2nd route leaves within the timeWindow from when the person arrived at the second route
                    #Then create walking transfer link
                    if (nodeSet[n2].meanTime >= (nodeSet[n1].meanTime + float(tmpIn[3])) ) and ( (nodeSet[n2].meanTime -(nodeSet[n1].meanTime + float(tmpIn[3])))  <= timeWindow):
                        linkId = "transfer"+","+str(len(linkSet)+1)
                        
                        if linkId in linkSet:
                            print ("ERROR")
                            
                        linkSet[linkId] = Link(n1, n2, "walkingtransfer", float(tmpIn[3])) #Generate walking transfer links where ID is a "transfer"
                        nodeSet[n1].outLinks.append(linkId)
                        nodeSet[n2].inLinks.append(linkId)
    inFile.close()
    #print (len(linkSet), "transit+waitingtransfer+walkingtransfer links")
#-
def readDemand(inputDemandDataPath, passengerSet, addedPDTMin):
    '''
    PURPOSE: Populates passenger dictionary with origin, dest, direction, and Prefered Departure Time (PDT)

    Input: 
           inputDemandDataPath:        stopTimes dat file path                      (String)
           passengerSet:               dictionary of passenger objects              (Dictionary)     
           addedPDTMin:                minutes to add to PDT from demand file       (int)
    Output:
            PASSENGER OBJECTS
    '''
    inFile = open(inputDemandDataPath)
    tmpIn = inFile.readline().strip().split("\t")
    for row in inFile:
        tmpIn = row.strip().split("\t")
        passengerId = tmpIn[0]
        passengerSet[passengerId] = Passenger(tmpIn)
        passengerSet[passengerId].PDT = passengerSet[passengerId].PDT+addedPDTMin
    inFile.close()
#-
def findShortestPath(orig, PDT, pathType, accessTimeWindow, weights, zoneSet, nodeSet, linkSet, excludedTripsList):
    '''
    PURPOSE: Use forward label-setting algorithm to update node labels
             
    Input: 
                   orig:            origin node location                            (String)
                    PDT:            preferred time of departure                     (Float)
               pathType:            what type of shortest path                      (string) 
       accessTimeWindow:            Max. wait time for access waiting               (int)
                nodeSet:            dictionary of node objects                      (Dictionary)
                zoneSet:            dictionary of zone objects                      (Dictionary)
                linkSet:            dictionary of link objects                      (Dictionary)
      excludedTripsList:            list of tripID's in previous SP                 (list)

    Output:
               Updated Labels for nodes on shortest path
    '''
    #For each iteration of shortest path start with fresh labels and preds
    for n in nodeSet:
        nodeSet[n].labels = (999999, 999999, 1.0)                                   #(time, cost, reliability factor (not used here)) Set labels as ~ infinite
        nodeSet[n].preds = ("", "")                                                 ##Set all nodes to have no current predecessor
        
    if zoneSet[orig].accessNode==[]:                                                #If there isn't a connection to the access node, stop
        return -1
    
    countLabled = 0
    for node in nodeSet:
        if nodeSet[node].labels[0]<999999:
            countLabled +=1
            
    accessNode = zoneSet[orig].accessNode
    nodeSet[accessNode].labels = (PDT,0,1)                                          #Set access node with time equal to the prefered time of dept. and a cost of 0 b/c it's the start node

    SE = [((nodeSet[accessNode].labels[2], accessNode))]                            #list of potential nodes are those emminating from the access node
    
    it=0
    iLabel = 0
    
    while len(SE)>0:
        currentNode = heapq.heappop(SE)[1]                                          #Pop and return nodeID of smallest COST from the heap, maintaining the heap invariant
        currentLabels = nodeSet[currentNode].labels                                 #Labels are (time,cost)
        currentPreds = nodeSet[currentNode].preds
        it = it+1
        
        for link in nodeSet[currentNode].outLinks:                                  #To update the next links look at links that emminate from the current node
            if linkSet[link].trip not in excludedTripsList:                         #Only look at trips that haven't been done before (excludes transfers and access and egress)
                newNode = linkSet[link].toNode
                newPreds = [currentNode, link]
                existingLabels = nodeSet[newNode].labels 
                newLabels = []
            
#CALCULATE NEW LABELS           ###
#    Weights= [IVT, WT, WK, TR] ###
                                  
    #ACCESS NODE
                if linkSet[link].trip=="access":
                    
                    #If the transit departure from the desired node occurs after you get there AND you don't wait longer than the timeWindow updates labels
                    if ((PDT+linkSet[link].time) <= nodeSet[newNode].meanTime) and (nodeSet[newNode].meanTime - (linkSet[link].time+PDT)) < accessTimeWindow:
                        newLabels.append(round(nodeSet[newNode].meanTime,3))
                        newLabels.append(round(weights[2]*linkSet[link].time+weights[1]*(nodeSet[newNode].meanTime-linkSet[link].time-PDT),3))
                    
    #EGRESS NODE    
                elif linkSet[link].trip=="egress" and linkSet[currentPreds[1]].trip not in ['access','waitingtransfer','walkingtransfer']:
                    newLabels.append(round(currentLabels[0]+linkSet[link].time,3))
                    newLabels.append(round(currentLabels[1]+weights[2]*linkSet[link].time,3))
    #WAITING TRANSFER NODE
                elif linkSet[link].trip=="waitingtransfer" and linkSet[currentPreds[1]].trip not in ['access','waitingtransfer','walkingtransfer']:
                    newLabels.append(round(nodeSet[newNode].meanTime,3))
                    newLabels.append(round(currentLabels[1]+weights[3]+ weights[1]*(nodeSet[newNode].meanTime-nodeSet[currentNode].meanTime),3))
    #WALKING TRANSFER NODE
                elif linkSet[link].trip=="walkingtransfer" and linkSet[currentPreds[1]].trip not in ['access','waitingtransfer','walkingtransfer']:
                    newLabels.append(round(nodeSet[newNode].meanTime,3))
                    newLabels.append(round(currentLabels[1]+weights[3]+weights[2]*linkSet[link].time+weights[1]*(nodeSet[newNode].meanTime-nodeSet[currentNode].meanTime-linkSet[link].time),3))
    #IVT-NODE
                elif linkSet[link].trip not in ['access', 'waitingtransfer', 'walkingtransfer', 'egress']:
                    newLabels.append(round(nodeSet[newNode].meanTime,3))
                    newLabels.append(round(currentLabels[1]+weights[0]*(nodeSet[newNode].meanTime-nodeSet[currentNode].meanTime),3))
                else:
                    continue
            
###   Update the node labels    ###    
                  
                if pathType=="optimal" and newLabels[1]<existingLabels[1]:       #If cost (including weighted factor and penalty time) [not true time]
                    nodeSet[newNode].labels = newLabels
                    nodeSet[newNode].preds = newPreds
                    heapq.heappush(SE, (newLabels[1], newNode))                  #Fill SE with new label and node where first value is the node cost and the second is the node

                            
    return [it, iLabel]
#--
def getShortestPath(passenger, dest, zoneSet, nodeSet ,linkSet, passengerSet, tripSet, stopSet, route2RouteShortDict=None):
    '''
    PURPOSE: Determine shortest path by stringing together labels. 
             This is fairly rapid as it only has to go through the nodes that 
             were updated in findShortest path. No updating will be needed 
             for nodes not on path as as predecessor nodes are stored from 
             findShortest path so this function directly label only those nodes on the path.
    Input: 
              passenger:        PassengerID                           (String)
                   dest:        destination node location             (String)
                zoneSet:        dictionary of zone objects            (Dictionary)
                nodeSet:        dictionary of node objects            (Dictionary)
                linkSet:        dictionary of link objects            (Dictionary)
           passengerSet:        dictionary of passenger objects       (Dictionary)
                tripSet:        dictionary of trip objects            (Dictionary)
                stopSet:        dictionary of stop objects            (Dictionary)
   route2RouteShortDict:        dictionary of routeID to routeShort   (Dictionary)
       
    Output:
               Shortest path per passenger
    '''
    currentNode = zoneSet[dest].egressNode
    if nodeSet[currentNode].labels[1]>=999999:
        return [] , []
    
    path = []
    scannedTrips = []
    timingList = []
    completeTimeList = []
    transferTimes = []
    transferWtTimeList = []
    uniqueTripCount = -1 
    testLength = 0
#### Create Shortest Path per Passenger and Calculate Path Time & Cost
    while currentNode!="":
        testLength+=1   
        newNode = nodeSet[currentNode].preds[0]
        newLink = nodeSet[currentNode].preds[1]
        if newNode!="":
            path = [newLink] + path
            
            #Determine if the selected node contains a new trip; if so append to scanned trips list
            if nodeSet[currentNode].trip not in scannedTrips and nodeSet[currentNode].trip not in ['transfer', 'egress', 'access']:
                scannedTrips.append(nodeSet[currentNode].trip)

#Determine travel time             
        if path[-1]==nodeSet[currentNode].preds[1]:
            pathEndTime=nodeSet[currentNode].labels[0]
            pathEndCost=nodeSet[currentNode].labels[1]
            
        currentNode = newNode
        
####------------------------------    
#For each passengers shortest path, determine various timing values such as egress, transfer, IVT, access   
    if path != [] and len(path)>2:                                                  #Need to have more than just access and egress links
        tripID = ''
        singleRoute = []
        for l in path:
            currentTrip = l.split(',')[0]
            if currentTrip != 'access' and currentTrip != 'egress' and currentTrip != 'transfer':
                if currentTrip not in timingList:
                    uniqueTripCount +=1
                    timingList.append(currentTrip)
                    currentTripStartTime = nodeSet[linkSet[l].fromNode].meanTime
                    currentTripBeginStopID = nodeSet[linkSet[l].fromNode].stop
                    placeholderTripEndTime = nodeSet[linkSet[l].toNode].meanTime
                    placeholderEndStopID = nodeSet[linkSet[l].toNode].stop
                    completeTimeList.append([])
                    
                tripToAppend = [currentTrip, currentTripStartTime, placeholderTripEndTime, currentTripBeginStopID, placeholderEndStopID]  
                    
                if currentTrip in timingList and nodeSet[linkSet[l].toNode].meanTime >= placeholderTripEndTime:
                    tripToAppend[2] = nodeSet[linkSet[l].toNode].meanTime           #Update a single route's end time
                    tripToAppend[4] = nodeSet[linkSet[l].toNode].stop               #Update a single route's end stop
                    
                    placeholderTripEndTime = nodeSet[linkSet[l].toNode].meanTime
                    
                completeTimeList[uniqueTripCount] = tripToAppend                    #Update the timing values for the route in the complete list
                
            if currentTrip == 'access':
                accessWalkTime = linkSet[l].time
                
            if currentTrip == 'transfer':
                transferTime = linkSet[l].time
                transferWtTimeList.append(round((nodeSet[linkSet[l].toNode].meanTime-nodeSet[linkSet[l].fromNode].meanTime) -transferTime,3))
                transferTimes.append(transferTime)
                
            if currentTrip == 'egress':
                egressWalkTime = linkSet[l].time
            

            if linkSet[l].trip not in ['access', 'waitingtransfer', 'walkingtransfer', 'egress'] and linkSet[l].trip != tripID:
                tripID = linkSet[l].trip
                routeID = tripSet[tripID].route
                stopNode = linkSet[l].fromNode
                stopID = nodeSet[stopNode].stop
                boardTime = nodeSet[stopNode].meanTime
                routeShortName = routeID2RouteShortDict[routeID]
                
                singleRouteString=[routeShortName,stopID,boardTime]
                singleRoute.append(singleRouteString)
           
            if linkSet[l].trip in ['waitingtransfer', 'walkingtransfer'] and linkSet[l].trip != tripID:
                tripID = linkSet[l].trip
                stopNode = linkSet[l].fromNode
                stopID = nodeSet[stopNode].stop
                boardTime = nodeSet[stopNode].meanTime
                singleRouteString=['TRANSFER',stopID,boardTime]
                singleRoute.append(singleRouteString)

            passengerSet[passenger].CompletePath = singleRoute                        #Need this attribute to print passenger routes
            
        if timingList != []:
            ivtTimes = []
            boardStops = []
            alightStops = []
            for z in range(len(completeTimeList)):
                if completeTimeList[z] != []:
                    indivRouteTime = completeTimeList[z][2]-completeTimeList[z][1]
                    ivtTimes.append(indivRouteTime)
                    boardStops.append(completeTimeList[z][3])
                    alightStops.append(completeTimeList[z][4])
                    
            initialTransitRouteStartTime = completeTimeList[0][1]
            
            passengerSet[passenger].startTime = round(initialTransitRouteStartTime-accessWalkTime ,3)
            passengerSet[passenger].ivtTime = ivtTimes
            passengerSet[passenger].accessWalkTime = round(accessWalkTime,3)
            passengerSet[passenger].egressWalkTime = round(egressWalkTime,3)
            passengerSet[passenger].transferTimes = transferTimes
            passengerSet[passenger].travelEndTime = round(pathEndTime,3)
            passengerSet[passenger].pathCost = round(pathEndCost,3)
            passengerSet[passenger].boardStops = boardStops
            passengerSet[passenger].alightStops = alightStops
            passengerSet[passenger].transferWtTime= transferWtTimeList

    return path,scannedTrips
#-
###############################################################################
#############         DEFINE RESULT PRINTING FUNCTIONS             ############
###############################################################################  
def printPassengerRoutes(pasengerRoutesDataPath, passengerSet, passengerID):
    '''
    PURPOSE: Write output passenger paths to file
             
    Input: 
            pasengerRoutesDataPath:          location to pasengerRoutesDataPath data      (PathString)
                      passengerSet:          Dictionary or passenger objects              (Dictionary)
                       passengerID:          ID of single passenger                       (String)

    Output:
            Output file that contains aggregate stats/info of each shortest path including all relevant timings
    '''
    printUnlinkedStatus = 'continue' 
    outPassReadFile = open(pasengerRoutesDataPath, 'r')
    existingPathAndTime = []
    outPassReadFile.readline()
    currentNumUniquePaths = 1
    for line in outPassReadFile:
        currentNumUniquePaths +=1
        lineCol = line.strip().split("\t")
        oldPaths=(lineCol[0],lineCol[3],lineCol[5])                                 #These columns need to be passengerID, Path, and travel cost
        if not oldPaths in existingPathAndTime:
            existingPathAndTime.append(oldPaths)
    outPassReadFile.close()
        
    outPassFile = open(pasengerRoutesDataPath, 'a')
    routes = []
    orig = passengerSet[passengerID].origin
    dest = passengerSet[passengerID].destination
    path = passengerSet[passengerID].CompletePath
    travelTime = passengerSet[passengerID].travelTime
    accessWalkTime = passengerSet[passengerID].accessWalkTime
    egressWalkTime = passengerSet[passengerID].egressWalkTime
    ivtTimes = passengerSet[passengerID].ivtTime
    transferTimes = passengerSet[passengerID].transferTimes
    travelCost = passengerSet[passengerID].pathCost
    boardStops = passengerSet[passengerID].boardStops
    alightStops = passengerSet[passengerID].alightStops
    brdRt1Time = passengerSet[passengerID].CompletePath[0][2]
    accessWaitTime=round(float(passengerSet[passengerID].accessWtTime),3)
    transferWaitTime=passengerSet[passengerID].transferWtTime
    
    if path == []:
        travelCost = 999999
        
    for segment in path:
        if segment[0]!='TRANSFER':
            routes.append(segment[0])

    tmpOut = str(passengerID)+'\t'+str(orig)+'\t'+str(dest)
    bracketlessRoutes="-->".join(routes)
    
    if routes != []:
        potentialNewPath = (str(passengerID),str(bracketlessRoutes),str(travelCost))     
    
        if potentialNewPath in existingPathAndTime:                                  #Control to make sure that path repetition in tree leaves not printed again  
            printUnlinkedStatus = 'skip'
            
        else:
            tmpOut = tmpOut +'\t'+str(bracketlessRoutes)+'\t'+str(travelTime)+'\t'+str(travelCost)+'\t'+str(brdRt1Time)+'\t'+str(accessWalkTime)+'\t'+str(accessWaitTime)+'\t'+str(boardStops)+'\t'+ str(ivtTimes)+'\t'+str(transferTimes)+'\t'+str(transferWaitTime)+'\t'+str(alightStops)+'\t'+str(egressWalkTime)
            outPassFile.write(tmpOut+'\n')
            
    outPassFile.close()

    return [printUnlinkedStatus, currentNumUniquePaths]
#--
#--
def printUnlinkedTrips(unlinkedDataPath, passengerSet, passengerID, linkSet, tripSet, stopSet, nodeSet):
    '''
    PURPOSE: Write output unlinked paths to file
             .
    Input: 
            unlinkedDataPath:          location to unlinkedDataPath data            (PathString)
                passengerSet:          Dictionary or passenger objects              (Dictionary)
                 passengerID:          ID of single passenger                       (String)
                passengerSet:          Dictionary of passenger objects              (Dictionary)
                     linkSet:          Dictionary of link objects                   (Dictionary)
                     tripSet:          Dictionary of trip objects                   (Dictionary)
                     stopSet:          Dictionary of stop objects                   (Dictionary)
                     nodeSet:          Dictionary of node objects                   (Dictionary)
    Output:
            Output file that includes details of every segment of an individuals shortest paths
    '''
    outUTripFile = open(unlinkedDataPath, 'a')
    tripID = ''
    seq = 1
    for p in passengerSet[passengerID].path:
        if p[0] != 'a' and p[0] != 'e':
            if linkSet[p].trip not in ['access', 'waitingtransfer', 'walkingtransfer', 'egress'] and linkSet[p].trip != tripID:
                tripID = linkSet[p].trip
                routeID = tripSet[tripID].route
                stopNode = linkSet[p].fromNode
                stopID = nodeSet[stopNode].stop
                stopLat = stopSet[stopID].lat
                stopLong = stopSet[stopID].long
                boardTime = nodeSet[stopNode].meanTime
                
                tmpOut = str(passengerID)+'\t'+str(seq)+'\t'+str(routeID)+'\t'+str(tripID)+'\t'+str(stopID)+'\t'+str(stopLat)+'\t'+str(stopLong)+'\t'+str(boardTime)
                outUTripFile.write(tmpOut+'\n')

                seq += 1

    outUTripFile.close()
#--
#--
def printMatchSuccessRate(ouputMatchPercentFilePath, inputPassengerRoutesPath, inputDemandPath, weightParams, numOfShortestPathIterations, passengerSet): 
    '''
    PURPOSE: Write stats on algorithm matching success with survey data
             
    Input: 
            ouputMatchPercentFilePath:          location to send output match data to                           (PathString)
             inputPassengerRoutesPath:          location of simulated path data                                 (PathString)
                      inputDemandPath:          ft_demand file for select passenge                              (PathString)
                         weightParams:          Perception of time weights (IVT, wait, walk,transfer)           (List of strings)
          numOfShortestPathIterations:          How many shortest paths have been run                           (String)
                         passengerSet:          Dictionary of passenger objects                                 (Dictionary)
    Output:
            Output file showing which passengers had a shortest path that exactly matched their surveyed path
    '''
    if os.path.exists(inputDemandPath) and os.path.exists(inputPassengerRoutesPath):
        if not Path(ouputMatchPercentFilePath).is_file():                       #If matching file doesnt exist
            testResultFile = open(ouputMatchPercentFilePath, 'w+')
            outputPercentMatch = "NoPath\tCompleteMatch\tInputParams\tPassengerID\t#UniqueShortestPath\tMatch?"
            testResultFile.write(outputPercentMatch+'\n')
            
        elif Path(ouputMatchPercentFilePath).is_file():                         #If the match file does exist then line break and append results of new path (match or not)
            testResultFile = open(ouputMatchPercentFilePath, 'a')
            testResultFile.write('\n')
    
        inputDemandFile = open(inputDemandPath)
        inputSimulatedPathsFile = open(inputPassengerRoutesPath)
        
        passengerID = ''
        completeMatchCount = 0
        noPossiblePathCount = 0
        simulatedPathDict = defaultdict(list)
    
        next(inputSimulatedPathsFile)
        for pathRow in inputSimulatedPathsFile:                                 #Create dictionary of all simulated paths for a selected person
            tmpPathIn = pathRow.strip().split("\t")
            if tmpPathIn[3] not in simulatedPathDict[tmpPathIn[0]]:                 
                simulatedPathDict[tmpPathIn[0]].append(tmpPathIn[3])

    #### Add Surveyed Routes To List For Each Passenger      
        next(inputDemandFile)
        for row in inputDemandFile:
            tmpIn = row.strip().split("\t")
            passengerID = tmpIn[0]
            numShortestPath = len(simulatedPathDict[passengerID])
            print('From PrintMatchFunct:', simulatedPathDict[tmpIn[0]])             #This is a nice feature that prints unique routes at end of each passenger
            
            if simulatedPathDict[passengerID] == []:
                noPossiblePathCount += 1
            else:
                for i in range(len(simulatedPathDict.get(tmpIn[0]))):               #For each passenger
                    if simulatedPathDict.get(tmpIn[0])[i] == tmpIn[-1] :            #If one of the shortest paths matches the actual path taken
                        completeMatchCount += 1
                        break                                                       #As soon as a match is found exit
            if completeMatchCount != 0:
                matchYorN = 'YES'
            else:
                matchYorN = 'NO'
        
        testResultFile.write(str(noPossiblePathCount)+'\t'+str(completeMatchCount)+'\t'+str(weightParams)+
                                 '\t'+ str(passengerID)+'\t'+str(numShortestPath)+'\t'+str(matchYorN))

        inputDemandFile.close()
        testResultFile.close()  
#--
###############################################################################
#############             DEFINE ASSIGNMENT FUNCTION               ############
###############################################################################   
def singleElim(passenger, passOrig, passDest, passPDT, passengerSet, _pathType, timeWindow, accessTimeWindow, assignedSP, totalSPCount,
               weights, zoneSet, nodeSet, stopSet, linkSet, tripSet, indivEliminatedTrips, pastParentNode, inputDataLocation, parentTreeDict):
    '''
    PURPOSE: Combine both find and getShortestPath functions together while using single link(aka trip) (aggregate) elimination to generate more than 1 shortest path
             
    Input: 
                       passengerID:     PassengerID for the passenger whose shortest paths will be assigned      (string)
                          passOrig:     Origin node for the given passenger                                      (string)
                          passDest:     Destination node for the given passenger                                 (string) 
                           passPDT:     Preferred departure time for selected passenger                          (int)
                      passengerSet:     Dictionary of passengers and their associated attributes                 (dict)                      
                         _pathType:     location to output linkFlow data to set in assignPassengers function     (PathString)
                        timeWindow:     Maximum allowable wait time of any portion of the trip                   (int)
                  accessTimeWindow:
                        assignedSP:
                      totalSPCount:
                           weights:     Perception of time weights for IVT, Wait, Walk, & Transfer               (list of ints)
                           zoneSet:     Dictionary of passenger origins and destinations with lat-long           (dict)
                           nodeSet:     Dictionary of all nodes in transit network                               (dict)
                           stopSet:     Dictionary of all stops in transit network                               (dict)
                           linkSet:     Dictionary of all links in transit network                               (dict)
                           tripSet:     Dictionary of all transit trips on the transit network                   (dict)
              indivEliminatedTrips:
                    pastParentNode:
                 inputDataLocatoin:
                    parentTreeDict:


    Output: Labeled SP nodes and assigned SP for each passenger printed to output files from printPassengerRoutes and printUnlinkedTrips
        
    '''
    try:
        findShortestPath(passOrig, passPDT, _pathType, accessTimeWindow,weights, zoneSet, nodeSet, linkSet, indivEliminatedTrips)
    except TypeError:
        print("No Access To Zone:", passDest)
        totalSPCount += 1
        
    _path, previouslyScannedTrips = getShortestPath(passenger, passDest, zoneSet, nodeSet, linkSet, passengerSet, tripSet, stopSet, routeID2RouteShortDict) 
        
    for prevScan in previouslyScannedTrips:
        parentTreeDict[prevScan]= treeNode(prevScan, parent = pastParentNode)

    if _path==[]:
        print ("No path for passenger ", passenger)
        passengerSet[passenger].path = []                                          #Assign path from shortest path to passenger
    
    else:
        assignedSP = assignedSP + 1
    #Determine Travel Time
        passengerSet[passenger].path = _path                                       #Assign path from shortest path to passenger
        print()
        passengerSet[passenger].travelStartTime = round(nodeSet[linkSet[passengerSet[passenger].path[0]].toNode].labels[0],3)
        passengerSet[passenger].travelTime=round(passengerSet[passenger].accessWalkTime+float(passengerSet[passenger].travelEndTime)-float(passengerSet[passenger].travelStartTime),2)
        passengerSet[passenger].accessWtTime = (round(nodeSet[linkSet[passengerSet[passenger].path[0]].toNode].labels[0],3)-round(nodeSet[linkSet[passengerSet[passenger].path[0]].fromNode].labels[0],3)-passengerSet[passenger].accessWalkTime)
            
    totalSPCount = totalSPCount + 1
            
    
    proceedWithUnlinkedPrint, numUniquePath = printPassengerRoutes(os.path.join(inputDataLocation,('passengerRoutes%s_%s_%s_%s_%s.dat'%(int(weights[0]),int(weights[1]),int(weights[2]),int(weights[3]),passenger))),passengerSet,passenger)
    if proceedWithUnlinkedPrint != 'skip':
        printUnlinkedTrips(os.path.join(inputDataLocation,"unlinkedTrips%s_%s_%s_%s_%s.dat"%(int(weights[0]),int(weights[1]),int(weights[2]),int(weights[3]),passenger)), passengerSet, passenger, linkSet, tripSet, stopSet, nodeSet)
    
    #Reset prevScannedTrips to be empty for next subsequent iterations
    previouslyScannedTrips = []        
  
    indivEliminatedTrips = [child.name for child in pastParentNode.children]      #Where the children (trips on the first shortest path were assigned immediately above this)
    singleElimTripNodes=[child for child in pastParentNode.children]              #Tree nodes for each trip on the old SP
    elimTripIterations = len(indivEliminatedTrips)

    return [indivEliminatedTrips, singleElimTripNodes,elimTripIterations, assignedSP, totalSPCount, numUniquePath]
#--
#--

    
def assignPassengers(_pathType, accessTimeWindow, totalTripTimeLimit, weights, zoneSet, nodeSet, linkSet, passengerSet, tripSet, stopSet, numOfShortestPathIterations, passengerID):
    '''
    PURPOSE: Function that assigns each passenger to his/her shortest path given the perception of time (weights)
             
    Input: 
                         _pathType:     location to output linkFlow data to set in assignPassengers function     (PathString)
                  accessTimeWindow:     Maximum allowable wait time for access                                   (int)
                totalTripTimeLimit:     Maximum allowable total cost (perception of time) for complete path      (int)
                           weights:     Perception of time weights for IVT, Wait, Walk, & Transfer               (list of ints)
                           zoneSet:     Dictionary of passenger origins and destinations with lat-long           (dict)
                           nodeSet:     Dictionary of all nodes in transit network                               (dict)
                           linkSet:     Dictionary of all links in transit network                               (dict)
                      passengerSet:     Dictionary of passengers and their associated attributes                 (dict)
                           tripSet:     Dictionary of all transit trips on the transit network                   (dict)
                           stopSet:     Dictionary of all stops in transit network                               (dict)
       numOfShortestPathIterations:     Number of shortest paths per passenger to stop algorithm at              (int)
                       passengerID:     PassengerID for the passenger whose shortest paths will be assigned      (string)
                       
    Output: Assigned passengers and matchingPathSuccess txt file as well as passengerRoutes and unlinkedTrips file for each passenger that contains all assignment info
            
    '''
    
    totalSPCount = 0
    assignedSP = 0
    startTime = time.perf_counter()
    passengerCount = 0
    
    for passenger in passengerSet:
        passengerCount+=1
        accessScannedList = []
        egressScannedList = []
        passOrig = passengerSet[passenger].origin
        passDest = passengerSet[passenger].destination
        passPDT = passengerSet[passenger].PDT
        passengerSet[passenger].path = []
        parentNode = treeNode('ParentNode') #Used in single link elim tree construction
        treeDict = dict()
        
##### Find available access points for passenger #####
        tmpLinksA = []
        tmpLinksE = []
        tmpNodesA = []
        tmpNodesE = []

        accessNodeId = "access" + "," + passOrig
        if not(accessNodeId in nodeSet):
            nodeSet[accessNodeId] = Node(["access", -1, -1, passOrig, 0])
            zoneSet[passOrig].accessNode=accessNodeId
        
        tmpLat1 = zoneSet[passOrig].lat
        tmpLon1 = zoneSet[passOrig].long
        temp1 = (tmpLat1, tmpLon1)
        originG=ox.core.graph_from_point(temp1, (1.1*1609.34), 'network', 'walk', simplify=True) #Based on 95% coverage of data. Make distance ~0.1 miles larger than actual buffer you want
         
        for _stp in stopSet:
            tmpLatSecond = stopSet[_stp].lat 
            tmpLonSecond = stopSet[_stp].long 
            tempStop2 = (tmpLatSecond, tmpLonSecond)
            if tempStop2 != temp1 and tempStop2 not in accessScannedList and haversine(temp1, tempStop2, unit='mi') <= 1.0:
                accessScannedList.append(tempStop2)
                accessPathLengthMiles = round((nx.shortest_path_length(originG, ox.get_nearest_node(originG,temp1),ox.get_nearest_node(originG,tempStop2), weight='length'))/1609.34,3)

                if accessPathLengthMiles <= 1.0:
                    accessTmpDist = max(accessPathLengthMiles,0.001)
                    accessTmpNodes = stopSet[_stp].nodes    
                    
                    for accessN in accessTmpNodes:
                        tmpWalkTime = (accessTmpDist/3.0) * 60
                        
                        if (nodeSet[accessN].meanTime > (passPDT + tmpWalkTime)) and (nodeSet[accessN].meanTime < (passPDT + tmpWalkTime + accessTimeWindow)):

                            if nodeSet[accessN].last!=1:
                                accessLinkId = "access"+","+str(len(linkSet)+1)
                                
                                if accessLinkId not in linkSet:   
                                    linkSet[accessLinkId] = Link(accessNodeId, accessN, "access", tmpWalkTime)
                                    nodeSet[accessNodeId].outLinks.append(accessLinkId)
                                    nodeSet[accessN].inLinks.append(accessLinkId)
                                    tmpLinksA.append(accessLinkId)
                                    tmpNodesA.append(accessN)
                                                       
                                elif accessLinkId in linkSet:
                                    print ("1.ERROR: Access linkId already in linkSet")
                            
##### Find available egress points for passenger #####
        nodeId = "egress" + "," + passDest
        if not(nodeId in nodeSet):
            nodeSet[nodeId] = Node(["egress", -1, -1, passDest, 0])
            zoneSet[passDest].egressNode=nodeId
                        
        destTmpLat1 = zoneSet[passDest].lat 
        destTmpLon1 = zoneSet[passDest].long 
        destTemp1 = (destTmpLat1, destTmpLon1)
        destG=ox.core.graph_from_point(destTemp1, (0.72*1609.34), 'network', 'walk', simplify=True) #Based on 95% coverage. Make distance ~0.1 miles larger than actual buffer you want
        
        for stp in stopSet:
            destTmpLat2 = stopSet[stp].lat 
            destTmpLon2 = stopSet[stp].long 
            destTemp2 = (destTmpLat2, destTmpLon2)
            if destTemp2 != destTemp1 and destTemp2 not in egressScannedList and haversine(destTemp1, destTemp2, unit='mi')<1.0:
                egressScannedList.append(destTemp2)
                destPathLengthMiles = round((nx.shortest_path_length(destG, ox.get_nearest_node(destG,destTemp1),ox.get_nearest_node(destG,destTemp2), weight='length'))/1609.34,3)

                if destPathLengthMiles <= 0.71:
                    destTmpDist = max(destPathLengthMiles,0.001)

                    destTmpNodes = stopSet[stp].nodes
                    for n in destTmpNodes:
                        tmpWalkTime = (destTmpDist/3.0) * 60
                        if ((nodeSet[n].meanTime + tmpWalkTime) > passPDT) and (nodeSet[n].meanTime < (passPDT + totalTripTimeLimit)):# limit transit trips to 3 hours tmpWalkTime > PDT - timeWindow:

                            if nodeSet[n].seq!=1:
                                linkId = "egress"+","+str(len(linkSet)+1)
                                
                                if linkId in linkSet:
                                    print ("2.ERROR")
                                linkSet[linkId] = Link(n, nodeId, "egress", tmpWalkTime)
                                nodeSet[n].outLinks.append(linkId)
                                nodeSet[nodeId].inLinks.append(linkId)
                            
                                tmpLinksE.append(linkId)
                                tmpNodesE.append(n)
        
        if tmpLinksA == []:
            totalSPCount += 1
            print ("no ACCESS for passenger" , passenger)
            continue
    
        if tmpLinksE == []:
            print ("no EGRESS for passenger" , passenger)
            continue
        
#### LINK/TRIP ELIMINATION CODE CONTAINED WITHIN THE LOOP BELOW
        #After each SP is found exclude the trips contained within that path and re-run for new SP
            
        
        outUTripFile = open(os.path.join(inputDataLocation,"unlinkedTrips%s_%s_%s_%s_%s.dat"%(int(weights[0]),int(weights[1]),int(weights[2]),int(weights[3]),passenger)), "w+")
        tmpOut = "passenger\tseqNum\troute\ttripID\tboardStop\tboardStopLat\tboardStopLon\tboardTime"
        outUTripFile.write(tmpOut+'\n')
        outUTripFile.close()
        
        outPassFile = open(os.path.join(inputDataLocation,('passengerRoutes%s_%s_%s_%s_%s.dat'%(int(weights[0]),int(weights[1]),int(weights[2]),int(weights[3]),passenger))), 'w+')
        tmpOut = "ID\tOrigin\tDestination\tRoutes\tTime\tCost\tBrdRt1Time\tAccessTime\tAccessWtTime\tBrdStops\tivtTimes\tTransferTimes\tTrWtTime\tEgressStops\tEgressTime"
        outPassFile.write(tmpOut+'\n')
        outPassFile.close()
    
    
        #First sp with no trips eliminated
        singleElimTrip = []
        singleElimTripList = []
        singleElimTripNodesList = []
        singleElimTripIterationsList =[]


        singleElimTrip, singleElimTripNodes,elimTripIterations, assignedSP, totalSPCount, currentUniquePaths= singleElim(passenger, passOrig, passDest, passPDT,passengerSet, _pathType, maxWaitTimeWindow,accessTimeWindow, assignedSP,totalSPCount,
                                                                                                     weights, zoneSet, nodeSet,stopSet, linkSet, tripSet, singleElimTrip, parentNode, inputDataLocation, treeDict)
        singleElimTripList.append(singleElimTrip)
        singleElimTripNodesList.append(singleElimTripNodes)
        singleElimTripIterationsList.append(elimTripIterations)
  
    
        doubleElimTripList = []
        doubleElimTripNodesList = []
        doubleElimTripIterationsList =[]
        
        for singleTripIter in range (len(singleElimTripList)):
            for kidNum in range(elimTripIterations):
                doubleElimTrip, doubleElimTripNodes,doubleElimTripIterations, assignedSP, totalSPCount, currentUniquePaths= singleElim(passenger, passOrig, passDest, passPDT,passengerSet, _pathType, maxWaitTimeWindow,accessTimeWindow,assignedSP,totalSPCount,
                                                                                                         weights, zoneSet, nodeSet,stopSet, linkSet, tripSet, 
                                                                                                         [node.name for node in singleElimTripNodesList[singleTripIter][kidNum].path[1:]], singleElimTripNodesList[singleTripIter][kidNum], 
                                                                                                         inputDataLocation, treeDict)
                doubleElimTripList.append(doubleElimTrip)
                doubleElimTripNodesList.append(doubleElimTripNodes)
                doubleElimTripIterationsList.append(doubleElimTripIterations)
        
        if int(currentUniquePaths) < 10:
            tripleElimTripList = []
            tripleElimTripNodesList = []
            tripleElimTripIterationsList =[]
                
            for doubleTripIter in range (len(doubleElimTripList)):   
                for doubleKidNum in range(doubleElimTripIterationsList[doubleTripIter]):
                    tripleElimTrip, tripleElimTripNodes,tripleElimTripIterations, assignedSP, totalSPCount, currentUniquePaths= singleElim(passenger, passOrig, passDest, passPDT,passengerSet, _pathType, maxWaitTimeWindow,accessTimeWindow, assignedSP,totalSPCount,
                                                                                    weights, zoneSet, nodeSet,stopSet, linkSet, tripSet,
                                                                                    [node.name for node in doubleElimTripNodesList[doubleTripIter][doubleKidNum].path[1:]],
                                                                                    doubleElimTripNodesList[doubleTripIter][doubleKidNum],inputDataLocation, treeDict)
                    tripleElimTripList.append(tripleElimTrip)
                    tripleElimTripNodesList.append(tripleElimTripNodes)
                    tripleElimTripIterationsList.append(tripleElimTripIterations)

        if int(currentUniquePaths) < 10:
            quadElimTripList = []
            quadElimTripNodesList = []
            quadElimTripIterationsList =[]
            
            for tripleTripIter in range (len(tripleElimTripList)):   
                for tripleKidNum in range(tripleElimTripIterationsList[tripleTripIter]):
                    quadElimTrip, quadElimTripNodes,quadElimTripIterations, assignedSP, totalSPCount, currentUniquePaths= singleElim(passenger, passOrig, passDest, passPDT,passengerSet, _pathType, maxWaitTimeWindow,accessTimeWindow, assignedSP,totalSPCount,
                                                                                    weights, zoneSet, nodeSet,stopSet, linkSet, tripSet,
                                                                                    [node.name for node in tripleElimTripNodesList[tripleTripIter][tripleKidNum].path[1:]],
                                                                                    tripleElimTripNodesList[tripleTripIter][tripleKidNum],inputDataLocation, treeDict)
                    quadElimTripList.append(quadElimTrip)
                    quadElimTripNodesList.append(quadElimTripNodes)
                    quadElimTripIterationsList.append(quadElimTripIterations)
           
               
        if int(currentUniquePaths) < 10:
            quintElimTripList = []
            quintElimTripNodesList = []
            quintElimTripIterationsList =[]
            
            for quadTripIter in range (len(quadElimTripList)):   
                for quadKidNum in range(quadElimTripIterationsList[quadTripIter]):
                    quintElimTrip, quintElimTripNodes,quintElimTripIterations, assignedSP, totalSPCount, currentUniquePaths= singleElim(passenger, passOrig, passDest, passPDT,passengerSet, _pathType, maxWaitTimeWindow,accessTimeWindow,assignedSP,totalSPCount,
                                                                                    weights, zoneSet, nodeSet,stopSet, linkSet, tripSet,
                                                                                    [node.name for node in quadElimTripNodesList[quadTripIter][quadKidNum].path[1:]],
                                                                                    quadElimTripNodesList[quadTripIter][quadKidNum],inputDataLocation, treeDict)
                    quintElimTripList.append(quintElimTrip)
                    quintElimTripNodesList.append(quintElimTripNodes)
                    quintElimTripIterationsList.append(quintElimTripIterations)
               
        
##Make Sure 10SP are run    
        if (len(parentNode.descendants) < int(numOfShortestPathIterations)) and int(currentUniquePaths) < 10:
            quitLoop = 'no'
            allPrevSingleScannedTrips = []
            if 'kidNum' in locals():
                for singleNum in range(kidNum):
                    allPrevSingleScannedTrips.append(singleElimTripList[singleNum])
            if 'doubleKidNum' in locals():
                for doubleNum in range(doubleKidNum):
                    allPrevSingleScannedTrips.append(doubleElimTripList[doubleNum])
            if 'tripleKidNum' in locals():
                for tripleNum in range(tripleKidNum):
                    allPrevSingleScannedTrips.append(tripleElimTripList[tripleNum])
            if 'quadKidNum' in locals():
                for quadNum in range(quadKidNum):
                    allPrevSingleScannedTrips.append(quadElimTripList[quadNum])

            
        while (len(parentNode.descendants) < int(numOfShortestPathIterations)) and (len(allPrevSingleScannedTrips) <= int(numOfShortestPathIterations)) and (quitLoop !='yes'):
            try:    
                findShortestPath(passOrig, passPDT, _pathType, accessTimeWindow,weights, zoneSet, nodeSet, linkSet, 
                                 allPrevSingleScannedTrips)[0]
                
            except:
                print ("No Access to Zone:", passDest)
                totalSPCount += 1
            
            _pathExtra, previouslyScannedTrips = getShortestPath(passenger, passDest, zoneSet, nodeSet, linkSet, passengerSet, tripSet, stopSet, routeID2RouteShortDict) 
            
            for prevScanExtra in previouslyScannedTrips:
                if prevScanExtra not in allPrevSingleScannedTrips:
                    allPrevSingleScannedTrips.append(prevScanExtra)
            
            if _pathExtra == []:
                print ("No path for passenger ", passenger, '\tverify with min stop label: ', min([nodeSet[n].labels[1] for n in tmpNodesE]))
                break
                quitLoop = 'yes'
            else:
                assignedSP = assignedSP + 1
                
            totalSPCount = totalSPCount + 1
            passengerSet[passenger].path = _pathExtra #Assign path from shortest path to passenger
            
            #Determine Travel Time (Added on 4/18/19)
            passengerSet[passenger].travelStartTime = round(nodeSet[linkSet[passengerSet[passenger].path[0]].toNode].labels[0],3)
            passengerSet[passenger].travelTime=round(passengerSet[passenger].accessWalkTime+float(passengerSet[passenger].travelEndTime)-float(passengerSet[passenger].travelStartTime),2)
            passengerSet[passenger].accessWtTime = (round(nodeSet[linkSet[passengerSet[passenger].path[0]].toNode].labels[0],3)-round(nodeSet[linkSet[passengerSet[passenger].path[0]].fromNode].labels[0],3)-passengerSet[passenger].accessWalkTime)

            #Print Results
            proceedWithUnlinkedPrint = printPassengerRoutes(os.path.join(inputDataLocation,('passengerRoutes%s_%s_%s_%s_%s.dat'%(int(weights[0]),int(weights[1]),int(weights[2]),int(weights[3]),passengerID))),passengerSet,passenger)[0]
            if proceedWithUnlinkedPrint != 'skip':
                printUnlinkedTrips(os.path.join(inputDataLocation,"unlinkedTrips%s_%s_%s_%s_%s.dat"%(int(weights[0]),int(weights[1]),int(weights[2]),int(weights[3]),passengerID)), passengerSet, passenger, linkSet, tripSet, stopSet, nodeSet)

     
        timeCount = round(time.perf_counter()-startTime,3)
        

        
        if totalSPCount%1==0:
            print ("%s shortest paths assigned out of %s. %s Passengers assigned in %4d seconds" %(assignedSP, totalSPCount, passengerCount, timeCount))
        
        ### Remove passenger access/egress links from memory
        nodeSet["access" + "," + passOrig].outLinks = []
        nodeSet["egress" + "," + passDest].inLinks = []


        for link in tmpLinksA:
            del linkSet[link]
            
            for nd in tmpNodesA:
                nodeSet[nd].inLinks = [x for x in nodeSet[nd].inLinks if not link]
            
        for link in tmpLinksE:
            del linkSet[link]
            
            for nd in tmpNodesE:
                nodeSet[nd].outLinks = [x for x in nodeSet[nd].outLinks if not link]
                    
        tmpLinksA = []
        tmpLinksE = []
        tmpNodesA = []
        tmpNodesE = []
        
    printMatchSuccessRate(os.path.join(inputDataLocation,'matchingPathSuccessData.txt'),
                          os.path.join(inputDataLocation,'passengerRoutes%s_%s_%s_%s_%s.dat'%(int(weights[0]),int(weights[1]),int(weights[2]),int(weights[3]),passengerID)),
                          os.path.join(inputDataLocation,"ft_input_demand.dat"),
                          weights, numOfShortestPathIterations, passengerSet)
    
 
###############################################################################
#############                    EXECUTE CODE                      ############
###############################################################################          
##Create list of unique Passenger ID's
passIDList = []
avgUnlinkedPathTimeMinutes = 30


with open(OBSFilePath) as inputOBSFile:
    inputOBSFile.readline()
    reader = csv.reader(inputOBSFile, delimiter=",")
    for row in reader:
        if row[accessModeIndex] == 'Walked all the way' and row[egressModeIndex] == 'Walk all the way' and row[surveyDateIndex] in validDates:
            passIDList.append(row[0])

routeID2RouteShortDict={}
routesInputFile = open(os.path.join(inputDataLocation, "ft_input_routes.dat"),'r')
routesInputFile.readline()
for line in routesInputFile:
    row = line.strip().split('\t')
    routeID2RouteShortDict[row[0]] = str(row[2])
    

for i,assignPassID in enumerate(passIDList):                                                 #Total list is 2087 but some of these may be excluded because of filtering from access/egress etc etc
    print('\n\n')
    demandInputFileGeneration.createDemandFile(validDates, assignPassID,accessModeIndex, egressModeIndex, surveyDateIndex, passengerIDIndex, amOrPmIndex, 
                     transfersBeforeSurveyCountIndex, firstRouteBeforeTransferIndex,secondRouteBeforeTransferRouteIndex,thirdRouteBeforeTransferRouteIndex,
                     transfersAfterSurveyCountIndex, firstRouteAfterTransferIndex, secondRouteAfterTransferIndex, thirdRouteAfterTransferIndex,
                     survyedRouteIndex, surveyedTimeMinPastMidnightIndex, avgUnlinkedPathTimeMinutes, originLatIndex, originLonIndex, destLatIndex, destLonIndex)
    
    print('Start Time: ', str(datetime.datetime.now()))
    maxWaitTimeWindow = 20                                                             #Transfer wait time as 20min or less
    accessTimeWindow = 60                                                       #Access scan of 1hr (this wait time will not be included in the total time)
    totalTripTimeLimit = 300                                                    #Limit to 5 hrs
    addedPDTMin = 0
    weights = [1.0,1.0,1.0,15.0]                                                #IVT, WT, WK, TR  
    
    zoneDict = {}
    stopDict = {}
    tripDict = {}
    nodeDict = {}
    linkDict = {}
    passengerDict = {}
     
    ##LOAD DATA
    numZones = readZones(os.path.join(inputDataLocation,"ft_input_zones.dat"), zoneDict)[0]
    if numZones >0:
        print('Person Exists:', assignPassID)
        print(numZones, 'zones')
        readStops(os.path.join(inputDataLocation, "ft_input_stops.dat"), stopDict)
        readTrips(os.path.join(inputDataLocation, "ft_input_trips.dat"), tripDict)
        readDemand(os.path.join(inputDataLocation,"ft_input_demand.dat"),passengerDict, addedPDTMin)
        readSchedule(os.path.join(inputDataLocation, "ft_input_stopTimes.dat"), nodeDict, stopDict, linkDict)
        readWaitingTransfer(stopDict, nodeDict, tripDict, linkDict, maxWaitTimeWindow)
        readTransferLinks(os.path.join(inputDataLocation,"ft_input_transfers.dat"), stopDict, nodeDict, tripDict, linkDict, maxWaitTimeWindow)
        print('Current Time after reading schedule, demand, trips, stops, transfers, and zones: ', str(datetime.datetime.now()))
        
        ##ASSIGN DATA
        treeTest = assignPassengers("optimal", accessTimeWindow, totalTripTimeLimit, weights, zoneDict, nodeDict, linkDict, passengerDict, tripDict, stopDict,11, assignPassID) #10+
        print('Current Time after passenger assignment is: ', str(datetime.datetime.now()))
