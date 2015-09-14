from django.db import models
import ephem
from math import pi,cos

# The limit for rise/set of the objects.
ALT_LIMIT = 32.0
# The altitude of an object where we're a bit worried.
ALT_SOFT_LIMIT = 40.0

def genMWO(date=None):
   MWO = ephem.Observer()
   MWO.long = "-118.0590"
   MWO.lat = "34.2170"
   MWO.elev = 1579
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
   
   def __unicode__(self):
      return unicode(self.name)
   
   def rah(self):
      '''Get the RA in hh:mm:ss.ss format'''
      ra = ephem.hours(self.RA*pi/180.)
      ra = str(ra)
      if ra[1] == ':':  ra = '0'+ra
      return ra

   def decd(self):
      '''Get the Dec in dd:mm:ss.ss format'''
      dec = ephem.degrees(self.DEC*pi/180.)
      return str(dec)


   def genobj(self):
      '''Generate a pyephem object'''
      if self.objtype == "SS":
         # solar system object, no ra or dec
         star = getattr(ephem, self.name)
      else:
         star = ephem.FixedBody()
         star._ra = self.RA*pi/180.0
         star._dec = self.DEC*pi/180.0
         star._epoch = ephem.J2000
      return star

   def PrecRAh(self, date=None):
      '''Return the precessed RA to date'''
      MWO = genMWO(date)
      star = self.genobj()
      star.compute(MWO)
      return str(star.ra)

   def PrecDECd(self, date=None):
      '''Return the precessed Declination to date'''
      MWO = genMWO(date)
      star = self.genobj()
      star.compute(MWO)
      return str(star.dec)

   def hour_angle(self, date=None):
      MWO = genMWO(date)
      star = self.genobj()
      star.compute(MWO)
      return (MWO.sidereal_time() - star.ra)*180./pi/15.0

   def airmass(self, date):
      alt = self.altitude(date)
      if alt < 0:
         return "-1.0"
      airmass = 1.0/cos(pi/2 - alt)
      return "%.3f" % airmass

   def sdistance(self):
      dist = self.distance
      if dist < 1000.:
         return "%.1f" % (dist)
      if dist < 1e6:
         return "%.1fK" % (dist/1000)
      if dist < 1e9:
         return "%.1fM" % (dist/1e6)
      return "%.1fG" % (dist/1e9)

   def const(self):
      MWO = genMWO()
      star = self.genobj()
      star.compute(MWO)
      return ephem.constellation(star)[0]

   def altitude(self,date=None):
      '''Compute the altitude of the object'''
      MWO = genMWO(date)
      star = self.genobj()
      star.compute(MWO)
      return star.alt*180.0/pi

   def azimuth(self, date=None):
      '''Compute the altitude of the object'''
      MWO = genMWO(date)
      star = self.genobj()
      star.compute(MWO)
      return star.az*180.0/pi

   def srating(self):
      return "&#9734;"*self.rating

   def visible(self, date=None):
      return self.altitude(date) > ALT_LIMIT

   def low(self, date=None):
      return ALT_SOFT_LIMIT < self.altitude(date) < ALT_LIMIT

   def savename(self):
      '''return a name safe for filenames'''
      return self.name.replace(' ','_')

