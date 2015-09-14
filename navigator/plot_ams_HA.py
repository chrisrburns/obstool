#!/usr/bin/env python

#import os
#os.environ['HOME'] = '/Library/WebServer/mpl_home'
import sys
import matplotlib
import matplotlib.cbook
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
#from matplotlib import pyplot as plt
from numpy import *
import matplotlib.dates as mdates
import StringIO
import Image
import urllib
try:
   import ephem3 as ephem
except:
   import ephem
import HJD

colors = {'c':'blue','ab':'red'}

def plot_ams_map(RRLs, date=None, new_window=False, phase_low=0.,
      phase_high=1., phase_c_low=0., phase_c_high=1., airmass_high=None):
   '''Plots the airmass for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the first is the binary
   PNG file that is the graph, the second is the <map> HTML that will be used
   to make the points in the graph "hot spots"'''
   if date is None:
      date = ephem.now()
   else:
      date = ephem.Date(date)

   lco = HJD.lco_gen()
   lco.date = date
   LST = lco.sidereal_time()

   # Setup the graph
   fig = Figure()
   canvas = FigureCanvasAgg(fig)
   ax = fig.add_subplot(111)
   #ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
   #ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=[0,30]))
   ax.set_xlabel('Hour Angle')
   ax.set_ylabel('Airmass')
   ax.grid(True, which='major', linestyle='-', color='gray')
   #ax.set_title('Night of %d/%d %s %d' % (t.day, t.day+1, t.strftime('%b'), t.year))
   lines = []
   names = []
   ids = []
   
   for RRL in RRLs:
      RRL.epoch = date
      phase = float(RRL.phase())
      am = float(RRL.airmass())
      if RRL.type == 'ab':
         if phase_low is None:  phase_low=0
         dt0 = (phase - phase_low)*RRL.period
         if phase_high is None:  phase_high=1.
         dt1 = (phase_high - phase)*RRL.period
      else:
         if phase_c_low is None:  phase_c_low=0
         dt0 = (phase - phase_c_low)*RRL.period
         if phase_c_high is None:  phase_c_high=1.
         dt1 = (phase_c_high - phase)*RRL.period
      RRL.epoch = ephem.Date(date-dt0)
      am0 = float(RRL.airmass())
      RRL.epoch = ephem.Date(date+dt1)
      am1 = float(RRL.airmass())
      dt0 *= 24  # convert to hours
      dt1 *= 24


      obj = ephem.FixedBody()
      obj._ra = RRL.ra*pi/180.
      obj._dec = RRL.dec*pi/180.
      obj._epoch = ephem.J2000
      obj.compute(lco)
      if pi/2 < obj.az < 3*pi/2:
         # object is in the south
         sym = 's'
      else:
         sym = 'o'
      HA = (LST - obj.ra)/pi*12
      if HA > 12:
         HA -= 24
      if HA < -12:
         HA += 24
            
      obj = ax.plot([HA], [am], sym, mfc=colors[RRL.type])
      lines.append(obj[0])
      names.append(RRL.name)
      ids.append(RRL.pk)
      ax.plot([HA-dt0, HA, HA+dt1], [am0, am, am1], '-', color=colors[RRL.type])
   for tick in ax.xaxis.get_major_ticks():
      tick.label2On = True

   # Set to +/- 4 hours:
   ax.set_xlim(-4,4)
   ax.set_ylim(0.9, airmass_high*1.1)


   # Now we save to a string and also convert to a PIL image, so we can get the size.
   output = StringIO.StringIO()
   #plt.draw()
   #fig.savefig(output, format='png')
   canvas.print_figure(output)
   img_str = 'data:image/png,' + urllib.quote(output.getvalue())
   output.seek(0)
   img = Image.open(output)
   output.close()
   xsize,ysize = img.size
   
   # Get the window coordinates of the points
   bboxes = [o.get_window_extent(0).inverse_transformed(fig.transFigure) \
         for o in lines]
   coords = [(b.x0, 1-b.y1, b.x1, 1-b.y0) for b in bboxes]
   
   HTML = "<img src=\"%s\" usemap=\"#map\" >" % img_str
   HTML += "<map name=\"map\">\n"
   for i in range(len(names)):
      HTML += "<area shape=rect coords=\"%d %d %d %d\" title=\"%s\" href=\"../object/%d/\"" \
            % (int(coords[i][0]*xsize),
               int(coords[i][1]*ysize),
               int(coords[i][2]*xsize),
               int(coords[i][3]*ysize),
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


