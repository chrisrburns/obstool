#!/usr/bin/env python

import matplotlib
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from numpy import *
import StringIO
import Image
import urllib
try:
   import ephem3 as ephem
except:
   import ephem

symbols = {'GC':r'$\oplus$',
           'SS':r'$\odot$',
           'Double':r':','Triple':r'$\therefore$',
           'E/RN':r'$\boxdot$','EN':r'$\boxdot$','EN-OC':r'$\boxdot$',
           'E/DN':r'$\boxdot$','RN':r'$\boxdot$','SNR':r'$\boxdot$',
           'PN':r'$\circ$','OC':r'$\varnothing$','QSO':r'$\cdot$'}
def osymb(s):
   '''returns an appropriate symbol to use based on object type.'''
   if s[0:2] == 'G-':
      # galaxy
      return r"$\S$"
   if s in symbols:
      return symbols[s]
   # default:
   return '.'

def plot_sky_map(objs, date=None, new_window=False, airmass_high=None,
      tel_alt=90, tel_az=45):
   '''Plots the objects for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the first is the binary
   PNG file that is the graph, the second is the <map> HTML that will be used
   to make the points in the graph "hot spots"'''
   if date is None:
      date = ephem.now()
   else:
      date = ephem.Date(date)

   # Setup the graph
   fig = Figure((6,6))
   canvas = FigureCanvasAgg(fig)
   ax = fig.add_subplot(111, projection='polar')
   #ax.set_xlabel('Hour Angle')
   #ax.set_ylabel('Airmass')
   ax.grid(True, which='major', linestyle='-', color='gray')
   #ax.set_title('Night of %d/%d %s %d' % (t.day, t.day+1, t.strftime('%b'), t.year))
   lines = []
   names = []
   ids = []
   
   for obj in objs:
      obj.epoch = date
      #pobj = ax.plot([obj.azimuth()], [90-obj.altitude()], osymb(obj.objtype), 
      #      mfc='k')
      theta = -(obj.azimuth()*pi/180-pi/2)
      tobj = ax.text(theta, 90-obj.altitude(), osymb(obj.objtype),
            va='center', ha='center')
            
      lines.append(tobj)
      names.append(obj.name + "*"*obj.rating)
      ids.append(obj.pk)
   # Telescope pos
   theta = -(float(tel_az)*pi/180-pi/2)
   ax.plot([theta], [90-float(tel_alt)], "o", ms=15, mfc='none', mec='red')
   ax.plot([theta], [90-float(tel_alt)], "o", ms=10, mfc='none', mec='red')

   # Set limits
   #ax.set_rmax(90)
   ax.set_ylim(0,60)
   #ax.set_yticks([])
   labs = ax.yaxis.get_ticklabels()
   ax.yaxis.set_ticklabels(["" for lab in labs])

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
   bboxes = [o.get_window_extent().inverse_transformed(fig.transFigure) \
         for o in lines]
   coords = [(b.x0, 1-b.y1, b.x1, 1-b.y0) for b in bboxes]
   
   HTML = "<img src=\"%s\" usemap=\"#map\" >" % img_str
   HTML += "<map name=\"map\">\n"
   for i in range(len(names)):
      HTML += "<area shape=rect coords=\"%d %d %d %d\" title=\"%s\" href=\"../navigator/%d/\"" \
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

