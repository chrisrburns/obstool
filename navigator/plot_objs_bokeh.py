#/!/usr/bin/env python

from bokeh.plotting import ColumnDataSource,figure,output_file,show
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.models import FuncTickFormatter,Range1d,SingleIntervalTicker,LinearAxis
from bokeh.models import Span, HoverTool
from numpy import *
try:
   import ephem3 as ephem
except:
   import ephem
from models import genMWO

colors = {'c':'blue','ab':'red'}

def plot_alt_map(objs, date=None, toff=0, new_window=False, imsize=300):
   '''Plots the altitude for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the first is the binary
   PNG file that is the graph, the second is the <map> HTML that will be used
   to make the points in the graph "hot spots"'''
   if date is None:
      date = ephem.now()
   toff = toff/24.   # Now in decimal days
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
   if len(objs) == 1:
      hoverobj = 'line'
   else:
      hoverobj = 'objs'
   hover = HoverTool(tooltips=[("time","@tlabel"), ("altitude","@alt")], 
         mode='vline', names=[hoverobj])
   fig = figure(plot_height=2*imsize/3, plot_width=imsize, tools=[hover], 
         x_axis_type=None)
   ticker = SingleIntervalTicker(interval=2.0/24, num_minor_ticks=5)
   xaxis = LinearAxis(ticker=ticker)
   fig.add_layout(xaxis, 'below')
   if toff != 0:
      sign = ['+','-'][toff < 0]
      fig.xaxis.axis_label = 'UTC time %s %.1f' % (sign, abs(toff*24))
   else:
      fig.xaxis.axis_label = 'UTC time'
   fig.yaxis.axis_label = 'Altitude'
   fig.xaxis.formatter = FuncTickFormatter(code='''
      var t = (tick - Math.floor(tick) - 0.5)*24
      if (t < 0) { t = t + 24 }
      return (t.toFixed(0)+'h')
      ''')

   sunset = sunset - 60*ephem.minute
   sunrise = sunrise + 60*ephem.minute

   point_data = dict(time=[], alt=[], obj=[])
   for obj in objs:
      line_data = dict(time=[], alt=[], tlabel=[])
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
      tt = tt*1 + toff
      point_data['time'].append(tt)
      saved_epoch = obj.epoch
      obj.epoch = date
      aa = obj.altitude()
      point_data['alt'].append(aa)
      point_data['obj'].append(obj.name+"*"*obj.rating)
      ts = arange(t0,t1+ephem.minute,10*ephem.minute)
      for t in ts:
         MWO.date = t
         eobj.compute(MWO)
         line_data['alt'].append(eobj.alt*180.0/pi)
         line_data['tlabel'].append(str(ephem.date(t+toff)).split()[-1])
      line_data['time'] = ts + toff
      line_data['alt'] = array(line_data['alt'])

      mid = argmax(line_data['alt'])
      merid = ephem.Date(ts[mid])
      maxalt = line_data['alt'][mid]
      title = "Meridian @ %s (%.1fd)" % (str(merid).split()[1], maxalt)
      if len(objs) == 1:
         fig.title.text = title
      line_data = ColumnDataSource(line_data)
      fig.line('time', 'alt', line_width=2, source=line_data, name='line')
      #fig.circle([tt],[aa], size=7)
      obj.epoch = saved_epoch
   
   point_data['time'] = array(point_data['time'])
   point_data['alt'] = array(point_data['alt'])
   point_data = ColumnDataSource(point_data)

   fig.circle('time','alt', size=7, source=point_data, name='objs')
   fig.y_range = Range1d(0, 90)

   x0 = ephem.date(sunset+toff)*1.0
   x1 = ephem.date(sunrise+toff)*1.0
   fig.x_range = Range1d(x0, x1)
   fig.toolbar_location = None

   sp1 = Span(location=sunset+60*ephem.minute + toff, dimension='height', 
         line_color='red', line_dash='dashed', line_width=2)
   fig.patch(x=[x0,x1,x1,x0], y=[0, 0, 30, 30], color='gray', alpha=0.3)
   fig.add_layout(sp1)
   sp2 = Span(location=sunrise-60*ephem.minute + toff,dimension='height', 
         line_color='red', line_dash='dashed', line_width=2)
   fig.add_layout(sp2)
   #ax.axvline(date*1+693595.5+toff, color='red')
   #ax.axvline(sunset+60*ephem.minute+693595.5+toff, linestyle='--',
   #      linewidth=2, color='red')
   #ax.axvline(sunrise-60*ephem.minute+693595.5+toff, linestyle='--',
   #      linewidth=2, color='red')
   #ax.fill_between([sunset*1+693595.5+toff,sunrise*1+1+693595.5+toff], 0, 30,
   #      color='0.7', zorder=0)
   

   script,div = components(fig, CDN)

   return(script,div)


