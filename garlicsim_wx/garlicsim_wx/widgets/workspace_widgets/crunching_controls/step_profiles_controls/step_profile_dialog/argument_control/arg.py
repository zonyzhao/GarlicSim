import wx

from garlicsim_wx.general_misc import wx_tools



class Arg(wx.Panel):
    def __init__(self, argument_control, name, value=''):
        wx.Panel.__init__(self, argument_control)
        self.SetBackgroundColour(wx_tools.get_background_color())
        
        self.argument_control = argument_control
        self.name = name
        
        self.main_h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.name_static_text = wx.StaticText(self, label=('%s: ' % name))
        
        self.main_h_sizer.Add(self.name_static_text, 1,
                              wx.ALIGN_CENTER_VERTICAL)
        
        self.text_ctrl = wx.TextCtrl(self, size=(100, -1), value=value)
        
        self.main_h_sizer.Add(self.text_ctrl, 0,
                              wx.ALIGN_CENTER_VERTICAL)
        
        self.SetSizer(self.main_h_sizer)
        
        #self.main_h_sizer.Fit(self)