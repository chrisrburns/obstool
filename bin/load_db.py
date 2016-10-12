#!/usr/bin/env python

'''Take a file with a list of objects, one objct per line and populate the
The script will query the DSS server and get the finder automatically.'''
import sys,os
os.environ['DJANGO_SETTINGS_MODULE'] = 'obstool.settings'
if 'OBSTOOL_DIR' not in os.environ:
   print "Please set your OBSTOOL_DIR environment variable"
   sys.exit(1)
sys.path.insert(0, os.environ['OBSTOOL_DIR'])
sys.path.insert(0, os.path.dirname(os.environ['OBSTOOL_DIR']))
import settings
from navigator.models import Object
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist
import string
import urllib
from astropy.io import ascii
import ephem
import Image
from math import pi
import cStringIO

url = "http://archive.stsci.edu/cgi-bin/dss_search?v=poss2ukstu_red&r=%f&d=%f&e=J2000&h=60.0&w=60.0&f=gif"

t = ascii.read(sys.argv[1])
epoch = ephem.date('2010/01/01')

for i in range(len(t)):
   args = {}
   name = t['name'][i]
   args['descr'] = t['descr'][i]
   ra = ephem.hours(t['RA'][i])
   dec = ephem.degrees(t['DEC'][i])
   star = ephem.FixedBody()
   star._ra = ra
   star._dec = dec
   star._epoch = epoch
   star.compute(ephem.J2000)
   args['RA'] = star.ra*180./pi
   args['DEC'] = star.dec*180./pi
   args['dark'] = bool(t['dark'][i])
   rating = t['ratin'][i]
   if rating:
      args['rating'] = len(rating)
   else:
      args['rating'] = 0
   args['size'] = t['size'][i]
   args['Mv'] = t['Mv'][i]
   args['objtype'] = t['type'][i]
   if not t['distance'][i]:
      args['distance'] = -1
   else:
      args['distance'] = t['distance'][i]

   try:
      o = Object.objects.get(name=name)
      for key in args:
         setattr(o, key, args[key])
      print "Found existing object",o.pk
   except ObjectDoesNotExist:
      print "Adding object"
      o = Object(name=name, **args)
      if args['objtype'] == 'SS':
         f = open('SS_default.png')
         o.finder.save('finder_'+o.savename()+'.png', ContentFile(f.read()))
         f.close()
      else:
         print "Fetching",url % (args['RA'],args['DEC'])
         u = urllib.urlopen(url % (args['RA'],args['DEC']))
         f = cStringIO.StringIO(u.read())
         u.close()
         im = Image.open(f)
         #f.close()
         x,y = im.size
         im2 = im.resize((x/2,y/2))
         f2 = cStringIO.StringIO()
         im2.save(f2, format='PNG')
         o.finder.save('finder_'+o.savename()+'.gif', ContentFile(f2.getvalue()))
         f.close()
         f2.close()
   o.save()
   print o.name + " loaded"

