# -*- coding: utf-8 -*-

## \package globals.wizardhelper

# MIT licensing
# See: docs/LICENSE.txt


import wx

from dbr.language   import GT


## TODO: Doxygen
class ErrorTuple:
    def __init__(self, error_code=None, error_string=None):
        
        # FIXME: Shoule throw exception for wrong instance types???
        self.error_code = error_code
        self.error_string = error_string
    
    
    ## Same as dbr.functions.ErrorTuple.GetTuple
    def Get(self):
        return self.GetTuple()
    
    
    ## TODO: Doxygen
    def GetCode(self):
        return self.error_code
    
    
    ## TODO: Doxygen
    def GetString(self):
        return self.error_string
    
    
    ## TODO: Doxygen
    def GetTuple(self):
        return (self.error_code, self.error_string,)
    
    
    ## TODO: Doxygen
    def Set(self, error_code, error_string):
        # FIXME: Shoule throw exception for wrong instance types???
        self.error_code = error_code
        self.error_string = error_string
    
    
    ## TODO: Doxygen
    def SetCode(self, error_code):
        # FIXME: Should throw exception for wrong instance type???
        if not isinstance(error_code, int):
            return 1
        
        self.error_code = error_code
        
        return 0
    
    
    ## TODO: Doxygen
    def SetString(self, error_string):
        # FIXME: Should throw exception for wrong instance type???
        if not isinstance(error_string, (unicode, str)):
            return 1
        
        self.error_string = error_string
        
        return 0


## Retrieves a field/control from a page
#  
#  FIXME: field_type is currently unused
#  
#  \param page
#        \b \e dbr.wizard.WizardPage : The page to search
#  \param field_id
#        \b \e int : ID of desired field/control
#  \param field_type
#        \b \b wx.Window : The class type that field/control should be
#  \return
#        \b \e wx.Window : Field control matching field_id or None
def GetField(page, field_id, field_type=wx.Window):
    if isinstance(page, field_type) and page.GetId() == field_id:
        return page
    
    # Recursively check children
    children = page.GetChildren()
    if children:
        for C in children:
            field = GetField(C, field_id)
            
            if field and isinstance(field, field_type) and \
                    field.GetId() == field_id:
                return field
    
    return ErrorTuple(1, GT(u'Field ID does not exist or match any fields: {}').format(field_id))


## Retrieves the input value of a field/control
#  
#  FIXME: field_type is currently unused
#  
#  \param page_id
#        \b \e int : ID of desired page
#  \param field_id
#        \b \e int : ID of desired field/control
#  \param field_type
#        \b \b wx.Window : The class type that field/control should be
#  \param return
#        The retrieved value of the field/control or an error tuple
def GetFieldValue(page_id, field_id, field_type=wx.Window):
    
    wizard = wx.GetApp().GetTopWindow().GetWizard()
    
    page = wizard.GetPage(page_id)
    
    if not isinstance(page, wx.Window):
        # FIXME: Should have error id
        return ErrorTuple(1,
                GT(u'Page retrieved from page_id ({}) was not instance of a window/widget').format(page_id)
            )
    
    field = GetField(page, field_id)
    
    if isinstance(field, ErrorTuple):
        return field
    
    value_methods = {
        wx.Choice: field.GetStringSelection,
        wx.TextCtrl: field.GetValue,
        }
    
    for T in value_methods:
        if isinstance(field, T):
            return value_methods[T]()
    
    # FIXME: Should have error id
    return ErrorTuple(1,
            GT(u'Unrecognized field type: {} (ID: {})').format(type(field), field_id)
        )
