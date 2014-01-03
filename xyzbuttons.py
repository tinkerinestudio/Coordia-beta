# This file is part of the Printrun suite.
# 
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

import wx, os, math
from bufferedcanvas import *

def imagefile(filename):
    if os.path.exists(os.path.join(os.path.dirname(__file__), "images", filename)):
        return os.path.join(os.path.dirname(__file__), "images", filename)
    else:
        return os.path.join(os.path.split(os.path.split(__file__)[0])[0], "images", filename)
    
def sign(n):
    if n < 0: return -1
    elif n > 0: return 1
    else: return 0
label_overlay_positions2 = {
}
mpos=(0,0)

class abutton():
	def __init__(self, ftn, x1,y1,x2,y2):
		self.x1=x1
		self.y1=y1
		self.x2=x2
		self.y2=y2
		self.ftn=ftn
		label_overlay_positions2.update({self.ftn: (self.x1, self.y1, self.x2, self.y2)})
		#print (str(x1) + " " + str(y1) + " " + str(x2) + " " + str(y2))

	
class XYZButtons(BufferedCanvas):
    button_ydistances = [7, 30, 55, 83] # ,112
    center = (30, 118)
    label_overlay_positions = {
        0: (1, 18, 11),
        1: (1, 41, 13),
        7: (1, 67, 15),
        3: None
    }

    #def abutton(x1,y1,x2,y2):
    #    print(str(x1) + " " + str(y1) + " " + str(x2) + " " + str(y2))
		
    def __init__(self, parent, moveCallback=None, ID=-1):
        btn1 = abutton('Y1', 110,74,30,38)
        btn1 = abutton('Y10', 110,37,30,38)
        btn1 = abutton('Y50', 110,0,30,38)
        
        btn1 = abutton('Y-1', 110,141,30,38)
        btn1 = abutton('Y-10', 110,178,30,38)
        btn1 = abutton('Y-50', 110,215,30,38)
		
        btn1 = abutton('X1', 140,111,38,27)
        btn1 = abutton('X10', 177,111,38,27)
        btn1 = abutton('X50', 214,111,38,27)
        
        btn1 = abutton('X-1', 74,111,38,27)
        btn1 = abutton('X-10', 37,111,38,27)
        btn1 = abutton('X-50', 0,111,38,27)
        
        btn1 = abutton('Z1', 270,73,30,35)
        btn1 = abutton('Z10', 270,38,30,35)
        btn1 = abutton('Z50', 270,3,30,35)
        
        btn1 = abutton('Z-1', 270,142,30,35)
        btn1 = abutton('Z-10', 270,177,30,35)
        btn1 = abutton('Z-50', 270,212,30,35)

        btn1 = abutton('home X', 30,30,50,50)
        btn1 = abutton('home Y', 170,30,50,50)
        btn1 = abutton('home Z', 170,170,50,50)
        
        btn1 = abutton('home A', 30,170,50,50)
        
        #self.SetSize(wx.Window(100, 100))
        
        self.bg_bmp = wx.Image(imagefile("axis.png"),wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        
        self.range = None
        self.direction = None
        self.orderOfMagnitudeIdx = 0 # 0 means '1', 1 means '10', 2 means '100', etc.
        self.moveCallback = moveCallback
        self.enabled = False

        BufferedCanvas.__init__(self, parent, ID)

        #self.Image2.SetPosition((500,100))
        self.SetSize(self.bg_bmp.GetSize())
        #self.Image2 = wx.StaticBitmap(self, -1, wx.Bitmap("images/blank.png"),pos=(291,250))

        #self.Image2 = wx.StaticBitmap(self, -1, wx.Bitmap("images/-1.png"),pos=(83,118))
        #self.Image2 = wx.StaticBitmap(self, -1, wx.Bitmap("images/blank.png"),pos=(291,250))

        # Set up mouse and keyboard event capture
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        
#bmp = wx.Image('aliens.jpg',wx.BITMAP_TYPE_JPEG).ConvertToBitmap()
        #self.Image = wx.Image('images/-1.png',wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        #self.Image.SetPosition((150,150))
        
        
    def disable(self):
        self.enabled = False
        self.update()
    
    def enable(self):
        self.enabled = True
        self.update()

    def lookupRange(self, ydist):
        idx = -1
        for d in XYZButtons.button_ydistances:
            if ydist < d:
                return idx
            idx += 1
        return None
    
    def highlight(self, gc, rng, dir):
        assert(rng >= -1 and rng <= 3)
        assert(dir >= -1 and dir <= 1)

        fudge = 11
        x = 0 + fudge
        w = 59 - fudge*2
        if rng >= 0:
            k = 1 if dir > 0 else 0
            y = XYZButtons.center[1] - (dir * XYZButtons.button_ydistances[rng+k])
            h = XYZButtons.button_ydistances[rng+1] - XYZButtons.button_ydistances[rng]
            gc.DrawRoundedRectangle(x, y, w, h, 4)
            # gc.DrawRectangle(x, y, w, h)
        # self.drawPartialPie(dc, center, r1-inner_ring_radius, r2-inner_ring_radius, a1+fudge, a2-fudge)
    
    def getRangeDir(self, pos):
        ydelta = XYZButtons.center[1] - pos[1]
        return (self.lookupRange(abs(ydelta)), sign(ydelta))
        
    def CheckCollision(self, mpos, bpos):
        if mpos[0] > bpos[0]:
            if mpos[0] < bpos[0]+bpos[2]:
                if mpos[1] > bpos[1]:
					if mpos[1] < bpos[1]+bpos[3]:
						return True
        else:
            return False
    def draw(self, dc, w, h):
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        if self.bg_bmp:
            w, h = (self.bg_bmp.GetWidth(), self.bg_bmp.GetHeight())
            gc.DrawBitmap(self.bg_bmp, 0, 0, w, h)
        
        if self.enabled:
            # Draw label overlays
            gc.SetPen(wx.Pen(wx.Colour(255,255,0,0), 1))
            #gc.SetBrush(wx.Brush(wx.Colour(255,0,222,128))) #justin: overlay debug areas
			
            for idx, kpos in XYZButtons.label_overlay_positions.items():
                if kpos and idx != self.range:
                    r = kpos[2]
                    #gc.DrawEllipse(XYZButtons.center[0]-kpos[0]-r, XYZButtons.center[1]-kpos[1]-r, r*2, r*2)
					
            for ftn, kpos in label_overlay_positions2.items():
                gc.DrawRectangle(kpos[0],kpos[1],kpos[2],kpos[3])
            
            # Top 'layer' is the mouse-over highlights
            gc.SetPen(wx.Pen(wx.Colour(100,100,100,172), 4))
            gc.SetBrush(wx.Brush(wx.Colour(0,0,0,128)))
            #if self.range != None and self.direction != None:
                #self.highlight(gc, self.range, self.direction)
        else:
            gc.SetPen(wx.Pen(wx.Colour(255,255,255,0), 4))
            gc.SetBrush(wx.Brush(wx.Colour(255,255,255,0))) #justin: no display for disable overlay
            gc.DrawRectangle(0, 0, w, h)
        bmp1 = wx.Bitmap("images/-1.png")
        bmp2 = wx.Bitmap("images/-10.png")
        bmp3 = wx.Bitmap("images/-50.png")
        bmp4 = wx.Bitmap("images/1.png")
        bmp5 = wx.Bitmap("images/10.png")
        bmp6 = wx.Bitmap("images/50.png")
        bmp7 = wx.Bitmap("images/x.png")
        #bmp8 = wx.Bitmap("images/-x.png")
        bmp9 = wx.Bitmap("images/y.png")
        #bmp10 = wx.Bitmap("images/-y.png")
        bmp11 = wx.Bitmap("images/z.png")
        #bmp12 = wx.Bitmap("images/-z.png")
        
        #bmp13 = wx.Bitmap("images/home_new.png")
        #dc.DrawBitmap(bmp13, 0, 0,1) 
        #print("asdf")
        
        for ftn, kpos in label_overlay_positions2.items():
            #print (ftn)
            if self.CheckCollision(mpos,kpos) == True:
                if ftn == "X-1":
                    dc.DrawBitmap(bmp1, 81, 114,1) 
                    dc.DrawBitmap(bmp7, 115, 115,1)
                elif ftn == "X-10":
                    dc.DrawBitmap(bmp2, 43, 114,1)
                    dc.DrawBitmap(bmp7, 115, 115,1)
                elif ftn == "X-50":
                    dc.DrawBitmap(bmp3, 7, 114,1)
                    dc.DrawBitmap(bmp7, 115, 115,1)
                elif ftn == "X1":
                    dc.DrawBitmap(bmp4, 150, 114,1)
                    dc.DrawBitmap(bmp7, 115, 115,1)
                elif ftn == "X10":
                    dc.DrawBitmap(bmp5, 186, 114,1) 
                    dc.DrawBitmap(bmp7, 115, 115,1)
                elif ftn == "X50":
                    dc.DrawBitmap(bmp6, 223, 114,1)
                    dc.DrawBitmap(bmp7, 115, 115,1)
                    
                elif ftn == "Y-1":
                    dc.DrawBitmap(bmp1, 117, 150,1) 
                    dc.DrawBitmap(bmp9, 115, 115,1) 
                elif ftn == "Y-10":
                    dc.DrawBitmap(bmp2, 116, 186,1) 
                    dc.DrawBitmap(bmp9, 115, 115,1) 
                elif ftn == "Y-50":
                    dc.DrawBitmap(bmp3, 116, 222,1)
                    dc.DrawBitmap(bmp9, 115, 115,1)  
                    
                elif ftn == "Y1":
                    dc.DrawBitmap(bmp4, 118, 82,1) 
                    dc.DrawBitmap(bmp9, 115, 115,1) 
                elif ftn == "Y10":
                    dc.DrawBitmap(bmp5, 117, 45,1)
                    dc.DrawBitmap(bmp9, 115, 115,1)  
                elif ftn == "Y50":
                    dc.DrawBitmap(bmp6, 117, 9,1)
                    dc.DrawBitmap(bmp9, 115, 115,1) 
                
                elif ftn == "Z-1":
                    dc.DrawBitmap(bmp1, 277, 149,1)
                    dc.DrawBitmap(bmp11, 276, 114,1) 
                elif ftn == "Z-10":
                    dc.DrawBitmap(bmp2, 276, 186,1)
                    dc.DrawBitmap(bmp11, 276, 114,1) 
                elif ftn == "Z-50":
                    dc.DrawBitmap(bmp3, 276, 222,1)
                    dc.DrawBitmap(bmp11, 276, 114,1) 
                
                elif ftn == "Z1":
                    dc.DrawBitmap(bmp4, 278, 82,1)
                    dc.DrawBitmap(bmp11, 276, 114,1) 
                elif ftn == "Z10":
                    dc.DrawBitmap(bmp5, 277, 45,1)
                    dc.DrawBitmap(bmp11, 276, 114,1) 
                elif ftn == "Z50":
                    dc.DrawBitmap(bmp6, 277, 9,1)
                    dc.DrawBitmap(bmp11, 276, 114,1) 
                
                elif ftn == "home X":
                    dc.DrawBitmap(bmp7, 115, 115,1)
                elif ftn == "home Y":
                    dc.DrawBitmap(bmp9, 115, 115,1)
                elif ftn == "home Z":
                    dc.DrawBitmap(bmp11, 276, 114,1) 
            #dc.DrawBitmap(bmp8, 111, 120,1) 
            #dc.DrawBitmap(bmp9, 120, 129,1) 
            #dc.DrawBitmap(bmp10, 119, 110,1) 

    ## ------ ##
    ## Events ##
    ## ------ ##
    

		
    def OnMotion(self, event):
        global mpos
        
        if not self.enabled:
            return
        
        oldr, oldd = self.range, self.direction
        #print(oldr)
        mpos = event.GetPosition()
        self.range, self.direction = self.getRangeDir(mpos)
	
        for ftn, kpos in label_overlay_positions2.items():
            if self.CheckCollision(mpos,kpos) == True:
                self.update()
                
        #self.CheckCollision(mpos,label_overlay_positions2['move X 10'])for ftn, kpos in label_overlay_positions2.items():
        if oldr != self.range or oldd != self.direction:
            self.update()
            #print("lol")

    def OnLeftDown(self, event):
        if not self.enabled:
            return

        mpos = event.GetPosition()
        #r, d = self.getRangeDir(mpos)
        #print (mpos[0]*-1)-mpos[1]
        for ftn, kpos in label_overlay_positions2.items():
            if(self.CheckCollision(mpos,kpos) == True):
                #print ftn[:1]
                if ftn[:1] == "X":
                    self.moveCallback(ftn[1:],0,0)
                elif ftn[:1] == "Y":
                    self.moveCallback(0,ftn[1:],0)
                elif ftn[:1] == "Z":
                    self.moveCallback(0,0,ftn[1:])
                    
                elif ftn[-1:] == "X":
                    self.moveCallback("h",0,0)
                    print("Homing X")
                elif ftn[-1:] == "Y":
                    self.moveCallback(0,"h",0)
                    print("Homing Y")
                elif ftn[-1:] == "Z":
                    self.moveCallback(0,0,"h")
                    print("Homing Z")
                    
                elif ftn[-1:] == "A":
                    self.moveCallback("h","h","h")
                    print("Homing All")
                
                #elif ftn[-1:] == "X" and (mpos[0]*-1)-mpos[1] > -103:
                #    self.moveCallback("h",0,0)
                #    print("homing X")
                #elif ftn[-1:] == "Y" and mpos[0]-mpos[1]-150 > 0:
                #    self.moveCallback(0,"h",0)
                #    print("homing Y")
                #elif ftn[-1:] == "Z" and (mpos[0]*-1)-mpos[1] < -400:
                #    self.moveCallback(0,0,"h")
                #    print("homing Z")
                    
                #elif ftn[-1:] == "A" and mpos[0]-mpos[1]+150 < 0:
                #    self.moveCallback("h","h","h")
                #    print("homing All")
                
    def OnLeaveWindow(self, evt):
        self.range = None
        self.direction = None
        self.update()
