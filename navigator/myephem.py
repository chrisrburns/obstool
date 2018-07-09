from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.coordinates import solar_system_ephemeris, get_body
solar_system_ephemeris.set('de432s')  # to get pluto
from astropy.time import Time
from astropy.units import degree
from scipy.optimize import brentq
from numpy import array,nan

class Observer:

   def __init__(self, location='mwo', date=None, horizon=None):
      self.location = EarthLocation.site_of(location)
      if date is None:
         self.date = Time.now()
      else:
         self.date = date

      if horizon is None:
         horizon = 0*degree
      else:
         if getattr(horizon, 'unit', None) is None:
            # assume in degress
            horizon = horizon*degree
      self.horizon = horizon

   def sidereal_time(self):
      return self.date.sidereal_time(self.location.longitude)

   def altitude(self, obj, date=None):
      '''compute the altitude of the object for a given time.'''
      if date is None:
         date = self.date
      altaz = obj.transform_to(AltAz(obstime=date, location=self.location))
      return altaz.alt - self.horizon

   def azimuth(self, obj, date=None):
      '''compute the altitude of the object for a given time.'''
      if date is None:
         date = self.date
      altaz = obj.transform_to(AltAz(obstime=date, location=self.location))
      return altaz.az

   def circumpolar(self, obj):
      '''Is the object always above the horizon?'''
      return greater(obj.dec, 90*degree-self.location.latitude + self.horizon)

   def never_rises(self, obj):
      return less(obj.dec, location.latitude - 90*degree + self.horizon)

   def next_rising(self, obj):
      t0 = self.date
      alt0 = self.altitude(obj, t0)
      if alt0 > 0:
         # already risen, so go ahead 12 hours
         t0 = t0 + 12*hour
      f = lambda x: self.altitude(obj, t0+x*hour) - horison
      return t0 + brentq(f, 0, 12)*hour

   def previous_rising(self, obj):
      t0 = self.date
      alt0 = self.altitude(obj, t0)
      if alt0 > 0:
         # already risen, so go ahead 12 hours
         t0 = t0 - 12*hour
      f = lambda x: self.altitude(obj, t0+x*hour).value
      return t0 + brentq(f, 0, 12)*hour

   def next_setting(self, obj):
      t0 = self.date
      alt0 = self.altitude(obj, t0)
      if alt0 < 0:
         # already set, so go ahead 12 hours
         t0 = t0 + 12*hour
      f = lambda x: self.altitude(obj, t0+x*hour).value
      return t0 + brentq(f, 0, 12)*hour

   def previous_setting(self, obj):
      t0 = self.date
      alt0 = self.altitude(obj, t0)
      if alt0 < 0:
         # already set, so go back 12 hours
         t0 = t0 - 12*hour
      f = lambda x: self.altitude(obj, t0+x*hour).value
      return t0 + brentq(f, 0, 12)*hour

class SkyObject:

   def __init__(self, name=None, RA=None, DEC=None, epoch="J2000"):
      if name is not None:
         if name not in solar_system_ephemeris.bodies:
            raise(ValueError("object {} not supported".format(name)))
         self.coord = get_body(name)
      elif RA is not None and DEC is not None:
         self.coord = SkyCoord(RA, DEC, frame='icrs', equinox=epoch)
      else:
         raise(ValueError("Either name or RA/DEC must be specified"))
