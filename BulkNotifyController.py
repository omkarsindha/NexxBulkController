import json
import socket
import time
import os
import sys
import threading
from typing import Dict

try:
    import wx
    import wx.lib.mixins.inspection as WIT
    import wx.adv
except ImportError as err:
    print("wxPython required: http://www.wxpython.org")
    sys.exit(1)

try:
    import ahttp
except ImportError as err:
    print("ahttp required: http://stash/projects/DVG/repos/ahttp/browse")
    sys.exit(1)
http = ahttp.start()

DEBUG = False  # Enable/disable the debug stderr/stdout window
APPNAME = "Bulk Standard MV Controller"
VENDORNAME = "Evertz"
COMPANYNAME = "Evertz Microsystems Ltd."
PRODUCTNAME = "Bulk Notify Controller"
COPYRIGHT = "2025 Evertz Microsystems Ltd."
VERSION = "0.1"
BASE_API = "v.api/apis/EV/"
IP_LOC = "nexxIP"
# Define colors
DARK_GRAY = wx.Colour(50, 50, 50)
WHITE = wx.Colour(255, 255, 255)
YELLOW = wx.Colour(255, 255, 0)


class AppFrame(wx.Frame):
    """Main application frame (window)"""

    def __init__(self, debug=0):
        """Initialize our main application frame."""
        # Call the original constructor to do its job
        TITLE = "%s v%s" % (PRODUCTNAME, VERSION)
        wx.Frame.__init__(self, parent=None, title=TITLE, size=(1250, 800))
        self.wxconfig = wx.Config()
        self.http = ahttp.start()
        menubar = wx.MenuBar()
        helpMenu = wx.Menu()
        helpMenu.Append(wx.ID_ABOUT, "&About")
        menubar.Append(helpMenu, "&Help")
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.SetMenuBar(menubar)

        self.CreateStatusBar(number=2, style=wx.STB_DEFAULT_STYLE)
        self.SetStatusWidths([-1, 100])
        self.SetStatusText("Welcome to NEXX Bulk Controller", 0)

        self.panel = AppPanel(frame=self, wxconfig=self.wxconfig,
                              http_thread=self.http)

        sizer = wx.BoxSizer()
        sizer.Add(self.panel, proportion=1, flag=wx.EXPAND)
        self.SetSizer(sizer)

        # Set background color
        self.SetBackgroundColour(DARK_GRAY)

        self.Center()
        self.Show()

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnExit(self, event=None):
        """Exit the program. Frame.Close() generates a EVT_CLOSE event."""
        self.Close()

    def OnAbout(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName(APPNAME)
        info.SetDescription(
            "Python version %s.%s.%s (%s %s)\n" % tuple(sys.version_info) +
            "Powered by wxPython %s\n" % (wx.version()) +
            "Running on %s\n\n" % (wx.GetOsDescription()) +
            "Process ID = %s\n" % (os.getpid()))
        info.SetWebSite("www.evertz.com", "Evertz")
        info.AddDeveloper("Omkarsinh Sindha")
        wx.adv.AboutBox(info)

    def OnClose(self, event: wx.CloseEvent):
        """User wants to close the application. Forward to app_panel."""
        # Skip event by default so it propagates, closing the application.
        event.Skip()
        # Send event to AppPanel/BookPages. They can veto by clearing skip flag.
        # self.panel.OnExit(event)
        # If we are exiting, stop the timer and loader processes.
        if event.GetSkipped():
            self.http.stop()


class AppPanel(wx.Panel):
    def __init__(self, frame: wx.Frame, wxconfig: wx.ConfigBase, http_thread):
        wx.Panel.__init__(self, parent=frame)
        self.http = http_thread
        self.wxconfig = wxconfig

        self.SetBackgroundColour(DARK_GRAY)

        # IP label and text ctrl
        self.label1 = wx.StaticText(self, label="Nexx IP:")
        self.label1.SetForegroundColour(WHITE)
        self.ip_input = wx.TextCtrl(self)
        self.ip_input.SetValue(self.wxconfig.Read(IP_LOC, defaultVal=""))
        self.ip_input.SetBackgroundColour(DARK_GRAY)
        self.ip_input.SetForegroundColour(WHITE)
        self.connet_btn = wx.Button(self, label="Connect")
        self.reset_btn = wx.Button(self, label="Reset")
        self.connet_btn.Bind(wx.EVT_BUTTON, self.on_connect)
        self.reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        hbox = wx.BoxSizer(orient=wx.HORIZONTAL)
        hbox.Add(self.label1, 0, wx.ALL, 10)
        hbox.Add(self.ip_input, 0, wx.ALL, 10)
        hbox.Add(self.connet_btn, 0, wx.ALL, 10)
        hbox.Add(self.reset_btn, 0, wx.ALL, 10)
        self.notebook = wx.Notebook(self)
        self.notebook.SetBackgroundColour(DARK_GRAY)
        self.notebook.SetForegroundColour(WHITE)
        self.page1 = SystemNotify(self.notebook, frame, self.wxconfig, self.http)
        self.page2 = VideoNotify(self.notebook, frame, self.wxconfig, self.http)
        self.page3 = AudioNotify(self.notebook, frame, self.wxconfig, self.http)
        self.page4 = AdvancedNotify(self.notebook, frame, self.wxconfig, self.http)
        self.page5 = AdvancedAudioNotify(self.notebook, frame, self.wxconfig, self.http)
        self.notebook.AddPage(self.page5, "Advanced Audio Notify")
        self.notebook.AddPage(self.page4, "Advanced Notify")
        self.notebook.AddPage(self.page3, "Audio Notify")
        self.notebook.AddPage(self.page2, "Video Notify")
        self.notebook.AddPage(self.page1, "System Notify")
        #self.notebook.Disable()
        # Main sizer for notebook and top elements
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(hbox, 0, wx.ALIGN_LEFT)
        main_sizer.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(main_sizer)

    def on_connect(self, evt):
        ip = self.ip_input.GetValue()
        try:
            socket.inet_aton(ip)
        except socket.error:
            dlg: wx.MessageDialog = wx.MessageDialog(self, "Invalid IP. Please Try Again", "IP Error", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()
            return
        error = "Error:"
        try:
            varid1 = "1"
            url = f"http://{ip}/{BASE_API}GET/parameter/{varid1}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            value = op_content.get("value", None)
            dlg: wx.MessageDialog = wx.MessageDialog(self, f"Card Found: {value}", "Card Found", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            self.wxconfig.Write(IP_LOC, ip)
            self.ip_input.Disable()
            self.connet_btn.Disable()
            self.notebook.Enable()
        except Exception as e:
            self.error_alert(f"{error} Cannot connect to {ip}. ")

    def error_alert(self, message: str) -> None:
        dlg: wx.MessageDialog = wx.MessageDialog(self, message, "Error", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def on_reset(self, evt):
        self.ip_input.Clear()
        self.ip_input.Enable()
        self.connet_btn.Enable()
        self.notebook.Disable()
        self.wxconfig.Write("/nexxIP", "") # Clear IP from config

class SystemNotify(wx.ScrolledWindow):
    """System Notify panel (window)"""

    CPU_USE_TH = "343@i"
    CPU_USE_DUR = "344@i"
    CPU_USE_RES_DUR = "345@i"
    DISK_USE_TH = "219@i"
    # List of notification and its var id
    NOTIFICATIONS = {
        "CPU Usage too high": "850.2@i",
        "CPU Temperature too high": "850.3@i",
        "Memory Usage too high": "850.4@i",
        "FPGA temperature fabric too high": "850.5@i",
        "FPGA temperature BR too high": "850.6@i",
        "FPGA temperature TR too high": "850.7@i",
        "FPGA temperature BL too high": "850.8@i",
        "FPGA temperature TL too high": "850.9@i",
        "NTP Error": "850.18@i",
        "CPU Load too high": "850.19@i",
        "NTP Unsynchronised": "850.20@i",
        "SSD Critical Warning": "850.21@i",
        "High lifetime disk usage": "850.23@i",
        "Genlock REF 1 Missing": "850.24@i",
        "Genlock REF 2 Missing": "850.25@i",
        "Serial FVH 1 Missing": "850.26@i",
        "Serial FVH 2 Missing": "850.27@i"
    }

    def __init__(self, notebook: wx.Notebook, main_frame, wxconfig: wx.ConfigBase, http_thread):
        """Initialize our main application frame."""
        wx.ScrolledWindow.__init__(self, parent=notebook)
        self.main_frame = main_frame
        self.http = http_thread
        self.wxconfig = wxconfig
        self.SetBackgroundColour(DARK_GRAY)
        self.toggle_flag = True
        self.comboboxes: dict[wx.ComboBox: str] = {}
        self.spin_inputs:dict[wx.SpinCtrl: str] = {}
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        btn_hbox = wx.BoxSizer()
        self.load_btn = wx.Button(self, label="Load Values From Card")
        self.load_btn.Bind(wx.EVT_BUTTON, self.load_values)

        self.apply_btn = wx.Button(self, label="Apply Config")
        self.apply_btn.Bind(wx.EVT_BUTTON, self.on_apply)

        btn_hbox.Add(self.load_btn, 0, wx.ALL, 10)
        btn_hbox.Add(self.apply_btn, 0, wx.ALL, 10)
        main_sizer.Add(btn_hbox, 0, wx.ALL | wx.LEFT, 25)

        # System Notify Control
        system_control_label = wx.StaticText(self, label="System Notify Control")
        font = system_control_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        system_control_label.SetFont(font)
        system_control_label.SetForegroundColour(YELLOW)
        main_sizer.Add(system_control_label, 0, wx.LEFT, 25)

        grid = wx.GridBagSizer()
        # CPU Usage Threshold
        hbox1 = wx.BoxSizer(orient=wx.HORIZONTAL)
        cpu_usage_label = wx.StaticText(self, label="CPU Usage Threshold")
        cpu_usage_label.SetForegroundColour(WHITE)
        hbox1.Add(cpu_usage_label, 0, wx.ALL, 5)
        self.cpu_usage_threshold = wx.SpinCtrl(self, min=0, max=100)
        self.cpu_usage_threshold.SetBackgroundColour(DARK_GRAY)
        self.cpu_usage_threshold.SetForegroundColour(WHITE)
        hbox1.Add(self.cpu_usage_threshold, 0, wx.ALL, 5)
        percent_label = wx.StaticText(self, label="(0 to 100) %")
        percent_label.SetForegroundColour(WHITE)
        hbox1.Add(percent_label, 0, wx.ALL, 5)
        grid.Add(hbox1, pos=(0, 0),
               flag=wx.TOP | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)

        # CPU Usage Duration
        hbox2 = wx.BoxSizer()
        cpu_duration_label = wx.StaticText(self, label="CPU Usage Duration")
        cpu_duration_label.SetForegroundColour(WHITE)
        hbox2.Add(cpu_duration_label, 0, wx.ALL, 5)
        self.cpu_usage_duration = wx.SpinCtrl(self, min=0, max=600)
        self.cpu_usage_duration.SetBackgroundColour(DARK_GRAY)
        self.cpu_usage_duration.SetForegroundColour(WHITE)
        hbox2.Add(self.cpu_usage_duration, 0, wx.ALL, 5)
        seconds_label = wx.StaticText(self, label="(0 to 600) seconds")
        seconds_label.SetForegroundColour(WHITE)
        hbox2.Add(seconds_label, 0, wx.ALL, 5)
        grid.Add(hbox2, pos=(1, 0),
                 flag=wx.TOP | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)

        grid.Add((0, 0), pos=(0, 1), flag=wx.ALL, border=20)
        grid.Add((0, 0), pos=(1, 1), flag=wx.ALL, border=20)

        # CPU Usage Reset Duration
        hbox3 = wx.BoxSizer()
        cpu_reset_label = wx.StaticText(self, label="CPU Usage Reset Duration")
        cpu_reset_label.SetForegroundColour(WHITE)
        hbox3.Add(cpu_reset_label, 0, wx.ALL, 5)
        self.cpu_usage_reset_duration = wx.SpinCtrl(self, min=0, max=60)
        self.cpu_usage_reset_duration.SetBackgroundColour(DARK_GRAY)
        self.cpu_usage_reset_duration.SetForegroundColour(WHITE)
        hbox3.Add(self.cpu_usage_reset_duration, 0, wx.ALL, 5)
        reset_seconds_label = wx.StaticText(self, label="(0 to 60) seconds")
        reset_seconds_label.SetForegroundColour(WHITE)
        hbox3.Add(reset_seconds_label, 0, wx.ALL, 5)
        grid.Add(hbox3, pos=(0, 2),flag=wx.TOP | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)

        # High Lifetime Disk Usage Threshold
        hbox4 = wx.BoxSizer()
        disk_usage_label = wx.StaticText(self, label="High Lifetime Disk Usage Threshold")
        disk_usage_label.SetForegroundColour(WHITE)
        hbox4.Add(disk_usage_label, 0, wx.ALL, 5)
        self.disk_usage_threshold = wx.SpinCtrl(self, min=0, max=100)
        self.disk_usage_threshold.SetBackgroundColour(DARK_GRAY)
        self.disk_usage_threshold.SetForegroundColour(WHITE)
        hbox4.Add(self.disk_usage_threshold, 0, wx.ALL, 5)
        disk_percent_label = wx.StaticText(self, label="(0 to 100) %")
        disk_percent_label.SetForegroundColour(WHITE)
        hbox4.Add(disk_percent_label, 0, wx.ALL, 5)
        grid.Add(hbox4, pos=(1, 2),
                 flag=wx.TOP | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

        self.spin_inputs[self.cpu_usage_threshold] = self.CPU_USE_TH
        self.spin_inputs[self.cpu_usage_duration] = self.CPU_USE_DUR
        self.spin_inputs[self.cpu_usage_reset_duration] = self.CPU_USE_RES_DUR
        self.spin_inputs[self.disk_usage_threshold] = self.DISK_USE_TH

        head_hbox = wx.BoxSizer()
        # System Notify
        system_notify_label = wx.StaticText(self, label="System Notify")
        font = system_notify_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        system_notify_label.SetFont(font)
        system_notify_label.SetForegroundColour(YELLOW)
        head_hbox.Add(system_notify_label, 0, wx.ALL, 5)

        self.toggle_all_button = wx.Button(self, label="Toggle All")
        self.toggle_all_button.Bind(wx.EVT_BUTTON, self.on_toggle_all)
        head_hbox.Add(self.toggle_all_button, 0, wx.CENTER | wx.LEFT, 5)

        # Create a grid sizer for the combo boxes
        grid_sizer = wx.GridBagSizer(hgap=5, vgap=5)
        grid_sizer.Add(head_hbox, pos=(0,0), flag=wx.ALL, border=5)

        for i, (notification, varid) in enumerate(self.NOTIFICATIONS.items(), start=1):
            notification_label = wx.StaticText(self, label=notification)
            notification_label.SetForegroundColour(WHITE)
            grid_sizer.Add(notification_label, pos=(i, 0), flag=wx.ALL, border=5)

            combobox = wx.ComboBox(self, choices=["False", "True"], style=wx.CB_READONLY)
            combobox.SetSelection(1)  # Set "True" as the default selection
            combobox.SetBackgroundColour(DARK_GRAY)
            combobox.SetForegroundColour(WHITE)
            self.comboboxes[combobox] = varid
            grid_sizer.Add(combobox, pos=(i, 1), flag=wx.ALL, border=5)

        main_sizer.Add(grid_sizer, 0, wx.ALL | wx.LEFT, 25)

        self.SetSizer(main_sizer)
        self.SetScrollRate(20, 20)

        # Fit the sizer to the virtual size of the scrolled window
        self.FitInside()

    def update_status(self, message, pane=0):
        self.main_frame.SetStatusText(message, pane)

    def on_toggle_all(self, evt):
        for box in self.comboboxes:
            if self.toggle_flag:
                box.SetSelection(0)
            else:
                box.SetSelection(1)
        self.toggle_flag = not self.toggle_flag

    def error_alert(self, message: str) -> None:
        dlg: wx.MessageDialog = wx.MessageDialog(self, message, "Error", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def on_apply(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return
        threading.Thread(target=self._apply_thread, args=(ip,)).start()

    def _apply_thread(self, ip):
        self.apply_btn.Disable()
        self.update_status("Applying config to card")
        for spin, varid in self.spin_inputs.items():
            value = spin.GetValue()
            url = f"http://{ip}/v.api/apis/EV/SET/parameter/{varid}/{value}"
            self.http.get(url)

        for box, varid in self.comboboxes.items():
            value = box.GetSelection()
            url = f"http://{ip}/v.api/apis/EV/SET/parameter/{varid}/{value}"
            self.http.get(url)
        self.apply_btn.Enable()
        self.update_status("Successfully applied config to card :)")


    def load_values(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        threading.Thread(target=self._load_values_thread, args=(ip,)).start()

    def _load_values_thread(self, ip):
        self.load_btn.Disable()
        self.update_status("Loading values from card")
        for spin, varid in self.spin_inputs.items():
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{varid}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
            except ValueError as e:
                self.error_alert("Did not get expected value for System Notify Control.")
                continue
            wx.CallAfter(spin.SetValue, int(value))

        for box, varid in self.comboboxes.items():
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{varid}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            value = op_content.get("value", None)
            wx.CallAfter(box.SetSelection, int(value))
        self.load_btn.Enable()
        self.update_status("Successfully loaded values from card :)")


class VideoNotify(wx.ScrolledWindow):
    """Video Notify panel (window)"""

    # Video Monitoring Control parameters
    PICTURE_NOISE_LEVEL = "410.x@i"
    BLACK_DURATION = "411.x@i"
    BLACK_RESET_DURATION = "412.x@i"
    FREEZE_DURATION = "413.x@i"
    FREEZE_RESET_DURATION = "414.x@i"
    MOTION_DURATION = "423.x@i"
    MOTION_RESET_DURATION = "422.x@i"
    LOSS_DURATION = "415.x@i"
    LOSS_RESET_DURATION = "416.x@i"
    FREEZE_BLACK_H_START = "417.x@i"
    FREEZE_BLACK_H_STOP = "418.x@i"
    FREEZE_BLACK_V_START = "419.x@i"
    FREEZE_BLACK_V_STOP = "420.x@i"
    FREEZE_CHECK_ENABLE = "983.x@i"
    BLACK_CHECK_ENABLE = "985.x@i"

    # Video Notify parameters
    VIDEO_NOTIFICATIONS = {
        "Loss of Video": "400.x.0@i",
        "Video Frozen": "400.x.1@i",
        "Video Black": "400.x.2@i",
        "Motion Detected": "400.x.3@i"
    }

    def __init__(self, notebook: wx.Notebook, main_frame, wxconfig: wx.ConfigBase, http_thread):
        """Initialize our main application frame."""
        wx.ScrolledWindow.__init__(self, parent=notebook)
        self.main_frame = main_frame
        self.http = http_thread
        self.wxconfig = wxconfig
        self.SetBackgroundColour(DARK_GRAY)
        self.toggle_flag = True
        self.comboboxes: Dict[wx.ComboBox, str] = {}
        self.spin_inputs: Dict[wx.SpinCtrl, str] = {}
        self.current_input = 1  # Default to input 1

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        top_vbox = wx.BoxSizer(wx.VERTICAL)
        # Buttons for loading and applying values
        btn_hbox = wx.BoxSizer()
        load_label = wx.StaticText(self, label="Load Values from input")
        load_label.SetForegroundColour(WHITE)

        self.input = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input.SetBackgroundColour(DARK_GRAY)
        self.input.SetForegroundColour(WHITE)
        self.load_btn = wx.Button(self, label="Load Values")
        self.load_btn.Bind(wx.EVT_BUTTON, self.load_values)

        btn_hbox.Add(load_label, flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        btn_hbox.Add(self.input, 0, wx.ALL, 10)
        btn_hbox.Add(self.load_btn, 0, wx.ALL, 10)


        # Input selection
        input_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_label = wx.StaticText(self, label="Select Input:")
        input_label.SetForegroundColour(WHITE)
        input_select_sizer.Add(input_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.input_from = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input_from.SetBackgroundColour(DARK_GRAY)
        self.input_from.SetForegroundColour(WHITE)
        input_select_sizer.Add(self.input_from, 0, wx.ALL, 5)

        to_label = wx.StaticText(self, label="to")
        to_label.SetForegroundColour(WHITE)
        input_select_sizer.Add(to_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.input_to = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input_to.SetBackgroundColour(DARK_GRAY)
        self.input_to.SetForegroundColour(WHITE)
        input_select_sizer.Add(self.input_to, 0, wx.ALL, 5)

        self.apply_input_btn = wx.Button(self, label="Apply to Selected Inputs")
        self.apply_input_btn.Bind(wx.EVT_BUTTON, self.on_apply_to_inputs)
        input_select_sizer.Add(self.apply_input_btn, 0, wx.ALL, 5)

        top_vbox.Add(btn_hbox, 0, wx.TOP, 5)
        top_vbox.Add(input_select_sizer, 0, wx.TOP, 5)

        main_sizer.Add(top_vbox, 0, wx.ALL, 25)
        # Video Monitoring Control section
        self.create_video_monitoring_control(main_sizer)

        # Video Notify section
        self.create_video_notify(main_sizer)

        self.SetSizer(main_sizer)
        self.SetScrollRate(20, 20)
        self.FitInside()

    def create_video_monitoring_control(self, main_sizer):
        # Video Monitoring Control header
        control_label = wx.StaticText(self, label="Video Monitoring Control")
        font = control_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        control_label.SetFont(font)
        control_label.SetForegroundColour(YELLOW)
        main_sizer.Add(control_label, 0, wx.LEFT, 25)

        # Create a grid for the controls
        grid = wx.GridBagSizer(hgap=10, vgap=10)

        # Parameters and their controls
        parameters = [
            ("Picture Noise Level", self.PICTURE_NOISE_LEVEL, 1, 14, "", 8),
            ("Black Duration", self.BLACK_DURATION, 6, 9000, "frames", 330),
            ("Black Reset Duration", self.BLACK_RESET_DURATION, 0, 60, "seconds", 3),
            ("Freeze Duration", self.FREEZE_DURATION, 6, 9000, "frames", 330),
            ("Freeze Reset Duration", self.FREEZE_RESET_DURATION, 0, 60, "seconds", 3),
            ("Motion Duration", self.MOTION_DURATION, 6, 9000, "frames", 330),
            ("Motion Reset Duration", self.MOTION_RESET_DURATION, 0, 60, "seconds", 3),
            ("Loss Duration", self.LOSS_DURATION, 6, 9000, "frames", 6),
            ("Loss Reset Duration", self.LOSS_RESET_DURATION, 0, 60, "seconds", 3),
            ("Freeze Black Horizontal Start Percent", self.FREEZE_BLACK_H_START, 0, 100, "%", 0),
            ("Freeze Black Horizontal Stop Percent", self.FREEZE_BLACK_H_STOP, 0, 100, "%", 100),
            ("Freeze Black Vertical Start Percent", self.FREEZE_BLACK_V_START, 0, 100, "%", 0),
            ("Freeze Black Vertical Stop Percent", self.FREEZE_BLACK_V_STOP, 0, 100, "%", 100),
        ]

        # Add parameter rows
        for row, (param_name, var_id, min_val, max_val, unit, default_val) in enumerate(parameters):
            label = wx.StaticText(self, label=param_name)
            label.SetForegroundColour(WHITE)
            grid.Add(label, pos=(row, 0), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

            spin = wx.SpinCtrl(self, min=min_val, max=max_val, initial=default_val)
            spin.SetBackgroundColour(DARK_GRAY)
            spin.SetForegroundColour(WHITE)
            grid.Add(spin, pos=(row, 1), flag=wx.ALL, border=5)

            range_label = wx.StaticText(self, label=f"({min_val} to {max_val}) {unit}")
            range_label.SetForegroundColour(WHITE)
            grid.Add(range_label, pos=(row, 2), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

            self.spin_inputs[spin] = var_id

        enable_params = [
            ("Freeze Check Enable", self.FREEZE_CHECK_ENABLE),
            ("Black Check Enable", self.BLACK_CHECK_ENABLE)
        ]

        row = len(parameters)
        for param_name, var_id in enable_params:
            label = wx.StaticText(self, label=param_name)
            label.SetForegroundColour(WHITE)
            grid.Add(label, pos=(row, 0), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

            combobox = wx.ComboBox(self, choices=["Disable", "Enable"], style=wx.CB_READONLY)
            combobox.SetSelection(0)
            combobox.SetBackgroundColour(DARK_GRAY)
            combobox.SetForegroundColour(WHITE)
            grid.Add(combobox, pos=(row, 1), flag=wx.ALL, border=5)

            self.comboboxes[combobox] = var_id
            row += 1

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)


    def create_video_notify(self, main_sizer):
        # Video Notify header
        notify_label = wx.StaticText(self, label="Video Notify")
        font = notify_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        notify_label.SetFont(font)
        notify_label.SetForegroundColour(YELLOW)

        head_hbox = wx.BoxSizer()
        head_hbox.Add(notify_label, 0, wx.ALL, 5)

        self.toggle_all_button = wx.Button(self, label="Toggle All")
        self.toggle_all_button.Bind(wx.EVT_BUTTON, self.on_toggle_all)
        head_hbox.Add(self.toggle_all_button, 0, wx.CENTER | wx.LEFT, 25)

        main_sizer.Add(head_hbox, 0, wx.LEFT, 20)

        # Create a grid for the video notifications
        grid = wx.GridBagSizer(hgap=10, vgap=5)

        traps_label = wx.StaticText(self, label="Video Traps")
        traps_label.SetForegroundColour(WHITE)
        grid.Add(traps_label, pos=(0, 0), flag=wx.ALL, border=5)

        faults_label = wx.StaticText(self, label="Video Faults")
        faults_label.SetForegroundColour(WHITE)
        grid.Add(faults_label, pos=(0, 1), flag=wx.ALL, border=5)

        for row, (notification_type, var_id) in enumerate(self.VIDEO_NOTIFICATIONS.items()):
            type_label = wx.StaticText(self, label=notification_type)
            type_label.SetForegroundColour(WHITE)
            grid.Add(type_label, pos=(row+1, 0), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

            combobox = wx.ComboBox(self, choices=["False", "True"], style=wx.CB_READONLY)
            combobox.SetSelection(1)  # Default to True
            combobox.SetBackgroundColour(DARK_GRAY)
            combobox.SetForegroundColour(WHITE)

            # Store the combobox with its var id
            self.comboboxes[combobox] = var_id

            grid.Add(combobox, pos=(row+1, 1), flag=wx.ALL, border=5)

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

    def update_status(self, message, pane=0):
        self.main_frame.SetStatusText(message, pane)

    def on_toggle_all(self, evt):
        for i, combobox in enumerate(self.comboboxes.keys()):
            if i == 0 or i ==1: # skip first 2 as they are not in video notify and are enable/disable combobox
                continue
            if self.toggle_flag:
                combobox.SetSelection(0)  # Set to False
            else:
                combobox.SetSelection(1)  # Set to True
        self.toggle_flag = not self.toggle_flag

    def error_alert(self, message: str) -> None:
        dlg: wx.MessageDialog = wx.MessageDialog(self, message, "Error", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def on_apply_to_inputs(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        from_input = self.input_from.GetValue()
        to_input = self.input_to.GetValue()

        if from_input > to_input:
            self.error_alert("Starting input must be less than or equal to ending input.")
            return

        threading.Thread(target=self._apply_to_inputs_thread, args=(ip, from_input, to_input)).start()

    def _apply_to_inputs_thread(self, ip, from_input, to_input):
        self.apply_input_btn.Disable()
        self.update_status(f"Applying config to inputs {from_input} to {to_input}")

        for input_num in range(from_input, to_input + 1):
            for spinctrl, var_id in self.spin_inputs.items():
                value = spinctrl.GetValue()
                var_id = var_id.replace("x", str(input_num-1))
                url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                self.http.get(url)

            for combobox, var_id in self.comboboxes.items():
                value = combobox.GetSelection()
                #print(value)
                var_id = var_id.replace("x", str(input_num-1))
                #print(var_id)
                url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                self.http.get(url)

        self.apply_input_btn.Enable()
        self.update_status(f"Successfully applied config to inputs {from_input} to {to_input} :)")

    def load_values(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        # Get the current input number
        input_num = self.input.GetValue()
        threading.Thread(target=self._load_values_thread, args=(ip, input_num)).start()

    def _load_values_thread(self, ip, input_num):
        self.load_btn.Disable()
        self.update_status(f"Loading values from card for input {input_num}")

        # Load spin control values
        for i, (spin, varid) in enumerate(self.spin_inputs.items()):
            varid = varid.replace("x", str(input_num-1))
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{varid}"
            op = self.http.get(url, block=True)
            #print(op.content)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(spin.SetValue, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {varid}.")
                continue

        # Load combobox values
        for box, varid in self.comboboxes.items():
            varid = varid.replace("x", str(input_num))
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{varid}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(box.SetSelection, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {varid}.")
                continue

        self.load_btn.Enable()
        self.update_status(f"Successfully loaded values from card for input {input_num} :)")


class AudioNotify(wx.ScrolledWindow):
    """Audio Notify panel (window)"""

    # Audio Monitoring Control parameters for individual channels
    # Format: parameter.input.channel@i
    AUDIO_OVER_LEVEL = "511.x.y@i"
    AUDIO_OVER_DURATION = "512.x.y@i"
    AUDIO_OVER_RESET_DURATION = "513.x.y@i"
    AUDIO_SILENCE_LEVEL = "514.x.y@i"
    AUDIO_SILENCE_DURATION = "515.x.y@i"
    AUDIO_SILENCE_RESET_DURATION = "516.x.y@i"
    AUDIO_LOSS_DURATION = "517.x.y@i"
    AUDIO_LOSS_RESET_DURATION = "518.x.y@i"

    # Audio Monitoring Control parameters for pairs
    # Format: parameter.input.pair@i
    MONO_DETECTION_LEVEL = "521.x.y@i"
    MONO_DETECTION_DURATION = "522.x.y@i"
    MONO_DETECTION_RESET_DURATION = "523.x.y@i"
    PHASE_REVERSE_LEVEL = "524.x.y@i"
    PHASE_REVERSE_DURATION = "525.x.y@i"
    PHASE_REVERSE_RESET_DURATION = "526.x.y@i"

    # Audio Notify parameters
    # Dictionary mapping notification types to their var_ids
    AUDIO_NOTIFICATIONS = {
        # Channel Loss
        "Channel 1 Audio Loss": "530.x.0@i",
        "Channel 2 Audio Loss": "530.x.1@i",
        "Channel 3 Audio Loss": "530.x.2@i",
        "Channel 4 Audio Loss": "530.x.3@i",
        "Channel 5 Audio Loss": "530.x.4@i",
        "Channel 6 Audio Loss": "530.x.5@i",
        "Channel 7 Audio Loss": "530.x.6@i",
        "Channel 8 Audio Loss": "530.x.7@i",
        "Channel 9 Audio Loss": "530.x.8@i",
        "Channel 10 Audio Loss": "530.x.9@i",
        "Channel 11 Audio Loss": "530.x.10@i",
        "Channel 12 Audio Loss": "530.x.11@i",
        "Channel 13 Audio Loss": "530.x.12@i",
        "Channel 14 Audio Loss": "530.x.13@i",
        "Channel 15 Audio Loss": "530.x.14@i",
        "Channel 16 Audio Loss": "530.x.15@i",
        # Channel Over
        "Channel 1 Audio Over": "530.x.16@i",
        "Channel 2 Audio Over": "530.x.17@i",
        "Channel 3 Audio Over": "530.x.18@i",
        "Channel 4 Audio Over": "530.x.19@i",
        "Channel 5 Audio Over": "530.x.20@i",
        "Channel 6 Audio Over": "530.x.21@i",
        "Channel 7 Audio Over": "530.x.22@i",
        "Channel 8 Audio Over": "530.x.23@i",
        "Channel 9 Audio Over": "530.x.24@i",
        "Channel 10 Audio Over": "530.x.25@i",
        "Channel 11 Audio Over": "530.x.26@i",
        "Channel 12 Audio Over": "530.x.27@i",
        "Channel 13 Audio Over": "530.x.28@i",
        "Channel 14 Audio Over": "530.x.29@i",
        "Channel 15 Audio Over": "530.x.30@i",
        "Channel 16 Audio Over": "530.x.31@i",
        # Channel Silence
        "Channel 1 Audio Silence": "530.x.32@i",
        "Channel 2 Audio Silence": "530.x.33@i",
        "Channel 3 Audio Silence": "530.x.34@i",
        "Channel 4 Audio Silence": "530.x.35@i",
        "Channel 5 Audio Silence": "530.x.36@i",
        "Channel 6 Audio Silence": "530.x.37@i",
        "Channel 7 Audio Silence": "530.x.38@i",
        "Channel 8 Audio Silence": "530.x.39@i",
        "Channel 9 Audio Silence": "530.x.40@i",
        "Channel 10 Audio Silence": "530.x.41@i",
        "Channel 11 Audio Silence": "530.x.42@i",
        "Channel 12 Audio Silence": "530.x.43@i",
        "Channel 13 Audio Silence": "530.x.44@i",
        "Channel 14 Audio Silence": "530.x.45@i",
        "Channel 15 Audio Silence": "530.x.46@i",
        "Channel 16 Audio Silence": "530.x.47@i",
        # Group Mono
        "Group 1 Audio Mono 1 and 2": "530.x.48@i",
        "Group 1 Audio Mono 3 and 4": "530.x.49@i",
        "Group 2 Audio Mono 1 and 2": "530.x.50@i",
        "Group 2 Audio Mono 3 and 4": "530.x.51@i",
        "Group 3 Audio Mono 1 and 2": "530.x.52@i",
        "Group 3 Audio Mono 3 and 4": "530.x.53@i",
        "Group 4 Audio Mono 1 and 2": "530.x.54@i",
        "Group 4 Audio Mono 3 and 4": "530.x.55@i",
        # Group Phase Reverse
        "Group 1 Audio PhaseRev 1 and 2": "530.x.56@i",
        "Group 1 Audio PhaseRev 3 and 4": "530.x.57@i",
        "Group 2 Audio PhaseRev 1 and 2": "530.x.58@i",
        "Group 2 Audio PhaseRev 3 and 4": "530.x.59@i",
        "Group 3 Audio PhaseRev 1 and 2": "530.x.60@i",
        "Group 3 Audio PhaseRev 3 and 4": "530.x.61@i",
        "Group 4 Audio PhaseRev 1 and 2": "530.x.62@i",
        "Group 4 Audio PhaseRev 3 and 4": "530.x.63@i",
    }

    PAIRS = ["Audio 1 and 2", "Audio 3 and 4", "Audio 5 and 6", "Audio 7 and 8",
     "Audio 9 and 10", "Audio 11 and 12", "Audio 13 and 14", "Audio 15 and 16"]

    def __init__(self, notebook: wx.Notebook, main_frame, wxconfig: wx.ConfigBase, http_thread):
        """Initialize our main application frame."""
        wx.ScrolledWindow.__init__(self, parent=notebook)
        self.main_frame = main_frame
        self.http = http_thread
        self.wxconfig = wxconfig
        self.SetBackgroundColour(DARK_GRAY)
        self.toggle_flag = True
        self.comboboxes: Dict[wx.ComboBox, str] = {}
        self.channel_controls: Dict[wx.SpinCtrl, str] = {}
        self.pair_controls: Dict[wx.SpinCtrl, str] = {}

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        load_label = wx.StaticText(self, label="Load Values from Input:")
        load_label.SetForegroundColour(WHITE)

        self.input = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input.SetBackgroundColour(DARK_GRAY)
        self.input.SetForegroundColour(WHITE)

        channel_label = wx.StaticText(self, label="Channel:")
        channel_label.SetForegroundColour(WHITE)
        self.channel = wx.SpinCtrl(self, min=1, max=16, initial=1)
        self.channel.SetBackgroundColour(DARK_GRAY)
        self.channel.SetForegroundColour(WHITE)

        pair_label = wx.StaticText(self, label="Pair:")
        pair_label.SetForegroundColour(WHITE)
        self.pair = wx.ComboBox(self, choices=self.PAIRS, style=wx.CB_READONLY)
        self.pair.SetSelection(0)
        self.load_btn = wx.Button(self, label="Load Values")
        self.load_btn.Bind(wx.EVT_BUTTON, self.load_values)

        btn_hbox = wx.BoxSizer()
        btn_hbox.Add(load_label, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        btn_hbox.Add(self.input, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_hbox.Add(channel_label, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=15)
        btn_hbox.Add(self.channel, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_hbox.Add(pair_label, flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=15)
        btn_hbox.Add(self.pair, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_hbox.Add(self.load_btn, 0, wx.ALL, 10)

        # Input selection
        input_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_label = wx.StaticText(self, label="Select Input:")
        input_label.SetForegroundColour(WHITE)
        input_select_sizer.Add(input_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.input_from = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input_from.SetBackgroundColour(DARK_GRAY)
        self.input_from.SetForegroundColour(WHITE)
        input_select_sizer.Add(self.input_from, 0, wx.ALL, 5)

        to_label = wx.StaticText(self, label="to")
        to_label.SetForegroundColour(WHITE)
        input_select_sizer.Add(to_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.input_to = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input_to.SetBackgroundColour(DARK_GRAY)
        self.input_to.SetForegroundColour(WHITE)
        input_select_sizer.Add(self.input_to, 0, wx.ALL, 5)

        self.apply_input_btn = wx.Button(self, label="Apply to Selected Inputs")
        self.apply_input_btn.Bind(wx.EVT_BUTTON, self.on_apply_to_inputs)
        input_select_sizer.Add(self.apply_input_btn, 0, wx.ALL, 5)

        top_vbox = wx.BoxSizer(wx.VERTICAL)
        top_vbox.Add(btn_hbox, 0, wx.TOP, 5)
        top_vbox.Add(input_select_sizer, 0, wx.TOP, 5)

        main_sizer.Add(top_vbox, 0, wx.ALL, 25)

        self.create_audio_monitoring_control(main_sizer)

        self.create_audio_monitoring_control_pair(main_sizer)

        self.create_audio_notify(main_sizer)

        self.SetSizer(main_sizer)
        self.SetScrollRate(20, 20)
        self.FitInside()

    def create_audio_monitoring_control(self, main_sizer):
        # Audio Monitoring Control header
        control_label = wx.StaticText(self, label="Audio Monitoring Control")
        font = control_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        control_label.SetFont(font)
        control_label.SetForegroundColour(YELLOW)
        main_sizer.Add(control_label, 0, wx.LEFT, 25)

        # Channel selection
        channel_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        channel_label = wx.StaticText(self, label="Select Channel:")
        channel_label.SetForegroundColour(WHITE)
        channel_select_sizer.Add(channel_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.channel_start = wx.SpinCtrl(self, min=1, max=16, initial=1)
        self.channel_start.SetBackgroundColour(DARK_GRAY)
        self.channel_start.SetForegroundColour(WHITE)
        to_text = wx.StaticText(self, label="to")
        to_text.SetForegroundColour(WHITE)
        self.channel_end = wx.SpinCtrl(self, min=1, max=16, initial=16)
        self.channel_end.SetBackgroundColour(DARK_GRAY)
        self.channel_end.SetForegroundColour(WHITE)
        channel_select_sizer.Add(self.channel_start, 0, wx.ALL, 5)
        channel_select_sizer.Add(to_text, 0, wx.CENTER)
        channel_select_sizer.Add(self.channel_end, 0, wx.ALL, 5)

        # Create a grid for the controls
        grid = wx.GridBagSizer(hgap=10, vgap=10)
        grid.Add(channel_select_sizer, pos=(0, 0), span=(0,2), flag=wx.ALL | wx.ALIGN_LEFT, border=5)

        headers = ["Audio Over Level", "Audio Over Duration", "Audio Over Reset Duration",
                   "Audio Silence Level", "Audio Silence Duration", "Audio Silence Reset Duration",
                   "Audio Loss Duration", "Audio Loss Reset Duration"]

        ranges = ["(-30 to 0) dBFS", "(1 to 3600) seconds", "(0 to 60) seconds",
                  "(-96 to -20) dBFS", "(1 to 3600) seconds", "(0 to 60) seconds",
                  "(1 to 300) seconds", "(0 to 60) seconds"]

        for col, header in enumerate(headers):
            header_label = wx.StaticText(self, label=header)
            header_label.SetForegroundColour(WHITE)
            grid.Add(header_label, pos=(1, col), flag=wx.ALL | wx.ALIGN_LEFT, border=5)

            range_label = wx.StaticText(self, label=ranges[col])
            range_label.SetForegroundColour(WHITE)
            grid.Add(range_label, pos=(2, col), flag=wx.ALL | wx.ALIGN_LEFT, border=5)

        # Parameters for the selected channel
        parameters = [
            (self.AUDIO_OVER_LEVEL, -30, 0, -24),
            (self.AUDIO_OVER_DURATION, 1, 3600, 10),
            (self.AUDIO_OVER_RESET_DURATION, 0, 60, 3),
            (self.AUDIO_SILENCE_LEVEL, -96, -20, -60),
            (self.AUDIO_SILENCE_DURATION, 1, 3600, 10),
            (self.AUDIO_SILENCE_RESET_DURATION, 0, 60, 3),
            (self.AUDIO_LOSS_DURATION, 1, 300, 1),
            (self.AUDIO_LOSS_RESET_DURATION, 0, 60, 3)
        ]

        # Add spin controls for the parameters
        for col, (var_id, min_val, max_val, default_val) in enumerate(parameters):
            spin = wx.SpinCtrl(self, min=min_val, max=max_val, initial=default_val)
            spin.SetBackgroundColour(DARK_GRAY)
            spin.SetForegroundColour(WHITE)
            grid.Add(spin, pos=(3, col), flag=wx.ALL, border=5)
            self.channel_controls[spin] = var_id

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

    def create_audio_monitoring_control_pair(self, main_sizer):
        control_label = wx.StaticText(self, label="Audio Monitoring Control Pair")
        font = control_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        control_label.SetFont(font)
        control_label.SetForegroundColour(YELLOW)
        main_sizer.Add(control_label, 0, wx.LEFT, 25)

        pair_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pair_label = wx.StaticText(self, label="Select Audio Pair:")
        pair_label.SetForegroundColour(WHITE)
        pair_select_sizer.Add(pair_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.pair_start = wx.ComboBox(self, choices=self.PAIRS, style=wx.CB_READONLY)
        self.pair_start.SetSelection(0)
        to_text = wx.StaticText(self, label="to")
        to_text.SetForegroundColour(WHITE)
        self.pair_end = wx.ComboBox(self, choices=self.PAIRS, style=wx.CB_READONLY)
        self.pair_end.SetSelection(len(self.PAIRS)-1)
        pair_select_sizer.Add(self.pair_start, 0, wx.ALL, 5)
        pair_select_sizer.Add(to_text, 0, wx.CENTER)
        pair_select_sizer.Add(self.pair_end, 0, wx.ALL, 5)

        # Create a grid for the controls
        grid = wx.GridBagSizer(hgap=10, vgap=10)
        grid.Add(pair_select_sizer, pos=(0, 0), span=(0, 3), flag=wx.ALL | wx.ALIGN_LEFT, border=5)
        # Headers for the grid
        headers = ["Mono Detection Level", "Mono Detection Duration", "Mono Detection Reset Duration",
                   "Phase Reverse Level", "Phase Reverse Duration", "Phase Reverse Reset Duration"]

        ranges = ["(20 to 50)", "(0 to 127) seconds", "(0 to 60) seconds",
                  "(50 to 100)", "(0 to 127) seconds", "(0 to 60) seconds"]

        for col, header in enumerate(headers):
            header_label = wx.StaticText(self, label=header)
            header_label.SetForegroundColour(WHITE)
            grid.Add(header_label, pos=(1, col), flag=wx.ALL | wx.ALIGN_LEFT, border=5)

            range_label = wx.StaticText(self, label=ranges[col])
            range_label.SetForegroundColour(WHITE)
            grid.Add(range_label, pos=(2, col), flag=wx.ALL | wx.ALIGN_LEFT, border=5)

        parameters = [
            (self.MONO_DETECTION_LEVEL, 20, 50, 20),
            (self.MONO_DETECTION_DURATION, 0, 127, 1),
            (self.MONO_DETECTION_RESET_DURATION, 0, 60, 3),
            (self.PHASE_REVERSE_LEVEL, 50, 100, 50),
            (self.PHASE_REVERSE_DURATION, 0, 127, 1),
            (self.PHASE_REVERSE_RESET_DURATION, 0, 60, 3)
        ]

        # Add spin controls for the parameters
        for col, (var_id, min_val, max_val, default_val) in enumerate(parameters):
            spin = wx.SpinCtrl(self, min=min_val, max=max_val, initial=default_val)
            spin.SetBackgroundColour(DARK_GRAY)
            spin.SetForegroundColour(WHITE)
            grid.Add(spin, pos=(3, col), flag=wx.ALL, border=5)
            self.pair_controls[spin] = var_id

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

    def create_audio_notify(self, main_sizer):
        # Audio Notify header
        notify_label = wx.StaticText(self, label="Audio Notify")
        font = notify_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        notify_label.SetFont(font)
        notify_label.SetForegroundColour(YELLOW)

        head_hbox = wx.BoxSizer()
        head_hbox.Add(notify_label, 0, wx.ALL, 5)

        self.toggle_all_button = wx.Button(self, label="Toggle All")
        self.toggle_all_button.Bind(wx.EVT_BUTTON, self.on_toggle_all)
        head_hbox.Add(self.toggle_all_button, 0, wx.CENTER | wx.LEFT, 25)

        main_sizer.Add(head_hbox, 0, wx.LEFT, 20)

        # Create a grid for the audio notifications
        grid = wx.GridBagSizer(hgap=10, vgap=5)

        # Input selection
        toggle_input_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        toggle_input_label = wx.StaticText(self, label="Select Input:")
        toggle_input_label.SetForegroundColour(WHITE)
        toggle_input_select_sizer.Add(toggle_input_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.toggle_input_from = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.toggle_input_from.SetBackgroundColour(DARK_GRAY)
        self.toggle_input_from.SetForegroundColour(WHITE)
        toggle_input_select_sizer.Add(self.toggle_input_from, 0, wx.ALL, 5)

        to_label = wx.StaticText(self, label="to")
        to_label.SetForegroundColour(WHITE)
        toggle_input_select_sizer.Add(to_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.toggle_input_to = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.toggle_input_to.SetBackgroundColour(DARK_GRAY)
        self.toggle_input_to.SetForegroundColour(WHITE)
        toggle_input_select_sizer.Add(self.toggle_input_to, 0, wx.ALL, 5)

        self.apply_toggle_input_btn = wx.Button(self, label="Apply to Selected Inputs")
        self.apply_toggle_input_btn.Bind(wx.EVT_BUTTON, self.on_apply_to_toggle_inputs)
        toggle_input_select_sizer.Add(self.apply_toggle_input_btn, 0, wx.ALL, 5)

        grid.Add(toggle_input_select_sizer, pos=(0, 0), flag=wx.ALL, border=5)
        traps_label = wx.StaticText(self, label="Audio Traps")
        traps_label.SetForegroundColour(WHITE)

        grid.Add(traps_label, pos=(1, 0), flag=wx.ALL, border=5)
        faults_label = wx.StaticText(self, label="Audio Faults")
        faults_label.SetForegroundColour(WHITE)
        grid.Add(faults_label, pos=(1, 1), flag=wx.ALL, border=5)

        # Group notifications by type for better organization
        notification_groups = [
            # Channel Loss
            ["Channel 1 Audio Loss", "Channel 2 Audio Loss", "Channel 3 Audio Loss", "Channel 4 Audio Loss",
             "Channel 5 Audio Loss", "Channel 6 Audio Loss", "Channel 7 Audio Loss", "Channel 8 Audio Loss",
             "Channel 9 Audio Loss", "Channel 10 Audio Loss", "Channel 11 Audio Loss", "Channel 12 Audio Loss",
             "Channel 13 Audio Loss", "Channel 14 Audio Loss", "Channel 15 Audio Loss", "Channel 16 Audio Loss"],

            # Channel Over
            ["Channel 1 Audio Over", "Channel 2 Audio Over", "Channel 3 Audio Over", "Channel 4 Audio Over",
             "Channel 5 Audio Over", "Channel 6 Audio Over", "Channel 7 Audio Over", "Channel 8 Audio Over",
             "Channel 9 Audio Over", "Channel 10 Audio Over", "Channel 11 Audio Over", "Channel 12 Audio Over",
             "Channel 13 Audio Over", "Channel 14 Audio Over", "Channel 15 Audio Over", "Channel 16 Audio Over"],

            # Channel Silence
            ["Channel 1 Audio Silence", "Channel 2 Audio Silence", "Channel 3 Audio Silence", "Channel 4 Audio Silence",
             "Channel 5 Audio Silence", "Channel 6 Audio Silence", "Channel 7 Audio Silence", "Channel 8 Audio Silence",
             "Channel 9 Audio Silence", "Channel 10 Audio Silence", "Channel 11 Audio Silence",
             "Channel 12 Audio Silence",
             "Channel 13 Audio Silence", "Channel 14 Audio Silence", "Channel 15 Audio Silence",
             "Channel 16 Audio Silence"],

            # Group Mono
            ["Group 1 Audio Mono 1 and 2", "Group 1 Audio Mono 3 and 4",
             "Group 2 Audio Mono 1 and 2", "Group 2 Audio Mono 3 and 4",
             "Group 3 Audio Mono 1 and 2", "Group 3 Audio Mono 3 and 4",
             "Group 4 Audio Mono 1 and 2", "Group 4 Audio Mono 3 and 4"],

            # Group Phase Reverse
            ["Group 1 Audio PhaseRev 1 and 2", "Group 1 Audio PhaseRev 3 and 4",
             "Group 2 Audio PhaseRev 1 and 2", "Group 2 Audio PhaseRev 3 and 4",
             "Group 3 Audio PhaseRev 1 and 2", "Group 3 Audio PhaseRev 3 and 4",
             "Group 4 Audio PhaseRev 1 and 2", "Group 4 Audio PhaseRev 3 and 4"]
        ]

        row = 1
        for group in notification_groups:
            for notification_type in group:
                type_label = wx.StaticText(self, label=notification_type)
                type_label.SetForegroundColour(WHITE)
                grid.Add(type_label, pos=(row+1, 0), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

                combobox = wx.ComboBox(self, choices=["False", "True"], style=wx.CB_READONLY)
                combobox.SetSelection(1)  # Default to True
                combobox.SetBackgroundColour(DARK_GRAY)
                combobox.SetForegroundColour(WHITE)

                # Store the combobox with its var id
                self.comboboxes[combobox] = self.AUDIO_NOTIFICATIONS[notification_type]

                grid.Add(combobox, pos=(row+1, 1), flag=wx.ALL, border=5)
                row += 1

            # Add a separator between groups
            if group != notification_groups[-1]:
                separator = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
                grid.Add(separator, pos=(row+1, 0), span=(1, 2), flag=wx.EXPAND | wx.ALL, border=5)
                row += 1

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

    def update_status(self, message, pane=0):
        self.main_frame.SetStatusText(message, pane)

    def on_toggle_all(self, evt):
        for combobox in self.comboboxes:
            if self.toggle_flag:
                combobox.SetSelection(0)  # Set to False
            else:
                combobox.SetSelection(1)  # Set to True
        self.toggle_flag = not self.toggle_flag

    def error_alert(self, message: str) -> None:
        dlg: wx.MessageDialog = wx.MessageDialog(self, message, "Error", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def on_apply_to_inputs(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        from_input = self.input_from.GetValue()
        to_input = self.input_to.GetValue()
        from_channel = self.channel_start.GetValue()
        to_channel = self.channel_end.GetValue()
        from_pair = self.pair_start.GetSelection()
        to_pair = self.pair_end.GetSelection()
        if from_input > to_input:
            self.error_alert("Starting input must be less than or equal to ending input.")
            return
        if from_channel > to_channel:
            self.error_alert("Starting channel must be less than or equal to ending input.")
            return
        if from_pair > to_pair:
            self.error_alert("Starting pair must be less than or equal to ending input.")
            return
        threading.Thread(target=self._apply_to_inputs_thread, args=(ip, from_input, to_input, from_channel, to_channel, from_pair, to_pair)).start()

    def _apply_to_inputs_thread(self, ip, from_input, to_input, from_channel, to_channel, from_pair, to_pair):
        self.apply_input_btn.Disable()
        self.update_status(f"Applying config to inputs {from_input} / {to_input}")

        for input_num in range(from_input, to_input + 1):
            self.update_status(f"Applying configuration to input {input_num} / {to_input}")
            for channel_num in range(from_channel, to_channel + 1):
                for spinctrl, var_id in self.channel_controls.items():
                    value = spinctrl.GetValue()
                    var_id = var_id.replace("x", str(input_num - 1)).replace("y", str(channel_num-1)) # -1 due to 0 indexed var ids
                    #print(var_id)
                    url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                    self.http.get(url,)

            for pair_num in range(from_pair, to_pair + 1):
                for spinctrl, var_id in self.pair_controls.items():
                    value = spinctrl.GetValue()
                    var_id = var_id.replace("x", str(input_num - 1)).replace("y", str(pair_num)) # No -1 as combobox is 0 indexed
                    #print(var_id)
                    url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                    self.http.get(url)

        self.apply_input_btn.Enable()
        self.update_status(f"Successfully applied config to inputs {from_input} to {to_input} :)")

    def on_apply_to_toggle_inputs(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        from_input = self.toggle_input_from.GetValue()
        to_input = self.toggle_input_to.GetValue()
        if from_input > to_input:
            self.error_alert("Starting input must be less than or equal to ending input.")
            return
        threading.Thread(target=self._apply_to_toggle_inputs_thread, args=(ip, from_input, to_input)).start()

    def _apply_to_toggle_inputs_thread(self, ip, from_input, to_input):
        self.apply_toggle_input_btn.Disable()
        self.update_status(f"Applying config to inputs {from_input} / {to_input}")

        for input_num in range(from_input, to_input + 1):
            self.update_status(f"Applying configuration to input {input_num} / {to_input}")
            for combobox, var_id in self.comboboxes.items():
                value = combobox.GetSelection()
                var_id = var_id.replace("x", str(input_num - 1))
                #print(var_id)
                url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                self.http.get(url)

        self.apply_toggle_input_btn.Enable()
        self.update_status(f"Successfully applied config to inputs {from_input} to {to_input} :)")

    def load_values(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        # Get the load values
        input_num = self.input.GetValue()
        channel = self.channel.GetValue()
        pair = self.pair.GetSelection() + 1 # As selection starts from 0
        threading.Thread(target=self._load_values_thread, args=(ip, input_num, channel, pair)).start()

    def _load_values_thread(self, ip, input_num, channel, pair):
        self.load_btn.Disable()
        self.update_status(f"Loading values from card for input {input_num}")

        # Load channel settings for the selected input's selected channel
        for i, (spin, var_id) in enumerate(self.channel_controls.items()):
            var_id_formatted = var_id.replace("x", str(input_num - 1)).replace("y", str(channel - 1))
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{var_id_formatted}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(spin.SetValue, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {var_id_formatted}.")
                continue

        # Load pair settings for the selected input's selected pair
        for i, (spin, var_id) in enumerate(self.pair_controls.items()):
            var_id_formatted = var_id.replace("x", str(input_num - 1)).replace("y", str(pair - 1))
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{var_id_formatted}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(spin.SetValue, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {var_id_formatted}.")
                continue

        # Load Values for combobox
        for box, varid in self.comboboxes.items():
            varid = varid.replace("x", str(input_num))
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{varid}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(box.SetSelection, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {varid}.")
                continue
        self.load_btn.Enable()
        self.update_status("Successfully loaded values from Card")


class AdvancedNotify(wx.ScrolledWindow):
    """Advanced Notify panel (window)"""

    # Advanced Notify parameters
    # Dictionary mapping notification types to their var_ids
    ADVANCED_NOTIFICATIONS = {
        # Advanced Video Traps
        "APL Above Max": "560.x.0@i",
        "APL Below Min": "560.x.1@i",
        "PPL Max above Threshold": "560.x.2@i",
        "PPL Min below Threshold": "560.x.3@i",
        "Loss of Closed Caption 1": "560.x.4@i",
        "Loss of Closed Caption 2": "560.x.5@i",
        "Loss of Closed Caption 3": "560.x.6@i",
        "Loss of Closed Caption 4": "560.x.7@i",
        "Loss of Text 1": "560.x.8@i",
        "Loss of Text 2": "560.x.9@i",
        "Loss of Text 3": "560.x.10@i",
        "Loss of Text 4": "560.x.11@i",
        "Loss of 708 Service 1": "560.x.12@i",
        "Loss of 708 Service 2": "560.x.13@i",
        "Loss of 708 Service 3": "560.x.14@i",
        "Loss of 708 Service 4": "560.x.15@i",
        "Loss of 708 Service 5": "560.x.16@i",
        "Loss of 708 Service 6": "560.x.17@i",
        "Loss of 708 Service 7": "560.x.18@i",
        "Loss of 708 Service 8": "560.x.19@i",
        "Loss of 708 Service 9": "560.x.20@i",
        "Loss of 708 Service 10": "560.x.21@i",
        "Loss of 708 Service 11": "560.x.22@i",
        "Loss of 708 Service 12": "560.x.23@i",
        "Loss of 708 Service 13": "560.x.24@i",
        "Loss of 708 Service 14": "560.x.25@i",
        "Loss of 708 Service 15": "560.x.26@i",
        "Loss of 708 Service 16": "560.x.27@i",
        "Loss of SMPTE AFD": "560.x.28@i",
        "SMPTE AFD Value Change": "560.x.29@i",
        "Loss of Video Index": "560.x.30@i",
        "Video Index Value Change": "560.x.31@i",
        "Loss of CC Waveform": "560.x.32@i",
        "Loss of Program Rating": "560.x.33@i",
        "Change of Program Rating": "560.x.34@i",
        "Loss of SID": "560.x.35@i",
        "Loss of VITC": "560.x.36@i",
        "Loss of VITC Waveform": "560.x.37@i",
        "Loss of WSS": "560.x.38@i",
        "Loss of Extended Data Services": "560.x.39@i",
        "Loss of World Standard Teletext": "560.x.40@i",
        "SCTE 104 Program Start": "560.x.41@i",
        "SCTE 104 Program End": "560.x.42@i",
        "SCTE 104 Chapter Start": "560.x.43@i",
        "SCTE 104 Chapter End": "560.x.44@i",
        "SCTE 104 Provider Ad Start": "560.x.45@i",
        "SCTE 104 Provider Ad End": "560.x.46@i",
        "SCTE 104 Distributor Ad Start": "560.x.47@i",
        "SCTE 104 Distributor Ad End": "560.x.48@i",
        "SCTE 104 Placement Op Start": "560.x.49@i",
        "SCTE 104 Placement Op End": "560.x.50@i",
        "SCTE 104 Break Start": "560.x.51@i",
        "SCTE 104 Break End": "560.x.52@i",
        "SCTE 104 Web Restrict": "560.x.53@i",
        "SCTE 104 Region Blackout": "560.x.54@i",
        "SCTE 104 Splice Start Normal": "560.x.55@i",
        "SCTE 104 Splice Start Immediate": "560.x.56@i",
        "SCTE 104 Splice End Normal": "560.x.57@i",
        "SCTE 104 Splice End Immediate": "560.x.58@i",
        "SCTE 104 Splice Cancel": "560.x.59@i",
        "Video Standard Change": "560.x.60@i",
        "Video Standard Mismatch": "560.x.61@i",
        "SCTE 104 Content Identification": "560.x.62@i",
        "Loss of LTC": "560.x.63@i",
        "LTC Frozen": "560.x.64@i",
        "LTC Jumping": "560.x.65@i",
        "Chroma Subsampling Mismatch": "560.x.66@i",
        "Loss of DVB": "560.x.67@i",
        "Loss of SCTE 27": "560.x.68@i",
        "Storage Aspect Ratio Mismatch": "560.x.69@i",
        "Display Aspect Ratio Mismatch": "560.x.70@i",
        "Loss of Caption Data": "560.x.71@i",
        "Loss of Caption Content": "560.x.72@i",
    }

    def __init__(self, notebook: wx.Notebook, main_frame, wxconfig: wx.ConfigBase, http_thread):
        """Initialize our main application frame."""
        wx.ScrolledWindow.__init__(self, parent=notebook)
        self.main_frame = main_frame
        self.http = http_thread
        self.wxconfig = wxconfig
        self.SetBackgroundColour(DARK_GRAY)
        self.toggle_flag = True
        self.comboboxes: Dict[wx.ComboBox, str] = {}

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        top_vbox = wx.BoxSizer(wx.VERTICAL)
        btn_hbox = wx.BoxSizer()
        load_label = wx.StaticText(self, label="Load Values from input")
        load_label.SetForegroundColour(WHITE)

        self.input = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input.SetBackgroundColour(DARK_GRAY)
        self.input.SetForegroundColour(WHITE)
        self.load_btn = wx.Button(self, label="Load Values")
        self.load_btn.Bind(wx.EVT_BUTTON, self.load_values)

        btn_hbox.Add(load_label, flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        btn_hbox.Add(self.input, 0, wx.ALL, 10)
        btn_hbox.Add(self.load_btn, 0, wx.ALL, 10)

        input_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        input_label = wx.StaticText(self, label="Select Input:")
        input_label.SetForegroundColour(WHITE)
        input_select_sizer.Add(input_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.input_from = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input_from.SetBackgroundColour(DARK_GRAY)
        self.input_from.SetForegroundColour(WHITE)
        input_select_sizer.Add(self.input_from, 0, wx.ALL, 5)

        to_label = wx.StaticText(self, label="to")
        to_label.SetForegroundColour(WHITE)
        input_select_sizer.Add(to_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.input_to = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input_to.SetBackgroundColour(DARK_GRAY)
        self.input_to.SetForegroundColour(WHITE)
        input_select_sizer.Add(self.input_to, 0, wx.ALL, 5)

        self.apply_input_btn = wx.Button(self, label="Apply to Selected Inputs")
        self.apply_input_btn.Bind(wx.EVT_BUTTON, self.on_apply_to_inputs)
        input_select_sizer.Add(self.apply_input_btn, 0, wx.ALL, 5)

        top_vbox.Add(btn_hbox, 0, wx.TOP, 5)
        top_vbox.Add(input_select_sizer, 0, wx.TOP, 5)

        main_sizer.Add(top_vbox, 0, wx.ALL, 25)

        self.create_advanced_notify(main_sizer)

        self.SetSizer(main_sizer)
        self.SetScrollRate(20, 20)
        self.FitInside()

    def create_advanced_notify(self, main_sizer):
        # Advanced Notify header
        notify_label = wx.StaticText(self, label="Advanced Notify")
        font = notify_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        notify_label.SetFont(font)
        notify_label.SetForegroundColour(YELLOW)

        head_hbox = wx.BoxSizer()
        head_hbox.Add(notify_label, 0, wx.ALL, 5)

        self.toggle_all_button = wx.Button(self, label="Toggle All")
        self.toggle_all_button.Bind(wx.EVT_BUTTON, self.on_toggle_all)
        head_hbox.Add(self.toggle_all_button, 0, wx.CENTER | wx.LEFT, 25)

        main_sizer.Add(head_hbox, 0, wx.LEFT, 20)

        # Create a grid for the advanced notifications
        grid = wx.GridBagSizer(hgap=10, vgap=5)

        traps_label = wx.StaticText(self, label="Advanced Video Traps")
        traps_label.SetForegroundColour(WHITE)
        grid.Add(traps_label, pos=(0, 0), flag=wx.ALL, border=5)

        faults_label = wx.StaticText(self, label="Advanced Video Faults")
        faults_label.SetForegroundColour(WHITE)
        grid.Add(faults_label, pos=(0, 1), flag=wx.ALL, border=5)

        # Add all notifications to the grid
        row = 1
        for notification_type, var_id in self.ADVANCED_NOTIFICATIONS.items():
            type_label = wx.StaticText(self, label=notification_type)
            type_label.SetForegroundColour(WHITE)
            grid.Add(type_label, pos=(row, 0), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

            combobox = wx.ComboBox(self, choices=["False", "True"], style=wx.CB_READONLY)
            combobox.SetSelection(1)  # Default to True
            combobox.SetBackgroundColour(DARK_GRAY)
            combobox.SetForegroundColour(WHITE)

            # Store the combobox with its var id
            self.comboboxes[combobox] = var_id

            grid.Add(combobox, pos=(row, 1), flag=wx.ALL, border=5)
            row += 1

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

    def update_status(self, message, pane=0):
        self.main_frame.SetStatusText(message, pane)

    def on_toggle_all(self, evt):
        for combobox in self.comboboxes:
            if self.toggle_flag:
                combobox.SetSelection(0)  # Set to False
            else:
                combobox.SetSelection(1)  # Set to True
        self.toggle_flag = not self.toggle_flag

    def error_alert(self, message: str) -> None:
        dlg: wx.MessageDialog = wx.MessageDialog(self, message, "Error", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def on_apply_to_inputs(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        from_input = self.input_from.GetValue()
        to_input = self.input_to.GetValue()

        if from_input > to_input:
            self.error_alert("Starting input must be less than or equal to ending input.")
            return

        threading.Thread(target=self._apply_to_inputs_thread, args=(ip, from_input, to_input)).start()

    def _apply_to_inputs_thread(self, ip, from_input, to_input):
        self.apply_input_btn.Disable()
        self.update_status(f"Applying config to inputs {from_input} / {to_input}")

        for input_num in range(from_input, to_input + 1):
            self.update_status(f"Applying configuration to input {input_num} / {to_input}")
            for combobox, var_id in self.comboboxes.items():
                value = combobox.GetSelection()
                var_id = var_id.replace("x", str(input_num - 1))  # -1 due to 0 indexed var ids
                url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                self.http.get(url)

        self.apply_input_btn.Enable()
        self.update_status(f"Successfully applied config to inputs {from_input} to {to_input} :)")

    def load_values(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        # Get the input number
        input_num = self.input.GetValue()
        threading.Thread(target=self._load_values_thread, args=(ip, input_num)).start()

    def _load_values_thread(self, ip, input_num):
        self.load_btn.Disable()
        self.update_status(f"Loading values from card for input {input_num}")

        # Load values for comboboxes
        for box, var_id in self.comboboxes.items():
            var_id = var_id.replace("x", str(input_num - 1))  # -1 due to 0 indexed var ids
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{var_id}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(box.SetSelection, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {var_id}.")
                continue

        self.load_btn.Enable()
        self.update_status("Successfully loaded values from Card")

class AdvancedAudioNotify(wx.ScrolledWindow):
    """Advanced Audio Notify panel (window)"""

    # Advanced Audio Notify parameters
    # Dictionary mapping notification types to their var_ids
    ADVANCED_AUDIO_NOTIFICATIONS = {
        # Audio Loudness Traps
        "Audio Loudness Over Group 1 and 2 Program 1": "840.x.0@i",
        "Audio Loudness Over Group 1 and 2 Program 2": "840.x.1@i",
        "Audio Loudness Over Group 1 and 2 Program 3": "840.x.2@i",
        "Audio Loudness Over Group 1 and 2 Program 4": "840.x.3@i",
        "Audio Loudness Over Group 1 and 2 Program 5": "840.x.4@i",
        "Audio Loudness Over Group 1 and 2 Program 6": "840.x.5@i",
        "Audio Loudness Over Group 1 and 2 Program 7": "840.x.6@i",
        "Audio Loudness Over Group 1 and 2 Program 8": "840.x.7@i",
        "Audio Loudness Over Group 3 and 4 Program 1": "840.x.8@i",
        "Audio Loudness Over Group 3 and 4 Program 2": "840.x.9@i",
        "Audio Loudness Over Group 3 and 4 Program 3": "840.x.10@i",
        "Audio Loudness Over Group 3 and 4 Program 4": "840.x.11@i",
        "Audio Loudness Over Group 3 and 4 Program 5": "840.x.12@i",
        "Audio Loudness Over Group 3 and 4 Program 6": "840.x.13@i",
        "Audio Loudness Over Group 3 and 4 Program 7": "840.x.14@i",
        "Audio Loudness Over Group 3 and 4 Program 8": "840.x.15@i",
        "Audio Loudness Silence Group 1 and 2 Program 1": "840.x.16@i",
        "Audio Loudness Silence Group 1 and 2 Program 2": "840.x.17@i",
        "Audio Loudness Silence Group 1 and 2 Program 3": "840.x.18@i",
        "Audio Loudness Silence Group 1 and 2 Program 4": "840.x.19@i",
        "Audio Loudness Silence Group 1 and 2 Program 5": "840.x.20@i",
        "Audio Loudness Silence Group 1 and 2 Program 6": "840.x.21@i",
        "Audio Loudness Silence Group 1 and 2 Program 7": "840.x.22@i",
        "Audio Loudness Silence Group 1 and 2 Program 8": "840.x.23@i",
        "Audio Loudness Silence Group 3 and 4 Program 1": "840.x.24@i",
        "Audio Loudness Silence Group 3 and 4 Program 2": "840.x.25@i",
        "Audio Loudness Silence Group 3 and 4 Program 3": "840.x.26@i",
        "Audio Loudness Silence Group 3 and 4 Program 4": "840.x.27@i",
        "Audio Loudness Silence Group 3 and 4 Program 5": "840.x.28@i",
        "Audio Loudness Silence Group 3 and 4 Program 6": "840.x.29@i",
        "Audio Loudness Silence Group 3 and 4 Program 7": "840.x.30@i",
        "Audio Loudness Silence Group 3 and 4 Program 8": "840.x.31@i",
    }

    # Compressed Audio Notifications
    COMPRESSED_AUDIO_NOTIFICATIONS = {
        "Compressed Audio Loss Ch1/2 Grp1": "1009.x.4@i",
        "Compressed Audio Loss Ch3/4 Grp1": "1009.x.5@i",
        "Compressed Audio Loss Ch1/2 Grp2": "1009.x.6@i",
        "Compressed Audio Loss Ch3/4 Grp2": "1009.x.7@i",
        "Compressed Audio Loss Ch1/2 Grp3": "1009.x.8@i",
        "Compressed Audio Loss Ch3/4 Grp3": "1009.x.9@i",
        "Compressed Audio Loss Ch1/2 Grp4": "1009.x.10@i",
        "Compressed Audio Loss Ch3/4 Grp4": "1009.x.11@i",
        "Audio Type Change Ch1/2 Grp1": "1009.x.12@i",
        "Audio Type Change Ch3/4 Grp1": "1009.x.13@i",
        "Audio Type Change Ch1/2 Grp2": "1009.x.14@i",
        "Audio Type Change Ch3/4 Grp2": "1009.x.15@i",
        "Audio Type Change Ch1/2 Grp3": "1009.x.16@i",
        "Audio Type Change Ch3/4 Grp3": "1009.x.17@i",
        "Audio Type Change Ch1/2 Grp4": "1009.x.18@i",
        "Audio Type Change Ch3/4 Grp4": "1009.x.19@i",
    }

    def __init__(self, notebook: wx.Notebook, main_frame, wxconfig: wx.ConfigBase, http_thread):
        """Initialize our audio notify panel."""
        wx.ScrolledWindow.__init__(self, parent=notebook)
        self.main_frame = main_frame
        self.http = http_thread
        self.wxconfig = wxconfig
        self.SetBackgroundColour(DARK_GRAY)
        self.toggle_flag_loudness = True
        self.toggle_flag_compressed = True
        self.loudness_comboboxes: Dict[wx.ComboBox, str] = {}
        self.compressed_comboboxes: Dict[wx.ComboBox, str] = {}

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        top_vbox = wx.BoxSizer(wx.VERTICAL)
        btn_hbox = wx.BoxSizer()
        load_label = wx.StaticText(self, label="Load Values from input")
        load_label.SetForegroundColour(WHITE)

        self.input = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.input.SetBackgroundColour(DARK_GRAY)
        self.input.SetForegroundColour(WHITE)
        self.load_btn = wx.Button(self, label="Load Values")
        self.load_btn.Bind(wx.EVT_BUTTON, self.load_values)

        btn_hbox.Add(load_label, flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
        btn_hbox.Add(self.input, 0, wx.ALL, 10)
        btn_hbox.Add(self.load_btn, 0, wx.ALL, 10)



        top_vbox.Add(btn_hbox, 0, wx.TOP, 5)

        main_sizer.Add(top_vbox, 0, wx.ALL, 25)

        # Create both audio notification sections
        self.create_audio_loudness_notify(main_sizer)
        self.create_compressed_audio_notify(main_sizer)

        self.SetSizer(main_sizer)
        self.SetScrollRate(20, 20)
        self.FitInside()

    def create_audio_loudness_notify(self, main_sizer):
        # Audio Loudness Notify header
        notify_label = wx.StaticText(self, label="Audio Loudness Notify")
        font = notify_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        notify_label.SetFont(font)
        notify_label.SetForegroundColour(YELLOW)

        head_hbox = wx.BoxSizer()
        head_hbox.Add(notify_label, 0, wx.ALL, 5)

        self.toggle_all_loudness_button = wx.Button(self, label="Toggle All")
        self.toggle_all_loudness_button.Bind(wx.EVT_BUTTON, self.on_toggle_all_loudness)
        head_hbox.Add(self.toggle_all_loudness_button, 0, wx.CENTER | wx.LEFT, 25)

        main_sizer.Add(head_hbox, 0, wx.LEFT, 20)

        # Create a grid for the audio loudness notifications
        grid = wx.GridBagSizer(hgap=10, vgap=5)

        loudness_input_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        loudness_input_label = wx.StaticText(self, label="Select Input:")
        loudness_input_label.SetForegroundColour(WHITE)
        loudness_input_select_sizer.Add(loudness_input_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.loudness_input_from = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.loudness_input_from.SetBackgroundColour(DARK_GRAY)
        self.loudness_input_from.SetForegroundColour(WHITE)
        loudness_input_select_sizer.Add(self.loudness_input_from, 0, wx.ALL, 5)

        to_label = wx.StaticText(self, label="to")
        to_label.SetForegroundColour(WHITE)
        loudness_input_select_sizer.Add(to_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.loudness_input_to = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.loudness_input_to.SetBackgroundColour(DARK_GRAY)
        self.loudness_input_to.SetForegroundColour(WHITE)
        loudness_input_select_sizer.Add(self.loudness_input_to, 0, wx.ALL, 5)

        self.apply_loudness_input_btn = wx.Button(self, label="Apply to Selected Inputs")
        self.apply_loudness_input_btn.Bind(wx.EVT_BUTTON, self.on_apply_to_loudness_inputs)
        loudness_input_select_sizer.Add(self.apply_loudness_input_btn, 0, wx.ALL, 5)

        grid.Add(loudness_input_select_sizer, pos=(0, 0), flag=wx.ALL, border=5)

        traps_label = wx.StaticText(self, label="Audio Loudness Traps")
        traps_label.SetForegroundColour(WHITE)
        grid.Add(traps_label, pos=(1, 0), flag=wx.ALL, border=5)

        faults_label = wx.StaticText(self, label="Audio Loudness Faults")
        faults_label.SetForegroundColour(WHITE)
        grid.Add(faults_label, pos=(1, 1), flag=wx.ALL, border=5)

        # Add all notifications to the grid
        row = 1
        for notification_type, var_id in self.ADVANCED_AUDIO_NOTIFICATIONS.items():
            type_label = wx.StaticText(self, label=notification_type)
            type_label.SetForegroundColour(WHITE)
            grid.Add(type_label, pos=(row+1, 0), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

            combobox = wx.ComboBox(self, choices=["False", "True"], style=wx.CB_READONLY)
            combobox.SetSelection(1)  # Default to True
            combobox.SetBackgroundColour(DARK_GRAY)
            combobox.SetForegroundColour(WHITE)

            # Store the combobox with its var id
            self.loudness_comboboxes[combobox] = var_id

            grid.Add(combobox, pos=(row+1, 1), flag=wx.ALL, border=5)
            row += 1

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

    def create_compressed_audio_notify(self, main_sizer):
        # Compressed Audio Notify header
        notify_label = wx.StaticText(self, label="Compressed Audio Notify")
        font = notify_label.GetFont()
        font.PointSize += 6
        font = font.Bold()
        font = font.Italic()
        notify_label.SetFont(font)
        notify_label.SetForegroundColour(YELLOW)

        head_hbox = wx.BoxSizer()
        head_hbox.Add(notify_label, 0, wx.ALL, 5)

        self.toggle_all_compressed_button = wx.Button(self, label="Toggle All")
        self.toggle_all_compressed_button.Bind(wx.EVT_BUTTON, self.on_toggle_all_compressed)
        head_hbox.Add(self.toggle_all_compressed_button, 0, wx.CENTER | wx.LEFT, 25)

        main_sizer.Add(head_hbox, 0, wx.LEFT | wx.TOP, 20)

        # Create a grid for the compressed audio notifications
        grid = wx.GridBagSizer(hgap=10, vgap=5)

        compressed_input_select_sizer = wx.BoxSizer(wx.HORIZONTAL)
        compressed_input_label = wx.StaticText(self, label="Select Input:")
        compressed_input_label.SetForegroundColour(WHITE)
        compressed_input_select_sizer.Add(compressed_input_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.compressed_input_from = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.compressed_input_from.SetBackgroundColour(DARK_GRAY)
        self.compressed_input_from.SetForegroundColour(WHITE)
        compressed_input_select_sizer.Add(self.compressed_input_from, 0, wx.ALL, 5)

        to_label = wx.StaticText(self, label="to")
        to_label.SetForegroundColour(WHITE)
        compressed_input_select_sizer.Add(to_label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.compressed_input_to = wx.SpinCtrl(self, min=1, max=32, initial=1)
        self.compressed_input_to.SetBackgroundColour(DARK_GRAY)
        self.compressed_input_to.SetForegroundColour(WHITE)
        compressed_input_select_sizer.Add(self.compressed_input_to, 0, wx.ALL, 5)

        self.apply_compressed_input_btn = wx.Button(self, label="Apply to Selected Inputs")
        self.apply_compressed_input_btn.Bind(wx.EVT_BUTTON, self.on_apply_to_compressed_inputs)
        compressed_input_select_sizer.Add(self.apply_compressed_input_btn, 0, wx.ALL, 5)

        grid.Add(compressed_input_select_sizer, pos=(0, 0), flag=wx.ALL, border=5)

        traps_label = wx.StaticText(self, label="Compressed Audio Traps")
        traps_label.SetForegroundColour(WHITE)
        grid.Add(traps_label, pos=(1, 0), flag=wx.ALL, border=5)

        faults_label = wx.StaticText(self, label="Compressed Audio Faults")
        faults_label.SetForegroundColour(WHITE)
        grid.Add(faults_label, pos=(1, 1), flag=wx.ALL, border=5)

        # Add all notifications to the grid
        row = 1
        for notification_type, var_id in self.COMPRESSED_AUDIO_NOTIFICATIONS.items():
            type_label = wx.StaticText(self, label=notification_type)
            type_label.SetForegroundColour(WHITE)
            grid.Add(type_label, pos=(row+1, 0), flag=wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=5)

            combobox = wx.ComboBox(self, choices=["False", "True"], style=wx.CB_READONLY)
            combobox.SetSelection(1)  # Default to True
            combobox.SetBackgroundColour(DARK_GRAY)
            combobox.SetForegroundColour(WHITE)

            # Store the combobox with its var id
            self.compressed_comboboxes[combobox] = var_id

            grid.Add(combobox, pos=(row+1, 1), flag=wx.ALL, border=5)
            row += 1

        main_sizer.Add(grid, 0, wx.ALL | wx.LEFT, 25)

    def update_status(self, message, pane=0):
        self.main_frame.SetStatusText(message, pane)

    def on_toggle_all_loudness(self, evt):
        for combobox in self.loudness_comboboxes:
            if self.toggle_flag_loudness:
                combobox.SetSelection(0)  # Set to False
            else:
                combobox.SetSelection(1)  # Set to True
        self.toggle_flag_loudness = not self.toggle_flag_loudness

    def on_toggle_all_compressed(self, evt):
        for combobox in self.compressed_comboboxes:
            if self.toggle_flag_compressed:
                combobox.SetSelection(0)  # Set to False
            else:
                combobox.SetSelection(1)  # Set to True
        self.toggle_flag_compressed = not self.toggle_flag_compressed

    def error_alert(self, message: str) -> None:
        dlg: wx.MessageDialog = wx.MessageDialog(self, message, "Error", wx.OK | wx.ICON_ERROR)
        dlg.ShowModal()
        dlg.Destroy()

    def on_apply_to_loudness_inputs(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        from_input = self.loudness_input_from.GetValue()
        to_input = self.loudness_input_to.GetValue()

        if from_input > to_input:
            self.error_alert("Starting input must be less than or equal to ending input.")
            return

        threading.Thread(target=self._apply_to_loudness_inputs_thread, args=(ip, from_input, to_input)).start()

    def _apply_to_loudness_inputs_thread(self, ip, from_input, to_input):
        self.apply_loudness_input_btn.Disable()
        self.update_status(f"Applying config to input {from_input} / {to_input}")

        for input_num in range(from_input, to_input + 1):
            self.update_status(f"Applying configuration to input {input_num} / {to_input}")

            # Apply loudness settings
            for combobox, var_id in self.loudness_comboboxes.items():
                value = combobox.GetSelection()
                var_id = var_id.replace("x", str(input_num - 1))  # -1 due to 0 indexed var ids
                url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                self.http.get(url)

        self.apply_loudness_input_btn.Enable()
        self.update_status(f"Successfully applied audio config to inputs {from_input} to {to_input} :)")

    def on_apply_to_compressed_inputs(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        from_input = self.compressed_input_from.GetValue()
        to_input = self.compressed_input_to.GetValue()

        if from_input > to_input:
            self.error_alert("Starting input must be less than or equal to ending input.")
            return
        print("starting audio thread")
        threading.Thread(target=self._apply_to_compressed_inputs_thread, args=(ip, from_input, to_input)).start()

    def _apply_to_compressed_inputs_thread(self, ip, from_input, to_input):
        self.apply_loudness_input_btn.Disable()
        self.update_status(f"Applying config to inputs {from_input} / {to_input}")

        for input_num in range(from_input, to_input + 1):
            self.update_status(f"Applying configuration to input {input_num} / {to_input}")
            # Apply compressed audio settings
            for combobox, var_id in self.compressed_comboboxes.items():
                value = combobox.GetSelection()
                var_id = var_id.replace("x", str(input_num - 1))  # -1 due to 0 indexed var ids
                url = f"http://{ip}/v.api/apis/EV/SET/parameter/{var_id}/{value}"
                self.http.get(url)

        self.apply_loudness_input_btn.Enable()
        self.update_status(f"Successfully applied audio config to inputs {from_input} to {to_input} :)")

    def load_values(self, evt):
        ip = self.wxconfig.Read(IP_LOC, defaultVal="")  # Get IP from registry

        if ip == "":
            self.error_alert("IP not set. Try connecting first.")
            return

        # Get the input number
        input_num = self.input.GetValue()
        threading.Thread(target=self._load_values_thread, args=(ip, input_num)).start()

    def _load_values_thread(self, ip, input_num):
        self.load_btn.Disable()
        self.update_status(f"Loading audio values from card for input {input_num}")

        # Load values for loudness comboboxes
        for box, var_id in self.loudness_comboboxes.items():
            var_id = var_id.replace("x", str(input_num - 1))  # -1 due to 0 indexed var ids
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{var_id}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(box.SetSelection, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {var_id}.")
                continue

        # Load values for compressed audio comboboxes
        for box, var_id in self.compressed_comboboxes.items():
            var_id = var_id.replace("x", str(input_num - 1))  # -1 due to 0 indexed var ids
            url = f"http://{ip}/v.api/apis/EV/GET/parameter/{var_id}"
            op = self.http.get(url, block=True)
            op_content = json.loads(op.content)
            try:
                value = int(op_content.get("value", None))
                wx.CallAfter(box.SetSelection, value)
            except (ValueError, TypeError) as e:
                self.error_alert(f"Did not get expected value for parameter {var_id}.")
                continue

        self.load_btn.Enable()
        self.update_status("Successfully loaded audio values from Card")

if __name__ == "__main__":
    app = WIT.InspectableApp(DEBUG)
    app.SetAppName(APPNAME)
    app.SetVendorName(VENDORNAME)
    frame = AppFrame(DEBUG)
    app.MainLoop()
