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
prevSelfItem = 0
itemDir = 0

itemDict = {"fuel": 0, "wideangle": 1, "rearshot": 2, "afterburner": 3, "cloak": 4, 
            "sensor": 5, "transporter": 6, "tank": 7, "mine": 8, "missile": 9, "ecm": 10,
            "laser": 11, "emergencythrust": 12, "tractorbeam": 13, "autopilot": 14, 
            "emergencyshield": 15, "itemdeflector": 16, "hyperjump": 17, "phasing": 18, 
            "mirror": 19, "armor": 20} 
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
        global prevSelfItem
        global itemDir

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
            mode = "ready"

        if mode == "ready":
            
            # To limit times mode we start the mission
            stopCount += 1
        
            # Start mission
            if stopCount == 1:
                ai.talk("teacherbot: start-mission 8")

            if "collect-item" in ai.scanTalkMsg(0):
                mode = "scan"
        
        if mode == "scan":
            
            message = ai.scanTalkMsg(0)
            
            messageList = list(message.split(" "))
            selectItemType = messageList[1]

            if selectItemType in itemDict:
                selectItemType = itemDict[selectItemType]
            
            prevSelfItem = ai.selfItem(selectItemType)
                    
            mode = "aim"
            
        if mode == "aim":

            # Take the closest item   
            itemCountScreen = ai.itemCountScreen()
            prevItemDist = 1000
            prevSelectItemDist = 1000
            selectedItemCount = 0
            
            if itemCount == 0:
                
                ai.turnToRad(middleDir)
                
                # Thrust if we are in a sufficient right direction
                if angleDiff(selfHeading, middleDir) < 0.1:                    
                    ai.setPower(30)
                    ai.thrust()
            
                # Stop if we are in a sufficient wrong direction
                elif angleDiff(ai.selfTrackingRad(), middleDir) > 0.8 and selfSpeed > 3:
                    if (0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) > 100):
                        mode = "stop"
            else:
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
                
                if ai.itemSpeed(itemId) > 0:
                
                    # Point of impact, where ship is supposed to hit item
                    aimAtX = relX + relVelX*t
                    aimAtY = relY + relVelY*t

                    # Direction of aimpoint
                    itemDir = math.atan2(aimAtY, aimAtX)

                    # Turns to item direction
                    ai.turnToRad(itemDir)

                    # Thrust if we are in a sufficient right direction
                    if angleDiff(selfHeading, itemDir) < 0.05:

                        if (0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) > 100):
                   
                            ai.setPower(35)
                            ai.thrust()
                            mode = "aim"

                    elif angleDiff(ai.selfTrackingRad(), itemDir) > 0.1:
                        mode = "adjust"
                
                else:
                    # If item has no velocity 
                    itemStopped = math.atan2(relY, relX)
                    ai.turnToRad(itemStopped)

                    # Thrust if we are in a sufficient right direction
                    if angleDiff(selfHeading, itemStopped) < 0.1:
                        ai.setPower(30)
                        ai.thrust()
            
                    # Stop if we are in a sufficient wrong direction
                    if angleDiff(ai.selfTrackingRad(), itemStopped) > 0.8 and selfSpeed > 3:
                        if (0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) > 100):
                            mode = "stop"
       
            # Different distances to wall for different speeds
            if (0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) < 100):
                mode = "closeToWall"
            
            if selfSpeed > 12:
                if (0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) < 250):
                    mode = "closeToWall" 
            
            if selfSpeed > 18:
                if (0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) < 350):
                    mode = "closeToWall"
            
            if selfSpeed > 24:
                if (0 < ai.wallFeelerRad(1000, ai.selfTrackingRad()) < 450):
                    mode = "closeToWall"
        
        elif mode == "closeToWall":
            
            prevTrackRad = ai.selfTrackingRad()
            ai.turnToRad(ai.selfTrackingRad() - math.pi)
            angle = angleDiff(ai.selfTrackingRad(), selfHeading)
            
            if selfSpeed < 3:
                mode = "aim"
            
            ai.setPower(55)
            ai.thrust()
        
        elif mode == "stop":
            if selfSpeed > 1:
                ai.turnToRad(ai.selfTrackingRad() - math.pi)

            angle = angleDiff(ai.selfTrackingRad(), selfHeading)

            if angle < 0.5:
                mode = "aim"

            ai.setPower(45)
            ai.thrust()

            if prevSelfItem < ai.selfItem(selectItemType):
                if selfSpeed < 3:
                    mode = "done"
                else:
                    mode = "stop"
        
        elif mode == "adjust":
            
            # kolla på rörelseriktningen och målets riktning.
            # Ta ut riktningen mitt mellan och thrusta.
            movItemDiff = angleDiff(ai.selfTrackingRad(), itemDir)
            selfTrackRad = ai.selfTrackingRad() % (2*math.pi)
            absItemDir = itemDir % (2*math.pi)
            
            if movItemDiff < math.pi/2:
                adjustAngle = 2*absItemDir - selfTrackRad
            
            elif 3*math.pi/4 > movItemDiff >= math.pi/2:
                adjustAngle = (3*absItemDir - selfTrackRad)/2
            
            elif movItemDiff == math.pi:
                mode = "stop"
                return
            
            else:    
                adjustAngle = absItemDir
            
            ai.turnToRad(adjustAngle)
            selfHeading = ai.selfHeadingRad()

            ai.setPower(45)
            ai.thrust()

            if angleDiff(selfHeading, itemDir) < 0.05:
                mode = "aim"
            else:
                mode = "adjust"
        
        elif mode == "done":
            
            # Gets the key from the value of our desired item in order to
            # send a message to teacherbot
            itemStrValue = list(itemDict.keys())[list(itemDict.values()).index(selectItemType)]
            completed = "Teacherbot: completed collect-item " + itemStrValue
            ai.removeTalkMsg(0)
            ai.talk(completed)
            mode = "scan"


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
