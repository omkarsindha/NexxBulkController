import json
import socket
import time
import os
import sys
import threading

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
        wx.Frame.__init__(self, parent=None, title=TITLE, size=(800, 800))
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

        # Set background color
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

        self.notebook.AddPage(self.page1, "System Notify")
        self.notebook.AddPage(self.page2, "Video Notify")

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
        except:
            raise Exception(
                f"{error} Cannot connect to {ip}. ")

    def on_reset(self, evt):
        self.ip_input.Clear()
        self.ip_input.Enable()
        self.connet_btn.Enable()
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
        main_sizer.Add(btn_hbox, 0, wx.ALL | wx.CENTER, 10)

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
        grid.Add(hbox3, pos=(0, 2),
                 flag=wx.TOP | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, border=10)

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

        main_sizer.Add(grid, 0, wx.ALL, 5)

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
        head_hbox.Add(self.toggle_all_button, 0, wx.CENTER | wx.LEFT, 25)

        main_sizer.Add(head_hbox, 0, wx.LEFT, 20)

        # Create a grid sizer for the combo boxes
        grid_sizer = wx.GridSizer(rows=0, cols=2, hgap=5, vgap=5)

        for notification, varid in self.NOTIFICATIONS.items():
            notification_label = wx.StaticText(self, label=notification)
            notification_label.SetForegroundColour(WHITE)
            grid_sizer.Add(notification_label, 0, wx.ALL, 5)

            combobox = wx.ComboBox(self, choices=["False", "True"], style=wx.CB_READONLY)
            combobox.SetSelection(1)  # Set "True" as the default selection
            combobox.SetBackgroundColour(DARK_GRAY)
            combobox.SetForegroundColour(WHITE)
            self.comboboxes[combobox] = varid
            grid_sizer.Add(combobox, 0, wx.ALL, 5)

        main_sizer.Add(grid_sizer, 0, wx.ALL, 5)

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
    """System Notify panel (window)"""
    def __init__(self, notebook: wx.Notebook, main_frame, wxconfig: wx.ConfigBase, http_thread):
        """Initialize our main application frame."""
        wx.ScrolledWindow.__init__(self, parent=notebook)
        self.main_frame = main_frame
        self.http = http_thread
        self.wxconfig = wxconfig
        self.SetBackgroundColour(DARK_GRAY)
        self.toggle_flag = True
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.notify_btn = wx.Button(self, label="Apply")

        main_sizer.Add(self.notify_btn, 0, wx.LEFT, 20)

        self.SetSizer(main_sizer)
        self.SetScrollRate(20, 20)

        # Fit the sizer to the virtual size of the scrolled window
        self.FitInside()

if __name__ == "__main__":
    app = WIT.InspectableApp(DEBUG)
    app.SetAppName(APPNAME)
    app.SetVendorName(VENDORNAME)
    frame = AppFrame(DEBUG)
    app.MainLoop()
