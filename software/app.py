
import app
import simple_tildagon as st
from system.eventbus import eventbus
from tildagonos import tildagonos, led_colours
from system.eventbus import eventbus
from system.patterndisplay.events import *

from events.input import Buttons, BUTTON_TYPES, ButtonDownEvent
from system.hexpansion.config import *
from machine import Pin, ADC
import time
import random
import asyncio
import math

# EMF Camp Tilda badge sound to light application

# This application uses the Sparkfun sound detector board (https://www.sparkfun.com/sparkfun-sound-detector.html)
# to produce a half-decent sound to light display on the EMF camp (https://www.emfcamp.org/) 
# Tildagon badge (https://tildagon.badge.emfcamp.org/) LEDs
#
# This code ported to Python from C for the Sparkfun LED visualizer (https://github.com/sparkfun/SparkFun-RGB-LED-Music-Sound-Visualizer-Arduino-Code)
# code by Michael Bartlett. Ported Tony Goacher (https://github.com/tonygoacher/tildagon_soundtolight)
# Licence as oroginal below.
# I'm a C/C++ guy with no Python experience so please forgive my SNAFUs below!

# SparkFun Addressable RGB LED Sound and Music Visualizer Tutorial Arduino Code
# by: Michael Bartlett
# SparkFun Electronics
# date: 2/7/16
# license: Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)
# Do whatever you'd like with this code, use it for any purpose.
# Please attribute and keep this license.





NUM_LEDS = 12
LED_HALF = int(NUM_LEDS / 2)
VISUALS = 5     # The number of different visual effects
hexpansion_configa = None
audioIn = None
effectName = ""
#########################################################################################
def absint(i):
    i = int(i)
    if i < 0:
        i += 2**32            
    return i     
###########################################################################

class Strip():


    ledCache = [(0,0,0)for y in range(NUM_LEDS)] 
        
       
    def getColorAsNumber(self,led):
        led = int(led)
        if absint(led) >= NUM_LEDS:
            return 0
        
        col = list(self.ledCache[led])
        return self.createColourAsNumber(col[0], col[1], col[2])
    
    def setColourByNumber(self,led, colourValue):   # Set colour as number RRGGBB for led 0-nn
        if absint(led) >= NUM_LEDS:
            return
        
        colour = ((colourValue & 0xff0000) >> 16, (colourValue & 0xff00)>> 8 , colourValue & 0xff)
        self.ledCache[led] = colour

    def setPixelColour(self,led, r,g,b):   
        led = int(led)   
        if absint(led) >= NUM_LEDS:
            return
        
        #print("R:", absint(r) ,"G", absint(g), "B",absint(b))
        self.ledCache[led] = (absint(r),absint(g),absint(b))
        
    def createColourAsNumber(self,r,g,b):
        return (absint(r) * 0x010000) + (absint(g) * 0x0100) + absint(b)
    
    def deployLeds(self):
        for i in range( NUM_LEDS):
            st.led.set(i+1, self.ledCache[i])


    
theLedStrip = Strip()

HSH = 2
HSI = 3
LOOP_LEDS = NUM_LEDS + 1
DEFAULT_PORT = 4
ADJUST_PIN  = HSH      
AUDIO_IN_PIN = HSI     

audioIn = None
hexpansion_config = HexpansionConfig(DEFAULT_PORT)  # Due to A/D use we are limited what hexpansion we can use
audioIn = ADC(Pin(hexpansion_config.pin[AUDIO_IN_PIN]))
print("Using ADC pin ",hexpansion_config.pin[AUDIO_IN_PIN], "for audio in" )

knobAnalogueIn = ADC(Pin(hexpansion_config.pin[ADJUST_PIN]))

audioIn.atten(ADC.ATTN_11DB)



thresholds = [1529, 1019, 764, 764, 764, 1274]

palette = 0  #Holds the current color palette.
visual = 0   #Holds the current visual being displayed.
volume = 0   #Holds the volume level read from the sound detector.
last = 0     #Holds the value of volume from the previous loop() pass.

maxVol = 15    #Holds the largest volume recorded thus far to proportionally adjust the visual's responsiveness.
knob = 1023.0  #Holds the percentage of how twisted the trimpot is. Used for adjusting the max brightness.
avgBump = 0    #Holds the "average" volume-change to trigger a "bump."
avgVol = 0     #Holds the "average" volume-level to proportionally adjust the visual experience.
shuffleTime = 0  #Holds how many seconds of runtime ago the last shuffle was (if shuffle mode is on).
shuffle = False
bump = False
gradient = 0

dotPos = 0  #Holds which LED in the strand the dot is positioned at. Recycled in most other visuals.
timeBump = 0 #Holds the time (in runtime seconds) the last "bump" occurred.
avgTime = 0
left = False

returnNow = 0   # Used to force the main loop to return for n iterations after a switch change
                # to allow time for another switch press/LCD update

pos = [-2] * NUM_LEDS


rgb = [[0 for x in range(3)] for y in range(NUM_LEDS)] 


####################################################################################

def map( x,  in_min,  in_max,  out_min,  out_max):
  return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

######################################################################################
def getADValue():
    advalue = audioIn.read_u16()
 
    return map(advalue, 0, 10500, 0,1023)

#########################################################################################
def millis():
    return time.ticks_ms()

#########################################################################################

def Wheel(WheelPos):
    WheelPos = 63 - WheelPos
    if WheelPos < 21:
        return theLedStrip.createColourAsNumber(63 - WheelPos * 3, 0, WheelPos * 3)

    if WheelPos < 42:
        WheelPos -= 21
        return theLedStrip.createColourAsNumber(0, WheelPos * 3, 63 - WheelPos * 3)
  
    WheelPos -= 42
    return theLedStrip.createColourAsNumber(WheelPos * 3, 63 - WheelPos * 3, 0)


##########################################################################################



#########################################################################################


def split(color, i ):

    #0 = Red, 1 = Green, 2 = Blue

    if i == 0:
        return (color & 0xff0000) >> 16
    if i == 1:
        return (color & 0x00ff00) >> 8
    if i == 2:
        return (color & 0xff) 
    print("Split invalid index ", i)
    return -1


#########################################################################################

def fade(damper):

  #"damper" must be between 0 and 1, or else you'll end up brightening the lights or doing nothing.

 # for (int i = 0; i < strand.numPixels(); i++) {
    for i in range(0,NUM_LEDS):

        #//Retrieve the color at the current position.
        col = theLedStrip.getColorAsNumber(i)
    
        #If it's black, you can't fade that any further.
        if (col == 0):
            continue

        colors= [0,0,0] #Array of the three RGB values

        #Multiply each value by "damper"
        for j in range(3):
            colors[j] = split(col, j) * damper
 
        #Set the dampened colors back to their spot.
        theLedStrip.setPixelColour(i, colors[0], colors[1], colors[2])

#########################################################################################
def bleed(point):
    for i in range(1, NUM_LEDS):
        # Pixels left and right of the starting point
        sides = [point - i, point + i]
        for j in range(0,2):
            p = sides[j]
            colors = [
                theLedStrip.getColorAsNumber(p - 1),
                theLedStrip.getColorAsNumber(p),
                theLedStrip.getColorAsNumber(p + 1)
            ]

            r = (split(colors[0], 0) +
                 split(colors[1], 0) +
                 split(colors[2], 0)) / 3.0

            g = (split(colors[0], 1) +
                 split(colors[1], 1) +
                 split(colors[2], 1)) / 3.0

            b = (split(colors[0], 2) +
                 split(colors[1], 2) +
                 split(colors[2], 2)) / 3.0

            theLedStrip.setPixelColour(p, r,g,b)

   
#########################################################################################

def Sunset(i):
  i = absint(i)
  if i > 1019:
      return Sunset(i % 1020)

  if i > 764:
     return theLedStrip.createColourAsNumber((i % 255), 0, 255 - (i % 255))          #blue -> red
  
  if i > 509:
     return  theLedStrip.createColourAsNumber(255 - (i % 255), 0, 255)                #purple -> blue
  
  if i > 255:
     return theLedStrip.createColourAsNumber(255, 128 - (i % 255) / 2, (i % 255))   #orange -> purple
  return theLedStrip.createColourAsNumber(255, i / 2, 0)   
#######################################################################################

def Rainbow( i):
  i = absint(i)
  if (i > 1529):
      return Rainbow(i % 1530)
  if (i > 1274):
     return theLedStrip.createColourAsNumber(255, 0, 255 - (i % 255))      #//violet -> red
  if (i > 1019):
      return theLedStrip.createColourAsNumber((i % 255), 0, 255);         #//blue -> violet
  if (i > 764):
      return theLedStrip.createColourAsNumber(0, 255 - (i % 255), 255)    #//aqua -> blue
  if (i > 509):
      return theLedStrip.createColourAsNumber(0, 255, (i % 255));          #//green -> aqua
  if (i > 255):
      return theLedStrip.createColourAsNumber(255 - (i % 255), 255, 0)    #//yellow -> green
  return theLedStrip.createColourAsNumber(255, i, 0)                               #//red -> yellow


####################################################################################

def ColorPalette(num):
    global palette
    global gradient
   
    if palette == 0:
        if num < 0:
            return  Rainbow(gradient) 
        else: 
            return Rainbow(num)

    if palette == 1:
        if num < 0:
          return Sunset(gradient)
        else:   
          return Sunset(num)

    return  Rainbow(gradient)
  


##########################################################################################

def Paintball():
  global bump
  global timeBump
  global palette
  global dotPos
  global thresholds
  global volume
  global maxVol
  global knob
  global avgTime

  #If it's been twice the average time for a "bump" since the last "bump," start fading.
  if ((millis() / 1000.0) - timeBump) > (avgTime * 2.0):
    fade(0.99)

  #Bleeds colors together. Operates similarly to fade. For more info, see its definition below

  bleed(dotPos)

  #Create a new paintball if there's a bump (like the sparkles in Glitter())
  if bump: 

    #Random generator needs a seed, and micros() gives a large range of values.
    #  micros() is the amount of microseconds since the program started running.
    random.seed(millis())

    #Pick a random spot on the strip. Random was already reseeded above, so no real need to do it again.
    dotPos = random.randint(0,NUM_LEDS - 1)
    

    #Grab a random color from our palette.
    col = ColorPalette(random.randint(0,thresholds[palette]))

    #Array to hold final RGB values
    colors = [0,0,0]

    #Relates brightness of the color to the relative volume and potentiometer value.
    for i in range(3):
        colors[i] = split(col, i) * pow(volume / maxVol, 2.0) * knob

    #Splatters the "paintball" on the random position.
    theLedStrip.setPixelColour(dotPos, colors[0], colors[1], colors[2])

    #//This next part places a less bright version of the same color next to the left and right of the
    #//  original position, so that the bleed effect is stronger and the colors are more vibrant.
    for j in range(0,3):
        colors[j] *= .8

    theLedStrip.setPixelColour(dotPos-1, colors[0], colors[1], colors[2])
    theLedStrip.setPixelColour(dotPos + 1,colors[0], colors[1], colors[2])
#########################################################################################


def Glitter():
    global gradient
    global dotPos
    #This visual also fits a whole palette on the entire strip
    #  This just makes the palette cycle more quickly so it's more visually pleasing
    gradient += thresholds[palette] / 204

    #"val" is used again as the proportional value to pass to ColorPalette() to fit the whole palette.
    for i in range(NUM_LEDS):
        val =   int((thresholds[palette] + 1) * (i / NUM_LEDS) + (gradient))
    
        val %= thresholds[palette]
        col = ColorPalette(val)

        #We want the sparkles to be obvious, so we dim the background color.
        theLedStrip.setPixelColour(i,   split(col, 0) / 6.0 * knob,
                                        split(col, 1) / 6.0 * knob,
                                        split(col, 2) / 6.0 * knob)

    #Create sparkles every bump
    if (bump):

        #Random generator needs a seed, and micros() gives a large range of values.
        #  micros() is the amount of microseconds since the program started running.
        

        #Pick a random spot on the strand.
        dotPos = random.randint(0,NUM_LEDS - 1)

        #Draw  sparkle at the random position, with appropriate brightness.
        theLedStrip.setPixelColour(dotPos,   255.0 * pow(volume / maxVol, 2.0) * knob,
                                            255.0 * pow(volume / maxVol, 2.0) * knob,
                                            255.0 * pow(volume / maxVol, 2.0) * knob)
                          
  
    bleed(dotPos)



#########################################################################################

def Traffic():
  global gradient
  global rgb
  global pos

  #fade() actually creates the trail behind each dot here, so it's important to include.
  fade(0.8)

  #Create a dot to be displayed if a bump is detected.
  if (bump):

    #This mess simply checks if there is an open position (-2) in the pos[] array.
    slot = 0

    for slot in range(NUM_LEDS):
        if (pos[slot] < -1):
            break

        else:
            if (slot + 1 >= NUM_LEDS):
                slot = -3
                break


    #If there is an open slot, set it to an initial position on the strand.
    if (slot != -3):

        #Evens go right, odds go left, so evens start at 0, odds at the largest position.

        if (slot % 2) == 0:
            pos[slot] = -1
        else:
            pos[slot] = NUM_LEDS

        #Give it a color based on the value of "gradient" during its birth.
        col = ColorPalette(-1)
        gradient += thresholds[palette] / 24
        for j in range(3):
            rgb[slot][j] = split(col, j)
        
    

    #Again, if it's silent we want the colors to fade out.
    if volume > 0:

        #If there's sound, iterate each dot appropriately along the strand.
        for i in range(NUM_LEDS):

            #If a dot is -2, that means it's an open slot for another dot to take over eventually.
            if pos[i] < -1:
                continue

            #As above, evens go right (+1) and odds go left (-1)
    
            if i % 2:
                pos[i] += -1
            else:    
                pos[i] += 1      

            #Odds will reach -2 by subtraction, but if an even dot goes beyond the LED strip, it'll be purged.
            if pos[i] >= NUM_LEDS:
                pos[i] = -2

            #Set the dot to its new position and respective color.
            #  I's old position's color will gradually fade out due to fade(), leaving a trail behind it.
            theLedStrip.setPixelColour(pos[i], 
                                    (rgb[i][0]) * pow(volume / maxVol, 2.0) * knob,
                                    (rgb[i][1]) * pow(volume / maxVol, 2.0) * knob,
                                    (rgb[i][2]) * pow(volume / maxVol, 2.0) * knob)



##########################################################################################

def visualize():
    if visual == 0:
        Traffic()
        return
    
    if visual == 1:
        Paintball()
        return
    
    if visual == 2:
        PaletteDance()
        return    
    
    if visual == 3:
        Glitter()
        return
    
    if visual == 4:
        Pulse()
        return
    
    # Default
    Pulse()
    
def getEffectName():
    if visual == 0:
        return "Traffic"
    
    if visual == 1:
        return "Paintball"
    
    if visual == 2:
        return  "PaletteDance"
    
    if visual == 3:
        return "Glitter"
    
    if visual == 4:
        return "Pulse"
    
    # Default
    return "Pulse"
        
###########################################################################################

def rainbowCycle():
    for j in range(256*5): # 5 cycles of all colors on wheel
        for i in range(0,NUM_LEDS):
            theLedStrip.setColourByNumber(i, Wheel(((i * int(63 / NUM_LEDS)) + j) & 63))
        j += 1
        if j > (5*256):
            j=0            

######################################################################################

def PaletteDance():
  #This is the most calculation-intensive visual, which is why it doesn't need delayed.
    global left
    global dotPos
    if bump:
        left = not left  #Change direction of iteration on bump

  #Only show if there's sound.
    if (volume > avgVol):

        #This next part is convoluted, here's a summary of what's happening:
        #  First, a sin wave function is introduced to change the brightness of all the pixels (stored in "sinVal")
        #      This is to make the dancing effect more obvious. The trick is to shift the sin wave with the color so it all appears
        #      to be the same object, one "hump" of color. "dotPos" is added here to achieve this effect.
        #  Second, the entire current palette is proportionally fitted to the length of the LED strand (stored in "val" each pixel).
        #      This is done by multiplying the ratio of position and the total amount of LEDs to the palette's threshold.
        #  Third, the palette is then "shifted" (what color is displayed where) by adding "dotPos."
        #      "dotPos" is added to the position before dividing, so it's a mathematical shift. However, "dotPos"'s range is not
        #      the same as the range of position values, so the function map() is used. It's basically a built in proportion adjuster.
        #  Lastly, it's all multiplied together to get the right color, and intensity, in the correct spot.
        #      "gradient" is also added to slowly shift the colors over time.

        for i in range (0,NUM_LEDS):

            sinVal = abs(math.sin(
                                (i + dotPos) *
                                (math.pi / (NUM_LEDS / 1.25) )
                                ))
            
            sinVal *= sinVal
            sinVal *= volume / maxVol
            sinVal *= knob

            val = abs(int((thresholds[palette] + 1)
                                #map takes a value between -LED_TOTAL and +LED_TOTAL and returns one between 0 and LED_TOTAL
                                * (float(i + map(dotPos, -1 * (NUM_LEDS - 1),NUM_LEDS - 1, 0, NUM_LEDS - 1))
                                / NUM_LEDS)
                                + (gradient)))

            val %= thresholds[palette]  #make sure "val" is within range of the palette

            col = ColorPalette(val) #get the color at "val"

            theLedStrip.setPixelColour(i, split(col, 0)*sinVal,
                                    split(col, 1)*sinVal,
                                    split(col, 2)*sinVal)
                            
        

        #After all that, appropriately reposition "dotPos."

        if left:
            dotPos -= 1
        else:
            dotPos +=1        
    #If there's no sound, fade.
    else:
        fade(0.8)

    #Loop "dotPos" if it goes out of bounds.
    if (dotPos < 0):
        dotPos = int(NUM_LEDS - NUM_LEDS / 6)
    else:
        if (dotPos >= NUM_LEDS - NUM_LEDS / 6):
            dotPos = 0


########################################################################################


def Pulse():
    global gradient
    fade(0.75);   #Listed below, this function simply dims the colors a little bit each pass of loop()

    #Advances the palette to the next noticeable color if there is a "bump"
    if bump:
        gradient += thresholds[palette] / 24

    # If it's silent, we want the fade effect to take over, hence this if-statement
    if (volume > 0):
        col = ColorPalette(-1)  #Our retrieved 32-bit color

    #These variables determine where to start and end the pulse since it starts from the middle of the strand.
    #  The quantities are stored in variables so they only have to be computed once (plus we use them in the loop).
    start = int(LED_HALF - (LED_HALF * (volume / maxVol)))
    finish = int(LED_HALF + (LED_HALF * (volume / maxVol)) + NUM_LEDS % 2)

    #Listed above, LED_HALF is simply half the number of LEDs on your strand. ↑ this part adjusts for an odd quantity.
    
    for i in range (start, finish):
     
        #"damp" creates the fade effect of being dimmer the farther the pixel is from the center of the strand.
        #  It returns a value between 0 and 1 that peaks at 1 at the center of the strand and 0 at the ends.
        damp = math.sin(((i - start) * math.pi)/ (finish - start))

        #Squaring damp creates more distinctive brightness.
        damp = pow(damp, 2.0)

        #Fetch the color at the current pixel so we can see if it's dim enough to overwrite.

        col2 = theLedStrip.getColorAsNumber(i)

        #Takes advantage of one for loop to do the following:
        # Appropriatley adjust the brightness of this pixel using location, volume, and "knob"
        # Take the average RGB value of the intended color and the existing color, for comparison
        colors = [0,0,0]
        avgCol = 0
        avgCol2 = 0

        for k in range(0,3):
            colors[k] = int(split(col, k) * damp * knob * pow(volume / maxVol, 2)) & 0xff
            avgCol += colors[k]
            avgCol2 += split(col2, k)
        
        avgCol /= 3.0
        avgCol2 /= 3.0

        #Compare the average colors as "brightness". Only overwrite dim colors so the fade effect is more apparent.
        if (avgCol > avgCol2):
             theLedStrip.setPixelColour(i,colors[0], colors[1], colors[2] )
                     




######################################################################################

class TGSTL(app.App):
    def __init__(self):
      
        self.button_states = Buttons(self)      
        eventbus.emit(PatternDisable())
        self.delay = 6  # Every 30ms
   


    def CycleVisual(self):
        global visual
        global gradient
        global pos
        global dotPos
        global maxVol
        global returnNow

        #IMPORTANT: Delete this whole if-block if you didn't use buttons//////////////////////////////////
        if self.button_states.get(BUTTON_TYPES["UP"]):
            visual += 1     #The purpose of this button: change the visual mode
            self.button_states.clear()
        else:
            return            

        gradient = 0; #Prevent overflow

        #Resets "visual" if there are no more visuals to cycle through.
        if visual > VISUALS:
            visual = 0

        print("New visual is ", visual)    
         
        #Resets the positions of all dots to nonexistent (-2) if you cycle to the Traffic() visual.
        if visual == 1:# memset(pos, -2, sizeof(pos));
            for i in range(NUM_LEDS):
                pos[i] = -2

        #Gives Snake() and PaletteDance() visuals a random starting point if cycled to.
        if visual == 2 or visual == 3: 
            dotPos = random.randint(0, NUM_LEDS)
    
        maxVol = avgVol; #Set max volume to average for a fresh experience
        returnNow = 50
  

    def dodraw(self, delta):
        global maxVol
        global avgVol
        global thresholds
        global gradient
        global palette
        global last
        global avgBump
        global bump
        global timeBump
        global avgTime
        global volume
        global knob
        global knobAnalogueIn
        
        
        volume = getADValue()

        knob = knobAnalogueIn.read_u16()
        knob = map(knob,0,65535,0,1023)
        knob = knob / 1023.0; #record how far the trimpot is twisted
    #    print("knob is ", knob)
       # return

        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            print("AAAAA")
            # The button_states do not update while you are in the background.  
            # Calling clear() ensures the next time you open the app, it stays
            # open. Without it the app would close again immediately.
            self.button_states.clear()
            self.minimise()


        
        # print("millis ", millis())

        # rainbowCycle()
        if (volume < (avgVol / 2.0)) or volume < 15:
            volume = 0
        else:
            avgVol = (avgVol + volume) / 2.0
   
        if (volume > maxVol):
            maxVol = volume     

 
        if gradient > thresholds[palette]:
            gradient %= thresholds[palette] + 1
            #   Everytime a palette gets completed is a good time to readjust "maxVol," just in case
            #  the song gets quieter; we also don't want to lose brightness intensity permanently
            #  because of one stray loud sound.
            maxVol = (maxVol + volume) / 2.0
                
        if volume - last > 10:
            avgBump = (avgBump + (volume - last)) / 2.0
        
        bump = (volume - last) > (avgBump * 0.9) 
       # print("Bump ", bump, "vol ", volume, "last ", last , "avgBump", avgBump)
        if (bump):
            avgTime = (((millis() / 1000.0) - timeBump) + avgTime) / 2.0
            timeBump = millis() / 1000.0

        visualize();    #Calls the appropriate visualization to be displayed with the globals as they are.

        gradient+=1;    #Increments gradient

        last = volume   # Records current volume for next pass

        return False

    def update(self, delta):
        global returnNow
        global pacer
        pacer = 0
        while True:
            self.dodraw(delta)
            theLedStrip.deployLeds()
            self.CycleVisual()  
            pacer += 1  # Ensure we return for background processing every now and then
            if pacer < 50 and returnNow == 0:
                time.sleep(0.02)
            else:
                if returnNow != 0:
                    returnNow -= 1
                return                
        

            

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0.2, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(255,255,255).move_to(-80, 0).text("TGSTL:" )
        ctx.rgb(255,255,255).move_to(-80, 40).text(getEffectName() )
        ctx.restore()

__app_export__ = TGSTL