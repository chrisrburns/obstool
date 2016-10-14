# General utilities functions.
from ephem import degrees,hours
from math import pi

def string2RADEC(st):
   '''Given a string, try to convert into internal ephem angle.'''
   fields = map(str,st.strip().split())
   if len(fields) == 2:
      # Try RA DEC in decimal degrees
      try:
         RA,DEC = map(float, fields)
         return RA,DEC
      except:
         # Try as sexadecimal notation
         try:
            RA,DEC = hours(fields[0]),degrees(fields[1])
            return RA*180/pi,DEC*180/pi
         except:
            # Fail!
            return None,None
   elif len(fields) in [4,6]:
      # assume RA and DEC have the same number of fields
      try:
         nf = len(fields)
         RA = ":".join(fields[0:nf/2])
         DEC = ":".join(fields[nf/2:])
         RA,DEC = hours(RA)*180/pi,degrees(DEC)*180/pi
         return RA,DEC
      except:
         # Fail!
         return None,None
   else:
      # Dunno!
      return None,None


