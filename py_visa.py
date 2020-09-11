#-------------------------------------------------------------------------------
# Name:        py_visa.py
# Purpose:     Communicate and control test instruments using SCPI protocols
#
#
# Author:      FClemen
#
# Created:     15/04/2020
# Copyright:   (c) FClemen 2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------

# imports
import sys
import time
import inspect
import visa

rm = visa.ResourceManager()

# With actual instruments
DEBUG = 0         # Disable DEBUG when interfacing with NI TestStand
VirtualRun = 0    # Virtual execution without actual instruments

# Simulation
##DEBUG = 1
##VirtualRun = 1    # Virtual execution without actual instruments


# UUT Power Supply and DAQ GPIB address assignment
# UUT index based on TestStand RunState.TestSockets.MyIndex
gpib_address = {
               0 : {'ps':7,  'daq':11 },     # UUT1
               1 : {'ps':8,  'daq':12 },     # UUT2
               2 : {'ps':9,  'daq':13 },     # UUT3
               3 : {'ps':10, 'daq':14 },     # UUT4
               }

# When using multiple GPIB controller for better test time performance,
# change the gpib_com dictionary assignment. Format is
# gpib_com = {UUT: GPIB cable address}
# Important: Remember to connect the physical GPIB cable correctly.
gpib_com = {
    0:0, 1:0,                                           # GPIB0 assigned to control UUT1 & UUT2,
    #2:0, 3:0,                                          # GPIB0 for UUT3 & UUT4
    2:1, 3:1                                            # GPIB1 for UUT3 & UUT4
    }

# Class container to handle Agilent E3634A programmble power supple
class PowerSupply:
   def __init__(self, **kwargs):

      #print "kwargs=%s"%kwargs
      self.uut = kwargs['uut']                           # uut
      self.gpib_usb = gpib_com[self.uut]                 # GPIB US controller address number
      self.gpib_ps = gpib_address[self.uut]['ps']        # gpib address
      #self.resource = 'GPIB0::%s::INSTR' %self.gpib_ps
      self.resource = 'GPIB%s::%s::INSTR' %(self.gpib_usb, self.gpib_ps)

      self.current_limit = 1.5   # amperes

      # Power supply GPIB address for UUT #1
      if not VirtualRun:
         self.E3634A = rm.open_resource('%s' %self.resource)


   def measure_voltage(self, **kwargs):
      """ Measure the UUT programmable voltage supply output """
      if DEBUG: print "Measure voltage"
      if not VirtualRun:
         self.E3634A.write(':SOURce:CURRent:PROTection:CLEar')
         temp_values = self.E3634A.query_ascii_values(':MEASure:VOLTage:DC?')
         dc = temp_values[0]
         print dc                      # print out measured value for TestStand
         self.E3634A.close()
         rm.close()

   def measure_current(self, **kwargs):
      """ Measure UUT current"""
      #if DEBUG: print "Measure current"
      if not VirtualRun:
         temp_values = self.E3634A.query_ascii_values(':MEASure:CURRent:DC?')
         current = temp_values[0]
         print current                # print out measured value for TestStand
         self.E3634A.close()
         rm.close()

   def set_voltage(self, **kwargs):
      """ Set the Keysight E634A power supply """

      #if DEBUG: print "Setting Power Supply voltage to %s volts." %kwargs.get('voltage')
      self.voltage = kwargs['voltage']

      if not VirtualRun:
         # Generic set voltage
         self.E3634A.write(':SOURce:CURRent:PROTection:CLEar')
         if self.voltage > 24:
            self.E3634A.write(':SOURce:VOLTage:RANGe %s' % ('HIGH'))
            self.E3634A.write(':SOURce:CURRent:PROTection:LEVel %s' % ('MAXimum'))
         else:
            self.E3634A.write(':SOURce:VOLTage:RANGe %s' % ('LOW'))
            self.E3634A.write(':SOURce:CURRent:PROTection:LEVel %G' % (self.current_limit))

         self.E3634A.write(':APPLy %G,%G' % (self.voltage, self.current_limit))
         self.E3634A.write(':OUTPut:STATe %d' % (1))
         apply = self.E3634A.query(':APPLy?')

         if kwargs.get('measure')==1:
            time.sleep(0.1)               # Wait 100 ms before measure
            self.measure_voltage()
         else:
            # Show voltage setting. Do not print during measure due to NI TestStand
            print "Setting Power Supply voltage to %s volts." %kwargs.get('voltage')

         self.E3634A.close()
         rm.close()


# Class container to handle DAQ 34970A module 34907A 20 channel multiplexer in slot #1
class Multiplexer:

   def __init__(self, **kwargs):
      self.uut = kwargs['uut']                              # uut
      self.gpib_usb = gpib_com[self.uut]                    # GPIB USB controller address number
      self.gpib_daq = gpib_address[self.uut]['daq']         # gpib address
      #self.resource = 'GPIB0::%s::INSTR' %self.gpib_daq     # DAQ address for UUT#?
      self.resource = 'GPIB%s::%s::INSTR' %(self.gpib_usb, self.gpib_daq)     # DAQ address for UUT#?

      if not VirtualRun:
         self.v34970A = rm.open_resource('%s'%self.resource)

   def measure_enable_in(self, **kwargs):
      """ Measure the UUT Enable IN terminal voltage """
      if DEBUG: print "Measure enable IN"
      if not VirtualRun:
         #self.v34970A = rm.open_resource('%s'%self.resource)   # needed?
         readings = self.v34970A.query(':MEASure:VOLTage:DC? (%s)' % ('@119'))
         print readings.strip()                # printout for TeestStand
         self.v34970A.close()
         rm.close()

   def measure_enable_out(self, **kwargs):
      """ Measure the UUT Enable OUT terminal voltage """
      if DEBUG: print "Measure enable OUT"
      if not VirtualRun:
         self.v34970A.write(':CONFigure:VOLTage:DC %s,%s,(%s)' % ('AUTO', 'DEF', '@119:120'))
         readings = self.v34970A.query(':MEASure:VOLTage:DC? (%s)' % ('@120'))
         #print readings                        # printout for TestStand
         print readings.strip()                # printout for TestStand
         self.v34970A.close()
         rm.close()

   def measure_all_channels(self, **kwargs):
      """ Measure all the UUT output channels """
      if DEBUG: print "Measure ALL Channels"
      if not VirtualRun:
         self.v34970A.write(':CONFigure:VOLTage:DC %s,%s,(%s)' % ('AUTO', 'DEF', '@101:108'))
         readings = self.v34970A.query(':MEASure:VOLTage:DC? (%s)' % ('@101:108'))
         print readings.strip()                # printout for TestStand
         self.v34970A.close()
         rm.close()

   def configure_dmm(self, **kwargs):
      """ Configure DMM to read UUT Enable IN and Enable Out thru MUX 19 and MUX 20 respectively"""
      #print "Configure MUX to DMM mode"
      if not VirtualRun:
         self.v34970A.write(':CONFigure:VOLTage:DC %s,%s,(%s)' % ('AUTO', 'DEF', '@119:120'))
         self.v34970A.close()
         rm.close()


# Class container to handle DAQ 34970A module 34904A 4 x 8 Two-Wire Matrix Module used to mimic A2Z Power Test Point in slot #2
class PowerTestPoint:
   """
   Handles Power Matrix switching on DAQ slot #2
   Required parameters:
      uut = uut number
      ch = uut number of channels (eg: 8, 4, 2)
   """

   def __init__(self, **kwargs):
      self.uut = kwargs['uut']                                       # uut
      self.gpib_usb = gpib_com[self.uut]                             # GPIB USB controller address number
      self.gpib_daq = gpib_address[self.uut]['daq']                  # gpib address
      self.channels = kwargs['ch']                                   # number of channels
      #self.resource = 'GPIB0::%s::INSTR' %self.gpib_daq
      self.resource = 'GPIB%s::%s::INSTR' %(self.gpib_usb, self.gpib_daq)
      if not VirtualRun:
         self.v34970A = rm.open_resource('%s'%self.resource)

   def connect_even_ch(self, **kwargs):
      """ Connect power to EVEN UUT channnels """
      #if DEBUG: print "Connect PTP EVEN channels"
      if not VirtualRun:
         if self.channels == 8:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:218'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@211,213,215,217'))
         elif self.channels == 4:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:214'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@211,213'))
         elif self.channels == 2:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:212'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@211'))

         self.v34970A.close()
         rm.close()


   def connect_odd_ch(self, **kwargs):
      """ Connect power to ODD UUT channnels """
      #if DEBUG: print "Connect PTP ODD channels"
      if not VirtualRun:
         if self.channels == 8:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:218'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@212,214,216,218'))
         elif self.channels == 4:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:214'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@212,214'))
         elif self.channels == 2:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:212'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@212'))

         self.v34970A.close()
         rm.close()

   def connect_all_ch(self, **kwargs):
      """ Connect power to All UUT channnels """
      #if DEBUG: print "Connect PTP ALL channels"
      if not VirtualRun:
         if self.channels == 8:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:218'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@211:218'))
         elif self.channels == 4:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:214'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@211:214'))
         elif self.channels == 2:
            self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:212'))
            self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@211:212'))

         self.v34970A.close()
         rm.close()

   def disconnect_all_ch(self, **kwargs):
      """ Disconnect power to All UUT channnels """
      #if DEBUG: print "Disconnect PTP ALL channels"
      if not VirtualRun:
         self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:218'))                      # open maximum all 8 channels to be safe
##         if self.channels == 8:   self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:218'))
##         elif self.channels == 4: self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:214'))
##         elif self.channels == 2: self.v34970A.write(':ROUTe:OPEN (%s)' % ('@211:212'))
         self.v34970A.close()
         rm.close()

# Class container to handle DAQ 34970A module 34904A 4 x 8 Two-Wire Matrix Module used to mimic A2Z 5K ohm MinLoad array in slot #3
class MinLoad:
   def __init__(self, **kwargs):

      self.uut = kwargs['uut']                              # uut
      self.gpib_usb = gpib_com[self.uut]                    # GPIB USB controller address number
      self.gpib_daq = gpib_address[self.uut]['daq']         # gpib address
      #self.resource = 'GPIB0::%s::INSTR' %self.gpib_daq
      self.resource = 'GPIB%s::%s::INSTR' %(self.gpib_usb, self.gpib_daq)

      if not VirtualRun:
         self.v34970A = rm.open_resource('%s'%self.resource)

   #def minload_even_ch(self, ch=None):
   def minload_even_ch(self, **kwargs):
      """ Connect MinLoad to EVEN UUT channnels """
      #if DEBUG: print "Connect MinLoad EVEN channels"
      if not VirtualRun:
         self.v34970A.write(':ROUTe:OPEN (%s)' % ('@311:318'))
         self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@311,313,315,317'))
         self.v34970A.close()
         rm.close()

   def minload_odd_ch(self, **kwargs):
      """ Connect MinLoad to ODD UUT channnels """
      #if DEBUG: print "Connect MinLoad ODD channels"
      if not VirtualRun:
         self.v34970A.write(':ROUTe:OPEN (%s)' % ('@311:318'))
         self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@312,314,316,318'))
         self.v34970A.close()
         rm.close()

   def minload_all_ch(self, **kwargs):
      """ Connect MinLoad to ALL UUT channnels """
      #if DEBUG: print "Connect MinLoad ALL channels"
      if not VirtualRun:
         self.v34970A.write(':ROUTe:OPEN (%s)' % ('@311:318'))
         self.v34970A.write(':ROUTe:CLOSe (%s)' % ('@311:318'))
         self.v34970A.close()
         rm.close()

   #def minload_disconnect_all_ch(ch=None):
   def minload_disconnect_all_ch(**kwargs):
      """ Disconnect MinLoad to ALL UUT channnels """
      #if DEBUG: print "Disconnect MinLoad ALL channels"
      if not VirtualRun:
         self.v34970A.write(':ROUTe:OPEN (%s)' % ('@311:318'))
         self.v34970A.close()
         rm.close()

def help():
   """ Show the class methods and their usage """
   methods = []
   tab = ""
   # Determine the active module class names
   cls_members = inspect.getmembers(sys.modules[__name__], inspect.isclass)      # get the list of current module classes
   cls_names = [cls[0] for cls in cls_members]                                   # get the names of each class

   for cls in cls_names:
      methods = [m for m in dir(eval(cls)) if not m.startswith('__')]
      for method in methods:                                                     # display method and its __doc__
         #  Handle output format
         if len(method) > 24: tab = "\t"
         elif len(method) > 15: tab = "\t\t"
         else: tab = "\t\t\t"
         print "%s%s %s" %(method, tab, eval("%s.%s.__doc__"%(cls,method)))


def main(function, **kwargs):
   """  Execute the passed argument based on class method """

   method_exists = False

   # Need to determine if the passed method exists in any class.

   # Determine the active module class names
   cls_members = inspect.getmembers(sys.modules[__name__], inspect.isclass)      # get the list of current module classes
   cls_names = [cls[0] for cls in cls_members]                                   # get the names of each class
   #print cls_names

   # Lookup and execute the class method
   for cls in cls_names:
      if hasattr(eval('%s'%cls), function):                                       # method exists on class?
         method_exists = True

         if DEBUG:
            print "'%s.%s' exists." %(cls,function)

         # Execute the class method with the following format:
         # classname(uut#).method(params)
         cmd = "%s(**%s).%s(**%s)" %(cls, kwargs, function, kwargs)
         eval(cmd)                                                                 # execute the class method
         break

   return method_exists


def parse_args(arg):
   """ Parse system arguments to determine the method and the passed arguments"""
   #print "sys.argv = %s" %arg
   params = {}
   function = None
   try:
      args = arg.split("(")                                                         # get the function name from the params
      function = args[0]

      args = args[1].split(",")                                                     # determine the parameters passed to the function
      for param in args:
         e = param.split("=")
         if e[1].count(")"):
            e[1] = e[1].replace(")","")                                             # Remove the close bracket in the value

         if e[0] in ['voltage', 'current', 'value']:
            e[1] = float(e[1])                                                      # numeric params
         else:
            e[1] = int(e[1])
         params[e[0]]=(e[1])
   except:
      import traceback
      traceback.format_exc()
   finally:
      return function, params

if __name__ == '__main__':

   #tstart = time.time()
   try:

      argv = ['py_visa.py', 'set_voltage(uut= 0,voltage=5,measure=1)']              # default value for verification
      if len(sys.argv) > 1:                                                         # process system arguments
         argv = sys.argv

      # Handle bad arguments. Example when a space is added between params
      arg = ""
      for a in argv[1:]:
         arg = arg + a.strip()

      function, kwargs = parse_args(arg)
      #print "function = %s, args = %s" %(function, kwargs)

   except:
      import traceback
      print traceback.format_exc()

   #print "function=%s,kwargs=%s"%(function,kwargs)

   if not VirtualRun:
      if not main(function, **kwargs):
         #print "Invalid Arguments: function = %s, args = %s" %(function, kwargs)
         print "Supported py_visa.py commands..."
         help()

##   if DEBUG:
##      print "Time elapsed: %.5f seconds." %(time.time()-tstart)
