# SBSP-With-Trip-Elimination-ChoiceSetGeneration
## Purpose
* Generate a specified number of attractive transit paths connecting a passenger's origin and destination coordinates
* The generate choice set will then be used to estimate a multinomial logit (MNL) transit route choice model

## Input Data Needed
* GTFS Transit Network Structure
* OpenStreetMap Sidewalk Walking Network
* Passenger origin and destination location coordinates (Typically acquired from a transit On Board Survey)

## Workflow and Corresponding Python File
1. Convert GTFS into a series of Fast-Trips formated .dat files and generate transfer links  **(gtfs2FastTripsDat.py)**
1. Reformat On Board Survey (OBS) data to meet following requirements **(reformatOBS.py)**
1. Generate attractive choice set **(choiceSetGeneration.py)** and **(demandInputFileGeneration.py)**



# Description of Each File
## Data Cleaning Files
### gtfs2FastTripsDat.py
#### Inputs
* **inputGTFSPath:** Path to folder containing GTFS .txt files
* **outputFastTripFilePath:** Path to (empty) folder where newly created Fast-Trips .dat files will be output
* **dayOfWeek:** Integer indicating single day of the week for analysis. [Mon.=0, Tues.=1, Wed.=2, Thurs.=3, Fri.=4, Sat.=5, Sun.=6]

#### Outputs
* Transit network data for service ID's/Trip ID's that occur on the specified day of the week. Tuesday often selected as a "typical" day for analyzing behavior.
* Headers for each output .dat file are as specified below in the correct order and capitalization

NOTE: If not specified, capacity is fixed at an arbitrary level (60) as it is not employed in the remainder of the code

| Output File                |  Header 1   |  Header 2   |  Header 3      |  Header 4     |  Header 5  |  Header 6 | Header 7    | 
|:-------------------------- |:-----------:| :----------:|:--------------:|:-------------:|:----------:|:---------:|:-----------:|
| **ft_input_trips.dat**     | tripId      | routeId     | type           | startTime     |	capacity   | shapeId   | directionId |
| **ft_input_stops.dat**     | stopId      | stopName    | stopDesciption | Latitude      |	Longitude  | capacity  |             |
| **ft_input_routes.dat**    | routeId     | agency      | routeShortName | routeLongName |	routeType  |           |             |
| **ft_input_stopTimes.dat** | tripId      | arrivalTime | departureTime  | stopId        |	sequence   |           |             |
| **ft_input_transfers.dat** | fromStop    | toStop      | dist           | time          |	           |           |             |
| **ft_input_zones.dat**     | zoneId      | Latitude    | Longitude      |               |	           |           |             |

***

### reformatOBS.py
**Purpose:** Change several headers and create new columns in order to be in compliance with requirements for following steps. The contents of this file will likely vary greatly based on the current survey contents.

**Potential Adjustments to Make**
* Create a column indicating if the passenger traversed his/her path in the 'AM' or 'PM'
* Create/reformat column to indicate at what time the passenger was surveyed **in minutes past midnight**


***

### demandInputFileGeneration.py
**Purpose:** This script creates the demand and zone Fast-Trips files for each person. The demand file information is extracted from the on board survey while the zone file includes the origin and destination latitude and longitudes as identified by their respective TAZ identifier (OrigTAZ, DestTAZ).  

**Make sure that row[accessModeIndex] and row[egressModeIndex] exactly match the listed walk mode in the on board survey. For example "Walk" vs. "Walked all the way" vs. "Walk all the way."**

NOTE: Origin, Destination, and zoneID are placeholder values in which an 'O' or a 'D' is appended to the front of the passenger ID. For example, passenger ID 17 has origin TAz O17 and destination TAz D17.

| Output File                |  Header 1   |  Header 2   |  Header 3 |  Header 4     |  Header 5  |  Header 6 | Header 7 | Header 8 | 
|:-------------------------- |:-----------:| :----------:|:--------:|:------:|:-----------:|:---------:|:-----:|:------------:|
| **ft_input_demand.dat**    | passengerId | OrigTAZ     | DestTAZ   | Mode  |	timePeriod | Direction | PDT   | SurveyedPath |
| **ft_input_zones.dat**     | zoneId      | Latitude    | Longitude |       |	           |           |       |              |

***
## Choice Set Generation Algorithm File
### choiceSetGeneration.py
**Purpose:** This is the primary script. 

#### Inputs
* **inputDataLocation**: 
  * Path leading to the folder in which all .dat files are stored. This will also be where the output files end up
* **OBSFilePath**: 
  * Path leading to the folder containing the edited on board survey from the script **reformatOBS.py**.
* **desiredDayOfTheWeekInt**:
  * Integer number specifying day of week to take survey responses from ([Mon.=0, Tues.=1, Wed.=2, etc.])
* **desiredBeginningMonthInt**: 
  * Integer number specifying beginning month over which to include passengers on board survey responses.
* **desiredEndMonthInt**: 
  * Integer number specifying end month over which to include passengers on board survey responses.
* **On Board Survey Specified Header Text**: 
  * List the header containing the data outlined below (with example string provided) from the On Board Survey.
* **maxWaitTimeWindow**: 
  * Longest allowable time (in minutes) that a passenger can wait to transfer at a stop.
* **accessTimeWindow**: 
  * Longest allowable time (in minutes) that a passenger can wait at the initial boarding stop.
* **weights**: 
  * **List** of weights denoting how time is percieved with 1.0 being one minute is percieved as one minute
  * [IVT Weight, Waiting Time Weight, Walking Time Weight, Transfer Penalty (Listed as a flat amount of minutes rather than factor)] 
* **avgUnlinkedPathTimeMinutes**:
  * Average unlinked trip time in minutes (i.e. average in-vehicle time of one trip component and transfer time). Used to calculated preferred time of departure (PDT) from surveyed time if surveyed route isn' the first.
  
NOTE: All input varaibles that need user-input assignment are at the beginning of the script except for the last three.

| OBS Header Variable Needing Assignment    |  Example String to Input     | 
|:------------------------------------------|:----------------------------:|
| passengerIDHeader                         |     'Passenger'              |
| accessModeDescriptionHeader               |     'ACCESS_MODE'            | 
| egressModeDescriptionHeader               |     'EGRESS_MODE'            |
| surveyedDateHeader                        |     'DATE'                   |
| surveyedTimeMinPastMidnight_NoRangeHeader | 'surveyMinPastMidnight'      |          
| surveyedRouteHeader                       | 'ROUTE_SURVEYED'             |
| AMOrPMIndicatorHeader                     | 'timePeriod'                 |
| numberOfTransfersBeforeSurveyHeader       | 'TRANSFERS_FROM_CODE'        |
| ifTransferFrom_FirstRouteTakenHeader      | 'TRANSFER_FROM_FIRST_ROUTE'  |
| ifTransferFrom_SecondRouteTakenHeader     | 'TRANSFER_FROM_SECOND_ROUTE' |
| ifTransferFrom_ThirdRouteTakenHeader      | 'TRANSFER_FROM_THIRD_ROUTE'  |
| numberOfTransfersAfterSurveyHeader        | 'TRANSFERS_TO_CODE'          |
| ifTransferTo_FirstRouteTakenHeader        | 'TRANSFER_TO_FIRST_ROUTE'    |
| ifTranfserTo_SecondRouteTakenHeader       | 'TRANSFER_TO_SECOND_ROUTE'   |
| ifTranfserTo_ThirdRouteTakenHeader        | 'TRANSFER_TO_THIRD_ROUTE'    |
| originLatitudeCoordinateHeader            | 'ORIGIN_LAT'                 |
| originLongitudeCoordinateHeader           | 'ORIGIN_LON'                 |
| destinationLaitudeCoordinateHeader        | 'DESTIN_LAT'                 |
| destinationLongitudeCoordinateHeader      | 'DESTIN_LON'                 |

#### High Level Algorithm Overview
1. Select valid dates over which passengers will be selected from OBS
1. Read in all Fast-Trip formated network and passenger files (Zones, Stops, Trips, Demand, Stop Times, Transfers)
1. For each passenger...
    * Find Shortest Path
    * Remove, one at a time, each trip on the shortest path (and all associated network links and nodes) and re-run body of algorithm to generate a new path.
    * Keep generating new paths for each person until the desired number has been reached

***

## Logit Model File
