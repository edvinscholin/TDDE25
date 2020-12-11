#
# This file can be used as a starting point for the bots.
#

import functions_lib as lib
import sys
import traceback
import math
import libpyAI as ai
from optparse import OptionParser

#
# Global variables that persist between ticks
#
tickCount = 0
mode = "ready"

# add more if needed

# Coordinates - Vill helst ha en tuple
coordinates = []
prevCoordinates = []

# Message handling
tasks = []
lenTasks = 0
send = []

# Movement
prevTrackRad = 0
dist = 0
dirRad = 0

# Items
itemDict = {"fuel": 0, "wideangle": 1, "rearshot": 2, "afterburner": 3, "cloak": 4,
            "sensor": 5, "transporter": 6, "tank": 7, "mine": 8, "missile": 9, "ecm": 10,
            "laser": 11, "emergencythrust": 12, "tractorbeam": 13, "autopilot": 14,
            "emergencyshield": 15, "itemdeflector": 16, "hyperjump": 17, "phasing": 18,
            "mirror": 19, "armor": 20}
prevSelfItem = 0
desiredItemType = -1
item_needed = 1
stateOfMine = "disarmed"

# Counters
shieldOnCount = -1
compCounter = 0
missionCount = 0


def tick():
    #
    # The API won't print out exceptions, so we have to catch and print them ourselves.
    #
    try:

        #
        # Declare global variables so we have access to them in the function
        #
        global tickCount
        global prevTrackRad
        global mode
        global itemDict
        global prevSelfItem
        global desiredItemType
        global tasks
        global lenTasks
        global send
        global coordinates
        global prevCoordinates
        global dist
        global dirRad
        global item_needed
        global stateOfMine

        global shieldOnCount
        global compCounter
        global missionCount

        #
        # Reset the state machine if we die.
        #
        if not ai.selfAlive():
            print("dead")
            tickCount = 0
            mode = "ready"
            return

        tickCount += 1
        missionCount += 1

        print("tick count:", tickCount, "mode", mode)

        if missionCount == 1:
            ai.talk("teacherbot: start-mission 9")
            ai.shield()
            #ai.talk('use-item laser teacherbot teacherbot [Teacherbot]:[Stub]')

        #
        # Read some "sensors" into local variables, to avoid excessive calls to the API
        # and improve readability.
        #

        selfX = ai.selfX()
        selfY = ai.selfY()
        selfSpeed = ai.selfSpeed()
        selfTrackingRad = ai.selfTrackingRad()

        selfRadarX = ai.selfRadarX()
        selfRadarY = ai.selfRadarY()
        radarWidth = ai.radarWidth()
        radarHeight = ai.radarHeight()

        selfHeading = ai.selfHeadingRad()

        # Allows the ship to turn 360 degrees.
        ai.setMaxTurnRad(2*math.pi)

        wallDistance = ai.wallFeelerRad(1000, selfTrackingRad)

        # Calcualtes which direction the middle is
        middleRelX = radarWidth/2 - selfRadarX
        middleRelY = radarHeight/2 - selfRadarY
        middleDir = lib.direction(middleRelX, middleRelY)

        # ----------------------------------------------------------------------------
        # Wallfeeler
        # ----------------------------------------------------------------------------

        if lib.brake(wallDistance) and wallDistance != -1:
            prevTrackRad = selfTrackingRad
            print("wallfeeler")
            mode = "stop"

        # ----------------------------------------------------------------------------
        # Shield
        # ----------------------------------------------------------------------------

        if -1 < shieldOnCount < 10:
            shieldOnCount += 1
            ai.shield()

        # ---------------------------------------------------------------------------
        # Ready
        # ---------------------------------------------------------------------------

        if mode == "ready":

            if not tasks:
                mode = "scan"

            else:
                mode = "mission"

        # ---------------------------------------------------------------------------
        # Missions
        # ---------------------------------------------------------------------------

        elif mode == "scan":

            ai.setMaxMsgs(15)
            maxMsgs = ai.getMaxMsgs()

            # Scans all the messages sent by teacherbot
            # and adds them to the list tasks
            for message in range(maxMsgs):
                if ai.scanTalkMsg(message) and "[Teacherbot]:[Stub]" in ai.scanTalkMsg(message):
                    tasks.append(ai.scanTalkMsg(message))
                    ai.removeTalkMsg(message)

            print("tasks: ", tasks)

            # Save the length of the task in the variable lenTasks
            lenTasks = len(tasks)

            # När vi inte har några kordinater ska vi ta ett nytt föremål.
            # Så länge vi har kordinater håller vi på med ett föremål.
            if not coordinates and tasks:
                for seq in tasks[-1].split():
                    if seq.isdigit():
                        coordinates.append(int(seq))
                    if seq in itemDict.keys():
                        desiredItemType = itemDict[seq]

            mode = "ready"

        elif mode == "mission":
            if not tasks:
                mode = "scan"

            #print("tasks: ", tasks)

            # INPUT: desiredItemType, tasks
            current_task = tasks[-1]
            mode = "navigation"

            if "collect-item" in current_task:

                if ai.itemCountScreen() == 0:
                    ai.turnToRad(middleDir)
                    ai.setPower(55)
                    ai.thrust()
                    mode = "mission"
                    return

                Id = lib.nearest_desired_item_Id(desiredItemType)

                # Targets position relativt self
                x, y = lib.target_future_pos(Id, selfSpeed)

                # If we already have the item
                if prevSelfItem < ai.selfItem(desiredItemType):
                    mode = "completed_task"

            elif "use-item" in current_task:

                # ------------ Tillfälligt ----------
                """
                if "mine" not in current_task:
                    print("cant handle other items")
                    ai.quitAI()
                """
                # -----------------------------------

                itemStrValue = list(itemDict.keys())[list(
                    itemDict.values()).index(desiredItemType)]

                if (ai.selfItem(desiredItemType) == 0 and stateOfMine == "disarmed"
                        and f'collect-item {itemStrValue} [Teacherbot]:[Stub]' not in current_task):
                    print("We have no mine")
                    ai.talk('collect-item ' + itemStrValue +
                            ' [Teacherbot]:[Stub]')
                    mode = "scan"
                    return

                elif "mine" in current_task:  # Meanes that we fire item

                    shipId = lib.nearest_ship_Id(selfX, selfY)
                    shipX = ai.shipX(shipId)
                    shipY = ai.shipY(shipId)

                    selfRelShipX, selfRelShipY = lib.relative_pos(
                        selfX, selfX, shipX, shipY)

                    selfShipDist = lib.distance(selfRelShipX, selfRelShipY)

                    if ai.mineScreenCount > 0:

                        mineId = lib.nearest_mine_Id(shipX, shipY)
                        mineX = ai.mineX(mineId)
                        mineY = ai.mineY(mineId)

                        shipRelMineX, shipRelMineY = lib.relative_pos(
                            shipX, shipY, mineX, mineY)

                        selfRelMineX, selfRelMineY = lib.relative_pos(
                            selfX, selfY, mineX, mineY)

                        shipMineDist = lib.distance(
                            shipRelMineX, shipRelMineY)

                        selfMineDist = lib.distance(selfRelMineX, selfRelMineY)

                        if coordinates:
                            # -------- tillfällig -------
                            shipMineDist = 0
                            # ---------------------------

                        if shipMineDist < 20:
                            if selfMineDist < 100:  # Give ourself a shield
                                ai.shield()
                                shieldOnCount = 0

                            ai.detonateMines()
                            stateOfMine = "disarmed"
                            mode = "completed_task"

                    if coordinates:  # Placera minan på den givna koordinaten

                        # Targets position relativt self
                        x, y = lib.relative_pos(selfX, selfY,
                                                coordinates[0], coordinates[1])

                        # Distance to dropzone
                        dist = lib.distance(x, y)

                        # Place mine
                        if dist < 20:
                            ai.dropMine()
                            stateOfMine = "armed"
                            prevTrackRad = selfTrackingRad

                        # Ship stops when target is reached.
                        elif lib.brake(dist):
                            print("placera")
                            prevTrackRad = selfTrackingRad
                            mode = "stop"
                            return

                    else:

                        dirRad = lib.direction(selfRelShipX, selfRelShipY)

                        if selfSpeed < 5 and selfShipDist < 20:
                            ai.dropMine()

                        elif lib.angleDiff(selfHeading, dirRad) < 0.1:
                            ai.detachMine()

                        else:
                            mode = "navigation"

                    '''
                    else:
                        # Targets position relativt self
                        x, y = lib.relative_pos(selfX, selfY,
                                                coordinates[0], coordinates[1])

                        shipId = lib.nearest_target_Id(
                            "ship", coordinates[0], coordinates[0])

                        playerRelMineX, playerRelMineY = lib.relative_pos(
                            coordinates[0], coordinates[1], ai.shipX(shipId), ai.shipY(shipId))

                        # -------- tillfällig ------
                        playerRelMineX = 0
                        playerRelMineY = 0
                        # --------------------------

                        # randomPlayerDist är spelarens distans till placerad mina
                        randomPlayerDist = lib.distance(
                            playerRelMineX, playerRelMineY)
                        selfMineDist = lib.distance(x, y)

                        # Place mine
                        if dist < 20:
                            ai.dropMine()
                            stateOfMine = "armed"
                            prevTrackRad = selfTrackingRad

                        # Ship stops when target is reached.
                        if lib.brake(dist):
                            print("placera")
                            prevTrackRad = selfTrackingRad
                            mode = "stop"
                            return

                    # Detonate mine
                    if randomPlayerDist < 50:

                        if selfMineDist < 100:  # Give ourself a shield
                            ai.shield()
                            shieldOnCount = 0

                        ai.detonateMines()
                        stateOfMine = "disarmed"
                        prevCoordinates.clear()
                        mode = "completed_task"
                    '''

                elif "missile" in current_task:
                    x, y = lib.relative_pos(
                        selfX, selfY, middleRelX, middleRelY)
                    ai.lockClose()
                    ai.fireMissile()
                    mode = "completed_task"

                elif "fuel" in current_task:
                    x, y = lib.relative_pos(
                        selfX, selfY, middleRelX, middleRelY)
                    ai.refuel()
                    mode = "completed_task"

                elif "emergencyshield" in current_task:
                    x, y = lib.relative_pos(
                        selfX, selfY, middleRelX, middleRelY)

                    ai.emergencyShield()
                    ai.shield()
                    shieldOnCount = 0

                    mode = "completed_task"

                elif "laser" in current_task:
                    if ai.shipCountScreen() == 1:
                        ai.turnToRad(middleDir)
                        ai.setPower(55)
                        ai.thrust()
                        mode = "mission"
                        return

                    Id = lib.nearest_ship_Id("ship")
                    # Targets position relative self
                    x, y = lib.relative_pos(
                        selfX, selfY, ai.shipX(Id), ai.shipY(Id))
                    dirRad = lib.direction(x, y)

                    if lib.angleDiff(selfHeading, dirRad) > 0.1:
                        mode = "aim"
                    else:
                        ai.fireLaser()
                        mode = "completed_task"

                elif "armor" in current_task:
                    mode = "completed_task"

            else:  # We cannot handle item
                print("cannot handle task")
                mode = "ready"
                return

            # Distance and direktion to target
            dist = lib.distance(x, y)
            dirRad = lib.direction(x, y)

            print("tasks1: ", tasks)

            # Save how many items of the desired item we already have
            prevSelfItem = ai.selfItem(desiredItemType)

        # ----------------------------------------------------------------
        # Mission completed
        # ----------------------------------------------------------------

        # ----------------------------------------------------------------
        # Senaste meddelandet tas inte bort av någon anledning. Complete meddelandena syns inte
        # I terminalen står det att teacherbot skickar meddelandet use-item mine. Tasklistan töms.
        # ----------------------------------------------------------------

        elif mode == "completed_task":

            for message in range(ai.getMaxMsgs()):
                print("message: ", ai.scanTalkMsg(message))
            # Tar inte bort gamla tasket
            current_task = tasks[-1]
            # Adds the completed task to a list send

            # for elem in tasks:
            if '[Teacherbot]:[Stub] [Stub]' not in current_task:
                if coordinates:
                    prevCoordinates = coordinates.copy()
                    coordinates.clear()

                new_msg = ""
                for seq in current_task.split():
                    if not "[" in seq:
                        new_msg += seq + " "
                completed = "Teacherbot:completed " + new_msg
                send.append(completed)
            else:
                completed = "Stub:completed"
                send.append(completed)

            # If you have completed all the tasks send the messages from the send list,
            # clear the send and tasks list and change mode to completed_all_tasks

            #print("len send: ", len(send))
            #print("len tasks: ", lenTasks)

            if len(send) == lenTasks:
                for elem in send:
                    ai.talk(elem)
                send.clear()
                tasks.clear()

                mode = "completed_all_tasks"

                for message in range(ai.getMaxMsgs()):
                    ai.removeTalkMsg(message)

            # If you havent completed all the tasks remove the
            # last task in the list and change mode to cords
            else:
                tasks.pop()
                mode = "ready"

        elif mode == "completed_all_tasks":
            for message in range(ai.getMaxMsgs()):
                print("message: ", ai.scanTalkMsg(message))

            print("tasks: ", tasks)

            compCounter += 1

            # If you recieve a new message from
            # teacherbot change mode to scan
            if "[Teacherbot]:[Stub]" in ai.scanTalkMsg(0):
                lenTasks = 0
                compCounter = 0
                mode = "ready"

            elif compCounter > 5:
                ai.pauseAI()

        # ---------------------------------------------------------------------------
        # Navigational modes, input is dist(only if ship need to stop at destination)
        # and dirRad to target
        # ---------------------------------------------------------------------------

        elif mode == "navigation":

            # Aim if any targets are detected
            if selfSpeed < 20:
                ai.setPower(55)
            mode = "aim"

        elif mode == "stop":

            # ai.turnToRad(prevTrackRad - math.pi)

            angle = lib.angleDiff(prevTrackRad, selfTrackingRad)

            if angle < math.pi/2:
                ai.turnToRad(selfTrackingRad - math.pi)

            if angle > math.pi/2:
                mode = "mission"
                return

            prevTrackRad = selfTrackingRad
            ai.setPower(55)
            ai.thrust()

        elif mode == "aim":  # dela upp i aim och travel

            # Convert selfTrackingRad and ItemDir to positive radians
            positiveSelfTrackingRad = selfTrackingRad % (2*math.pi)
            positiveItemDir = dirRad % (2*math.pi)

            # Calculate angle difference
            movItemDiff = lib.angleDiff(selfTrackingRad, dirRad)

            # Ship stops when target is reached. Not necessary.
            '''
            if brake(dist + 50):  
                prevTrackRad = selfTrackingRad
                mode = "stop"
                return
            '''

            # Move towards target
            if selfSpeed < 5 or movItemDiff == math.pi/2:
                angle = dirRad

            elif movItemDiff > math.pi/2:  # if angle between selfTrackingRad and item direction
                print("aim stop.........")
                prevTrackRad = selfTrackingRad
                mode = "stop"
                return

            else:  # Uses opposite velocity vektor to cancel out unwanted velocity vektors
                angle = 2*positiveItemDir - positiveSelfTrackingRad

            mode = "mission"

            ai.turnToRad(angle)
            ai.thrust()

    except:
        print(traceback.print_exc())


#
# Parse the command line arguments
#
parser = OptionParser()

parser.add_option("-p", "--port", action="store", type="int",
                  dest="port", default=15348,
                  help="The port number. Used to avoid port collisions when"
                  " connecting to the server.")

(options, args) = parser.parse_args()

name = "Stub"

#
# Start the AI
#

ai.start(tick, ["-name", name,
                "-join",
                "-turnSpeed", "64",
                "-turnResistance", "0",
                "-port", str(options.port)])