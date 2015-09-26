from django.db import models
import ephem
from math import pi,cos
from obstool import settings

def genMWO(date=None):
   MWO = ephem.Observer()
   MWO.long = settings.OBSERVING_LONG
   MWO.lat = settings.OBSERVING_LAT
   MWO.elev = settings.OBSERVING_ELEV
   if date is not None:
      MWO.date = date
   else:
      MWO.date = ephem.now()
   return MWO

class Object(models.Model):

   name = models.CharField(max_length=50)
   descr = models.CharField(max_length=200)
   RA = models.FloatField()   # Right-ascention in decimal degrees
   DEC = models.FloatField()  # declination in decimal degrees
   size = models.CharField(max_length=10)  # separation/size
   Mv = models.CharField(max_length=10)    # apparent magnitude
   objtype = models.CharField(max_length=10)
   distance = models.FloatField() # Distance in LY
   rating = models.IntegerField() # 1-5 star rating.
   dark = models.BooleanField()   # Dark skies required?
   finder = models.ImageField(upload_to='finders', default='default.gif')
   epoch = None
   
   
   def __unicode__(self):
      return unicode(self.name)
   
   def rah(self):
      '''Get the RA in hh:mm:ss.ss format, returns a string'''
      if self.objtype == 'PARK':
         # Park position is at meridian
         obs = genMWO(self.MWO)
         ra = obs.sidereal_time()
      else:
         ra = ephem.hours(self.RA*pi/180.)
      ra = str(ra)
      if ra[1] == ':':  ra = '0'+ra
      return ra

   def decd(self):
      '''Get the Dec in dd:mm:ss.ss format, returns a string'''
      dec = ephem.degrees(self.DEC*pi/180.)
      return str(dec)


   def genobj(self):
      '''Generate a pyephem object'''
      if self.objtype == "SS":
         # solar system object, no ra or dec
         star = getattr(ephem, self.name)()
      elif self.objtype == "PARK":
         MWO = genMWO(self.epoch)
         star = ephem.FixedBody()
         star._ra = MWO.sidereal_time()
         star._dec = self.DEC*pi/180.0
         star._epoch = ephem.date(self.epoch)
      else:
         star = ephem.FixedBody()
         star._ra = self.RA*pi/180.0
         star._dec = self.DEC*pi/180.0
         star._epoch = ephem.J2000
      return star

   def PrecRAh(self):
      '''Return the precessed RA to date as an ephem angle'''
      MWO = genMWO(self.epoch)
      star = self.genobj()
      star.compute(MWO)
      return (star.ra)

   def PrecDecd(self):
      '''Return the precessed Declination to date as an ephem angle'''
      #if self.objtype == 'PARK':
      #   return ephem.degrees('34:13:28.8')
      MWO = genMWO(self.epoch)
      star = self.genobj()
      star.compute(MWO)
      return (star.dec)

   def hour_angle(self):
      '''Returns the hour-angle in decimal hours'''
      #if self.obj == 'PARK':
      #   return 0.0
      MWO = genMWO(self.epoch)
      star = self.genobj()
      star.compute(MWO)
      return (MWO.sidereal_time() - star.ra)*180./pi/15.0

   def airmass(self):
      '''returns a string value of the airmass'''
      alt = self.altitude()
      if alt < 0:
         return "-1.0"
      airmass = 1.0/cos(pi/2 - alt)
      return "%.3f" % airmass

   def sdistance(self):
      '''Returns the distance as a nicely formatted string.'''
      dist = self.distance
      if self.objtype == 'SS':
         MWO = genMWO(self.epoch)
         star = self.genobj()
         star.compute(MWO)
         return "%.4f AU" % (star.earth_distance)
      if dist < 1000.:
         return "%.1f ly" % (dist)
      if dist < 1e6:
         return "%.1f Kly" % (dist/1000)
      if dist < 1e9:
         return "%.1f Mly" % (dist/1e6)
      return "%.1f Gly" % (dist/1e9)

   def const(self):
      '''Returns the constellation the object is current in
      as a 3-letter code.'''
      MWO = genMWO(self.epoch)
      star = self.genobj()
      star.compute(MWO)
      return ephem.constellation(star)[0]

   def altitude(self):
      '''Compute the altitude of the object in degrees'''
      MWO = genMWO(self.epoch)
      star = self.genobj()
      star.compute(MWO)
      return star.alt*180.0/pi

   def azimuth(self):
      '''Compute the altitude of the object in degrees'''
      if self.objtype == 'PARK':
         # dome azimuth is NE in park position
         return 45.0
      MWO = genMWO(self.epoch)
      star = self.genobj()
      star.compute(MWO)
      return star.az*180.0/pi

   def ssize(self):
      '''Return a string formatted size of the object'''
      if self.objtype == 'SS':
         MWO = genMWO(self.epoch)
         star = self.genobj()
         star.compute(MWO)
         return '%.2f"' % (star.radius*180./pi*3600)
      return self.size

   def sMv(self):
      '''Return a formatted string for the star's magnitude.'''
      if self.objtype == 'SS':
         MWO = genMWO(self.epoch)
         star = self.genobj()
         star.compute(MWO)
         return '%.2f' % (star.mag)

   def srating(self):
      '''Returns an HTML star rating.'''
      return "&#9734;"*self.rating

   def visible(self):
      '''Returns True/False whether object is visible'''
      return self.altitude() > settings.ALT_LIMIT

   def settime(self):
      '''Remaining time before the object sets, nicely formatted.'''
      MWO = genMWO(self.epoch)
      MWO.horizon = ephem.degrees(settings.ALT_LIMIT*pi/180.)
      star = self.genobj()
      try:
         settime = MWO.next_setting(star)
      except:
         return "-"
      dt = (settime - self.epoch)*24   # hours
      if dt >= 1:
         return "%.1f h" % dt
      dt = dt*60                       #minutes
      if dt >=1 :
         return "%.1f m" % dt
      dt = dt*60                       # seconds
      return "%.1f s" % dt


   def low(self):
      return settings.ALT_SOFT_LIMIT < self.altitude() < settings.ALT_LIMIT

   def savename(self):
      '''return a name safe for filenames'''
      return self.name.replace(' ','_')

