__copyright__ = "Copyright (C) 2016 Cat Casuat (Cura Type A) and David Braam - Released under terms of the AGPLv3 License"

import wx
import os
import webbrowser
import sys

from wx.lib.pubsub import pub

from Cura.gui import newVersionDialog
from Cura.gui import configBase
from Cura.gui import expertConfig
from Cura.gui import alterationPanel
from Cura.gui import pluginPanel
from Cura.gui import preferencesDialog
from Cura.gui import configWizard
from Cura.gui import simpleMode
from Cura.gui import sceneView
from Cura.gui import aboutWindow
from Cura.gui.util import dropTarget
from Cura.gui.tools import pidDebugger
from Cura.gui.tools import minecraftImport
from Cura.util import profile
from Cura.util import version
import platform
from Cura.util import meshLoader
from Cura.gui import materialProfileSelector

class mainWindow(wx.Frame):
	def __init__(self):
		super(mainWindow, self).__init__(None, title='Cura - ' + version.getVersion())
		wx.EVT_CLOSE(self, self.OnClose)
		
		# allow dropping any file, restrict later
		self.SetDropTarget(dropTarget.FileDropTarget(self.OnDropFiles))

		# TODO: wxWidgets 2.9.4 has a bug when NSView does not register for dragged types when wx drop target is set. It was fixed in 2.9.5
		if sys.platform.startswith('darwin'):
			try:
				import objc
				nswindow = objc.objc_object(c_void_p=self.MacGetTopLevelWindowRef())
				view = nswindow.contentView()
				view.registerForDraggedTypes_([u'NSFilenamesPboardType'])
			except:
				pass

		self.normalModeOnlyItems = []

		mruFile = os.path.join(profile.getBasePath(), 'mru_filelist.ini')
		self.config = wx.FileConfig(appName="Cura",
						localFilename=mruFile,
						style=wx.CONFIG_USE_LOCAL_FILE)
						
		# temporary directory for files to be sent to the printer directly
		tempDirectory = os.path.join(profile.getBasePath(), '.temp')
		if not os.path.exists(tempDirectory):
			os.makedirs(tempDirectory)

		self.ID_MRU_MODEL1, self.ID_MRU_MODEL2, self.ID_MRU_MODEL3, self.ID_MRU_MODEL4, self.ID_MRU_MODEL5, self.ID_MRU_MODEL6, self.ID_MRU_MODEL7, self.ID_MRU_MODEL8, self.ID_MRU_MODEL9, self.ID_MRU_MODEL10 = [wx.NewId() for line in xrange(10)]
		self.modelFileHistory = wx.FileHistory(10, self.ID_MRU_MODEL1)
		self.config.SetPath("/ModelMRU")
		self.modelFileHistory.Load(self.config)

		self.ID_MRU_PROFILE1, self.ID_MRU_PROFILE2, self.ID_MRU_PROFILE3, self.ID_MRU_PROFILE4, self.ID_MRU_PROFILE5, self.ID_MRU_PROFILE6, self.ID_MRU_PROFILE7, self.ID_MRU_PROFILE8, self.ID_MRU_PROFILE9, self.ID_MRU_PROFILE10 = [wx.NewId() for line in xrange(10)]
		self.profileFileHistory = wx.FileHistory(10, self.ID_MRU_PROFILE1)
		self.config.SetPath("/ProfileMRU")
		self.profileFileHistory.Load(self.config)

		self.menubar = wx.MenuBar()
		self.fileMenu = wx.Menu()
		i = self.fileMenu.Append(-1, _("Load Model File...\tCTRL+L"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.showLoadModel(), i)
		i = self.fileMenu.Append(-1, _("Save Model as AMF...\tCTRL+S"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.showSaveModel(), i)
		i = self.fileMenu.Append(-1, _("Reload Platform\tF5"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.reloadScene(e), i)
		i = self.fileMenu.Append(-1, _("Clear Platform"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.OnDeleteAll(e), i)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Print...\tCTRL+P"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.OnPrintButton(2), i)
		i = self.fileMenu.Append(-1, _("Save GCode...\tCTRL+G"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.showSaveGCode(), i)
		i = self.fileMenu.Append(-1, _("Show Slice Engine Log..."))
		self.Bind(wx.EVT_MENU, lambda e: self.scene._showEngineLog(), i)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Open Profile..."))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnLoadProfile, i)
		i = self.fileMenu.Append(-1, _("Save Profile..."))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnSaveProfile, i)
		if version.isDevVersion():
			i = self.fileMenu.Append(-1, "Save Difference From Default...")
			self.normalModeOnlyItems.append(i)
			self.Bind(wx.EVT_MENU, self.OnSaveDifferences, i)
		i = self.fileMenu.Append(-1, _("Load Profile From GCode..."))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnLoadProfileFromGcode, i)
		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Reset Profile to Default"))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnResetProfile, i)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Preferences...\tCTRL+,"))
		self.Bind(wx.EVT_MENU, self.OnPreferences, i)
		self.fileMenu.AppendSeparator()

		# Model MRU list
		modelHistoryMenu = wx.Menu()
		self.fileMenu.AppendMenu(wx.NewId(), '&' + _("Recent Model Files"), modelHistoryMenu)
		self.modelFileHistory.UseMenu(modelHistoryMenu)
		self.modelFileHistory.AddFilesToMenu()
		self.Bind(wx.EVT_MENU_RANGE, self.OnModelMRU, id=self.ID_MRU_MODEL1, id2=self.ID_MRU_MODEL10)

		# Profle MRU list
		profileHistoryMenu = wx.Menu()
		self.fileMenu.AppendMenu(wx.NewId(), _("Recent Profile Files"), profileHistoryMenu)
		self.profileFileHistory.UseMenu(profileHistoryMenu)
		self.profileFileHistory.AddFilesToMenu()
		self.Bind(wx.EVT_MENU_RANGE, self.OnProfileMRU, id=self.ID_MRU_PROFILE1, id2=self.ID_MRU_PROFILE10)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(wx.ID_EXIT, _("Quit"))
		self.Bind(wx.EVT_MENU, self.OnQuit, i)
		self.menubar.Append(self.fileMenu, '&' + _("File"))

		toolsMenu = wx.Menu()
		#i = toolsMenu.Append(-1, 'Batch run...')
		#self.Bind(wx.EVT_MENU, self.OnBatchRun, i)
		#self.normalModeOnlyItems.append(i)

		if minecraftImport.hasMinecraft():
			i = toolsMenu.Append(-1, _("Minecraft map import..."))
			self.Bind(wx.EVT_MENU, self.OnMinecraftImport, i)

		if version.isDevVersion():
			i = toolsMenu.Append(-1, _("PID Debugger..."))
			self.Bind(wx.EVT_MENU, self.OnPIDDebugger, i)
#			i = toolsMenu.Append(-1, _("Auto Firmware Update..."))
#			self.Bind(wx.EVT_MENU, self.OnAutoFirmwareUpdate, i)

		i = toolsMenu.Append(-1, _("Copy profile to clipboard"))
		self.Bind(wx.EVT_MENU, self.onCopyProfileClipboard,i)

		toolsMenu.AppendSeparator()
		self.allAtOnceItem = toolsMenu.Append(-1, _("Print All at Once"), kind=wx.ITEM_RADIO)
		self.Bind(wx.EVT_MENU, self.onOneAtATimeSwitch, self.allAtOnceItem)
		self.oneAtATime = toolsMenu.Append(-1, _("Print One at a Time"), kind=wx.ITEM_RADIO)
		self.Bind(wx.EVT_MENU, self.onOneAtATimeSwitch, self.oneAtATime)
		if profile.getPreference('oneAtATime') == 'True':
			self.oneAtATime.Check(True)
		else:
			self.allAtOnceItem.Check(True)

		self.menubar.Append(toolsMenu, _("Tools"))

		# material profile event caller		
		self.materialProfileUpdate = pub.subscribe(self.loadMaterialData, 'matProf.update')

		#Machine menu for machine configuration/tooling
		self.machineMenu = wx.Menu()
		self.updateMachineMenu()

		self.menubar.Append(self.machineMenu, _("Machine"))

		expertMenu = wx.Menu()
		i = expertMenu.Append(-1, _("Switch to Simple Mode..."), kind=wx.ITEM_RADIO)
		self.switchToQuickprintMenuItem = i
		self.Bind(wx.EVT_MENU, self.OnSimpleSwitch, i)
		i = expertMenu.Append(-1, _("Switch to Expert Mode..."), kind=wx.ITEM_RADIO)
		self.switchToNormalMenuItem = i
		self.Bind(wx.EVT_MENU, self.OnNormalSwitch, i)
		expertMenu.AppendSeparator()
		
		# add a checkmark to whichever mode is selected
		if profile.getPreference('startMode') == 'Simple':
			self.switchToQuickprintMenuItem.Check()
		else:
			self.switchToNormalMenuItem.Check()
		
		# opens the material profile selector window	
		i = expertMenu.Append(-1, _("Load Material Profile"))
		self.switchToNormalMenuItem = i
		self.Bind(wx.EVT_MENU, self.OnMaterialProfileSelect, i)
		expertMenu.AppendSeparator()

		i = expertMenu.Append(-1, _("Open Expert Settings...\tCTRL+E"))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnExpertOpen, i)
		expertMenu.AppendSeparator()

		self.menubar.Append(expertMenu, _("Expert"))

		helpMenu = wx.Menu()
		i = helpMenu.Append(-1, _("Online Documentation..."))
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('http://support.typeamachines.com/hc/en-us'), i)
		i = helpMenu.Append(-1, _("Release Notes..."))
		self.Bind(wx.EVT_MENU, lambda e: self.OnReleaseNotes(e), i)
		i = helpMenu.Append(-1, _("Report a Problem..."))
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('http://typeamachines.com/cura-beta'), i)
		i = helpMenu.Append(-1, _("Check for Update..."))
		self.Bind(wx.EVT_MENU, self.OnCheckForUpdate, i)
	#	i = helpMenu.Append(-1, _("Check for Update..."))
	#	self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('http://www.typeamachines.com/pages/downloads'), i)
		i = helpMenu.Append(-1, _("Open Type A Machines Website..."))
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('http://www.typeamachines.com/'), i)
		i = helpMenu.Append(-1, _("About Cura..."))
		self.Bind(wx.EVT_MENU, self.OnAbout, i)
		self.menubar.Append(helpMenu, _("Help"))
		self.SetMenuBar(self.menubar)

		self.splitter = wx.SplitterWindow(self, style = wx.SP_3D | wx.SP_LIVE_UPDATE)
		self.leftPane = wx.Panel(self.splitter, style=wx.BORDER_NONE)
		self.rightPane = wx.Panel(self.splitter, style=wx.BORDER_NONE)
		self.splitter.Bind(wx.EVT_SPLITTER_DCLICK, lambda evt: evt.Veto())

		#Preview window
		self.scene = sceneView.SceneView(self.rightPane)

		##Gui components##
		self.simpleSettingsPanel = simpleMode.simpleModePanel(self.leftPane, self.scene.sceneUpdated)
		self.normalSettingsPanel = normalSettingsPanel(self.leftPane, self.scene.sceneUpdated)

		self.leftSizer = wx.BoxSizer(wx.VERTICAL)
		self.leftSizer.Add(self.simpleSettingsPanel, 1)
		self.leftSizer.Add(self.normalSettingsPanel, 1, wx.EXPAND)
		self.leftPane.SetSizer(self.leftSizer)

		#Main sizer, to position the preview window, buttons and tab control
		sizer = wx.BoxSizer()
		self.rightPane.SetSizer(sizer)
		sizer.Add(self.scene, 1, flag=wx.EXPAND)

		# Main window sizer
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(sizer)
		sizer.Add(self.splitter, 1, wx.EXPAND)
		sizer.Layout()
		self.sizer = sizer

		self.updateProfileToAllControls()

		self.SetBackgroundColour(self.normalSettingsPanel.GetBackgroundColour())

		self.simpleSettingsPanel.Show(False)
		self.normalSettingsPanel.Show(False)

		# Set default window size & position
		self.SetSize((wx.Display().GetClientArea().GetWidth()/2,wx.Display().GetClientArea().GetHeight()/2))
		self.Centre()

		#Timer set; used to check if profile is on the clipboard
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.onTimer)
		#self.timer.Start(1000)
		self.lastTriedClipboard = profile.getProfileString()

		# Restore the window position, size & state from the preferences file
		try:
			if profile.getPreference('window_maximized') == 'True':
				self.Maximize(True)
			else:
				posx = int(profile.getPreference('window_pos_x'))
				posy = int(profile.getPreference('window_pos_y'))
				width = int(profile.getPreference('window_width'))
				height = int(profile.getPreference('window_height'))
				if posx > 0 or posy > 0:
					self.SetPosition((posx,posy))
				if width > 0 and height > 0:
					self.SetSize((width,height))

			self.normalSashPos = int(profile.getPreference('window_normal_sash'))
		except:
			self.normalSashPos = 0
			self.Maximize(True)
		if self.normalSashPos < self.normalSettingsPanel.printPanel.GetBestSize()[0] + 5:
			self.normalSashPos = self.normalSettingsPanel.printPanel.GetBestSize()[0] + 5

		self.splitter.SplitVertically(self.leftPane, self.rightPane, self.normalSashPos)

		if wx.Display.GetFromPoint(self.GetPosition()) < 0:
			self.Centre()
		if wx.Display.GetFromPoint((self.GetPositionTuple()[0] + self.GetSizeTuple()[1], self.GetPositionTuple()[1] + self.GetSizeTuple()[1])) < 0:
			self.Centre()
		if wx.Display.GetFromPoint(self.GetPosition()) < 0:
			self.SetSize((800,600))
			self.Centre()

		self.updateSliceMode()
		self.scene.SetFocus()
		self.dialogframe = None
	
		pub.subscribe(self.onPluginUpdate, "pluginupdate")

		pluginCount = self.normalSettingsPanel.pluginPanel.GetActivePluginCount()
		if pluginCount == 1:
			self.scene.notification.message("Warning: 1 plugin from the previous session is still active.")

		if pluginCount > 1:
			self.scene.notification.message("Warning: %i plugins from the previous session are still active." % pluginCount)
						
	def OnReleaseNotes(self, e):
		newVersion = newVersionDialog.newVersionDialog()
		newVersion.Show()
			
	def onPluginUpdate(self,msg): #receives commands from the plugin thread
		cmd = str(msg.data).split(";")
		if cmd[0] == "OpenPluginProgressWindow":
			if len(cmd)==1: #no titel received
				cmd.append("Plugin")
			if len(cmd)<3: #no message text received
				cmd.append("Plugin is executed...")
			dialogwidth = 300
			dialogheight = 80
			self.dialogframe = wx.Frame(self, -1, cmd[1],pos = ((wx.SystemSettings.GetMetric(wx.SYS_SCREEN_X)-dialogwidth)/2,(wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)-dialogheight)/2), size=(dialogwidth,dialogheight), style = wx.STAY_ON_TOP)
			self.dialogpanel = wx.Panel(self.dialogframe, -1, pos = (0,0), size = (dialogwidth,dialogheight))
			self.dlgtext = wx.StaticText(self.dialogpanel, label = cmd[2], pos = (10,10), size = (280,40))
			self.dlgbar = wx.Gauge(self.dialogpanel,-1, 100, pos = (10,50), size = (280,20), style = wx.GA_HORIZONTAL)
			self.dialogframe.Show()

		elif cmd[0] == "Progress":
			number = int(cmd[1])
			if number <= 100 and self.dialogframe is not None:
				self.dlgbar.SetValue(number)
			else:
				self.dlgbar.SetValue(100)
		elif cmd[0] == "ClosePluginProgressWindow":
			self.dialogframe.Destroy()
			self.dialogframe=None
		else: #assume first token to be the name and second token the percentage
			if len(cmd)>=2:
				number = int(cmd[1])
			else:
				number = 100
			# direct output to Cura progress bar
			self.scene.printButton.setProgressBar(float(number)/100.)
			self.scene.printButton.setBottomText('%s' % (cmd[0]))
			self.scene.QueueRefresh()

	def onTimer(self, e):
		#Check if there is something in the clipboard
		profileString = ""
		try:
			if not wx.TheClipboard.IsOpened():
				if not wx.TheClipboard.Open():
					return
				do = wx.TextDataObject()
				if wx.TheClipboard.GetData(do):
					profileString = do.GetText()
				wx.TheClipboard.Close()

				startTag = "CURA_PROFILE_STRING:"
				if startTag in profileString:
					#print "Found correct syntax on clipboard"
					profileString = profileString.replace("\n","").strip()
					profileString = profileString[profileString.find(startTag)+len(startTag):]
					if profileString != self.lastTriedClipboard:
						print profileString
						self.lastTriedClipboard = profileString
						profile.setProfileFromString(profileString)
						self.scene.notification.message("Loaded new profile from clipboard.")
						self.updateProfileToAllControls()
		except:
			print "Unable to read from clipboard"


	def updateSliceMode(self):
		isSimple = profile.getPreference('startMode') == 'Simple'

		self.normalSettingsPanel.Show(not isSimple)
		self.simpleSettingsPanel.Show(isSimple)
		self.leftPane.Layout()

		# Set splitter sash position & size
		if isSimple:
			self.switchToQuickprintMenuItem.Check()
			# Save normal mode sash
			self.normalSashPos = self.splitter.GetSashPosition()

			# Change location of sash to width of quick mode pane
			(width, height) = self.simpleSettingsPanel.GetSizer().GetSize()
			self.splitter.SetSashPosition(width, True)

			# Disable sash
			self.splitter.SetSashSize(0)
		else:
			self.splitter.SetSashPosition(self.normalSashPos, True)
			# Enabled sash
			self.splitter.SetSashSize(4)
#		self.defaultFirmwareInstallMenuItem.Enable(firmwareInstall.getDefaultFirmware() is not None)
		if profile.getMachineSetting('machine_type').startswith('ultimaker2'):
			pass
		if int(profile.getMachineSetting('extruder_amount')) < 2:
			pass
		self.scene.updateProfileToControls()
		self.scene._scene.pushFree()

	def onOneAtATimeSwitch(self, e):
		profile.putPreference('oneAtATime', self.oneAtATime.IsChecked())
		if self.oneAtATime.IsChecked() and profile.getMachineSettingFloat('extruder_head_size_height') < 1:
			wx.MessageBox(_('For "One at a time" printing, you need to have entered the correct head size and gantry height in the machine settings'), _('One at a time warning'), wx.OK | wx.ICON_WARNING)
		self.scene.updateProfileToControls()
		self.scene._scene.pushFree()
		self.scene.sceneUpdated()

	def OnPreferences(self, e):
		prefDialog = preferencesDialog.preferencesDialog(self)
		prefDialog.Centre()
		prefDialog.Show()
		prefDialog.Raise()
		wx.CallAfter(prefDialog.Show)

	def OnMachineSettings(self, e):
		prefDialog = preferencesDialog.machineSettingsDialog(self)
		prefDialog.Centre()
		prefDialog.Show()
		prefDialog.Raise()
				
	def OnDropFiles(self, files):
		self.scene.loadFiles(files)

	def OnModelMRU(self, e):
		fileNum = e.GetId() - self.ID_MRU_MODEL1
		path = self.modelFileHistory.GetHistoryFile(fileNum)
		# Update Model MRU
		self.modelFileHistory.AddFileToHistory(path)  # move up the list
		self.config.SetPath("/ModelMRU")
		self.modelFileHistory.Save(self.config)
		self.config.Flush()
		# Load Model
		profile.putPreference('lastFile', path)
		filelist = [ path ]
		self.scene.loadFiles(filelist)

	def addToModelMRU(self, file):
		self.modelFileHistory.AddFileToHistory(file)
		self.config.SetPath("/ModelMRU")
		self.modelFileHistory.Save(self.config)
		self.config.Flush()

	def OnProfileMRU(self, e):
		fileNum = e.GetId() - self.ID_MRU_PROFILE1
		path = self.profileFileHistory.GetHistoryFile(fileNum)
		# Update Profile MRU
		self.profileFileHistory.AddFileToHistory(path)  # move up the list
		self.config.SetPath("/ProfileMRU")
		self.profileFileHistory.Save(self.config)
		self.config.Flush()
		# Load Profile
		profile.loadProfile(path)
		self.updateProfileToAllControls()

	def addToProfileMRU(self, file):
		self.profileFileHistory.AddFileToHistory(file)
		self.config.SetPath("/ProfileMRU")
		self.profileFileHistory.Save(self.config)
		self.config.Flush()

	def updateProfileToAllControls(self):
		self.scene.updateProfileToControls()
		self.normalSettingsPanel.updateProfileToControls()
		self.simpleSettingsPanel.updateProfileToControls()

	def reloadSettingPanels(self):
		self.leftSizer.Detach(self.simpleSettingsPanel)
		self.leftSizer.Detach(self.normalSettingsPanel)
		self.simpleSettingsPanel.Destroy()
		self.normalSettingsPanel.Destroy()
		self.simpleSettingsPanel = simpleMode.simpleModePanel(self.leftPane, lambda : self.scene.sceneUpdated())
		self.normalSettingsPanel = normalSettingsPanel(self.leftPane, lambda : self.scene.sceneUpdated())
		self.leftSizer.Add(self.simpleSettingsPanel, 1)
		self.leftSizer.Add(self.normalSettingsPanel, 1, wx.EXPAND)
		self.updateSliceMode()
		self.updateProfileToAllControls()

	def updateMachineMenu(self):
		#Remove all items so we can rebuild the menu. Inserting items seems to cause crashes, so this is the safest way.
		for item in self.machineMenu.GetMenuItems():
			self.machineMenu.RemoveItem(item)

		#Add a menu item for each machine configuration.
		for n in xrange(0, profile.getMachineCount()):
			i = self.machineMenu.Append(n + 0x1000, profile.getMachineSetting('machine_name', n).title(), kind=wx.ITEM_RADIO)
			if n == int(profile.getPreferenceFloat('active_machine')):
				i.Check(True)
			self.Bind(wx.EVT_MENU, lambda e: self.OnSelectMachine(e.GetId() - 0x1000), i)

		self.machineMenu.AppendSeparator()
		i = self.machineMenu.Append(-1, _("Add Printer (Direct Upload)..."))
		self.Bind(wx.EVT_MENU, self.OnAddNewPrinter, i)
		i = self.machineMenu.Append(-1, _("Select Printer (Direct Upload)..."))
		self.Bind(wx.EVT_MENU, self.OnDirectUploadSettings, i)
		self.machineMenu.AppendSeparator()
		i = self.machineMenu.Append(-1, _("Add New Machine Profile..."))
		self.Bind(wx.EVT_MENU, self.OnAddNewMachine, i)
		i = self.machineMenu.Append(-1, _("Machine Settings..."))
		self.Bind(wx.EVT_MENU, self.OnMachineSettings, i)

		#Add tools for machines.
		self.machineMenu.AppendSeparator()

#		self.defaultFirmwareInstallMenuItem = self.machineMenu.Append(-1, _("Install default firmware..."))
#		self.Bind(wx.EVT_MENU, self.OnDefaultMarlinFirmware, self.defaultFirmwareInstallMenuItem)

		i = self.machineMenu.Append(-1, _("Install Custom Firmware..."))
		self.Bind(wx.EVT_MENU, self.OnCustomFirmware, i)
	
	def OnAddNewPrinter(self, e):
		scene = sceneView.AddNewPrinter(self)
		scene.Show()
		
	def OnDirectUploadSettings(self, e):
		if self.scene.printButton.isDisabled():
			enableUploadButton = False
		else:
			enableUploadButton = True
		
		print "Enable upload button: %s" % enableUploadButton
	#	self.scene.reloadScene(e)
		newPrinter = sceneView.printerSelector(enableUploadButton)
		newPrinter.Show()
		
		
	def OnLoadProfile(self, e):
		dlg=wx.FileDialog(self, _("Select profile file to load"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profileFile = dlg.GetPath()
			profile.loadProfile(profileFile)
			self.updateProfileToAllControls()

			# Update the Profile MRU
			self.addToProfileMRU(profileFile)
		dlg.Destroy()

	def OnLoadProfileFromGcode(self, e):
		dlg=wx.FileDialog(self, _("Select gcode file to load profile from"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("gcode files (*%s)|*%s;*%s" % (profile.getGCodeExtension(), profile.getGCodeExtension(), profile.getGCodeExtension()[0:2]))
		if dlg.ShowModal() == wx.ID_OK:
			gcodeFile = dlg.GetPath()
			f = open(gcodeFile, 'r')
			hasProfile = False
			for line in f:
				if line.startswith(';CURA_PROFILE_STRING:'):
					profile.setProfileFromString(line[line.find(':')+1:].strip())
					if ';{profile_string}' not in profile.getAlterationFile('end.gcode'):
						profile.setAlterationFile('end.gcode', profile.getAlterationFile('end.gcode') + '\n;{profile_string}')
					hasProfile = True
			if hasProfile:
				wx.MessageBox(_("The profile has been loaded from the selected GCode file."), _("Success"), wx.OK)
				self.updateProfileToAllControls()
			else:
				wx.MessageBox(_("No profile found in GCode file.\nThis feature only works with GCode files made by Cura 12.07 or newer."), _("Profile load error"), wx.OK | wx.ICON_INFORMATION)
		dlg.Destroy()

	def OnSaveProfile(self, e):
		dlg=wx.FileDialog(self, _("Select profile file to save"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profile_filename = dlg.GetPath()
			if not profile_filename.lower().endswith('.ini'): #hack for linux, as for some reason the .ini is not appended.
				profile_filename += '.ini'
			profile.saveProfile(profile_filename)
		dlg.Destroy()

	def OnSaveDifferences(self, e):
		dlg=wx.FileDialog(self, _("Select profile file to save"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profile_filename = dlg.GetPath()
			if not profile_filename.lower().endswith('.ini'): #hack for linux, as for some reason the .ini is not appended.
				profile_filename += '.ini'
			profile.saveProfileDifferenceFromDefault(profile_filename)
		dlg.Destroy()

	def OnResetProfile(self, e):
		dlg = wx.MessageDialog(self, _("This will reset all profile settings to defaults.\nUnless you have saved your current profile, all settings will be lost!\nDo you really want to reset?"), _("Profile reset"), wx.YES_NO | wx.ICON_QUESTION)
		result = dlg.ShowModal() == wx.ID_YES
		dlg.Destroy()
		if result:
			profile.resetProfile()
			self.updateProfileToAllControls()
			self.scene.notification.message("Profile settings have been reset to Default.")

	def OnSimpleSwitch(self, e):
		profile.putPreference('startMode', 'Simple')
		self.updateSliceMode()

	def OnMaterialProfileSelect(self, e):
		materialSelector = materialProfileSelector.MaterialProfileSelector()
		materialSelector.Show()
		
	def loadData(self, data, profileType):
		# Get the support settings user has set
		raft = profile.getProfileSetting('platform_adhesion')
		support = profile.getProfileSetting('support')
		for setting, value in data.items():
			if profileType == 'preference':
				profile.putPreference(setting, value)
			elif profileType == 'profile':
				profile.putProfileSetting(setting, value)
		# Add support preferences at the end to make sure they're not written over to 'None'
		profile.putProfileSetting('platform_adhesion', raft)
		profile.putProfileSetting('support', support)
		self.normalSettingsPanel.updateProfileToControls()
	#	self._callback()
		
	def loadMaterialData(self, path):
		import ConfigParser as ConfigParser
		
		sectionSettings = {}
		manufacturer = None
		name = None
		materialLoaded = None
		
		materialSettings = []
		cp = ConfigParser.ConfigParser()
		cp.read(path)
		
		# get the manufacturer and the name of the material
		if cp.has_section('info'):
			manufacturer = cp.get('info', 'manufacturer')
			name = cp.get('info', 'name')
			materialLoaded = manufacturer + " " + name
		
		# load the material profile settings
		if cp.has_section('profile'):
			for setting, value in cp.items('profile'):
				sectionSettings[setting] = value

		# update manufacturer and material names saved
		if manufacturer is not None and name is not None: 
			profile.putPreference('material_supplier', manufacturer)
			profile.putPreference('material_name', name)
			profile.putPreference('material_profile', materialLoaded)

		# profile setting information update + info panel update
		self.loadData(sectionSettings, 'profile')
				
	def OnNormalSwitch(self, e):
		profile.putPreference('startMode', 'Normal')
		dlg = wx.MessageDialog(self, _("Copy the settings from quickprint to your full settings?\n(This will overwrite any full setting modifications you have)"), _("Profile copy"), wx.YES_NO | wx.ICON_QUESTION)
		result = dlg.ShowModal() == wx.ID_YES
		dlg.Destroy()
		if result:
			profile.resetProfile()
			for k, v in self.simpleSettingsPanel.getSettingOverrides().items():
				profile.putProfileSetting(k, v)
			self.updateProfileToAllControls()
		self.updateSliceMode()

#	def OnDefaultMarlinFirmware(self, e):
#		firmwareInstall.InstallFirmware(self)

	def OnCustomFirmware(self, e):
		if profile.getMachineSetting('machine_type').startswith('ultimaker'):
			wx.MessageBox(_("Warning: Installing a custom firmware does not guarantee that you machine will function correctly, and could damage your machine."), _("Firmware update"), wx.OK | wx.ICON_EXCLAMATION)
		dlg=wx.FileDialog(self, _("Open firmware to upload"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("HEX file (*.hex)|*.hex;*.HEX")
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetPath()
			dlg.Destroy()
			if not(os.path.exists(filename)):
				return
			#For some reason my Ubuntu 10.10 crashes here.
			firmwareInstall.InstallFirmware(self, filename)

	def OnAddNewMachine(self, e):
		self.Hide()
		configWizard.ConfigWizard(True)
		self.Show()
		self.reloadSettingPanels()
		self.updateMachineMenu()

	def OnSelectMachine(self, index):
		profile.setActiveMachine(index)
		self.reloadSettingPanels()

	def OnExpertOpen(self, e):
		ecw = expertConfig.expertConfigWindow(lambda : self.scene.sceneUpdated())
		ecw.Centre()
		ecw.Show()

	def OnMinecraftImport(self, e):
		mi = minecraftImport.minecraftImportWindow(self)
		mi.Centre()
		mi.Show(True)

	def OnPIDDebugger(self, e):
		debugger = pidDebugger.debuggerWindow(self)
		debugger.Centre()
		debugger.Show(True)

	def OnAutoFirmwareUpdate(self, e):
		dlg=wx.FileDialog(self, _("Open Firmware to Upload"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("HEX file (*.hex)|*.hex;*.HEX")
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetPath()
			dlg.Destroy()
			if not(os.path.exists(filename)):
				return
			#For some reason my Ubuntu 10.10 crashes here.
			installer = firmwareInstall.AutoUpdateFirmware(self, filename)

	def onCopyProfileClipboard(self, e):
		try:
			if not wx.TheClipboard.IsOpened():
				wx.TheClipboard.Open()
				clipData = wx.TextDataObject()
				self.lastTriedClipboard = profile.getProfileString()
				profileString = profile.insertNewlines("CURA_PROFILE_STRING:" + self.lastTriedClipboard)
				clipData.SetText(profileString)
				wx.TheClipboard.SetData(clipData)
				wx.TheClipboard.Close()
		except:
			print "Could not write to clipboard, unable to get ownership. Another program is using the clipboard."

	# Version update checker
	def OnCheckForUpdate(self, e):

		needsUpdate = False
		downloadLink = ''
		updateVersion = ''
		
		versionStatus = version.checkForNewerVersion()
		
		# Corresponding keys for versionStatus:
		#		"needsUpdate"
		#		"downloadLink"
		# 	"updateVersion"
		#
		# If download is not needed, then the value returned will be: ''
		if versionStatus: 
			for x, y in versionStatus.items():
				if x == 'needsUpdate' and y != '':
					needsUpdate = y
				elif x == 'downloadLink' and y != '':
					downloadLink = y
				elif x == 'updateVersion' and y != '':
					updateVersion = y

			if needsUpdate is True and updateVersion != '':
				if wx.MessageBox(_("Cura Type A v%s is now available. Would you like to download it?" % updateVersion), _("New Version Available"), wx.YES_NO | wx.ICON_INFORMATION) == wx.YES:
					webbrowser.open(downloadLink)
				else:

					profile.putPreference('check_for_updates', False)
					# If the user says no, then set check_for_updates to False
					# Users will still be able to see the update dialog from the
					# help menu
			else:
				if e: 
					wx.MessageBox(_("You are running the latest version of Cura!"), style=wx.ICON_INFORMATION)
		else:
			if e:
				wx.MessageBox(_("Please check your internet connection or try again later."), _("Error"), wx.OK | wx.ICON_INFORMATION)
				
	def OnAbout(self, e):
		aboutBox = aboutWindow.aboutWindow()
		aboutBox.Centre()
		aboutBox.Show()

	def OnClose(self, e):
		profile.saveProfile(profile.getDefaultProfilePath(), True)

		# Save the window position, size & state from the preferences file
		profile.putPreference('window_maximized', self.IsMaximized())
		if not self.IsMaximized() and not self.IsIconized():
			(posx, posy) = self.GetPosition()
			profile.putPreference('window_pos_x', posx)
			profile.putPreference('window_pos_y', posy)
			(width, height) = self.GetSize()
			profile.putPreference('window_width', width)
			profile.putPreference('window_height', height)

			# Save normal sash position.  If in normal mode (!simple mode), get last position of sash before saving it...
			isSimple = profile.getPreference('startMode') == 'Simple'
			if not isSimple:
				self.normalSashPos = self.splitter.GetSashPosition()
			profile.putPreference('window_normal_sash', self.normalSashPos)

		#HACK: Set the paint function of the glCanvas to nothing so it won't keep refreshing. Which can keep wxWidgets from quiting.
		print "Closing down"
		self.scene.OnPaint = lambda e : e
		self.scene._engine.cleanup()
		self.Destroy()

	def OnQuit(self, e):
		self.Close()

class normalSettingsPanel(configBase.configPanelBase):
	"Main user interface window"
	def __init__(self, parent, callback = None):
		super(normalSettingsPanel, self).__init__(parent, callback)
		self.parent = parent
		self.callback = callback
		#Main tabs
		self.nb = wx.Notebook(self)
		self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		self.GetSizer().Add(self.nb, 1, wx.EXPAND)

		(left, right, self.printPanel) = self.CreateDynamicConfigTab(self.nb, _('Basic'))
		

		self._addSettingsToPanels('basic', left, right)
		self._addSettingsToPanels('informational', left, right)
		self.SizeLabelWidths(left, right)

		(left, right, self.advancedPanel) = self.CreateDynamicConfigTab(self.nb, _('Advanced'))
		self._addSettingsToPanels('advanced', left, right)
		self._addSettingsToPanels('informational', left, right)
		self.SizeLabelWidths(left, right)

		#Plugin page
		self.pluginPanel = pluginPanel.pluginPanel(self.nb, callback)
		self.nb.AddPage(self.pluginPanel, _("Plugins"))

		#Alteration page
		if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
			self.alterationPanel = None
		else:
			self.alterationPanel = alterationPanel.alterationPanel(self.nb, callback)
			self.nb.AddPage(self.alterationPanel, "Start/End-GCode")
		self.Bind(wx.EVT_SIZE, self.OnSize)

		self.nb.SetSize(self.GetSize())
		self.UpdateSize(self.printPanel)
		self.UpdateSize(self.advancedPanel)

	def _addSettingsToPanels(self, category, left, right):
		count = len(profile.getSubCategoriesFor(category)) + len(profile.getSettingsForCategory(category))

		p = left
		n = 0

		configBase.StaticTopRow(p)
		for title in profile.getSubCategoriesFor(category):
			n += 1 + len(profile.getSettingsForCategory(category, title))
			if n > count / 2:
				p = right
			configBase.TitleRow(p, _(title))
			for s in profile.getSettingsForCategory(category, title):
				configBase.SettingRow(p, s.getName())

			if str(title) == "Speed and Temperature":
				warning = self.PrintBedWarning(p)
				configBase.BoxedText(p, warning)

	#	configBase.BottomRow(p)

	def PrintBedWarning(self, p):
		# Heated bed warning
		warning = wx.StaticText(p, -1, "Always use surface treatment with heated bed to prevent damage from material bonding to glass. See material manufacturer recommendations.")
		return warning

	def SizeLabelWidths(self, left, right):
		leftWidth = self.getLabelColumnWidth(left)
		rightWidth = self.getLabelColumnWidth(right)
		maxWidth = max(leftWidth, rightWidth)
		self.setLabelColumnWidth(left, maxWidth)
		self.setLabelColumnWidth(right, maxWidth)


	def OnSize(self, e):
		# Make the size of the Notebook control the same size as this control
		self.nb.SetSize(self.GetSize())

		# Propegate the OnSize() event (just in case)
		e.Skip()

		# Perform out resize magic
		self.UpdateSize(self.printPanel)
		self.UpdateSize(self.advancedPanel)

	def UpdateSize(self, configPanel):
		sizer = configPanel.GetSizer()

		# Pseudocde
		# if horizontal:
		#     if width(col1) < best_width(col1) || width(col2) < best_width(col2):
		#         switch to vertical
		# else:
		#     if width(col1) > (best_width(col1) + best_width(col1)):
		#         switch to horizontal
		#

		col1 = configPanel.leftPanel
		colSize1 = col1.GetSize()
		colBestSize1 = col1.GetBestSize()
		col2 = configPanel.rightPanel
		colSize2 = col2.GetSize()
		colBestSize2 = col2.GetBestSize()

		orientation = sizer.GetOrientation()

		if orientation == wx.HORIZONTAL:
			if (colSize1[0] <= colBestSize1[0]) or (colSize2[0] <= colBestSize2[0]):
				configPanel.Freeze()
				sizer = wx.BoxSizer(wx.VERTICAL)
#				sizer.Add(configPanel.leftPanel, flag=wx.ALIGN_CENTER)
#				sizer.Add(configPanel.rightPanel, flag=wx.ALIGN_CENTER)
				sizer.Add(configPanel.leftPanel, flag=wx.EXPAND)
				sizer.Add(configPanel.rightPanel, flag=wx.EXPAND)
				configPanel.SetSizer(sizer)
				#sizer.Layout()
				configPanel.Layout()
				self.Layout()
				configPanel.Thaw()
		else:
			if max(colSize1[0], colSize2[0]) > (colBestSize1[0] + colBestSize2[0]):
				configPanel.Freeze()
				sizer = wx.BoxSizer(wx.HORIZONTAL)
				sizer.Add(configPanel.leftPanel, proportion=1, border=35, flag=wx.EXPAND)
				sizer.Add(configPanel.rightPanel, proportion=1, flag=wx.EXPAND)
				configPanel.SetSizer(sizer)
				#sizer.Layout()
				configPanel.Layout()
				self.Layout()
				configPanel.Thaw()

	def updateProfileToControls(self):
		super(normalSettingsPanel, self).updateProfileToControls()
		if self.alterationPanel is not None:
			self.alterationPanel.updateProfileToControls()
		self.pluginPanel.updateProfileToControls()
