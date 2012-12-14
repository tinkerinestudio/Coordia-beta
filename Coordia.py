#!/usr/bin/env python

#Coordia beta v0.1 by Tinkerine Studio
#Coordia is based on Pronterface and runs skeinforge in the background for slice commands (with pypy for quicker slicing).

#By using this software, you agree to the following conditions:
#Use this software at your own risk. The program is provided as is without any guarantees or warranty.
#Tinkerine Studio is not responsible for any damage to your machine (although highly unlikely) caused by the use of the software.

#For questions, comments or feedback, feel free to email: support@tinkerines.com 

#Coordia is open source software; you are free to distribute and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#For a copy of the GNU General Public License, see http://www.gnu.org/licenses/

# Set up Internationalization using gettext
# searching for installed locales on /usr/share; uses relative folder if not found (windows)
import os, gettext, Queue, re, math

if os.path.exists('/usr/share/pronterface/locale'):
    gettext.install('pronterface', '/usr/share/pronterface/locale', unicode=1)
else:
    gettext.install('pronterface', './locale', unicode=1)

try:
    import wx
except:
    print _("WX is not installed. This program requires WX to run.")
    raise
import printcore, sys, glob, time, threading, traceback, gviz, traceback, cStringIO, subprocess
try:
    os.chdir(os.path.split(__file__)[0])
except:
    pass
StringIO=cStringIO

thread=threading.Thread
winsize=(800,550)
if os.name=="nt":
    winsize=(800,530)
    try:
        import _winreg
    except:
        pass

import testcsv

from xybuttons import XYButtons
from xyzbuttons import XYZButtons
from graph import Graph
import pronsole

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8]+".g"

class Tee(object):
    def __init__(self, target):
        self.stdout = sys.stdout
        sys.stdout = self
        self.target=target
    def __del__(self):
        sys.stdout = self.stdout
    def write(self, data):
        self.target(data)
        self.stdout.write(data.encode("utf-8"))
    def flush(self):
        self.stdout.flush()


class PronterWindow(wx.Frame,pronsole.pronsole):
    def __init__(self, filename=None,size=winsize):

        pronsole.pronsole.__init__(self)
        self.dummy_log=wx.LogNull()
        self.settings.build_dimensions = '200x200x100+0+0+0' #default build dimensions are 200x200x100 with 0,0,0 in the corner of the bed
        self.settings.last_bed_temperature = 0.0
        self.settings.last_file_path = ""
        self.settings.last_temperature = 0.0
        self.settings.preview_extrusion_width = 0.5
        self.settings.preview_grid_step1 = 10.
        self.settings.preview_grid_step2 = 50.
        #self.settings.bgcolor = "#FFFFFF"
        
        self.settings.baudrate = 250000
        self.settings.e_feedrate = 300
        self.settings.xy_feedrate = 3000
        self.settings.z_feedrate = 200
        self.settings.slicecommand = "pypy/pypy.exe skeinforge/skeinforge_application/skeinforge_utilities/skeinforge_craft.py $s"
        self.settings.sliceoptscommand = "python/python.exe skeinforge/skeinforge_application/skeinforge.py"
        self.settings.home_on_start = "true"
        
        self.helpdict["build_dimensions"] = _("Dimensions of Build Platform\n & optional offset of origin\n\nExamples:\n   XXXxYYY\n   XXX,YYY,ZZZ\n   XXXxYYYxZZZ+OffX+OffY+OffZ")
        self.helpdict["last_bed_temperature"] = _("Last Set Temperature for the Heated Print Bed")
        self.helpdict["last_file_path"] = _("Folder of last opened file")
        self.helpdict["last_temperature"] = _("Last Temperature of the Hot End")
        self.helpdict["preview_extrusion_width"] = _("Width of Extrusion in Preview (default: 0.5)")
        self.helpdict["preview_grid_step1"] = _("Fine Grid Spacing (default: 10)")
        self.helpdict["preview_grid_step2"] = _("Coarse Grid Spacing (default: 50)")
        #self.helpdict["bgcolor"] = _("Pronterface background color (default: #FFFFFF)")
        self.helpdict["home_on_start"] = _("Home X and Y upon connecting to printer (default: true)")
        self.filename=filename
        os.putenv("UBUNTU_MENUPROXY","0")
        wx.Frame.__init__(self,None,title=_("Coordia"),size=size,style= wx.MINIMIZE_BOX 
	| wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX); #| wx.RESIZE_BORDER| wx.MAXIMIZE_BOX |
        self.SetIcon(wx.Icon("coordia.ico",wx.BITMAP_TYPE_ICO))
        self.panel=wx.Panel(self,-1,size=size)
        self.statuscheck=False
        self.capture_skip={}
        self.capture_skip_newline=False
        self.tempreport=""
        self.degree = unichr(176)
        self.monitor=0
        self.f=None
        self.skeinp=None
        self.monitor_interval=4 #justin: 4 seconds
        self.paused=False
        self.sentlines=Queue.Queue(30)
        xcol=(245,245,108)
        ycol=(180,180,255)
        zcol=(180,255,180)
        self.cpbuttons=[
            #[_("Motors off"),("M84"),(1,0),(250,250,250),(1,2)],
            #[_("Check temp"),("M105"),(3,5),(225,200,200),(1,3)],
            #[_("Extrude"),("extrude"),(7,0),(225,200,200),(1,2)],
            #[_("Reverse"),("reverse"),(8,0),(225,200,200),(1,2)],
        ]
        self.custombuttons=[]
        self.btndict={}
        self.parse_cmdline(sys.argv[1:])
        self.build_dimensions_list = self.get_build_dimensions(self.settings.build_dimensions)
        self.panel.SetBackgroundColour(wx.Colour(73,73,75))
        #self.panel.SetBackgroundColour(self.settings.bgcolor)
        customdict={}
        try:
            execfile("custombtn.txt",customdict)
            if len(customdict["btns"]):
                if not len(self.custombuttons):
                    try:
                        self.custombuttons = customdict["btns"]
                        for n in xrange(len(self.custombuttons)):
                            self.cbutton_save(n,self.custombuttons[n])
                        os.rename("custombtn.txt","custombtn.old")
                        rco=open("custombtn.txt","w")
                        rco.write(_("# I moved all your custom buttons into .pronsolerc.\n# Please don't add them here any more.\n# Backup of your old buttons is in custombtn.old\n"))
                        rco.close()
                    except IOError,x:
                        print str(x)
                else:
                    print _("Note!!! You have specified custom buttons in both custombtn.txt and .pronsolerc")
                    print _("Ignoring custombtn.txt. Remove all current buttons to revert to custombtn.txt")

        except:
            pass
        self.popmenu()
        self.popwindow()
        self.t=Tee(self.catchprint)
        self.stdout=sys.stdout
        self.skeining=0
        self.mini=False
        self.p.sendcb=self.sentcb
        self.p.startcb=self.startcb
        self.p.endcb=self.endcb
        self.starttime=0
        self.extra_print_time=0
        self.curlayer=0
        self.fractioncomplete=0.0
        self.cur_button=None
        self.hsetpoint=0.0
        self.bsetpoint=0.0
        
        self.tempstatus=1
        self.initialhome=0
        
    def startcb(self):
        self.starttime=time.time()
        print "Print Started at: " +time.strftime('%H:%M:%S',time.localtime(self.starttime))

    def endcb(self):
        if(self.p.queueindex==0):
            print "Print ended at: " +time.strftime('%H:%M:%S',time.localtime(time.time()))
            print "and took: "+time.strftime('%H:%M:%S', time.gmtime(int(time.time()-self.starttime+self.extra_print_time)))  #+str(int(time.time()-self.starttime)/60)+" minutes "+str(int(time.time()-self.starttime)%60)+" seconds."
            #wx.CallAfter(self.pausebtn.Disable)
            #wx.CallAfter(self.printbtn.SetLabel,_("Print"))
            self.printbtn.SetBitmapLabel(wx.Bitmap('images/print_3.png'))
            self.printbtn.SetToolTipString(_("Start Print"))
            self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
            
            self.stopbtn.Bind(wx.EVT_BUTTON,self.motorsoff)
            self.stopbtn.SetToolTipString(_("Turn Motors Off"))
            self.stopbtn.SetBitmapLabel(wx.Bitmap('images/motors_1.png'))
            self.do_settemp("off")

    def online(self):
        print _("Printer initializing...")
        self.connectbtn.SetBitmapLabel(wx.Bitmap('images/disconnect_2.png'))
        self.connectbtn.SetToolTipString(_("Disconnect Printer"))
        self.connectbtn.SetLabel, _("Disconnect")
        self.connectbtn.Bind(wx.EVT_BUTTON,self.disconnect)
        
        self.monitor=1 #justin: always monitoring
        
        #justin: enabling stuff moved to statuschecker
            
    def sentcb(self,line):
        if("G1" in line):
            if("Z" in line):
                try:
                    layer=float(line.split("Z")[1].split()[0])
                    if(layer!=self.curlayer):
                        #self.progressbar1.Refresh()
                        self.curlayer=layer
                        self.gviz.hilight=[]
						
                        threading.Thread(target=wx.CallAfter,args=(self.gviz.setlayer,layer)).start()
                except:
                    pass
            try:
                self.sentlines.put_nowait(line)
            except:
                pass
            #threading.Thread(target=self.gviz.addgcode,args=(line,1)).start()
            #self.gwindow.p.addgcode(line,hilight=1)
        if("M104" in line or "M109" in line):
            if("S" in line):
                try:
                    temp=float(line.split("S")[1].split("*")[0])
                    #self.hottgauge.SetTarget(temp)
                    self.graph.SetExtruder0TargetTemperature(temp)
                except:
                    pass
            try:
                self.sentlines.put_nowait(line)
            except:
                pass
        if("M140" in line):
            if("S" in line):
                try:
                    temp=float(line.split("S")[1].split("*")[0])
                    self.bedtgauge.SetTarget(temp)
                    self.graph.SetBedTargetTemperature(temp)
                except:
                    pass
            try:
                self.sentlines.put_nowait(line)
            except:
                pass

    def do_extrude(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.edist.GetValue())
            pronsole.pronsole.do_extrude(self,l)
        except:
            raise

    def do_reverse(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(float(self.edist.GetValue())*-1.0)
            pronsole.pronsole.do_extrude(self,l)
        except:
            pass

    def do_settemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.htemp.GetValue().split()[0])
            l=l.lower().replace(",",".")
            for i in self.temps.keys():
                l=l.replace(i,self.temps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M104 S"+l)
                    print _("Setting hotend temperature to %f degrees Celsius.") % f
                    self.hsetpoint=f
                    if f>0:
                        wx.CallAfter(self.htemp.SetValue,l)
                        self.set("last_temperature",str(f))
                        self.hotendlabel.SetBitmap(wx.Bitmap('images/hotend_2.png'))
                        self.tempstatus = 2
                    else:
                        self.hotendlabel.SetBitmap(wx.Bitmap('images/hotend_1.png'))
                        targettemp = 0.0
                        wx.CallAfter(self.htemp.Refresh)
                else:
                    print _("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0.")
        except Exception,x:
            print _("You must enter a temperature. (%s)" % (repr(x),))

    def do_bedtemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.btemp.GetValue().split()[0])
            l=l.lower().replace(",",".")
            for i in self.bedtemps.keys():
                l=l.replace(i,self.bedtemps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M140 S"+l)
                    print _("Setting bed temperature to %f degrees Celsius.") % f
                    self.bsetpoint=f
                    self.bedtgauge.SetTarget(int(f))
                    self.graph.SetBedTargetTemperature(int(f))
                    if f>0:
                        wx.CallAfter(self.btemp.SetValue,l)
                        self.set("last_bed_temperature",str(f))
                        self.bedlabel.SetBitmap(wx.Bitmap('images/bed_2.png'))
                    else:
                        wx.CallAfter(self.btemp.Refresh)
                        self.bedlabel.SetBitmap(wx.Bitmap('images/bed_1.png'))
                else:
                    print _("Printer is not online.")
            else:
                print _("You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0.")
        except:
            print _("You must enter a temperature.")

    def end_macro(self):
        pronsole.pronsole.end_macro(self)
        self.update_macros_menu()

    def delete_macro(self,macro_name):
        pronsole.pronsole.delete_macro(self,macro_name)
        self.update_macros_menu()

    def start_macro(self,macro_name,old_macro_definition=""):
        if not self.processing_rc:
            def cb(definition):
                if len(definition.strip())==0:
                    if old_macro_definition!="":
                        dialog = wx.MessageDialog(self,_("Do you want to erase the macro?"),style=wx.YES_NO|wx.YES_DEFAULT|wx.ICON_QUESTION)
                        if dialog.ShowModal()==wx.ID_YES:
                            self.delete_macro(macro_name)
                            return
                    print _("Cancelled.")
                    return
                self.cur_macro_name = macro_name
                self.cur_macro_def = definition
                self.end_macro()
            macroed(macro_name,old_macro_definition,cb)
        else:
            pronsole.pronsole.start_macro(self,macro_name,old_macro_definition)

    def catchprint(self,l):
        if self.capture_skip_newline and len(l) and not len(l.strip("\n\r")):
            self.capture_skip_newline = False
            return
        for pat in self.capture_skip.keys():
            if self.capture_skip[pat] > 0 and pat.match(l):
                self.capture_skip[pat] -= 1
                self.capture_skip_newline = True
                return
        wx.CallAfter(self.logbox.AppendText,l)

    def scanserial(self):
        """scan for available ports. return a list of device names."""
        baselist=[]
        if os.name=="nt":
            try:
                key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i=0
                while(1):
                    baselist+=[_winreg.EnumValue(key,i)[1]]
                    i+=1
            except:
                pass
        return baselist+glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') +glob.glob("/dev/tty.*")+glob.glob("/dev/cu.*")+glob.glob("/dev/rfcomm*")

    def project(self,event):
        import projectlayer
        if(self.p.online):
            projectlayer.setframe(self,self.p).Show()
        else:
            print _("Printer is not online.")

    def popmenu(self):
        self.menustrip = wx.MenuBar()
        # File menu
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, self.loadfile2, m.Append(-1,_("&Open File..."),_(" Opens file")))
        self.Bind(wx.EVT_MENU, self.do_editgcode, m.Append(-1,_("&Edit Gcode..."),_(" Edit open file")))
        self.Bind(wx.EVT_MENU, self.clearOutput, m.Append(-1,_("Clear console"),_(" Clear output console")))
        self.Bind(wx.EVT_MENU, self.rescanports, m.Append(-1,_("Refresh Ports"),_(" Rescan Ports")))
        #self.Bind(wx.EVT_MENU, self.project, m.Append(-1,_("Projector"),_(" Project slices")))
        self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT,_("E&xit"),_(" Closes the Window")))
        self.menustrip.Append(m,_("&File"))

        # Settings menu
        m = wx.Menu()
        self.macros_menu = wx.Menu()
        #m.AppendSubMenu(self.macros_menu, _("&Macros"))
        #self.Bind(wx.EVT_MENU, self.new_macro, self.macros_menu.Append(-1, _("<&New...>")))
        self.Bind(wx.EVT_MENU, lambda *e:options(self), m.Append(-1,_("&Options"),_(" Options dialog")))
        
        self.monitormenubox = m.Append(-1,_("Monitor Printer"),_(" Monitor Printer Temperature"), wx.ITEM_CHECK)
        self.Bind(wx.EVT_MENU, self.setmonitor,self.monitormenubox)
        m.Check(self.monitormenubox.GetId(), True)
        
        
        self.Bind(wx.EVT_MENU, lambda x:threading.Thread(target=lambda :self.do_skein("set")).start(), m.Append(-1,_("Slicing Settings"),_(" Adjust slicing settings")))
        try:
            from SkeinforgeQuickEditDialog import SkeinforgeQuickEditDialog
            #self.Bind(wx.EVT_MENU, lambda *e:SkeinforgeQuickEditDialog(self), m.Append(-1,_("SFACT Quick Settings"),_(" Quickly adjust SFACT settings for active profile")))
        except:
            pass

        self.menustrip.Append(m,_("&Settings"))
        self.update_macros_menu()
        self.SetMenuBar(self.menustrip)


    def doneediting(self,gcode):
        f=open(self.filename,"w")
        f.write("\n".join(gcode))
        f.close()
        wx.CallAfter(self.loadfile,None,self.filename)

    def do_editgcode(self,e=None):
        if(self.filename is not None):
            macroed(self.filename,self.f,self.doneediting,1)

    def new_macro(self,e=None):
        dialog = wx.Dialog(self,-1,_("Enter macro name"),size=(260,85))
        panel = wx.Panel(dialog,-1)
        vbox = wx.BoxSizer(wx.VERTICAL)
        wx.StaticText(panel,-1,_("Macro name:"),(8,14))
        dialog.namectrl = wx.TextCtrl(panel,-1,'',(110,8),size=(130,24),style=wx.TE_PROCESS_ENTER)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        okb = wx.Button(dialog,wx.ID_OK,_("Ok"),size=(60,24))
        dialog.Bind(wx.EVT_TEXT_ENTER,lambda e:dialog.EndModal(wx.ID_OK),dialog.namectrl)
        #dialog.Bind(wx.EVT_BUTTON,lambda e:self.new_macro_named(dialog,e),okb)
        hbox.Add(okb)
        hbox.Add(wx.Button(dialog,wx.ID_CANCEL,_("Cancel"),size=(60,24)))
        vbox.Add(panel)
        vbox.Add(hbox,1,wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM,10)
        dialog.SetSizer(vbox)
        dialog.Centre()
        macro = ""
        if dialog.ShowModal()==wx.ID_OK:
            macro = dialog.namectrl.GetValue()
            if macro != "":
                wx.CallAfter(self.edit_macro,macro)
        dialog.Destroy()
        return macro

    def edit_macro(self,macro):
        if macro == "": return self.new_macro()
        if self.macros.has_key(macro):
            old_def = self.macros[macro]
        elif hasattr(self.__class__,"do_"+macro):
            print _("Name '%s' is being used by built-in command") % macro
            return
        elif len([c for c in macro if not c.isalnum() and c != "_"]):
            print _("Macro name may contain only alphanumeric symbols and underscores")
            return
        else:
            old_def = ""
        self.start_macro(macro,old_def)
        return macro

    def update_macros_menu(self):
        if not hasattr(self,"macros_menu"):
            return # too early, menu not yet built
        try:
            while True:
                item = self.macros_menu.FindItemByPosition(1)
                if item is None: return
                self.macros_menu.DeleteItem(item)
        except:
            pass
        for macro in self.macros.keys():
            self.Bind(wx.EVT_MENU, lambda x,m=macro:self.start_macro(m,self.macros[m]), self.macros_menu.Append(-1, macro))

    def OnExit(self, event):
        self.Close()

    def rescanports(self,event=None):
        print "Rescanning Ports..."
        scan=self.scanserial()
        portslist=list(scan)
        if self.settings.port != "" and self.settings.port not in portslist:
            portslist += [self.settings.port]
            self.serialport.Clear()
            self.serialport.AppendItems(portslist)
        try:
            if os.path.exists(self.settings.port) or self.settings.port in scan:
                self.serialport.SetValue(self.settings.port)
            elif len(portslist)>0:
                self.serialport.SetValue(portslist[0])
        except:
            pass


    def popwindow(self):

        
        # this list will contain all controls that should be only enabled
        # when we're connected to a printer
        self.printerControls = []
        #sizer layout: topsizer is a column sizer containing two sections
        #upper section contains the mini view buttons
        #lower section contains the rest of the window - manual controls, console, visualizations
		
        #TOP ROW:
        uts=self.uppertopsizer=wx.BoxSizer(wx.VERTICAL)

        #SECOND ROW
        ubs=self.upperbottomsizer=wx.BoxSizer(wx.HORIZONTAL)

        #left pane
        lls=self.lowerlsizer=wx.GridBagSizer() #justin: everything is in lls now!
        leftbuttonpanel=wx.BoxSizer(wx.VERTICAL) #justin: please rename leftbuttonpanel!
	
        lls.Add(leftbuttonpanel,pos=(0,0),span=(1,1))

        self.serialport = wx.ComboBox(self.panel, -1, #justin: com port box
                choices=self.scanserial(),
                style=wx.CB_DROPDOWN,
				size = (62,-1))
                

        
        self.rescanports()
        leftbuttonpanel.Add(self.serialport,flag=wx.ALIGN_CENTER_VERTICAL|wx.BOTTOM|wx.TOP|wx.RIGHT|wx.LEFT, border=8)
		
		
        self.connectbtn=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/connect_3.png'),style=wx.NO_BORDER)
        self.connectbtn.SetToolTipString(_("Connect to the printer"))
        self.connectbtn.Bind(wx.EVT_BUTTON,self.connect)
        self.connectbtn.SetBackgroundColour(wx.Colour(73,73,75))

        leftbuttonpanel.Add(self.connectbtn,flag=wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM|wx.RIGHT|wx.LEFT, border=5)
		
        self.loadbtn=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/slice_4.png'),style=wx.NO_BORDER)
        self.loadbtn.SetToolTipString(_("Slice a .stl or .obj file into .gcode"))

        self.loadbtn.Bind(wx.EVT_BUTTON,self.loadfile)
        self.loadbtn.SetBackgroundColour(wx.Colour(73,73,75))
        leftbuttonpanel.Add(self.loadbtn,flag=wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM|wx.RIGHT|wx.LEFT, border=5)

        self.loadbtn2=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/upload_4.png'),style=wx.NO_BORDER)
        self.loadbtn2.SetToolTipString(_("Upload a .gcode file to the printer"))

        self.loadbtn2.Bind(wx.EVT_BUTTON,self.loadfile2)
        self.loadbtn2.SetBackgroundColour(wx.Colour(73,73,75))
        leftbuttonpanel.Add(self.loadbtn2,flag=wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM|wx.RIGHT|wx.LEFT, border=5)
        
        self.printbtn=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/print_3.png'),style=wx.NO_BORDER)
        self.printbtn.SetBitmapDisabled(wx.Bitmap('images/print_1.png'))
        self.printbtn.SetToolTipString(_("Start Print"))
        self.printbtn.SetBackgroundColour(wx.Colour(73,73,75))
        self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
        self.printbtn.Disable()
        leftbuttonpanel.Add(self.printbtn,flag=wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM|wx.RIGHT|wx.LEFT, border=5)

        self.stopbtn=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/motors_4.png'),style=wx.NO_BORDER)
        self.stopbtn.SetToolTipString(_("Turn Motors Off"))
        self.stopbtn.SetBackgroundColour(wx.Colour(73,73,75))
        self.stopbtn.Bind(wx.EVT_BUTTON,self.motorsoff)
        self.stopbtn.Disable()
        leftbuttonpanel.Add(self.stopbtn,flag=wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM|wx.RIGHT|wx.LEFT, border=5)

		
        controls=wx.BoxSizer(wx.VERTICAL) #justin: top right stuff
	
        xyzbuttons=wx.BoxSizer(wx.HORIZONTAL)
        
        self.xyb = XYZButtons(self.panel, self.moveXYZ)
        xyzbuttons.Add(self.xyb,flag=wx.BOTTOM,border=0) #justin: xy+z buttons

        controls.Add(xyzbuttons,flag=wx.ALL,border=8)
	
	
	
        extruderbuttons=wx.BoxSizer(wx.HORIZONTAL) #justin: rename this too!

        self.asdf=wx.StaticText(self.panel,-1, "Move Filament(mm):")
        font2 = wx.Font(8.5, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        self.asdf.SetFont(font2)
        self.asdf.SetForegroundColour((255,255,255)) # set text color
        
        extruderbuttons.Add(self.asdf,flag=wx.ALIGN_CENTER | wx.RIGHT, border=3)
        
        self.edist=wx.SpinCtrl(self.panel,-1,"5",min=0,max=1000,size=(50,-1)) #justin: extrude field
        self.edist.SetBackgroundColour((73,73,75))
        self.edist.SetForegroundColour("black")
        extruderbuttons.Add(self.edist,flag=wx.ALIGN_CENTER | wx.RIGHT, border=5)
        
        self.extrudebtn=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/extrude_2.png'),style=wx.NO_BORDER)
        self.extrudebtn.Bind(wx.EVT_BUTTON,self.do_extrude)
        self.extrudebtn.SetBitmapDisabled(wx.Bitmap('images/extrude_1.png'))
        self.extrudebtn.SetBackgroundColour(wx.Colour(73,73,75))

        self.printerControls.append(self.extrudebtn)
        extruderbuttons.Add(self.extrudebtn,flag=wx.ALIGN_CENTER | wx.RIGHT, border=6)
		
        self.retractbtn=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/retract_2.png'),style=wx.NO_BORDER)
        self.retractbtn.Bind(wx.EVT_BUTTON,self.do_reverse)
        self.retractbtn.SetBitmapDisabled(wx.Bitmap('images/retract_1.png'))
        self.retractbtn.SetBackgroundColour(wx.Colour(73,73,75))

        self.printerControls.append(self.retractbtn)
        extruderbuttons.Add(self.retractbtn,flag=wx.ALIGN_CENTER | wx.RIGHT, border=5)

		
        controls.Add(extruderbuttons,flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, border=5)
	
        lls.Add(controls, pos=(0,6), span=(1,2))
		
        lrs=self.lowerrsizer=wx.BoxSizer(wx.VERTICAL)
        self.logbox=wx.TextCtrl(self.panel,style = wx.TE_MULTILINE,size=(314,120)) #justin: output window
        self.logbox.SetEditable(0)
        self.logbox.SetBackgroundColour(wx.Colour(120,120,120))
	
        self.commandbox=wx.TextCtrl(self.panel,style = wx.TE_PROCESS_ENTER)
        self.commandbox.Bind(wx.EVT_TEXT_ENTER,self.sendline)
        
        
        self.sendbtn=wx.Button(self.panel,-1,_("Send"))
        self.sendbtn.Bind(wx.EVT_BUTTON,self.sendline)

        wx.CallAfter(self.xyb.SetFocus)
        lls.Add(self.logbox, pos=(1,6), span=(4,2)) #justin: send box
        lbrs=wx.BoxSizer(wx.HORIZONTAL)
        lbrs.Add(self.commandbox,1)
        lbrs.Add(self.sendbtn)
        lls.Add(lbrs, pos=(5,6), span=(1,3),flag=wx.EXPAND |wx.ALIGN_RIGHT | wx.RIGHT, border=5)
	
        for i in self.cpbuttons:
            btn=wx.Button(self.panel,-1,i[0])#)
            btn.SetBackgroundColour(i[3])
            btn.SetForegroundColour("black")
            btn.properties=i
            btn.Bind(wx.EVT_BUTTON,self.procbutton)
            self.btndict[i[1]]=btn
            self.printerControls.append(btn)
            lls.Add(btn,pos=i[2],span=i[4])

        temperaturestuff=wx.BoxSizer(wx.VERTICAL)		
	
        toprow=wx.BoxSizer(wx.HORIZONTAL)
	
		
        bottomrow=wx.BoxSizer(wx.HORIZONTAL)
        

        bitmap = wx.Bitmap("images/hotend_1.png")
        self.hotendlabel = wx.StaticBitmap(self, -1, bitmap)

        toprow.Add(self.hotendlabel,flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=5)
        htemp_choices=[self.temps[i]+" ("+i+")" for i in sorted(self.temps.keys(),key=lambda x:self.temps[x])]

        if self.settings.last_temperature not in map(float,self.temps.values()):
            htemp_choices = [str(self.settings.last_temperature)] + htemp_choices
        self.htemp=wx.ComboBox(self.panel, -1,
                choices=htemp_choices,style=wx.CB_DROPDOWN, size=(80,-1))
        self.htemp.Bind(wx.EVT_COMBOBOX,self.htemp_change)
        toprow.Add(self.htemp)
		
        self.setbtn1=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/set_2.png'),style=wx.NO_BORDER)
        self.setbtn1.Bind(wx.EVT_BUTTON,self.do_settemp) #justin: make sure this works eh?
        self.setbtn1.SetToolTipString(_("Set Hotend Temperature"))
        self.setbtn1.SetBitmapDisabled(wx.Bitmap('images/set_1.png'))
        
        self.printerControls.append(self.setbtn1)
        
        toprow.Add(self.setbtn1,flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT|wx.LEFT,border=5)
        
        self.setoffbtn=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/off_2.png'),style=wx.NO_BORDER)
        self.setoffbtn.Bind(wx.EVT_BUTTON,lambda e:self.do_settemp("off"))
        self.setoffbtn.SetToolTipString(_("Set Hotend Temperature"))
        self.setoffbtn.SetBitmapDisabled(wx.Bitmap('images/off_1.png'))
        self.printerControls.append(self.setoffbtn)
        toprow.Add(self.setoffbtn,flag=wx.ALIGN_RIGHT | wx.LEFT, border=0)
        
        bitmap = wx.Bitmap("images/bed_1.png")
        bedlabel = wx.StaticBitmap(self, -1, bitmap)
        
        bottomrow.Add(bedlabel,flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.RIGHT, border=5)
        btemp_choices=[self.bedtemps[i]+" ("+i+")" for i in sorted(self.bedtemps.keys(),key=lambda x:self.temps[x])]

        if self.settings.last_bed_temperature not in map(float,self.bedtemps.values()):
            btemp_choices = [str(self.settings.last_bed_temperature)] + btemp_choices
        self.btemp=wx.ComboBox(self.panel, -1,
                choices=btemp_choices,style=wx.CB_DROPDOWN, size=(80,-1))
        self.btemp.Bind(wx.EVT_COMBOBOX,self.btemp_change)
        bottomrow.Add(self.btemp, flag=wx.LEFT, border=0)
        
        self.setbtn2=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/set_2.png'),style=wx.NO_BORDER)
        self.setbtn2.Bind(wx.EVT_BUTTON,lambda e:self.do_bedtemp("off"))
        self.setbtn2.SetToolTipString(_("Set Hotend Temperature"))
        self.setbtn2.SetBitmapDisabled(wx.Bitmap('images/set_1.png'))
        self.printerControls.append(self.setbtn2)
        
        bottomrow.Add(self.setbtn2,flag=wx.ALIGN_LEFT | wx.LEFT,border=5)
        
        self.setoffbtn2=wx.BitmapButton(self.panel,-1,wx.Bitmap('images/off_2.png'),style=wx.NO_BORDER)
        self.setoffbtn2.Bind(wx.EVT_BUTTON,lambda e:self.do_bedtemp("off"))
        self.setoffbtn2.SetToolTipString(_("Set Hotend Temperature"))
        self.setoffbtn2.SetBitmapDisabled(wx.Bitmap('images/off_1.png'))
        self.printerControls.append(self.setoffbtn2)
        bottomrow.Add(self.setoffbtn2,flag=wx.ALIGN_LEFT | wx.LEFT, border=0)
		
        self.btemp.SetValue(str(self.settings.last_bed_temperature))
        self.htemp.SetValue(str(self.settings.last_temperature))
		
        temperaturestuff.Add(toprow,flag=wx.ALIGN_LEFT | wx.LEFT, border = 0)
        temperaturestuff.Add(bottomrow,flag=wx.ALIGN_LEFT | wx.TOP, border = 0)
		
        progressbarstuff=wx.BoxSizer(wx.VERTICAL)
        
        filenamestuff=wx.BoxSizer(wx.HORIZONTAL)
        progresspercentstuff=wx.BoxSizer(wx.HORIZONTAL)

        self.filenametext=wx.StaticText(self.panel,-1,_(""))
        self.progresstext=wx.StaticText(self.panel,-1,_(""))
        
        self.filenametext.SetForegroundColour((255,255,255)) # set text color
        self.progresstext.SetForegroundColour((255,255,255)) # set text color
        
        bitmap = wx.Bitmap("images/file.png")
        filelabel = wx.StaticBitmap(self, -1, bitmap)
        bitmap = wx.Bitmap("images/progress.png")
        progresslabel = wx.StaticBitmap(self, -1, bitmap)
        
        filenamestuff.Add(filelabel)
        filenamestuff.Add(self.filenametext)
        progresspercentstuff.Add(progresslabel)
        progresspercentstuff.Add(self.progresstext)

        self.progressbar1=progressbar(self.panel,size=(369,20),title=_("Progress:"))#justin: progress bar

        progressbarstuff.Add(filenamestuff,flag=wx.ALIGN_LEFT|wx.BOTTOM|wx.TOP,border=5)
        progressbarstuff.Add(progresspercentstuff,flag=wx.ALIGN_LEFT|wx.BOTTOM,border=5)
        progressbarstuff.Add(self.progressbar1,flag=wx.ALIGN_LEFT| wx.BOTTOM|wx.RIGHT, border=5)

	
        lls.Add(temperaturestuff, pos=(1,0), span=(1,4),flag=wx.ALIGN_LEFT|wx.LEFT,border=10)
        lls.Add(progressbarstuff, pos=(3,0), span=(3,5),flag=wx.EXPAND|wx.LEFT,border=15)

        ## added for an error where only the bed would get (pla) or (abs).
        #This ensures, if last temp is a default pla or abs, it will be marked so.
        # if it is not, then a (user) remark is added. This denotes a manual entry

        for i in btemp_choices:
            if i.split()[0] == str(self.settings.last_bed_temperature).split('.')[0] or i.split()[0] == str(self.settings.last_bed_temperature):
                self.btemp.SetValue(i)
        for i in htemp_choices:
            if i.split()[0] == str(self.settings.last_temperature).split('.')[0] or i.split()[0] == str(self.settings.last_temperature) :
               self.htemp.SetValue(i)

        if( '(' not in self.btemp.Value):
            self.btemp.SetValue(self.btemp.Value + ' (user)')
        if( '(' not in self.htemp.Value):
            self.htemp.SetValue(self.htemp.Value + ' (user)')


        font2 = wx.Font(8.5, wx.DEFAULT, wx.NORMAL, wx.BOLD)
        
        self.tempdisp=wx.StaticText(self.panel,-1, "T: 0/0" + self.degree + " C")
        self.tempdisp.SetFont(font2)
        self.tempdisp.SetForegroundColour((255,255,255)) # set text color

        self.beddisp=wx.StaticText(self.panel,-1,"B: 0/0" + self.degree + " C")
        self.beddisp.SetFont(font2)
        self.beddisp.SetForegroundColour((255,255,255)) # set text color
        
        toprow.Add(self.tempdisp,flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT, border=3)
        bottomrow.Add(self.beddisp,flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.LEFT, border=3)
		

        self.gviz=gviz.gviz(self.panel,(147,148), #justin: gcode grid
            build_dimensions=self.build_dimensions_list,
            grid=(self.settings.preview_grid_step1,self.settings.preview_grid_step2),
            extrusion_width=self.settings.preview_extrusion_width)
        self.gviz.showall=1
        try:
            raise ""
            import stlview
            self.gwindow=stlview.GCFrame(None, wx.ID_ANY, 'Gcode view, mousewheel to zoom, shift + mousewheel to set layer', size=(600,600))
        except:
            self.gwindow=gviz.window([],
            build_dimensions=self.build_dimensions_list,
            grid=(self.settings.preview_grid_step1,self.settings.preview_grid_step2),
            extrusion_width=self.settings.preview_extrusion_width)
        self.gviz.Bind(wx.EVT_LEFT_DOWN,self.showwin)
        self.gwindow.Bind(wx.EVT_CLOSE,lambda x:self.gwindow.Hide())
        vcs=wx.BoxSizer(wx.VERTICAL)
        lls.Add(self.gviz,pos=(0,1),span=(1,5),flag=wx.EXPAND|wx.BOTTOM|wx.TOP|wx.RIGHT|wx.LEFT, border=5)
		
        cs=self.centersizer=wx.GridBagSizer()
        #vcs.Add(cs,0,flag=wx.EXPAND)

        self.uppersizer=wx.BoxSizer(wx.VERTICAL)
        self.uppersizer.Add(self.uppertopsizer)
        self.uppersizer.Add(self.upperbottomsizer)

        self.lowersizer=wx.BoxSizer(wx.HORIZONTAL)
        self.lowersizer.Add(lls)
        self.lowersizer.Add(vcs,1,wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL)
        self.lowersizer.Add(lrs,0,wx.EXPAND)
        self.topsizer=wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(self.uppersizer)
        self.topsizer.Add(self.lowersizer,1,wx.EXPAND)
        self.panel.SetSizer(self.topsizer)
        self.status=self.CreateStatusBar()
        self.status.SetStatusText(_("Not connected to printer."))
        self.panel.Bind(wx.EVT_MOUSE_EVENTS,self.editbutton)
        self.Bind(wx.EVT_CLOSE, self.kill)

        self.topsizer.Layout()
        self.topsizer.Fit(self)

        # disable all printer controls until we connect to a printer
        #self.pausebtn.Disable()
        for i in self.printerControls:
            i.Disable()

        #self.panel.Fit()
        #uts.Layout()

        #self.cbuttons_reload()
        


    def plate(self,e):
        import plater
        print "plate function activated"
        plater.stlwin(size=(800,580),callback=self.platecb,parent=self).Show()

    def platecb(self,name):
        print "plated: "+name
        self.loadfile(None,name)

    def sdmenu(self,e):
        obj = e.GetEventObject()
        popupmenu=wx.Menu()
        item = popupmenu.Append(-1,_("SD Upload"))
        if not self.f or not len(self.f):
            item.Enable(False)
        self.Bind(wx.EVT_MENU,self.upload,id=item.GetId())
        item = popupmenu.Append(-1,_("SD Print"))
        self.Bind(wx.EVT_MENU,self.sdprintfile,id=item.GetId())
        self.panel.PopupMenu(popupmenu, obj.GetPosition())

    def htemp_change(self,event):
        if self.hsetpoint > 0:
            self.do_settemp("")
        wx.CallAfter(self.htemp.SetInsertionPoint,0)

    def btemp_change(self,event):
        if self.bsetpoint > 0:
            self.do_bedtemp("")
        wx.CallAfter(self.btemp.SetInsertionPoint,0)

    def showwin(self,event):
        if(self.f is not None):
            self.gwindow.Show(True)
            self.gwindow.Raise()

    def setfeeds(self,e):
        self.feedrates_changed = True
        try:
            self.settings._set("e_feedrate",self.efeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("z_feedrate",self.zfeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("xy_feedrate",self.xyfeedc.GetValue())
        except:
            pass


    def toggleview(self,e):
        if(self.mini):
            self.mini=False
            self.topsizer.Fit(self)

            #self.SetSize(winsize)
            wx.CallAfter(self.minibtn.SetLabel, _("Mini mode"))

        else:
            self.mini=True
            self.uppersizer.Fit(self)

            #self.SetSize(winssize)
            wx.CallAfter(self.minibtn.SetLabel, _("Full mode"))

    def cbuttons_reload(self):
        allcbs = []
        ubs=self.upperbottomsizer
        cs=self.centersizer
        for item in ubs.GetChildren():
            if hasattr(item.GetWindow(),"custombutton"):
                allcbs += [(ubs,item.GetWindow())]
        for item in cs.GetChildren():
            if hasattr(item.GetWindow(),"custombutton"):
                allcbs += [(cs,item.GetWindow())]
        for sizer,button in allcbs:
            #sizer.Remove(button)
            button.Destroy()
        self.custombuttonbuttons=[]
        newbuttonbuttonindex = len(self.custombuttons)
        while newbuttonbuttonindex>0 and self.custombuttons[newbuttonbuttonindex-1] is None:
            newbuttonbuttonindex -= 1
        while len(self.custombuttons) < 13:
            self.custombuttons.append(None)
        for i in xrange(len(self.custombuttons)):
            btndef = self.custombuttons[i]
            try:
                b=wx.Button(self.panel,-1,btndef[0])
                b.SetToolTip(wx.ToolTip(_("Execute command: ")+btndef[1]))
                if len(btndef)>2:
                    b.SetBackgroundColour(btndef[2])
                    rr,gg,bb=b.GetBackgroundColour().Get()
                    if 0.3*rr+0.59*gg+0.11*bb < 60:
                        b.SetForegroundColour("#ffffff")
            except:
                if i == newbuttonbuttonindex:
                    print("no need for new custom button!")
                    #self.newbuttonbutton=b=wx.Button(self.panel,-1,"+",size=(19,18))
                    #b.SetFont(wx.Font(12,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD))
                    #b.SetForegroundColour("#4444ff")
                    #b.SetToolTip(wx.ToolTip(_("click to add new custom button")))
                    #b.Bind(wx.EVT_BUTTON,self.cbutton_edit)
                else:
                    continue
            #b.custombutton=i
            #b.properties=btndef
            if btndef is not None:
                b.Bind(wx.EVT_BUTTON,self.procbutton)
                b.Bind(wx.EVT_MOUSE_EVENTS,self.editbutton)
            #else:
            #    b.Bind(wx.EVT_BUTTON,lambda e:e.Skip())
            #self.custombuttonbuttons.append(b)
            #if i<4:
            #    ubs.Add(b)
            #else:
            #    cs.Add(b,pos=((i-4)/3,(i-4)%3))
        self.topsizer.Layout()

    def help_button(self):
        print _('Defines custom button. Usage: button <num> "title" [/c "colour"] command')

    def do_button(self,argstr):
        def nextarg(rest):
            rest=rest.lstrip()
            if rest.startswith('"'):
               return rest[1:].split('"',1)
            else:
               return rest.split(None,1)
        #try:
        num,argstr=nextarg(argstr)
        num=int(num)
        title,argstr=nextarg(argstr)
        colour=None
        try:
            c1,c2=nextarg(argstr)
            if c1=="/c":
                colour,argstr=nextarg(c2)
        except:
            pass
        command=argstr.strip()
        if num<0 or num>=64:
            print _("Custom button number should be between 0 and 63")
            return
        while num >= len(self.custombuttons):
            self.custombuttons+=[None]
        self.custombuttons[num]=[title,command]
        if colour is not None:
            self.custombuttons[num]+=[colour]
        if not self.processing_rc:
            self.cbuttons_reload()
        #except Exception,x:
        #    print "Bad syntax for button definition, see 'help button'"
        #    print x


    def cbutton_save(self,n,bdef,new_n=None):
        if new_n is None: new_n=n
        if bdef is None or bdef == "":
            self.save_in_rc(("button %d" % n),'')
        elif len(bdef)>2:
            colour=bdef[2]
            if type(colour) not in (str,unicode):
                #print type(colour),map(type,colour)
                if type(colour)==tuple and tuple(map(type,colour))==(int,int,int):
                    colour = map(lambda x:x%256,colour)
                    colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                else:
                    colour = wx.Colour(colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
            self.save_in_rc(("button %d" % n),'button %d "%s" /c "%s" %s' % (new_n,bdef[0],colour,bdef[1]))
        else:
            self.save_in_rc(("button %d" % n),'button %d "%s" %s' % (new_n,bdef[0],bdef[1]))

    def cbutton_edit(self,e,button=None):
        bedit=ButtonEdit(self)
        def okhandler(event):
            if event.GetId()==wx.ID_OK:
                if n==len(self.custombuttons):
                    self.custombuttons+=[None]
                self.custombuttons[n]=[bedit.name.GetValue().strip(),bedit.command.GetValue().strip()]
                if bedit.color.GetValue().strip()!="":
                    self.custombuttons[n]+=[bedit.color.GetValue()]
                self.cbutton_save(n,self.custombuttons[n])
            bedit.Destroy()
            self.cbuttons_reload()

        bedit.Bind(wx.EVT_BUTTON,okhandler)
        if button is not None:
            n = button.custombutton
            bedit.name.SetValue(button.properties[0])
            bedit.command.SetValue(button.properties[1])
            if len(button.properties)>2:
                colour=button.properties[2]
                if type(colour) not in (str,unicode):
                    #print type(colour)
                    if type(colour)==tuple and tuple(map(type,colour))==(int,int,int):
                        colour = map(lambda x:x%256,colour)
                        colour = wx.Colour(*colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                    else:
                        colour = wx.Colour(colour).GetAsString(wx.C2S_NAME|wx.C2S_HTML_SYNTAX)
                bedit.color.SetValue(colour)
        else:
            n = len(self.custombuttons)
            while n>0 and self.custombuttons[n-1] is None:
                n -= 1
        bedit.Show()
        
        
    def cbutton_remove(self,e,button):
        n = button.custombutton
        self.custombuttons[n]=None
        self.cbutton_save(n,None)
        #while len(self.custombuttons) and self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        wx.CallAfter(self.cbuttons_reload)

    def cbutton_order(self,e,button,dir):
        n = button.custombutton
        if dir<0:
            n=n-1
        if n+1 >= len(self.custombuttons):
            self.custombuttons+=[None] # pad
        # swap
        self.custombuttons[n],self.custombuttons[n+1] = self.custombuttons[n+1],self.custombuttons[n]
        self.cbutton_save(n,self.custombuttons[n])
        self.cbutton_save(n+1,self.custombuttons[n+1])
        #if self.custombuttons[-1] is None:
        #    del self.custombuttons[-1]
        self.cbuttons_reload()

    def editbutton(self,e):
        if e.IsCommandEvent() or e.ButtonUp(wx.MOUSE_BTN_RIGHT):
            if e.IsCommandEvent():
                pos = (0,0)
            else:
                pos = e.GetPosition()
            popupmenu = wx.Menu()
            obj = e.GetEventObject()
            if hasattr(obj,"custombutton"):
                item = popupmenu.Append(-1,_("Edit custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_edit(e,button),item)
                item = popupmenu.Append(-1,_("Move left <<"))
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_order(e,button,-1),item)
                if obj.custombutton == 0: item.Enable(False)
                item = popupmenu.Append(-1,_("Move right >>"))
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_order(e,button,1),item)
                if obj.custombutton == 63: item.Enable(False)
                pos = self.panel.ScreenToClient(e.GetEventObject().ClientToScreen(pos))
                item = popupmenu.Append(-1,_("Remove custom button '%s'") % e.GetEventObject().GetLabelText())
                self.Bind(wx.EVT_MENU,lambda e,button=e.GetEventObject():self.cbutton_remove(e,button),item)
            #else:
                #item = popupmenu.Append(-1,_("Add custom button"))
                #self.Bind(wx.EVT_MENU,self.cbutton_edit,item) #justin: no custom button
            self.panel.PopupMenu(popupmenu, pos)
        elif e.Dragging() and e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            if not hasattr(self,"dragpos"):
                self.dragpos = scrpos
                e.Skip()
                return
            else:
                dx,dy=self.dragpos[0]-scrpos[0],self.dragpos[1]-scrpos[1]
                if dx*dx+dy*dy < 5*5: # threshold to detect dragging for jittery mice
                    e.Skip()
                    return
            if not hasattr(self,"dragging"):
                # init dragging of the custom button
                if hasattr(obj,"custombutton") and obj.properties is not None:
                    self.newbuttonbutton.SetLabel("")
                    self.newbuttonbutton.SetFont(wx.Font(10,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_NORMAL))
                    self.newbuttonbutton.SetForegroundColour("black")
                    self.newbuttonbutton.SetSize(obj.GetSize())
                    if self.upperbottomsizer.GetItem(self.newbuttonbutton) is not None:
                        self.upperbottomsizer.SetItemMinSize(self.newbuttonbutton,obj.GetSize())
                        self.topsizer.Layout()
                    self.dragging = wx.Button(self.panel,-1,obj.GetLabel())
                    self.dragging.SetBackgroundColour(obj.GetBackgroundColour())
                    self.dragging.SetForegroundColour(obj.GetForegroundColour())
                    self.dragging.sourcebutton = obj
                    self.dragging.Raise()
                    self.dragging.Disable()
                    self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                    for b in self.custombuttonbuttons:
                        #if b.IsFrozen(): b.Thaw()
                        if b.properties is None:
                            b.Enable()
                        #    b.SetStyle(wx.ALIGN_CENTRE+wx.ST_NO_AUTORESIZE+wx.SIMPLE_BORDER)
                    self.last_drag_dest = obj
                    self.dragging.label = obj.s_label = obj.GetLabel()
                    self.dragging.bgc = obj.s_bgc = obj.GetBackgroundColour()
                    self.dragging.fgc = obj.s_fgc = obj.GetForegroundColour()
            else:
                # dragging in progress
                self.dragging.SetPosition(self.panel.ScreenToClient(scrpos))
                wx.CallAfter(self.dragging.Refresh)
                btns = self.custombuttonbuttons
                dst = None
                src = self.dragging.sourcebutton
                drg = self.dragging
                for b in self.custombuttonbuttons:
                    if b.GetScreenRect().Contains(scrpos):
                        dst = b
                        break
                #if dst is None and self.panel.GetScreenRect().Contains(scrpos):
                #    # try to check if it is after buttons at the end
                #    tspos = self.panel.ClientToScreen(self.upperbottomsizer.GetPosition())
                #    bspos = self.panel.ClientToScreen(self.centersizer.GetPosition())
                #    tsrect = wx.Rect(*(tspos.Get()+self.upperbottomsizer.GetSize().Get()))
                #    bsrect = wx.Rect(*(bspos.Get()+self.centersizer.GetSize().Get()))
                #    lbrect = btns[-1].GetScreenRect()
                #    p = scrpos.Get()
                #    if len(btns)<4 and tsrect.Contains(scrpos):
                #        if lbrect.GetRight() < p[0]:
                #            print "Right of last button on upper cb sizer"
                #    if bsrect.Contains(scrpos):
                #        if lbrect.GetBottom() < p[1]:
                #            print "Below last button on lower cb sizer"
                #        if lbrect.GetRight() < p[0] and lbrect.GetTop() <= p[1] and lbrect.GetBottom() >= p[1]:
                #            print "Right to last button on lower cb sizer"
                if dst is not self.last_drag_dest:
                    if self.last_drag_dest is not None:
                        self.last_drag_dest.SetBackgroundColour(self.last_drag_dest.s_bgc)
                        self.last_drag_dest.SetForegroundColour(self.last_drag_dest.s_fgc)
                        self.last_drag_dest.SetLabel(self.last_drag_dest.s_label)
                    if dst is not None and dst is not src:
                        dst.s_bgc = dst.GetBackgroundColour()
                        dst.s_fgc = dst.GetForegroundColour()
                        dst.s_label = dst.GetLabel()
                        src.SetBackgroundColour(dst.GetBackgroundColour())
                        src.SetForegroundColour(dst.GetForegroundColour())
                        src.SetLabel(dst.GetLabel())
                        dst.SetBackgroundColour(drg.bgc)
                        dst.SetForegroundColour(drg.fgc)
                        dst.SetLabel(drg.label)
                    else:
                        src.SetBackgroundColour(drg.bgc)
                        src.SetForegroundColour(drg.fgc)
                        src.SetLabel(drg.label)
                    self.last_drag_dest = dst
        elif hasattr(self,"dragging") and not e.ButtonIsDown(wx.MOUSE_BTN_LEFT):
            # dragging finished
            obj = e.GetEventObject()
            scrpos = obj.ClientToScreen(e.GetPosition())
            dst = None
            src = self.dragging.sourcebutton
            drg = self.dragging
            for b in self.custombuttonbuttons:
                if b.GetScreenRect().Contains(scrpos):
                    dst = b
                    break
            if dst is not None:
                src_i = src.custombutton
                dst_i = dst.custombutton
                self.custombuttons[src_i],self.custombuttons[dst_i] = self.custombuttons[dst_i],self.custombuttons[src_i]
                self.cbutton_save(src_i,self.custombuttons[src_i])
                self.cbutton_save(dst_i,self.custombuttons[dst_i])
                while self.custombuttons[-1] is None:
                    del self.custombuttons[-1]
            wx.CallAfter(self.dragging.Destroy)
            del self.dragging
            wx.CallAfter(self.cbuttons_reload)
            del self.last_drag_dest
            del self.dragpos
        else:
            e.Skip()

    def homeButtonClicked(self, corner):
        if corner == 0: # upper-left
            self.onecmd('home X')
        if corner == 1: # upper-right
            self.onecmd('home Y')
        if corner == 2: # lower-right
            self.onecmd('home Z')
        if corner == 3: # lower-left
            self.onecmd('home')

    def moveXYZ(self, x, y, z):
        if x != 0 and x != "h":
            self.onecmd('move X %s' % x)
            print("Moving X: " + x)
        if y != 0 and y != "h":
            self.onecmd('move Y %s' % y)
            print("Moving Y: " + y)
        if z != 0 and z != "h":
            self.onecmd('move Z %s' % z)
            print("Moving Z: " + z )
            
        if x == "h":
            self.onecmd('home X')
        if y == "h":
            self.onecmd('home Y')
        if z == "h":
            self.onecmd('home Z')
        #self.motorsoffbutton.SetBitmapLabel(wx.Bitmap('images/motor_2.png'))
    def moveZ(self, z):
        if z != 0:
            self.onecmd('move Z %s' % z)

    def procbutton(self,e):
        try:
            if hasattr(e.GetEventObject(),"custombutton"):
                if wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_ALT):
                    return self.editbutton(e)
                self.cur_button=e.GetEventObject().custombutton
            self.onecmd(e.GetEventObject().properties[1])
            self.cur_button=None
        except:
            print _("event object missing")
            self.cur_button=None
            raise

    def kill(self,e):
        self.statuscheck=0
        self.p.recvcb=None
        self.p.disconnect()
        if hasattr(self,"feedrates_changed"):
            self.save_in_rc("set xy_feedrate","set xy_feedrate %d" % self.settings.xy_feedrate)
            self.save_in_rc("set z_feedrate","set z_feedrate %d" % self.settings.z_feedrate)
            self.save_in_rc("set e_feedrate","set e_feedrate %d" % self.settings.e_feedrate)
        try:
            self.gwindow.Destroy()
        except:
            pass
        self.Destroy()

    def do_monitor(self,l=""):
        if l.strip()=="":
            self.monitorbox.SetValue(not self.monitorbox.GetValue())
        elif l.strip()=="off":
            wx.CallAfter(self.monitorbox.SetValue,False)
        else:
            try:
                self.monitor_interval=float(l)
                wx.CallAfter(self.monitorbox.SetValue,self.monitor_interval>0)
            except:
                print _("Invalid period given.")
        self.setmonitor(None)
        if self.monitor:
            print _("Monitoring printer.")
        else:
            print _("Done monitoring.")


    def setmonitor(self,e):
        
        if self.monitor == 1:
            self.monitor = 0
            print "Stopping Printer Temperature Monitor"
        else:
            self.monitor = 1
            print "Monitoring Printer Temperature"
        #self.monitor=self.monitorbox.GetValue()
        #if self.monitor:
        #    self.graph.StartPlotting(1000)
        #else:
        #    self.graph.StopPlotting()



    def sendline(self,e):
        command=self.commandbox.GetValue()
        if not len(command):
            return
        wx.CallAfter(self.logbox.AppendText,">>>"+command+"\n")
        self.onecmd(str(command))
        self.commandbox.SetSelection(0,len(command))
        
    def skeintest(self,e):
        value=self.testbox.GetValue()
        testcsv.makeHello(value)
        testcsv.destroyHello()
        
    def clearOutput(self,e):
        self.logbox.Clear()

    def statuschecker(self):#justin: I want to add a home thing here maybe?
        try:
            while(self.statuscheck):
                #dummy_log=wx.LogNull()
                if(self.initialhome != 1):
                    self.initialhome = self.initialhome+1
                elif(self.initialhome ==1 and self.p.online):
                    print _("Printer is now online.")
                    print _("Coordia Beta v0.1 by Tinkerine Studio")
                    print _("*As this is a beta version, we are not responsible for any damage (although highly unlikely) this program may cause your machine*")
                    self.initialhome = self.initialhome+1
                    for i in self.printerControls:
                        wx.CallAfter(i.Enable)
                    # Enable XYButtons and ZButtons
                    wx.CallAfter(self.xyb.enable)
                    #wx.CallAfter(self.zb.enable)
                    
                    #wx.CallAfter(self.motorsoffbtn.Enable)
                    if self.filename:
                        wx.CallAfter(self.printbtn.Enable)
                    self.stopbtn.Bind(wx.EVT_BUTTON,self.motorsoff)
                    self.stopbtn.Enable()
                    self.stopbtn.SetToolTipString(_("Turn Motors Off"))
                    self.stopbtn.SetBitmapLabel(wx.Bitmap('images/motors_1.png'))
                    if self.settings.home_on_start.lower() == "true" or self.settings.home_on_start.lower() == "1" :
                        self.onecmd('home X')
                        self.onecmd('home Y')
                string=""
                if(self.p.online):
                    string+=_("") #printer online
                try:
                    #string+=_("Loaded ")+os.path.split(self.filename)[1]+" "
                    filename = self.filename[int(findlastletterindex(self.filename,"\\")+1):] #MAC is "/" instead of "\\"
                    wx.CallAfter(self.filenametext.SetLabel," " + str(filename)) #justin: filename
                except:
                    pass
                #string+=(self.tempreport.replace("\r","").replace("T:",_("Hotend") + ":").replace("B:",_("Bed") + ":").replace("\n","").replace("ok ",""))+" "
                #print(findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",2)) #find the 2nd space 
                #print(countletters(self.tempreport.strip().replace("ok ",""), " ")) #find num of spaces 
                #dummy_log=wx.LogNull()
                if (countletters(self.tempreport.strip().replace("ok ",""), " ")) == 3: #find num of spaces 
                    #print("cool")
                    wx.CallAfter(self.tempdisp.SetLabel,self.tempreport.strip().replace("ok ","")[:findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",2)] + self.degree + " C") #justin: change to something i want later
                    wx.CallAfter(self.beddisp.SetLabel,self.tempreport.strip().replace("ok ","")[findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",2)+1:] + self.degree + " C") #justin: change to something i want later
                    targettemp = float(self.tempreport.strip().replace("ok ","")[findnthletterindex(self.tempreport.strip().replace("ok ",""), "/",1)+1:findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",2)])
                    #print targettemp
                    currenttemp = float(self.tempreport.strip().replace("ok ","")[findnthletterindex(self.tempreport.strip().replace("ok ",""), ":",1)+1:findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",1)]) #justin: change to something i want later
                    #print currenttemp
                    if targettemp > 0:
                        #self.tempstatus = 0
                        if currenttemp > targettemp-5:
                            self.tempstatus = 3
                            self.hotendlabel.SetBitmap(wx.Bitmap('images/hotend_3.png'))
                        else:
                            self.tempstatus = 2
                            self.hotendlabel.SetBitmap(wx.Bitmap('images/hotend_2.png'))
                    else:
                        self.tempstatus = 1
                        self.hotendlabel.SetBitmap(wx.Bitmap('images/hotend_1.png'))
                elif (countletters(self.tempreport.strip().replace("ok ",""), " ")) == 2: #find num of spaces 
                    self.hotendlabel.SetBitmap(wx.Bitmap('images/hotend_2.png'))
                    
                try:
                    #self.hottgauge.SetValue(float(filter(lambda x:x.startswith("T:"),self.tempreport.split())[0].split(":")[1]))
                    self.graph.SetExtruder0Temperature(float(filter(lambda x:x.startswith("T:"),self.tempreport.split())[0].split(":")[1]))
                    self.bedtgauge.SetValue(float(filter(lambda x:x.startswith("B:"),self.tempreport.split())[0].split(":")[1]))
                    self.graph.SetBedTemperature(float(filter(lambda x:x.startswith("B:"),self.tempreport.split())[0].split(":")[1]))
                except:
                    pass
                fractioncomplete = 0.0

                if self.sdprinting:
                    fractioncomplete = float(self.percentdone/100.0)
                    string+= _(" SD printing:%04.2f %%") % (self.percentdone,)
                if self.p.printing:
                    fractioncomplete = float(self.p.queueindex)/len(self.p.mainqueue)
                    #string+= _(" Printing:%04.2f %% |") % (100*float(self.p.queueindex)/len(self.p.mainqueue),)
                    string+= _(" Line# %d of %d lines |" ) % (self.p.queueindex, len(self.p.mainqueue))
                if fractioncomplete > 0.0:
                    secondselapsed = int(time.time()-self.starttime+self.extra_print_time)
                    secondsestimate = secondselapsed/fractioncomplete
                    secondsremain = secondsestimate - secondselapsed
                    string+= _(" Est: %s of %s remaining | ") % (time.strftime('%H:%M:%S', time.gmtime(secondsremain)),
                                                                 time.strftime('%H:%M:%S', time.gmtime(secondsestimate)))
                    string+= _(" Z: %0.2f mm") % self.curlayer
                main.fractioncomplete=fractioncomplete
                if fractioncomplete > 0:
                    wx.CallAfter(self.progresstext.SetLabel," %04.2f" % (fractioncomplete*100) +"%") #justin: progresss!
                #print(fractioncomplete)
                #print(main.fractioncomplete)
                wx.CallAfter(self.status.SetStatusText,string)
                wx.CallAfter(self.gviz.Refresh)
                wx.CallAfter(self.progressbar1.Refresh)
                if(self.monitor and self.p.online):
                    if self.sdprinting:
                        self.p.send_now("M27")
                    if not hasattr(self,"auto_monitor_pattern"):
                        self.auto_monitor_pattern = re.compile(r"(ok\s+)?T:[\d\.]+(\s+B:[\d\.]+)?(\s+@:[\d\.]+)?\s*")
                    self.capture_skip[self.auto_monitor_pattern]=self.capture_skip.setdefault(self.auto_monitor_pattern,0)+1
                    self.p.send_now("M105")
                time.sleep(self.monitor_interval)
                while not self.sentlines.empty():
                    try:
                        gc=self.sentlines.get_nowait()
                        wx.CallAfter(self.gviz.addgcode,gc,1)
                    except:
                        break
                #print("check temp")
                #print(self.tempreport.strip().replace("ok ","")[findnthletterindex(self.tempreport.strip().replace("ok ",""), "/",1)+1:findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",2)]) #justin: change to something i want later
                #print (countletters(self.tempreport.strip().replace("ok ",""), " "))

                    #print self.tempstatus    
            wx.CallAfter(self.status.SetStatusText,_("Not connected to printer."))
        except:
            pass #if window has been closed
    def capture(self, func, *args, **kwargs):
        stdout=sys.stdout
        cout=None
        try:
            cout=self.cout
        except:
            pass
        if cout is None:
            cout=cStringIO.StringIO()

        sys.stdout=cout
        retval=None
        try:
            retval=func(*args,**kwargs)
        except:
            traceback.print_exc()
        sys.stdout=stdout
        return retval

    def recvcb(self,l):
        if "T:" in l:
            self.tempreport=l
            if (countletters(self.tempreport.strip().replace("ok ",""), " ")) == 2: #find num of spaces 
                #print("nice")
                wx.CallAfter(self.tempdisp.SetLabel,self.tempreport.strip().replace("ok ","")[:findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",1)] + self.degree + " C") #justin: change to something i want later
                wx.CallAfter(self.beddisp.SetLabel,self.tempreport.strip().replace("ok ","")[findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",1)+1:findnthletterindex(self.tempreport.strip().replace("ok ",""), " ",2)] + self.degree + " C") #justin: change to something i want later
            try:
                #self.hottgauge.SetValue(float(filter(lambda x:x.startswith("T:"),self.tempreport.split())[0].split(":")[1]))
                self.graph.SetExtruder0Temperature(float(filter(lambda x:x.startswith("T:"),self.tempreport.split())[0].split(":")[1]))
                self.graph.SetBedTemperature(float(filter(lambda x:x.startswith("B:"),self.tempreport.split())[0].split(":")[1]))
            except:
                pass
        tstring=l.rstrip()
        #print tstring
        if(tstring!="ok"):
            print tstring
            #wx.CallAfter(self.logbox.AppendText,tstring+"\n")
        for i in self.recvlisteners:
            i(l)

    def listfiles(self,line):
        if "Begin file list" in line:
            self.listing=1
        elif "End file list" in line:
            self.listing=0
            self.recvlisteners.remove(self.listfiles)
            wx.CallAfter(self.filesloaded)
        elif self.listing:
            self.sdfiles+=[line.replace("\n","").replace("\r","").lower()]

    def waitforsdresponse(self,l):
        if "file.open failed" in l:
            wx.CallAfter(self.status.SetStatusText,_("Opening file failed."))
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.status.SetStatusText,l)
        if "File selected" in l:
            wx.CallAfter(self.status.SetStatusText,_("Starting print"))
            self.sdprinting=1
            self.p.send_now("M24")
            self.startcb()
            return
        if "Done printing file" in l:
            wx.CallAfter(self.status.SetStatusText,l)
            self.sdprinting=0
            self.recvlisteners.remove(self.waitforsdresponse)
            self.endcb()
            return
        if "SD printing byte" in l:
            #M27 handler
            try:
                resp=l.split()
                vals=resp[-1].split("/")
                self.percentdone=100.0*int(vals[0])/int(vals[1])
            except:
                pass



    def filesloaded(self):
        dlg=wx.SingleChoiceDialog(self, _("Select the file to print"), _("Pick SD file"), self.sdfiles)
        if(dlg.ShowModal()==wx.ID_OK):
            target=dlg.GetStringSelection()
            if len(target):
                self.recvlisteners+=[self.waitforsdresponse]
                self.p.send_now("M23 "+target.lower())

        #print self.sdfiles
        pass

    def getfiles(self):
        if not self.p.online:
            self.sdfiles=[]
            return
        self.listing=0
        self.sdfiles=[]
        self.recvlisteners+=[self.listfiles]
        self.p.send_now("M21")
        self.p.send_now("M20")

    def skein_func(self):
        try:
            import shlex
            param = self.expandcommand(self.settings.slicecommand).encode()
            print param
            print "Slicing: ",param
            pararray=[i.replace("$s",self.filename).replace("$o",self.filename.replace(".stl","_export.gcode").replace(".STL","_export.gcode")).encode() for i in shlex.split(param.replace("\\","\\\\").encode())]
                #print pararray
            self.skeinp=subprocess.Popen(pararray,stderr=subprocess.STDOUT,stdout=subprocess.PIPE)
            while True:
                o = self.skeinp.stdout.read(1)
                if o == '' and self.skeinp.poll() != None: break
                sys.stdout.write(o)
            self.skeinp.wait()
            self.stopsf=1
        except:
            print _("Failed to execute slicing software: ")
            self.stopsf=1
            traceback.print_exc(file=sys.stdout)

    def skein_monitor(self):
        while(not self.stopsf):
            try:
                wx.CallAfter(self.status.SetStatusText,_("Slicing..."))#+self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn=self.filename
        try:
            self.filename=self.filename.replace(".stl","_export.gcode").replace(".STL","_export.gcode").replace(".obj","_export.gcode").replace(".OBJ","_export.gcode")
            of=open(self.filename)
            self.f=[i.replace("\n","").replace("\r","") for i in of]
            of.close
            if self.p.online:
                #print "ASDF"
                wx.CallAfter(self.printbtn.Enable)
                wx.CallAfter(self.stopbtn.Enable)
            wx.CallAfter(self.status.SetStatusText,_("Loaded ")+self.filename+_(", %d lines") % (len(self.f),))
            #wx.CallAfter(self.pausebtn.Disable)
            #wx.CallAfter(self.printbtn.SetLabel,_("Print"))

            threading.Thread(target=self.loadviz).start()
        except:
            self.filename=fn
        wx.CallAfter(self.loadbtn.SetLabel,_("Load File"))
        self.skeining=0
        self.skeinp=None


    def skein(self,filename):
        wx.CallAfter(self.loadbtn.SetLabel,_("Cancel"))
        print _("Slicing ") + filename
        self.cout=StringIO.StringIO()
        self.filename=filename
        self.stopsf=0
        self.skeining=1
        thread(target=self.skein_func).start()
        thread(target=self.skein_monitor).start()

    def loadfile(self,event,filename=None):
        if self.skeining and self.skeinp is not None:
            self.skeinp.terminate()
            return
        basedir=self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir=os.path.split(self.filename)[0]
            except:
                pass
        dlg=wx.FileDialog(self,_("Open file to print"),basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        #dlg.SetWildcard(_("OBJ, STL, and GCODE files (*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ)|*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ|All Files (*.*)|*.*"))
        dlg.SetWildcard(_("STL files (*.stl;)|*.stl|OBJ files (*.obj;)|*.obj|All Files (*.*)|*.*")) #justin: only gcode!
        if(filename is not None or dlg.ShowModal() == wx.ID_OK):
            if filename is not None:
                name=filename
            else:
                name=dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText(_("File not found!"))
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path",path)
            if name.lower().endswith(".stl"):
                self.skein(name)
            elif name.lower().endswith(".obj"):
                self.skein(name)
            else:
                self.filename=name
                of=open(self.filename)
                self.f=[i.replace("\n","").replace("\r","") for i in of]
                of.close
                self.status.SetStatusText(_("Loaded %s, %d lines") % (name, len(self.f)))
                #wx.CallAfter(self.printbtn.SetLabel, _("Print"))
                #wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                #wx.CallAfter(self.pausebtn.Disable)
                if self.p.online:
                    wx.CallAfter(self.printbtn.Enable)
                    wx.CallAfter(self.stopbtn.Enable)
                threading.Thread(target=self.loadviz).start()
        dlg.Destroy()
        
    def loadfile2(self,event,filename=None):
        if self.skeining and self.skeinp is not None:
            self.skeinp.terminate()
            return
        basedir=self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir=os.path.split(self.filename)[0]
            except:
                pass
        dlg=wx.FileDialog(self,_("Open file to print"),basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        #dlg.SetWildcard(_("OBJ, STL, and GCODE files (*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ)|*.gcode;*.gco;*.g;*.stl;*.STL;*.obj;*.OBJ|All Files (*.*)|*.*"))
        dlg.SetWildcard(_("GCODE files (*.gcode;*.gco;*.g;)|*.gcode;*.gco;*.g|All Files (*.*)|*.*")) #justin: only gcode!
        if(filename is not None or dlg.ShowModal() == wx.ID_OK):
            if filename is not None:
                name=filename
            else:
                name=dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText(_("File not found!"))
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path",path)
            if name.lower().endswith(".stl"):
                self.skein(name)
            elif name.lower().endswith(".obj"):
                self.skein(name)
            else:
                self.filename=name
                of=open(self.filename)
                self.f=[i.replace("\n","").replace("\r","") for i in of]
                of.close
                self.status.SetStatusText(_("Loaded %s, %d lines") % (name, len(self.f)))
                #wx.CallAfter(self.printbtn.SetLabel, _("Print"))
                #wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                #wx.CallAfter(self.pausebtn.Disable)
                if self.p.online:
                    wx.CallAfter(self.printbtn.Enable)
                    wx.CallAfter(self.stopbtn.Enable)
                threading.Thread(target=self.loadviz).start()
        dlg.Destroy()
        
    def loadviz(self):
        Xtot,Ytot,Ztot,Xmin,Xmax,Ymin,Ymax,Zmin,Zmax = pronsole.measurements(self.f)
        print pronsole.totalelength(self.f), _("mm of filament used in this print\n")
        print _("the print goes from %f mm to %f mm in X\nand is %f mm wide\n") % (Xmin, Xmax, Xtot)
        print _("the print goes from %f mm to %f mm in Y\nand is %f mm wide\n") % (Ymin, Ymax, Ytot)
        print _("the print goes from %f mm to %f mm in Z\nand is %f mm high\n") % (Zmin, Zmax, Ztot)
        print _("Estimated duration (pessimistic): "), pronsole.estimate_duration(self.f)
        #import time
        #t0=time.time()
        self.gviz.clear()
        self.gwindow.p.clear()
        self.gviz.addfile(self.f)
        #print "generated 2d view in %f s"%(time.time()-t0)
        #t0=time.time()
        self.gwindow.p.addfile(self.f)
        #print "generated 3d view in %f s"%(time.time()-t0)
        self.gviz.showall=1
        wx.CallAfter(self.gviz.Refresh)

    def motorsoff(self,event):
        self.p.send_now("M84")
        print("Turning Motors Off")
		
    def stopprint(self,event): 
        self.p.send_now("M0")
        print("Stopped Print")
		
    def homexaxis(self,event):
        self.onecmd('home X')
        
    def homeyaxis(self,event): 
        self.onecmd('home Y')
		
    def homezaxis(self,event):
        self.onecmd('home Z')
		
    def homeallaxis(self,event):
        self.onecmd('home')
		
    def printfile(self,event):
        self.extra_print_time=0
        if self.paused:
            self.p.paused=0
            self.paused=0
            self.on_startprint()
            if self.sdprinting:
                self.p.send_now("M26 S0")
                self.p.send_now("M24")
                return

        if self.f is None or not len(self.f):
            wx.CallAfter(self.status.SetStatusText, _("No file loaded. Please use load first."))
            return
        if not self.p.online:
            wx.CallAfter(self.status.SetStatusText,_("Not connected to printer."))
            return
        self.on_startprint()
        self.p.startprint(self.f)

    def on_startprint(self):
        #wx.CallAfter(self.printbtn.SetLabel, _("Pause"))
        #wx.CallAfter(self.pausebtn.Enable)
        #wx.CallAfter(self.printbtn.SetLabel, _("Restart"))
        #wx.CallAfter(self.printbtn.SetLabel, _("Printttt"))
        self.printbtn.SetBitmapLabel(wx.Bitmap('images/pause_2.png'))
        self.printbtn.Bind(wx.EVT_BUTTON,self.pause)
        self.printbtn.SetToolTipString(_("Pause Print"))
        self.stopbtn.SetBitmapLabel(wx.Bitmap('images/stop_2.png'))
        self.stopbtn.Bind(wx.EVT_BUTTON,self.reset)
        self.stopbtn.SetToolTipString(_("Stop Print"))
        wx.CallAfter(self.stopbtn.Enable)

    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.status.SetStatusText, _("File upload complete"))
        time.sleep(0.5)
        self.p.clear=True
        self.uploading=False

    def uploadtrigger(self,l):
        if "Writing to file" in l:
            self.uploading=True
            self.p.startprint(self.f)
            self.p.endcb=self.endupload
            self.recvlisteners.remove(self.uploadtrigger)
        elif "open failed, File" in l:
            self.recvlisteners.remove(self.uploadtrigger)

    def upload(self,event):
        if not self.f or not len(self.f):
            return
        if not self.p.online:
            return
        dlg=wx.TextEntryDialog(self, ("Enter a target filename in 8.3 format:"), _("Pick SD filename") ,dosify(self.filename))
        if dlg.ShowModal()==wx.ID_OK:
            self.p.send_now("M21")
            self.p.send_now("M28 "+str(dlg.GetValue()))
            self.recvlisteners+=[self.uploadtrigger]
        pass

    def pause(self,event):
        print _("Pausing...")
        if not self.paused:
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if(not self.p.printing):
                    #print "Not printing, cannot pause."
                    return
                self.p.pause()
            self.printbtn.SetBitmapLabel(wx.Bitmap('images/resume_3.png'))
            self.printbtn.SetToolTipString(_("Resume Print"))
            self.paused=True
            self.extra_print_time += int(time.time() - self.starttime)
            #wx.CallAfter(self.pausebtn.SetLabel, _("Resume"))
        else:
            self.printbtn.SetBitmapLabel(wx.Bitmap('images/pause_2.png'))
            self.printbtn.SetToolTipString(_("Pause Print"))
            self.paused=False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            #wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))


    def sdprintfile(self,event):
        self.on_startprint()
        threading.Thread(target=self.getfiles).start()
        pass

    def connect(self,event):
        print _("Connecting...")
        port=None
        try:
            port=self.scanserial()[0]
        except:
            pass
        if self.serialport.GetValue()!="":
            port=str(self.serialport.GetValue())
        baud=250000
        try:
            baud=int(self.baud.GetValue())
        except:
            pass
        if self.paused:
            self.p.paused=0
            self.p.printing=0
            #wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            #wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.paused=0
            if self.sdprinting:
                self.p.send_now("M26 S0")
        self.p.connect(port,baud)
        self.statuscheck=True
        if port != self.settings.port:
            self.set("port",port)
        if baud != self.settings.baudrate:
            self.set("baudrate",str(baud))
        threading.Thread(target=self.statuschecker).start()


    def disconnect(self,event):
        print _("Disconnected.")
        self.p.disconnect()
        self.statuscheck=False
        self.connectbtn.SetBitmapLabel(wx.Bitmap('images/connect_3.png'))
        self.connectbtn.SetToolTipString(_("Connect to the printer"))
        self.connectbtn.SetLabel("Connect")
        self.connectbtn.Bind(wx.EVT_BUTTON,self.connect)
        self.initialhome = 0
        wx.CallAfter(self.printbtn.Disable);
        wx.CallAfter(self.stopbtn.Disable);
        self.stopbtn.SetBitmapLabel(wx.Bitmap('images/motors_4.png'))

        #wx.CallAfter(self.pausebtn.Disable);
        for i in self.printerControls:
            wx.CallAfter(i.Disable)

        # Disable XYButtons and ZButtons
        wx.CallAfter(self.xyb.disable)
        #wx.CallAfter(self.zb.disable)

        if self.paused:
            self.p.paused=0
            self.p.printing=0
            #wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
            #wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.paused=0
            if self.sdprinting:
                self.p.send_now("M26 S0")


    def reset(self,event):
        dlg=wx.MessageDialog(self, _("Are you sure you want to stop the print?"), _("Stop?"), wx.YES|wx.NO)
        if dlg.ShowModal()==wx.ID_YES:
            self.p.send_now("M84")
            self.p.reset()
            print _("Stopping print...")
            self.p.printing=0
            #wx.CallAfter(self.printbtn.SetLabel, _("Print"))
            self.printbtn.SetBitmapLabel(wx.Bitmap('images/print_3.png'))
            self.printbtn.SetToolTipString(_("Start Print"))
            self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
            #self.stopbtn.Disable()
            self.stopbtn.SetToolTipString(_("Turn MotorsOff"))
            self.stopbtn.SetBitmapLabel(wx.Bitmap('images/motors_1.png'))
            self.stopbtn.Bind(wx.EVT_BUTTON,self.motorsoff)
            self.do_settemp("off")

            if self.paused:
                self.p.paused=0
                #wx.CallAfter(self.pausebtn.SetLabel, _("Pause"))
                self.paused=0

    def get_build_dimensions(self,bdim):
        import re
        # a string containing up to six numbers delimited by almost anything
        # first 0-3 numbers specify the build volume, no sign, always positive
        # remaining 0-3 numbers specify the coordinates of the "southwest" corner of the build platform
        # "XXX,YYY"
        # "XXXxYYY+xxx-yyy"
        # "XXX,YYY,ZZZ+xxx+yyy-zzz"
        # etc
        bdl = re.match(
        "[^\d+-]*(\d+)?" + # X build size
        "[^\d+-]*(\d+)?" + # Y build size
        "[^\d+-]*(\d+)?" + # Z build size
        "[^\d+-]*([+-]\d+)?" + # X corner coordinate
        "[^\d+-]*([+-]\d+)?" + # Y corner coordinate
        "[^\d+-]*([+-]\d+)?"   # Z corner coordinate
        ,bdim).groups()
        defaults = [200, 200, 100, 0, 0, 0]
        bdl_float = [float(value) if value else defaults[i] for i, value in enumerate(bdl)]
        return bdl_float

class macroed(wx.Dialog):
    """Really simple editor to edit macro definitions"""
    def __init__(self,macro_name,definition,callback,gcode=False):
        self.indent_chars = "  "
        title="  macro %s"
        if gcode:
            title="  %s"
        self.gcode=gcode
        wx.Dialog.__init__(self,None,title=title % macro_name,style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.callback = callback
        self.panel=wx.Panel(self,-1)
        
        titlesizer=wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(self.panel,-1,title%macro_name)
        #title.SetFont(wx.Font(11,wx.NORMAL,wx.NORMAL,wx.BOLD))
        titlesizer.Add(title,1)
        self.okb = wx.Button(self.panel, -1, _("Save"))
        self.okb.Bind(wx.EVT_BUTTON, self.save)
        self.Bind(wx.EVT_CLOSE, self.close)
        titlesizer.Add(self.okb)
        self.cancelb = wx.Button(self.panel, -1, _("Cancel"))
        self.cancelb.Bind(wx.EVT_BUTTON, self.close)
        titlesizer.Add(self.cancelb)
        topsizer=wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(titlesizer,0,wx.EXPAND)
        self.e=wx.TextCtrl(self.panel,style=wx.TE_MULTILINE+wx.HSCROLL,size=(200,200))
        if not self.gcode:
            self.e.SetValue(self.unindent(definition))
        else:
            self.e.SetValue("\n".join(definition))
        topsizer.Add(self.e,1,wx.ALL+wx.EXPAND)
        self.panel.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        self.Show()
        self.e.SetFocus()
        
    def save(self,ev):
        self.Destroy()
        if not self.gcode:
            self.callback(self.reindent(self.e.GetValue()))
        else:
            self.callback(self.e.GetValue().split("\n"))
    def close(self,ev):
        self.Destroy()
    def unindent(self,text):
        self.indent_chars = text[:len(text)-len(text.lstrip())]
        if len(self.indent_chars)==0:
            self.indent_chars="  "
        unindented = ""
        lines = re.split(r"(?:\r\n?|\n)",text)
        #print lines
        if len(lines) <= 1:
            return text
        for line in lines:
            if line.startswith(self.indent_chars):
                unindented += line[len(self.indent_chars):] + "\n"
            else:
                unindented += line + "\n"
        return unindented
    def reindent(self,text):
        lines = re.split(r"(?:\r\n?|\n)",text)
        if len(lines) <= 1:
            return text
        reindented = ""
        for line in lines:
            if line.strip() != "":
                reindented += self.indent_chars + line + "\n"
        return reindented

class options(wx.Dialog):
    """Options editor"""
    def __init__(self,pronterface):
        wx.Dialog.__init__(self, None, title=_("Edit settings"), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        topsizer=wx.BoxSizer(wx.VERTICAL)
        vbox=wx.StaticBoxSizer(wx.StaticBox(self, label=_("Defaults")) ,wx.VERTICAL)
        topsizer.Add(vbox,1,wx.ALL+wx.EXPAND)
        grid=wx.FlexGridSizer(rows=0,cols=2,hgap=8,vgap=2)
        grid.SetFlexibleDirection( wx.BOTH )
        grid.AddGrowableCol( 1 )
        grid.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
        vbox.Add(grid,0,wx.EXPAND)
        ctrls = {}
        for k,v in sorted(pronterface.settings._all_settings().items()):
            ctrls[k,0] = wx.StaticText(self,-1,k)
            ctrls[k,1] = wx.TextCtrl(self,-1,str(v))
            if k in pronterface.helpdict:
                ctrls[k,0].SetToolTipString(pronterface.helpdict.get(k))
                ctrls[k,1].SetToolTipString(pronterface.helpdict.get(k))
            grid.Add(ctrls[k,0],0,wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.ALIGN_RIGHT)
            grid.Add(ctrls[k,1],1,wx.ALIGN_CENTER_VERTICAL|wx.ALL|wx.EXPAND)
        topsizer.Add(self.CreateSeparatedButtonSizer(wx.OK+wx.CANCEL),0,wx.EXPAND)
        self.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        if self.ShowModal()==wx.ID_OK:
            for k,v in pronterface.settings._all_settings().items():
                if ctrls[k,1].GetValue() != str(v):
                    pronterface.set(k,str(ctrls[k,1].GetValue()))
        self.Destroy()
        
class ButtonEdit(wx.Dialog):
    """Custom button edit dialog"""
    def __init__(self,pronterface):
        wx.Dialog.__init__(self, None, title=_("Custom button"),style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.pronterface=pronterface
        topsizer=wx.BoxSizer(wx.VERTICAL)
        grid=wx.FlexGridSizer(rows=0,cols=2,hgap=4,vgap=2)
        grid.AddGrowableCol(1,1)
        grid.Add(wx.StaticText(self,-1, _("Button title")), 0, wx.BOTTOM|wx.RIGHT)
        self.name=wx.TextCtrl(self,-1,"")
        grid.Add(self.name,1,wx.EXPAND)
        grid.Add(wx.StaticText(self, -1, _("Command")), 0, wx.BOTTOM|wx.RIGHT)
        self.command=wx.TextCtrl(self,-1,"")
        xbox=wx.BoxSizer(wx.HORIZONTAL)
        xbox.Add(self.command,1,wx.EXPAND)
        self.command.Bind(wx.EVT_TEXT,self.macrob_enabler)
        self.macrob=wx.Button(self,-1,"..",style=wx.BU_EXACTFIT)
        self.macrob.Bind(wx.EVT_BUTTON,self.macrob_handler)
        xbox.Add(self.macrob,0)
        grid.Add(xbox,1,wx.EXPAND)
        grid.Add(wx.StaticText(self,-1, _("Color")),0,wx.BOTTOM|wx.RIGHT)
        self.color=wx.TextCtrl(self,-1,"")
        grid.Add(self.color,1,wx.EXPAND)
        topsizer.Add(grid,0,wx.EXPAND)
        topsizer.Add( (0,0),1)
        topsizer.Add(self.CreateStdDialogButtonSizer(wx.OK|wx.CANCEL),0,wx.ALIGN_CENTER)
        self.SetSizer(topsizer)
        self.handler=None
    
    def macrob_enabler(self,e):
        macro = self.command.GetValue()
        valid = False
        if macro == "":
            valid = True
        elif self.pronterface.macros.has_key(macro):
            valid = True
        elif hasattr(self.pronterface.__class__,"do_"+macro):
            valid = False
        elif len([c for c in macro if not c.isalnum() and c != "_"]):
            valid = False
        else:
            valid = True
        self.macrob.Enable(valid)
    def macrob_handler(self,e):
        macro = self.command.GetValue()
        macro = self.pronterface.edit_macro(macro)
        self.command.SetValue(macro)
        if self.name.GetValue()=="":
            self.name.SetValue(macro)

class TempGauge(wx.Panel):
    def __init__(self,parent,size=(200,22),title="",maxval=240,gaugeColour=None):
        wx.Panel.__init__(self,parent,-1,size=size)
        self.Bind(wx.EVT_PAINT,self.paint)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.width,self.height=size
        self.title=title
        self.max=maxval
        self.gaugeColour=gaugeColour
        self.value=0
        self.setpoint=0
        self.recalc()
    def recalc(self):
        mmax=max(int(self.setpoint*1.05),self.max)
        self.scale=float(self.width-2)/float(mmax)
        self.ypt=max(16,int(self.scale*max(self.setpoint,self.max/6)))
    def SetValue(self,value):
        self.value=value
        wx.CallAfter(self.Refresh)
    def SetTarget(self,value):
        self.setpoint=value
        self.recalc()
        wx.CallAfter(self.Refresh)
    def interpolatedColour(self,val,vmin,vmid,vmax,cmin,cmid,cmax):
        if val < vmin: return cmin
        if val > vmax: return cmax
        if val <= vmid:
            lo,hi,val,valhi = cmin,cmid,val-vmin,vmid-vmin
        else:
            lo,hi,val,valhi = cmid,cmax,val-vmid,vmax-vmid
        vv = float(val)/valhi
        rgb=lo.Red()+(hi.Red()-lo.Red())*vv,lo.Green()+(hi.Green()-lo.Green())*vv,lo.Blue()+(hi.Blue()-lo.Blue())*vv
        rgb=map(lambda x:x*0.8,rgb)
        return wx.Colour(*map(int,rgb))
	
    def paint(self,ev):
        x0,y0,x1,y1,xE,yE = 1,1,self.ypt+1,1,self.width+1-2,20
        dc=wx.PaintDC(self)
        dc.SetBackground(wx.Brush((255,255,255)))
        dc.Clear()
        print("sdfsdf")

        cold,medium,hot = wx.Colour(0,167,223),wx.Colour(239,233,119),wx.Colour(210,50.100)
        gauge1,gauge2 = wx.Colour(255,255,210),(self.gaugeColour or wx.Colour(234,82,0))
        shadow1,shadow2 = wx.Colour(110,110,110),wx.Colour(255,255,255)
        gc = wx.GraphicsContext.Create(dc)
        
        #bmp1 = wx.Bitmap("images/Background.png")
        #dc.DrawBitmap(bmp1, 0, 0,1) 
        
        # draw shadow first
        # corners
        gc.SetBrush(gc.CreateRadialGradientBrush(xE-7,9,xE-7,9,8,shadow1,shadow2))
        gc.DrawRectangle(xE-7,1,8,8)
        gc.SetBrush(gc.CreateRadialGradientBrush(xE-7,17,xE-7,17,8,shadow1,shadow2))
        gc.DrawRectangle(xE-7,17,8,8)
        gc.SetBrush(gc.CreateRadialGradientBrush(x0+6,17,x0+6,17,8,shadow1,shadow2))
        gc.DrawRectangle(0,17,x0+6,8)
        # edges
        gc.SetBrush(gc.CreateLinearGradientBrush(xE-13,0,xE-6,0,shadow1,shadow2))
        gc.DrawRectangle(xE-6,9,10,8)
        gc.SetBrush(gc.CreateLinearGradientBrush(x0,yE-2,x0,yE+5,shadow1,shadow2))
        gc.DrawRectangle(x0+6,yE-2,xE-12,7)
        # draw gauge background
        gc.SetBrush(gc.CreateLinearGradientBrush(x0,y0,x1+1,y1,cold,medium))
        gc.DrawRoundedRectangle(x0,y0,x1+4,yE,6)
        gc.SetBrush(gc.CreateLinearGradientBrush(x1-2,y1,xE,y1,medium,hot))
        gc.DrawRoundedRectangle(x1-2,y1,xE-x1,yE,6)
        # draw gauge
        width=12
        w1=y0+9-width/2
        w2=w1+width
        value=x0+max(10,min(self.width+1-2,int(self.value*self.scale)))
        #gc.SetBrush(gc.CreateLinearGradientBrush(x0,y0+3,x0,y0+15,gauge1,gauge2))
        #gc.SetBrush(gc.CreateLinearGradientBrush(0,3,0,15,wx.Colour(255,255,255),wx.Colour(255,90,32)))
        gc.SetBrush(gc.CreateLinearGradientBrush(x0,y0+3,x0,y0+15,gauge1,self.interpolatedColour(value,x0,x1,xE,cold,medium,hot)))
        val_path = gc.CreatePath()
        val_path.MoveToPoint(x0,w1)
        val_path.AddLineToPoint(value,w1)
        val_path.AddLineToPoint(value+2,w1+width/4)
        val_path.AddLineToPoint(value+2,w2-width/4)
        val_path.AddLineToPoint(value,w2)
        #val_path.AddLineToPoint(value-4,10)
        val_path.AddLineToPoint(x0,w2)
        gc.DrawPath(val_path)
        # draw setpoint markers
        setpoint=x0+max(10,int(self.setpoint*self.scale))
        gc.SetBrush(gc.CreateBrush(wx.Brush(wx.Colour(0,0,0))))
        setp_path = gc.CreatePath()
        setp_path.MoveToPoint(setpoint-4,y0)
        setp_path.AddLineToPoint(setpoint+4,y0)
        setp_path.AddLineToPoint(setpoint,y0+5)
        setp_path.MoveToPoint(setpoint-4,yE)
        setp_path.AddLineToPoint(setpoint+4,yE)
        setp_path.AddLineToPoint(setpoint,yE-5)
        gc.DrawPath(setp_path)
        # draw readout
        text=u"T\u00B0 %u/%u"%(self.value,self.setpoint)
        #gc.SetFont(gc.CreateFont(wx.Font(12,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD),wx.WHITE))
        #gc.DrawText(text,29,-2)
        gc.SetFont(gc.CreateFont(wx.Font(10,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD),wx.WHITE))
        gc.DrawText(self.title,x0+19,y0+4)
        gc.DrawText(text,      x0+133,y0+4)
        gc.SetFont(gc.CreateFont(wx.Font(10,wx.FONTFAMILY_DEFAULT,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)))
        gc.DrawText(self.title,x0+18,y0+3)
        gc.DrawText(text,      x0+132,y0+3)

class progressbar(wx.Panel):
    def __init__(self,parent,size=(111,111),title="",maxval=600):
        wx.Panel.__init__(self,parent,-1,size=size)
        self.Bind(wx.EVT_PAINT,self.repaint)
        self.width,self.height=size
        self.title=title
        self.max=maxval
		
    #def Refresh(self):
    #    wx.CallAfter(self.Refresh)
	
    def repaint(self,ev):
        dc=wx.PaintDC(self)
        dc.Clear()

        dc.SetPen(wx.Pen(wx.Colour(150,150,130)))
        dc.SetBrush(wx.Brush((222,222,222)))
        dc.SetDeviceOrigin(0, 0)
        dc.DrawRectangle(0,0,self.width,20) #justin: blue thing
        dc.SetPen(wx.Pen(wx.Colour(180,180,180)))
        dc.SetBrush(wx.Brush((175,220,115)))
        dc.DrawRectangle(0,0,self.width*(main.fractioncomplete),100)
        #print("fraction complete:")
        #print(main.fractioncomplete)
        #self.parent.SetStatusText("Layer "+str(self.layerindex +1)+" - Going Up - Z = "+str(self.layers[self.layerindex])+" mm",0)
        #print(main.curlayer) #justin: should try to not use main here
        #if main.curlayer:
        #    print("cool")
        #    dc.DrawRectangle(0,0,self.width/(main.fractioncomplete),100) #justin: green thing

def findlastletterindex(word, letter):
    lastfound = -1
    index = 0
    while index < len(word):
        if word[index] == letter:
            lastfound = index
        index = index + 1
    return lastfound
	
	
def findnthletterindex(word, letter, nth):
    numfound = 0
    index = 0
    while index < len(word):
        if word[index] == letter:
            numfound = numfound + 1
            if numfound == nth:
                return index
        index = index + 1
    return -1
	
def countletters(word, letter):
	numfound=0
	index=0
	while index<len(word):
		if word[index] == letter:
			numfound = numfound + 1
		index = index + 1
	return numfound
	

    
if __name__ == '__main__':
    app = wx.App(False)
    main = PronterWindow()
    main.Show()
    try:
        app.MainLoop()
    except:
        pass

