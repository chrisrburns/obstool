#!/usr/bin/env python

'''Plot a skymap using the Bokeh plotting package. Bokeh has the big 
advantage of embedding directly into the HTML canvas with a given size,
making it easier to place than a matplotlib-generated image. Intractions
are also much much better.'''

import os
import polar
from bokeh.plotting import ColumnDataSource
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.models import HoverTool, OpenURL, TapTool, CustomJS
from numpy import *
from models import genMWO
import pickle
try:
   import ephem3 as ephem
except:
   import ephem
import pickle



# The constellation data.
conlines = os.path.join(os.path.dirname(__file__), 'Conlines.pkl')
f = open(conlines)
d = pickle.load(f)
f.close()


# How to plot different types. The dictionary is keyed by object type. the value
# is a list of plotting instructions. Some objects are plotted with multiple
# elements, so each member of the list is a plotting element composed of a 
# 2-tuple:  the plotting element and the options controlling the size etc.
# Note that some elements (like oval and text) currently dont' work with the
# Tap tool, so we add invisible circle elements to trigger this event.
symbols = {
      'GC':[('scatter',{'marker':'circle_cross','fill_color':None,'size':10,'name':'obj'})],
      'SS':[('circle',{'size':10,'fill_color':'yellow','line_color':'black',
                       'name':'obj'}),
            ('circle',{'size':1, 'fill_color':'black'})],
      'PN':[('circle', {'size':5, 'line_color':'blue', 'name':'obj'})],
      'OC':[('circle', {'size':20, 'line_color':'blue','line_dash':'4 4',
         'name':'obj', 'fill_color':None})],
      'QSO':[('circle', {'size':10, 'line_color':'red','name':'obj'})]}
texts = {
      'Double':':',
      'Triple':':.'}
for name in ['E/RN','EN','EN-OC','E/DN','RN','SNR']:
   symbols[name] = [('square', {'size':10, 'line_color':'black','name':'obj'})]

def osymb(s):
   '''returns an appropriate symbol to use based on object type.'''
   if s[0:2] == 'G-':
      # galaxy
      return [('oval', {'width':15, 'height':7, 'angle':45, 
         'line_color':'black','fill_color':None, 'width_units':'screen',
         'height_units':'screen'}),
              ('circle', {'size':5, 'line_color':'white', 'fill_color':None,
                          'name':'obj'})]
   if s in symbols:
      return symbols[s]
   if s in texts:
      return [('text', {'text':'text',"text_align":"center","text_baseline":"middle"}),
            ('circle',{"size":5, "line_color":None, "fill_color":None,
                       "name":"obj"})]
   # default:
   return [('asterisk', {'size':6,'name':'obj'})]

def RAhDecd2AltAz(RA,DEC,obs):
   '''Given an RA/DEC of a constallation vertex, return alt/Az on the sky.
   We let polar.py deal with converting to x,y on the screen. If the vertex
   is below the horizon, set clip=True'''
   o = ephem.FixedBody()
   o._ra = ephem.degrees(RA*15*pi/180)
   o._dec = ephem.degrees(DEC*pi/180)
   o._epoch = ephem.J2000
   o.compute(obs)
   clip=False 
   if o.alt*180.0/pi < 0: clip=True
   return ((pi/2-o.alt)*180/pi, o.az, clip)


def plot_sky_map(objs, date=None, new_window=False, airmass_high=None,
      tel_alt=90, tel_az=45, imsize=500, crop=90):
   '''Plots the objects for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the <script> element that should
   be placed in the header, and the <div> that should be placed where you want
   the graph to show up.'''
   if date is None:
      date = ephem.now()
   else:
      date = ephem.Date(date)

   MWO = genMWO(date)

   # Setup the graph
   hover = HoverTool(tooltips=[("Name", "@label"),("Type","@type"),("Alt","@alt")],
         names=['obj'])
   #tap = TapTool(callback=OpenURL(url="/navigator/@pk/"), names=['obj'])

   fig = polar.PolarPlot(plot_height=imsize, plot_width=imsize, rmax=90,
         tools=["pan","wheel_zoom","box_zoom","reset",hover], theta0=pi/2,
         clockwise=True)
   
   sources = {}
   xs = []; ys = []
   pks = []
   for obj in objs:
      obj.epoch = date
      theta = obj.azimuth()*pi/180
      rho = 90 - obj.altitude()
      #maxrho = max(rho, maxrho)
      #x = rho*sin(theta)
      #y = rho*cos(theta)
      if obj.objtype == 'PARK': continue
      if obj.objtype not in sources:
         sources[obj.objtype] = {'rho':[], 'theta':[], 'label':[],
               'text':[], "type":[], "alt":[]}
      #tobj = ax.text(x, y, osymb(obj.objtype), va='center', ha='center')
      sources[obj.objtype]['rho'].append(rho)
      sources[obj.objtype]['theta'].append(theta)
      sources[obj.objtype]['label'].append(obj.name+"*"*obj.rating)
      sources[obj.objtype]['alt'].append(90.0-rho)
      sources[obj.objtype]['type'].append(obj.objtype)
      x,y = fig.rt2xy(rho,theta)
      xs.append(x)
      ys.append(y)
      pks.append("%d" % (obj.pk))
      if obj.objtype in texts:
         sources[obj.objtype]['text'].append(texts[obj.objtype])
      else:
         sources[obj.objtype]['text'].append("")

   xypk = ColumnDataSource(dict(x=xs, y=ys, pk=pks))
   if new_window:
      js_redirect = 'window.open("/navigator/"+pk+"/", "object");'
   else:
      js_redirect = 'window.location = "/navigator/"+pk+"/";'

   callback = CustomJS(args=dict(source=xypk), code="""
   var mindist = 1000;
   var dist = 0;
   var pk = -1;
   var data = source.data;
   for (var i=0; i < data['x'].length; i++) {
      dist = (cb_obj['x']-data['x'][i])*(cb_obj['x']-data['x'][i]) +
             (cb_obj['y']-data['y'][i])*(cb_obj['y']-data['y'][i]);
      if ( dist < mindist ) { 
         mindist = dist;
         pk = data['pk'][i];
      }
   }   
   if (mindist < 0.001) {
      %s
   }
   """ % js_redirect)
   fig.figure.js_on_event('tap', callback)
   for key in sources:
      sources[key]['rho'] = array(sources[key]['rho'])
      sources[key]['theta'] = array(sources[key]['theta'])
      sources[key]['alt'] = array(sources[key]['alt'])

      sources[key] = ColumnDataSource(sources[key])

      elements = osymb(key)
      for (func,args) in elements:
         f = getattr(fig, func)
         f('rho','theta',source=sources[key], **args)
            
   # Telescope pos
   theta = float(tel_az)*pi/180
   rho = 90 - float(tel_alt)
   fig.annulus([rho], [theta], 7, 8, inner_radius_units='screen',
         outer_radius_units='screen', fill_color='red')

   # Try some constellations
   for cons in d:
      draw = False
      ras,decs = d[cons]
      x1s,x2s,y1s,y2s = [],[],[],[]

      pendown=False
      for i in range(0,len(ras)):
         if ras[i] is not None:
            x,y,clip = RAhDecd2AltAz(ras[i],decs[i],MWO)
            if not clip: draw = True
            if pendown:
               x2s.append(x)
               y2s.append(y)
               x1s.append(x)
               y1s.append(y)
            else:
               pendown=True
               x1s.append(x)
               y1s.append(y)
         else:
            pendown=False
            x1s = x1s[:-1]
            y1s = y1s[:-1]
      if draw:
         x1s = array(x1s); x2s = array(x2s)
         y1s = array(y1s); y2s = array(y2s)
         fig.segment(x1s,y1s,x2s,y2s, line_color='gray', line_width=0.5)

   fig.grid()
   fig.taxis_label()
   script,div = components(fig.figure, CDN)

   return(script,div)

