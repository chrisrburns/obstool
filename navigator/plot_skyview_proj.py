#!/usr/bin/env python

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure,SubplotParams
from matplotlib.patches import Circle
from numpy import *
from models import genMWO
import StringIO
import Image
import urllib
import pickle
try:
   import ephem3 as ephem
except:
   import ephem
import pickle

symbols = {'GC':r'$\oplus$',
           'SS':r'$\odot$',
           'Double':r':','Triple':r'$\therefore$',
           'E/RN':r'$\boxdot$','EN':r'$\boxdot$','EN-OC':r'$\boxdot$',
           'E/DN':r'$\boxdot$','RN':r'$\boxdot$','SNR':r'$\boxdot$',
           'PN':r'$\circ$','OC':r'$\varnothing$','QSO':r'$\cdot$'}

f = open('/Users/cburns/MtWilson/obstool/navigator/Conlines.pkl')
d = pickle.load(f)
f.close()

def osymb(s):
   '''returns an appropriate symbol to use based on object type.'''
   if s[0:2] == 'G-':
      # galaxy
      return r"$\S$"
   if s in symbols:
      return symbols[s]
   # default:
   return '.'

def RAhDecd2xy(RA,DEC,obs):
   o = ephem.FixedBody()
   o._ra = ephem.degrees(RA*15*pi/180)
   o._dec = ephem.degrees(DEC*pi/180)
   o._epoch = ephem.J2000
   o.compute(obs)
   clip=False 
   if o.alt*180.0/pi < 30: clip=True
   x = (pi/2-o.alt)*180/pi*sin(o.az)
   y = (pi/2-o.alt)*180/pi*cos(o.az)
   return (x,y,clip)



def plot_sky_map(objs, date=None, new_window=False, airmass_high=None,
      tel_alt=90, tel_az=45, imsize=5, crop=90):
   '''Plots the objects for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the first is the binary
   PNG file that is the graph, the second is the <map> HTML that will be used
   to make the points in the graph "hot spots"'''
   if date is None:
      date = ephem.now()
   else:
      date = ephem.Date(date)

   MWO = genMWO(date)

   # Setup the graph
   fig = Figure((imsize,imsize), frameon=False, 
         subplotpars=SubplotParams(left=0.00,right=1.0, bottom=0.0, top=1.))
   fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
   canvas = FigureCanvasAgg(fig)
   ax = fig.add_subplot(111)
   lines = []
   names = []
   ids = []
   maxrho = 0
   
   for obj in objs:
      obj.epoch = date
      theta = obj.azimuth()*pi/180
      rho = 90 - obj.altitude()
      maxrho = max(rho, maxrho)
      x = rho*sin(theta)
      y = rho*cos(theta)
      tobj = ax.text(x, y, osymb(obj.objtype), va='center', ha='center')
            
      lines.append(tobj)
      names.append(obj.name + "*"*obj.rating)
      ids.append(obj.pk)
   # Telescope pos
   theta = -(float(tel_az)*pi/180-pi/2)
   rho = 90 - float(tel_alt)
   ax.plot([rho*cos(theta)],[rho*sin(theta)], "o", ms=15, mfc='none', mec='red')
   ax.plot([rho*cos(theta)],[rho*sin(theta)], "o", ms=10, mfc='none', mec='red')

   # draw grid lines:
   for rho in arange(15,maxrho+16,15):
      c = Circle((0,0), radius=rho, ec='0.5', fc='none', zorder=0)
      ax.add_artist(c)
   for theta in arange(0,pi,pi/6):
      ax.plot([rho*cos(theta), rho*cos(theta+pi)],
              [rho*sin(theta),rho*sin(theta+pi)], '-', color='0.5', zorder=0)

   clipper=c
   ax.axis('off')
   ax.set_xlim(-100,100)
   ax.set_ylim(-100,100)

   # Try some constellations
   for cons in d:
      ras,decs = d[cons]
      xs,ys = [],[]
      draw = False
      for i in range(len(ras)):
         if ras[i] is not None:
            x,y,clip = RAhDecd2xy(ras[i],decs[i],MWO)
            if not clip:
               # at least part of constellation is visible
               draw = True
         else:
            x,y = None,None
         xs.append(x); ys.append(y)
      if draw:
         ax.plot(xs,ys, '-', color='0.8', zorder=0, clip_path=clipper)


   # Now we save to a string and also convert to a PIL image, so we can get 
   #  the size.
   output = StringIO.StringIO()
   canvas.print_figure(output, dpi=150, pad_inches=0)
   output.seek(0)
   img = Image.open(output)
   output2 = StringIO.StringIO()
   xsize,ysize = img.size
   img = img.crop((crop,crop,xsize-crop,ysize-crop))
   img.save(output2, 'PNG')
   img_str = 'data:image/png,' + urllib.quote(output2.getvalue())
   #output.seek(0)
   # Get the window coordinates of the points
   bboxes = [o.get_window_extent().inverse_transformed(fig.transFigure) \
         for o in lines]
   coords = [(b.x0, 1-b.y1, b.x1, 1-b.y0) for b in bboxes]
   
   HTML = "<img style=\"margin-left:-10px;\" src=\"%s\" usemap=\"#map\" >" % img_str
   HTML += "<map name=\"map\">\n"
   for i in range(len(names)):
      HTML += "<area shape=rect coords=\"%d %d %d %d\" title=\"%s\" href=\"../navigator/%d/\"" \
            % (int(coords[i][0]*xsize)-crop,
               int(coords[i][1]*ysize)-crop,
               int(coords[i][2]*xsize)-crop,
               int(coords[i][3]*ysize)-crop,
               names[i], ids[i])
      if new_window:
         HTML += " target=\"object_window\">\n"
      else:
         HTML += ">\n"

   HTML += '''
   </map>
   </body>
   </html>'''

   return(HTML)

