#
# This file can be used as a starting point for the bots.
#

import sys
import traceback
import math
import libpyAI as ai
from optparse import OptionParser

#
# Global variables that persist between ticks
#
tickCount = 0
readyCount = 0
stopCount = 0
mode = "wait"
selectItemType = -1
itemId = 0
prevTrackRad = 0

itemDict = {"mine": 8} 

def tick():
    #
    # The API won't print out exceptions, so we have to catch and print them ourselves.
    #
    try:

        #
        # Declare global variables so we have access to them in the function
        #
        global tickCount
        global readyCount
        global stopCount
        global mode
        global selectItemType
        global itemId
        global prevTrackRad

        #
        # Reset the state machine if we die.
        #
        if not ai.selfAlive():
            tickCount = 0
            mode = "wait"
            return

        tickCount += 1

        #
        # Read some "sensors" into local variables, to avoid excessive calls to the API
        # and improve readability.
        #

        selfX = ai.selfX()
        selfY = ai.selfY()
        selfVelX = ai.selfVelX()
        selfVelY = ai.selfVelY()
        selfSpeed = ai.selfSpeed()

        selfHeading = ai.selfHeadingRad()

        # Calcualtes which direction the middle is 
        middleDisX = ai.radarWidth()/2 - ai.selfRadarX()                  
        middleDisY = ai.radarHeight()/2 - ai.selfRadarY()                 
        middleDir = math.atan2(middleDisY, middleDisX)

        itemCount = ai.itemCountScreen()

        ai.setMaxTurnRad(2*math.pi)

        # Add more sensors readings here

        print("tick count:", tickCount, "mode", mode)

        if mode == "wait":
            #if itemCount > 0:
                mode = "ready"
            #else: kanske att åka till mitten eller något för att 
            # hitta ett item.

        if mode == "ready":
            
            # To limit times mode we start the mission
            stopCount += 1
            selfItem = 0
            
            print(selectItemType)
            if selectItemType > -1:
                selfItem = ai.selfItem(selectItemType)
            #print(selfItem)

            # Start mission
            if stopCount == 1:
                ai.talk("teacherbot: start-mission 8")
            
            """# Completed mission if
            if not ai.scanTalkMsg(0) and selfItem > 0:
                complete = "teacherbot: completed collect-item " + str(selectItemType)
                ai.talk(complete) """

            if "collect-item" in ai.scanTalkMsg(0):
                mode = "scan"
        
        if mode == "scan":
            
            message = ai.scanTalkMsg(0)
            print("message: " + message)
            
            messageList = list(message.split(" "))
            selectItemType = messageList[1]

            print("selectItemType: " + str(selectItemType))

            if selectItemType in itemDict:
                selectItemType = itemDict[selectItemType]
                    
            mode = "aim"
            
        if mode == "aim":
            print(itemId)

            # Take the closest item   
            itemCountScreen = ai.itemCountScreen()
            prevItemDist = 1000
            prevSelectItemDist = 1000
            selectedItemCount = 0

            for index in range(itemCountScreen):
                
                itemDist = ai.itemDist(index)
                
                if ai.itemType(index) == selectItemType:
                    selectedItemCount += 1
                    
                    if itemDist < prevSelectItemDist:
                        prevSelectItemDist = itemDist
                        itemId = index
            
                else:
                    if itemDist < prevItemDist:
                        prevItemDist = itemDist
                        restItemId = index
            
            # If there are none of the desired type, we want to take the closest item 
            if selectedItemCount == 0:
                itemId = restItemId
       
            # item position and velocity
            itemX = ai.itemX(itemId)
            itemY = ai.itemY(itemId)
            itemVelX = ai.itemVelX(itemId)
            itemVelY = ai.itemVelY(itemId)

            # items initial position relative to self
            relX = itemX - selfX
            relY = itemY - selfY

            # items initial velocity relative to self
            relVelX = itemVelX - selfVelX
            relVelY = itemVelY - selfVelY

            # Time of impact, when ship is supposed to hit item
            try:
                t = time_of_impact(relX, relY, relVelX, relVelY, selfSpeed)
            except ZeroDivisionError:
                pass

            # Point of impact, where ship is supposed to hit item
            aimAtX = relX + relVelX*t
            aimAtY = relY + relVelY*t
            distance = math.sqrt((aimAtX**2 + aimAtY**2))

            # Direction of aimpoint
            itemDir = math.atan2(aimAtY, aimAtX)

            # Turns to item direction
            ai.turnToRad(itemDir)
                        
            # Thrust if we are in a sufficient right direction
            if angleDiff(selfHeading, itemDir) < 0.1:
                
                # Stops accelerating
                '''
                if selfSpeed < 7:
                    ai.setPower(30)
                else:
                    ai.setPower(15)
                '''
                ai.setPower(15)
                mode = "thrust"

            if 0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) < 100:
                ai.turnToRad(ai.selfTrackingRad() - math.pi)
                prevTrackRad = ai.selfTrackingRad()
                
                mode = "stop"
            
            if selfHeading != ai.selfTrackingRad():
                mode = "stop"
        
        elif mode == "stop":
            
            if ai.selfTrackingRad() == prevTrackRad - math.pi:
                mode = "stop"
            else:
                mode = "aim"

            ai.setPower(15)
            ai.thrust()

        elif mode == "thrust": 
            mode = "aim"
            ai.thrust()


    except:
        print(traceback.print_exc())

def angleDiff(one, two):
    """Calculates the smallest angle between two angles"""

    a1 = (one - two) % (2*math.pi)
    a2 = (two - one) % (2*math.pi)
    return min(a1, a2)


def time_of_impact(px, py, vx, vy, s):
    """
    Determine the time of impact, when ship hits moving target
    Parameters:
        px, py = initial target position in x,y relative to ship
        vx, vy = initial target velocity in x,y relative to ship
        s = initial ship speed
        t = time to impact, in our case ticks
    """

    a = s * s - (vx * vx + vy * vy)
    b = px * vx + py * vy
    c = px * px + py * py

    d = b*b + a*c

    t = 0

    if d >= 0:
        t = (b + math.sqrt(d)) / a
        if t < 0:
            t = 0

    return t

#
# Parse the command line arguments
#
parser = OptionParser()

parser.add_option ("-p", "--port", action="store", type="int", 
                   dest="port", default=15348, 
                   help="The port number. Used to avoid port collisions when" 
                   " connecting to the server.")

(options, args) = parser.parse_args()

name = "Stub"

#
# Start the AI
#

ai.start(tick,["-name", name, 
               "-join",
               "-turnSpeed", "64",
               "-turnResistance", "0",
               "-port", str(options.port)])