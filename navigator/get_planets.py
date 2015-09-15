'''This module uses the NASA solar system simulator to fetch an image of
a planetary body as seen from earth at a particular time.'''

base_url = "http://space.jpl.nasa.gov/cgi-bin/wspace?tbody=%s&vbody=399&month=%d&day=%d&year=%d&hour=%d&minute=%d&fovmul=1&rfov=%.4f&bfov=30&showac=1"

codes = {'Moon':'301',
         'Mercury':'199',
         'Venus':'299',
         'Mars':'499',
         'Jupiter':'599',
         'Saturn':'699',
         'Uranus':'799',
         'Neptune':'899',
         'Pluto':'999'}

import urllib
import Image
import cStringIO
import ephem
import datetime
from obstool import settings

def get_image(body, date, fov):
   '''Get the view of the astronomical body (see codes) on a given date
   (ephem.Date object) and with field of view in degrees.'''

   if not fov:
      fov = settings.FINDER_BASE_SIZE
   if body not in codes:
      raise ValueError, "Sorry, body must be a planet or moon"

   dt = date.datetime()
   try:
      url = base_url % (codes[body],
                                  dt.month,
                                  dt.day,
                                  dt.year,
                                  dt.hour,
                                  dt.minute,
                                  float(fov)*2/settings.FINDER_BASE_SIZE)

      u = urllib.urlopen(url)
   except:
      return None
    
   data = u.read()
   u.close()
   f = cStringIO.StringIO(data)
   im = Image.open(f)
   im2 = im.crop((200,25,600,425))
   f2 = cStringIO.StringIO()
   im2.save(f2, 'PNG')
   content = f2.getvalue()
   f.close()
   f2.close()
   return content


