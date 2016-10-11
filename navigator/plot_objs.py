#/!/usr/bin/env python

#import os
#os.environ['HOME'] = '/Library/WebServer/mpl_home'
import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.figure import SubplotParams
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
from models import genMWO

colors = {'c':'blue','ab':'red'}

def plot_alt_map(objs, date=None, toff=0, new_window=False):
   '''Plots the altitude for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the first is the binary
   PNG file that is the graph, the second is the <map> HTML that will be used
   to make the points in the graph "hot spots"'''
   if date is None:
      date = ephem.now()
   toff = toff/24.
   sun = ephem.Sun()
   MWO = genMWO(date=date)
   sun.compute(MWO)

   # Figure out the start and stop time for the night.
   sunset = MWO.next_setting(sun)    # In DJD
   sunrise = MWO.next_rising(sun)
   if sunset > sunrise:
      sunset = MWO.previous_setting(sun)
   #MWO.date = sunset

   # Setup the graph
   fig = Figure(subplotpars=SubplotParams(left=0.07, right=0.99))
   canvas = FigureCanvasAgg(fig)
   ax = fig.add_subplot(111)
   ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
   ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=[0,60]))
   ax.set_xlabel('UTC time')
   ax.set_ylabel('Altitude')
   ax.grid(True, which='both', linestyle='-', color='gray')
   lines = []
   names = []
   ids = []

   sunset = sunset - 60*ephem.minute
   sunrise = sunrise + 60*ephem.minute
   print 'Sunset/Sunrize:',sunset,sunrise

   for obj in objs:
      eobj = obj.genobj()
      t0 = obj.rise_time()
      if t0 is None or t0 < sunset: t0 = sunset
      if t0 > sunrise: continue
      t1 = obj.set_time()
      if t1 is None or t1 > sunrise: t1 = sunrise
      if t1 < sunset: 
         continue

      tt = date
      if tt < t0:  tt = t0
      if tt > t1:  tt = t1
      tt = tt*1 + 693595.5
      saved_epoch = obj.epoch
      obj.epoch = date
      aa = obj.altitude()
      ts = arange(t0,t1+ephem.minute,10*ephem.minute)
      alts = []
      for t in ts:
         #obj.epoch = t
         #alts.append(obj.altitude())
         MWO.date = t
         eobj.compute(MWO)
         alts.append(eobj.alt*180.0/pi)
      alts = array(alts)
      mid = argmax(alts)
      merid = ephem.Date(ts[mid]+toff)
      maxalt = alts[mid]
      ts = ts + 693595.5   # convert to matplotlib epochs
      title = "Meridian @ %s (%.1fd)" % (str(merid).split()[1], maxalt)
      ax.text(0.5, 1.1, title, transform=ax.transAxes, ha='center', 
            va='top', fontsize=18)
      ax.plot_date(ts+toff, alts, '-')
      pobj = ax.plot_date([tt+toff],[aa], 'o', mfc='k')
      lines.append(pobj[0])
      names.append(obj.name)
      ids.append(obj.pk)
      obj.epoch = saved_epoch
   
   ax.set_ylim(0, 90.)

   ax.set_xlim(sunset*1+693595.5+toff, sunrise*1+693595.5+toff)
   ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
   for tick in ax.xaxis.get_major_ticks():
      tick.label2On = True
   ax.axvline(date*1+693595.5+toff, color='red')
   ax.axvline(sunset+60*ephem.minute+693595.5+toff, linestyle='--',
         linewidth=2, color='red')
   ax.axvline(sunrise-60*ephem.minute+693595.5+toff, linestyle='--',
         linewidth=2, color='red')
   ax.fill_between([sunset*1+693595.5+toff,sunrise*1+1+693595.5+toff], 0, 30,
         color='0.7', zorder=0)

   # Now we save to a string and also convert to a PIL image, so we can get 
   #  the size.
   output = StringIO.StringIO()
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
   
   HTML = "<img src=\"%s\" style=\"width: 280px\" usemap=\"#map\" >" % img_str
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


