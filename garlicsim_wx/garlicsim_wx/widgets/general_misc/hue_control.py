import colorsys

import wx

from garlicsim_wx.widgets.general_misc.hue_selection_dialog \
     import HueSelectionDialog
from garlicsim_wx.general_misc import wx_tools
from garlicsim_wx.general_misc.emitters import Emitter


class HueControl(wx.Window):
    '''
    
    '''
    def __init__(self, parent, getter, setter, emitter, lightness, saturation,
                 size=(25, 10)):
        
        wx.Window.__init__(self, parent, size=size, style=wx.SIMPLE_BORDER)
        
        self.getter = getter
        self.setter = setter
                
        assert isinstance(emitter, Emitter)
        self.emitter = emitter
        
        self.lightness = lightness
        self.saturation = saturation
        
        self._pen = wx.Pen(wx.Color(0, 0, 0), width=0, style=wx.TRANSPARENT)
        
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_left_down)
        
        self.emitter.add_output(self.update)
        
    
    def on_paint(self, event):
        dc = wx.PaintDC(self)
        color = wx_tools.hls_to_wx_color(
            self.getter(),
            self.lightness,
            self.saturation
        )
        dc.SetBrush(wx.Brush(color))
        dc.SetPen(self._pen)
        dc.DrawRectangle(0, 0, *self.GetSize())
        dc.Destroy()
        
    
    def on_mouse_left_down(self, event):
        self.open_editing_dialog()
      
        
    def open_editing_dialog(self):
        old_hue = self.getter()
        
        hue_selection_dialog = \
            HueSelectionDialog(self.GetTopLevelParent(), self.getter,
                               self.setter, lightness=self.lightness,
                               saturation=self.saturation,
                               title='Select hue for step profile')
        
        self.emitter.add_output(hue_selection_dialog.update) # tododoc: put emitter in dialog
        try:
            hue_selection_dialog.ShowModal()
        finally:
            hue_selection_dialog.Destroy()
            gui_project.step_profiles_to_hues_modified_emitter.remove_output(
                hue_selection_dialog.update
            )

            
    def update(self):
        self.Refresh()

        
    def Destroy(self):
        self.emitter.remove_output(self.update)