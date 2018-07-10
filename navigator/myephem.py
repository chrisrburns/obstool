from astropy.coordinates import EarthLocation, SkyCoord, AltAz
from astropy.coordinates import solar_system_ephemeris, get_body
solar_system_ephemeris.set('de432s')  # to get pluto
import ephem
from astropy.time import Time
from astropy.units import degree
from scipy.optimize import brentq
from numpy import array,nan,pi

def gen_obs(name, date=None):
   '''Generate a pyephem Observer object from named location.'''
   _obs = EarthLocation.of_site(name)
   obs = ephem.Observer()
   obs.long = _obs.longitude.to('radian').value
   obs.lat = _obs.latitude.to('radian').value
   obs.elev = _obs.height.value
   if date is None:
      obs.date = ephem.now()
   else:
      obs.date = ephem.Date(date.to_datetime)
   return obs

class Observer:

   def __init__(self, location='mwo', date=None, horizon=None):
      self.location = EarthLocation.of_site(location)
      if date is None:
         self.date = Time.now()
      else:
         self.date = date
      self.obs = gen_obs(location)

      if horizon is None:
         horizon = 0*degree
      else:
         if getattr(horizon, 'unit', None) is None:
            # assume in degress
            horizon = horizon*degree
      self.horizon = horizon

   def sidereal_time(self):
      return self.date.sidereal_time(self.location.longitude)

   def altaz(self, obj, date=None):
      '''Compute the altitude and azimuth of an objects.'''
      if date is None:
         date = self.date
      if isinstance(obj, SkyCoord):
         # possibly many objects
         altaz = obj.transform_to(AltAz(obstime=date, 
            location=self.location))
         return ((altaz.alt - self.horizon).value, altaz.az.value)
      else:
         # It is a navigator.models.Object
         if obj.objtype == "SS":
            _obj = getattr(ephem, obj.name)()
            self.obs.date = ephem.Date(date.to_datetime())
            self.obs.compute(_obj)
            return _obj.alt*180.0/pi
         else:
            # simple RA/DEC
            _obj = SkyCoord(obj.RA, obj.DEC, unit=degree, frame='icrs')
            altaz = _obj.transform_to(AltAz(obstime=date,
               location=self.location))
            return ((altaz.alt - self.horizon).value, altaz.az.value)

   def altitude(self, obj, date=None):
      '''compute the altitude of the object for a given time.'''
      return self.altaz(obj, date)[0]

   def azimuth(self, obj, date=None):
      '''compute the altitude of the object for a given time.'''
      return self.altaz(obj, date)[1]

   def circumpolar(self, obj):
      '''Is the object always above the horizon?'''
      return greater(obj.dec, 90*degree-self.location.latitude + self.horizon)

   def never_rises(self, obj):
      return less(obj.dec, location.latitude - 90*degree + self.horizon)

   def next_rising(self, obj):
      # here use ephem, as it is much faster
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

