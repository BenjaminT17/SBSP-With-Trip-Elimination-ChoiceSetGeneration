# -*- coding: utf-8 -*-
"""
Created on Fri Aug  2 14:41:04 2019

@author: tomha021
"""

# -*- coding: utf-8 -*-
"""
Created on Mon Feb 11 09:48:33 2019

@author: tomha021.
"""

###########################################################################
#############                INPUT DEMAND                     #############    
###########################################################################
def createDemandFile(validDates, passengerID, accessModeIndex, egressModeIndex, surveyDateIndex, passengerIDIndex, amOrPmIndex, 
                     transfersBeforeSurveyCountIndex, firstRouteBeforeTransferIndex,secondRouteBeforeTransferRouteIndex,thirdRouteBeforeTransferRouteIndex,
                     transfersAfterSurveyCountIndex, firstRouteAfterTransferIndex, secondRouteAfterTransferIndex, thirdRouteAfterTransferIndex,
                     survyedRouteIndex, surveyedTimeMinPastMidnightIndex, avgUnlinkedPathTimeMinutes,
                     originLatIndex, originLonIndex, destLatIndex, destLonIndex):
    '''
    Creates function that creates passenger files from OBSurvey to be run in sbspWithRoutes.Py 
    Specify passengerID (int) for each passenger one at a time
        MODIFY THIS TO BE MORE INCLUSIVE BY CHANGING THE STRICT EQUALITY TO BE <= FOR (INT(ROW[0])==PASSENGERID)
    ''' 
    import os, csv
    OBSFilePath= r'[Path to Folder Containing On Board Survey]\Survey.csv'
    ftFilePath= r"[INPUT Path To Fast-Trips Formated Files]"

    with open(os.path.join(ftFilePath,"ft_input_demand.dat"), "w+") as outputFile:
        with open(OBSFilePath) as inputFile:
            inputFile
            i=-1
            for row in csv.reader(inputFile):
                if i == -1:
                    headerOut= "passengerId\tOrigTAZ\tDestTAZ\tMode\ttimePeriod\tDirection\tPDT\tSurveyedPath\n"
                    outputFile.write(headerOut)
                    i=i+1
                else:
                    if row[accessModeIndex] == 'Walked all the way' and row[egressModeIndex] == 'Walk all the way' and row[surveyDateIndex] in validDates and str(row[passengerIDIndex])==str(passengerID):
                        i=i+1     
                        passengerID = (row[passengerIDIndex])
                        origTAZ = ("{}{}".format("O", passengerID))
                        destTAZ = ("{}{}".format("D", passengerID))
                        mode = ('.')
                        timePeriod = row[amOrPmIndex]                                                            #Determine if end of time range is AM or PM
                        direction = ('.')

                        if int(row[transfersBeforeSurveyCountIndex])==0:                                         #If there are no transfers before surveyed route then create PDT as surveyed time
                            PDT = int(row[surveyedTimeMinPastMidnightIndex])                                       #In min past midnight to start of time range on surveyed route
                                                          
                        elif int(row[transfersBeforeSurveyCountIndex])==1:                                       #If there is one transfer before survyed route then create PDT as surveyed time-avg unlinked IVT
                            PDT = int(row[surveyedTimeMinPastMidnightIndex])-avgUnlinkedPathTimeMinutes                       #Same as above but subtracting avg matched path unlinked time (15.82 min) and avg. matched path transfer time for paths with transfer (TrWalk+TrWait=7.38min)
      
                        elif int(row[transfersBeforeSurveyCountIndex])==2:                                       #If there are 2 transfer before survyed route then create PDT as surveyed time-2*avg unlinked IVT
                            PDT = int(row[surveyedTimeMinPastMidnightIndex])-(2*avgUnlinkedPathTimeMinutes)                                    
  
                        elif int(row[transfersBeforeSurveyCountIndex])==3:                                       #If there are 3 transfer before survyed route then create PDT as surveyed time-3*avg unlinked IVT
                            PDT = int(row[surveyedTimeMinPastMidnightIndex])-(3*avgUnlinkedPathTimeMinutes)                             

#************************************************************************************************************************************************************************
####PRESERVE LEADING ZEROS               
#Comment this section of the code out/edit if more than three digit routes and leading zeros aren't uniform etc. or aren't used
                        if len(row[thirdRouteBeforeTransferRouteIndex])<3 and row[thirdRouteBeforeTransferRouteIndex]!= '':
                            row[thirdRouteBeforeTransferRouteIndex] = "{:03d}".format(int(row[thirdRouteBeforeTransferRouteIndex]))
                        if len(row[secondRouteBeforeTransferRouteIndex])<3 and row[secondRouteBeforeTransferRouteIndex]!= '':
                            row[secondRouteBeforeTransferRouteIndex] = "{:03d}".format(int(row[secondRouteBeforeTransferRouteIndex]))
                        if len(row[firstRouteBeforeTransferIndex])<3 and row[firstRouteBeforeTransferIndex]!= '':
                            row[firstRouteBeforeTransferIndex] = "{:03d}".format(int(row[firstRouteBeforeTransferIndex])) 
                            
                        if len(row[survyedRouteIndex])<3 and row[survyedRouteIndex]!= '':
                            row[survyedRouteIndex] = "{:03d}".format(int(row[survyedRouteIndex]))
                            
                        if len(row[firstRouteAfterTransferIndex])<3 and row[firstRouteAfterTransferIndex]!= '':
                            row[firstRouteAfterTransferIndex] = "{:03d}".format(int(row[firstRouteAfterTransferIndex]))
                        if len(row[secondRouteAfterTransferIndex])<3 and row[secondRouteAfterTransferIndex]!= '':
                            row[secondRouteAfterTransferIndex] = "{:03d}".format(int(row[secondRouteAfterTransferIndex]))                                 
                        if len(row[thirdRouteAfterTransferIndex])<3 and row[thirdRouteAfterTransferIndex]!= '':
                            row[thirdRouteAfterTransferIndex] = "{:03d}".format(int(row[thirdRouteAfterTransferIndex]))                                 
#*************************************************************************************************************************************************************************                                                                
                                
    ##IF THERE ARE TRANSFERS BEFORE SURVEYED...                       
                  #If THREE transfers before      
                        if row[transfersBeforeSurveyCountIndex] == '3':
                            thirdBeforeAppendedRoute = row[thirdRouteBeforeTransferRouteIndex]
                            secondBeforeAppendedRoute = row[secondRouteBeforeTransferRouteIndex]                            
                            firstBeforeAppendedRoute = row[firstRouteBeforeTransferIndex]
                            
                            surveyedPath=str(firstBeforeAppendedRoute+'-->'+secondBeforeAppendedRoute+'-->'+thirdBeforeAppendedRoute+'-->'+row[survyedRouteIndex])
                            
                  #If TWO transfers before      
                        if row[transfersBeforeSurveyCountIndex] == '2':
                            secondBeforeAppendedRoute = str(row[secondRouteBeforeTransferRouteIndex])
                            firstBeforeAppendedRoute = str(row[firstRouteBeforeTransferIndex])
                            surveyedPath=str(firstBeforeAppendedRoute+'-->'+secondBeforeAppendedRoute+'-->'+row[survyedRouteIndex])
                            
                 #If ONLY 1 transfers before          
                        if row[transfersBeforeSurveyCountIndex] == '1':
                            singleBeforeAppendedRoute = str(row[firstRouteBeforeTransferIndex])
                            surveyedPath=str(singleBeforeAppendedRoute+'-->'+ str(row[survyedRouteIndex]))
                        
    ##THEN APPEND SURVEYED ROUTE...  
                        if row[transfersBeforeSurveyCountIndex] == '0':
                            surveyedPath = str(row[survyedRouteIndex])
                            

    ##IF THERE ARE TRANSFERS AFTER SURVEYED...  
            #If there is 1 transfer AFTER the surveyed route append that routeShortName                     
                        if row[transfersAfterSurveyCountIndex] == '1': 
                            appendedRoute = str(row[firstRouteAfterTransferIndex])
                            surveyedPath = surveyedPath + str('-->'+appendedRoute)

            #If there are 2 transfers AFTER the surveyed route append that routeShortName
                        if row[transfersAfterSurveyCountIndex] == '2': 
                            appendedRoute = str(row[firstRouteAfterTransferIndex])
                            secondAfterAppendedRoute = str(row[secondRouteAfterTransferIndex])
                            surveyedPath=  surveyedPath+str('-->'+appendedRoute+'-->'+secondAfterAppendedRoute)
                            
                           
            #If there are 3 transfers AFTER the surveyed route append that routeShortName
                        if row[transfersAfterSurveyCountIndex] == '3': 
                            appendedRoute = str(row[firstRouteAfterTransferIndex])
                            secondAfterAppendedRoute = str(row[secondRouteAfterTransferIndex])                            
                            thirdAfterAppendedRoute = str(row[thirdRouteAfterTransferIndex])
                            surveyedPath=surveyedPath+str('-->'+appendedRoute+'-->'+secondAfterAppendedRoute+'-->'+thirdAfterAppendedRoute)
  
                        strOut = str(passengerID) + "\t" + str(origTAZ) + "\t" + str(destTAZ) + "\t" + str(mode) +"\t" + str(timePeriod) +"\t" + str(direction) +"\t" + str(PDT) + "\t" +str(surveyedPath) + "\n"
                        outputFile.write(strOut)

    ###########################################################################
    #############                    INPUT ZONES                  #############    
    ###########################################################################
    with open(os.path.join(ftFilePath,"ft_input_zones.dat"), "w+") as outputFile2:
        with open(OBSFilePath) as inputFile:
            i=-1
            for row in csv.reader(inputFile):
                if i == -1:
                    headerOut= "zoneId\tLatitude\tLongitude\n"
                    outputFile2.write(headerOut)
                    i=i+1
                else: 
                    if  row[accessModeIndex] == 'Walked all the way' and row[egressModeIndex] == 'Walk all the way' and row[surveyDateIndex] in validDates and str(row[passengerIDIndex])==str(passengerID):
                        i=i+1
                        passengerID = (row[passengerIDIndex])
                        originZoneID = ("{}{}".format("O", passengerID))
                        originZoneLat = row[originLatIndex]
                        originZoneLon = row[originLonIndex]
                        originStrOut = str(originZoneID) + "\t" + str(originZoneLat) + "\t" + str(originZoneLon) + "\n"
                        outputFile2.write(originStrOut)
                        
                        destZoneID = ("{}{}".format("D", passengerID) )
                        destZoneLat =  row[destLatIndex]
                        destZoneLon = row[destLonIndex]
                        destStrOut = str(destZoneID) + "\t" + str(destZoneLat) + "\t" + str(destZoneLon) + "\n"
                        outputFile2.write(destStrOut)

    print('Demand Files Created')