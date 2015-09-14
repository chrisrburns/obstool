#/!/usr/bin/env python

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

def columns(filename, skip=[], delim=None):
   f = open(filename,'r')
   if not f:
      raise IOError, 'Could not find file %s' % (filename)

   lines = f.readlines()
   data = []
   i = 0
   for line in lines:
      line = string.strip(line)
      if line == "":  continue
      if line[0] != "#" and i not in skip:  data.append(line)
      i = i + 1

   if delim is None:
      line = data[0]
      if len(string.split(line)) > 1:
         sep = None
      elif len(string.split(line,',')) > 1:
         sep = ","
      elif len(string.split(line,';')) > 1:
         sep = ";"
      else:
         sep = None
   else:
      sep = delim

   data = map(lambda str,s=sep: string.split(str, s), data)

   #check for consistency:
   M = len(data)
   N = len(data[0])
   for line in data:
      if len(line) != N:
         raise IndexError, "data has missing cells"

   # now do a transpose
   datat = []
   for i in range(N):
      datat.append([])
      for j in range(M):
         datat[-1].append(data[j][i])

   # Now try to convert to floats and numarrays
   for i in range(len(datat)):
      try:
         datat[i] = map(float, datat[i])
         datat[i] = Numeric.array(datat[i])
      except:
         # silently ignore non-numeric types.
         datat[i] = map(None, datat[i])

   return datat


def plot_ams_map(RRLs, date=None, target_phase=0.45, target_phase_c=0.45, p_lim=0.02, 
      max_am=2.0, new_window=False):
   '''Plots the airmass for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the first is the binary
   PNG file that is the graph, the second is the <map> HTML that will be used
   to make the points in the graph "hot spots"'''
   sun = ephem.Sun()
   lco = HJD.lco_gen()
   if date is None:
      date = ephem.now()
   else:
      date = ephem.Date(date)
   lco.date = date
   sun.compute(lco)

   # Figure out the start and stop time for the night.
   t0 = lco.next_setting(sun)    # In DJD
   t1 = lco.next_rising(sun)
   if t1 < t0:
      t0 = lco.previous_setting(sun)
   lco.date = t0

   # Setup the graph
   fig = Figure()
   canvas = FigureCanvasAgg(fig)
   ax = fig.add_subplot(111)
   ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
   ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=[0,60]))
   ax.set_xlabel('UTC time')
   ax.set_ylabel('Airmass')
   ax.grid(True, which='both', linestyle='-', color='gray')
   t = t0.datetime()
   #ax.set_title('Night of %d/%d %s %d' % (t.day, t.day+1, t.strftime('%b'), t.year))
   lines = []
   names = []
   ids = []
   
   for RRL in RRLs:
      if RRL.type == "ab":
         tp = target_phase
      else:
         tp = target_phase_c
      RRL.epoch = t0
      phase0 = float(RRL.phase())
      next = t0
      if phase0 < tp:
         next += (tp - phase0)*RRL.period
      else:
         next += (1 + tp - phase0)*RRL.period
      while next < t1:
         # while the sun hasn't risen:
         RRL.epoch = next
         am = float(RRL.airmass())
         if 0 < am < max_am:
            md = mdates.date2num(ephem.Date(next).datetime())
            obj = ax.plot_date([md], [am], 'o', mfc=colors[RRL.type])
            lines.append(obj[0])
            names.append(RRL.name)
            ids.append(RRL.pk)
            if p_lim > 0:
               xs = arange(next - p_lim*RRL.period,
                           next + p_lim*RRL.period + ephem.minute,
                           ephem.minute)
               ys = []
               for x in xs:
                  RRL.epoch = x
                  ys.append(float(RRL.airmass()))
               ys = array(ys)
               gids = greater_equal(xs, next-p_lim*RRL.period)*\
                     less_equal(xs, next+p_lim*RRL.period)
               line = ax.plot_date(xs[gids]-next+md, ys[gids], '-', color=colors[RRL.type])
               #gids = greater_equal(xs, next-p_lim[1]*RRL.period)*\
               #      less_equal(xs, next+p_lim[1]*RRL.period)
               #line = ax.plot_date(xs[gids]-next+md, ys[gids], '--', color=colors[RRL.type])
         next += RRL.period
   
   ax.set_ylim(max_am, 0.8)
   ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
   for tick in ax.xaxis.get_major_ticks():
      tick.label2On = True

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


