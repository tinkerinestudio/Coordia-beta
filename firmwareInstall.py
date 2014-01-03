from __future__ import absolute_import

import os, wx, threading, sys

from avr_isp import stk500v2
from avr_isp import ispBase
from avr_isp import intelHex

from util import machineCom
from util import profile
from util import resources

def getDefaultFirmware():
	if profile.getPreference('machine_type') == 'ultimaker':
		if profile.getPreferenceFloat('extruder_amount') > 1:
			return None
		if profile.getPreference('has_heated_bed') == 'True':
			return None
		if sys.platform.startswith('linux'):
			return resources.getPathForFirmware("ultimaker_115200.hex")
		else:
			return resources.getPathForFirmware("ultimaker_250000.hex")
	return None

class InstallFirmware(wx.Dialog):
	def __init__(self, filename = None, port = None):
		#super(InstallFirmware, self).__init__(parent=None, title="Firmware install", size=(250, 100))
		if port is None:
			port = profile.getPreference('serial_port')
		if filename is None:
			filename = getDefaultFirmware()
		if filename is None:
			wx.MessageBox('I am sorry, but Coordia does not ship with a default firmware for your machine configuration.', 'Firmware update', wx.OK | wx.ICON_ERROR)
			self.Destroy()
			return

		#sizer = wx.BoxSizer(wx.VERTICAL)
		
		#self.progressLabel = wx.StaticText(self, -1, 'Reading firmware...')
		#sizer.Add(self.progressLabel, 0, flag=wx.ALIGN_CENTER)
		#self.progressGauge = wx.Gauge(self, -1)
		#sizer.Add(self.progressGauge, 0, flag=wx.EXPAND)
		#self.okButton = wx.Button(self, -1, 'Ok')
		#self.okButton.Disable()
		#self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
		#sizer.Add(self.okButton, 0, flag=wx.ALIGN_CENTER)
		#self.SetSizer(sizer)
		
		self.filename = filename
		self.port = port
		
		threading.Thread(target=self.OnRun).start()
		
		#self.ShowModal()
		#self.Destroy()
		return

	def OnRun(self):
		hexFile = intelHex.readHex(self.filename)
		print "Connecting to machine."
		#wx.CallAfter(self.updateLabel, "Connecting to machine...")
		programmer = stk500v2.Stk500v2()
		#programmer.progressCallback = self.OnProgress
		if self.port == 'AUTO':
			for self.port in machineCom.serialList():
				try:
					programmer.connect(self.port)
					break
				except ispBase.IspError:
					pass
		else:
			try:
				programmer.connect(self.port)
			except ispBase.IspError:
				pass
				
		if programmer.isConnected():
			#wx.CallAfter(self.updateLabel, "Uploading firmware...")
			try:
				programmer.programChip(hexFile)
				print "Firmware successfully installed!"
				#wx.CallAfter(self.updateLabel, "Done!\nInstalled firmware: %s" % (os.path.basename(self.filename)))
			except ispBase.IspError as e:
				print "Failed to upload firmware."
				#wx.CallAfter(self.updateLabel, "Failed to write firmware.\n" + str(e))
				
			programmer.close()
			#wx.CallAfter(self.Close)
			#wx.CallAfter(self.okButton.Enable)
			return
		#wx.MessageBox('Failed to find machine for firmware upgrade\nIs your machine connected to the PC?', 'Firmware update', wx.OK | wx.ICON_ERROR)
		print "Failed to find machine. Ensure your machine is connected to your computer via USB."
		#wx.CallAfter(self.Close)
		
	
	def updateLabel(self, text):
		self.progressLabel.SetLabel(text)
		self.Layout()
	
	def OnProgress(self, value, max):
		wx.CallAfter(self.progressGauge.SetRange, max)
		wx.CallAfter(self.progressGauge.SetValue, value)

	def OnOk(self, e):
		self.Close()

	def OnClose(self, e):
		self.Destroy()

