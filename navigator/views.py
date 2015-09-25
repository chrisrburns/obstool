from django.shortcuts import render
import sys,os,subprocess
from django.template import Context, loader, RequestContext
from django.shortcuts import render_to_response
from navigator.models import Object,genMWO
from django.http import HttpResponse, HttpResponseRedirect
from django import forms
from django.core.context_processors import csrf
from obstool import settings
import datetime
import string
import time
#import plot_ams_phases,plot_ams_HA
import StringIO
import Image, ImageDraw
from numpy import argsort,mean
try:
   import ephem3 as ephem
except:
   import ephem
from math import pi
import get_planets

rotations = {'90':Image.ROTATE_90,
             '180':Image.ROTATE_180,
             '270':Image.ROTATE_270,
             '-90':Image.ROTATE_270}

class FilterForm(forms.Form):
   airmass_high = forms.FloatField(min_value=1.0, required=False,
         label='Airmass <', initial=2.0,
         widget=forms.TextInput(attrs={'size':'5'}))
   rating_low = forms.IntegerField(required=False,
         label='rating >', initial=0,
         widget=forms.TextInput(attrs={'size':'5'}))
   only_visible = forms.BooleanField(required=False, label='Only Visible')
   # Settings
   epoch = forms.DateTimeField(required=False)
   tz_offset = forms.FloatField(required=False, initial=0,
         widget=forms.TextInput(attrs={'size':'5'}))
                
   new_window = forms.BooleanField(required=False, initial=False)

def get_current_time(request):
   '''Get the current time. This could be 'now' or stored in the session'''
   epoch = None
   tz_offset = 0
   if 'object_list_form' in request.session:
      epoch = str(request.session['object_list_form']['epoch'])
      tz_offset = float(request.session['object_list_form']['tz_offset'])
      if tz_offset is None:
         tz_offset = 0
      if not epoch:
         date = ephem.now()
      else:
         date = ephem.Date(epoch) - tz_offset*ephem.hour
   else:
      date = ephem.now()

   return date

def telescope_position(obj_name,date):
   '''Given an RA/DEC, return hour-angle, altitude, and azimuth as strings.
   RA and DEC are assumed to be at the epoch 'date' (ie., have been precessed)'''
   obj = Object.objects.get(name=obj_name)
   obj.epoch = date
   return (obj.PrecRAh(),
           obj.PrecDecd(),
           ephem.hours(obj.hour_angle()*15.0*pi/180.),
           "%.2f" % (obj.altitude()),
           "%.2f" % (obj.azimuth()))

def index(request):
   only_visible = None
   airmass_high = 2.0
   epoch = None
   rating_low = None
   new_window = False
   tz_offset = 0
   #Default:  nothing posted and no session info
   cur_tel_obj = request.session.get('cur_tel_obj', 'Park')
   prev_tel_obj = request.session.get('prev_tel_obj', 'Park')
   form = FilterForm()

   if request.method == "POST":
      if request.POST['action'] == 'Update':
         form = FilterForm(request.POST)
         # save this form info into the session cache
         request.session['object_list_form'] = request.POST.copy()
      elif request.POST['action'] == 'Park':
         request.session['cur_tel_obj'] = 'Park'
         cur_tel_obj = 'Park'
      else:
         # The reset button was called
         form = FilterForm()
         if 'object_list_form' in request.session:
            del request.session['object_list_form']
   if 'object_list_form' in request.session:
      form = FilterForm(request.session['object_list_form'])

   if form.is_valid():
      only_visible = form.cleaned_data.get('only_visible',None)
      airmass_high = form.cleaned_data.get('airmass_high',2.0)
      rating_low = form.cleaned_data.get('rating_low',None)
      epoch = form.cleaned_data.get('epoch',None)
      tz_offset =form.cleaned_data.get('tz_offset', 0)
      new_window = form.cleaned_data.get('new_window',False)

   if tz_offset is None:
      tz_offset = 0
   if epoch:  
      date = ephem.Date(epoch) - tz_offset*ephem.hour
   else:
      date = ephem.now()

   obj_list = Object.objects.all()
   for obj in obj_list:
      obj.epoch = date
   obj_list = sorted(obj_list, key=lambda a: float(a.PrecRAh()))

   new_list = []
   for obj in obj_list:  
      obj.epoch = date
      if only_visible is not None and only_visible and not obj.visible():
         continue
      if airmass_high is not None and \
         not 0 < float(obj.airmass()) <= airmass_high:
         continue
      if rating_low is not None and obj.rating < rating_low:
         continue
      new_list.append(obj)
   obj_list = new_list

   if epoch:
      sdate = epoch.strftime('%m/%d/%y %H:%M:%S')
   else:
      sdate = ephem.now().datetime().strftime('%m/%d/%y %H:%M:%S')
   if tz_offset != 0:
      stz_offset = "%.1f" % (tz_offset)
   else:
      stz_offset = ""

   # Now deal with telescope position
   tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(cur_tel_obj, date)

   t = loader.get_template('navigator/object_list.sortable.html')
   c = RequestContext(request, {
      'object_list': obj_list, 'form':form, 'date':sdate,
      'method':request.method, 'new_window':new_window, 'tz_offset':stz_offset,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az,
      })
   return HttpResponse(t.render(c))

def detail(request, object_id):
   obj = Object.objects.get(id=object_id)
   message = None
   error = None
   extras = "?"
   epoch = None
   tz_offset = 0

   date = get_current_time(request)
   obj.epoch = date

   if request.method == 'POST':
      if request.POST['action'] == 'GOTO':
         request.session['prev_tel_obj'] = request.session.get('cur_tel_obj','Park')
         request.session['cur_tel_obj'] = obj.name
         request.session['tel_status'] = 'SLEW'
      elif request.POST['action'] == "Sync":
         request.session['prev_tel_obj'] = request.session.get('cur_tel_obj','Park')
         request.session['tel_status'] = 'IDLE'
      elif request.POST['action'] == "Cancel":
         request.session['cur_tel_obj'] = request.session.get('prev_tel_obj','Park')
         request.session['tel_status'] = 'IDLE'

   cur_tel_obj = request.session.get('cur_tel_obj', 'Park')
   prev_tel_obj = request.session.get('prev_tel_obj', 'Park')
   tel_status = request.session.get('tel_status', 'IDLE')

   if settings.FINDER_SIZE != settings.FINDER_BASE_SIZE:
      extras += "size=%d&" % (settings.FINDER_SIZE)
   if settings.FINDER_REVERSE:
      extras += "reverse=1&"
   if settings.FINDER_LOW:
      extras += "low=%d&" % (settings.FINDER_LOW)
   if settings.FINDER_HIGH:
      extras += "high=%d&" % (settings.FINDER_HIGH)
   extras = extras[:-1]     # cleanup trailing & or ?
   t = loader.get_template('navigator/object_detail.html')

   # Now deal with telescope position
   if tel_status == "SLEW":
      tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(prev_tel_obj, date)
      new_RA,new_DEC,new_ha,new_alt,new_az = telescope_position(cur_tel_obj, date)
      delta_az = float(new_az) - float(tel_az)
      if delta_az < -180:
         delta_az += 360
      elif delta_az > 180:
         delta_az -= 360
      if delta_az > 0:
         az_move = "Dome East %.2f" % (delta_az)
      else:
         az_move = "Dome West %.2f" % (-delta_az)
   else:
      az_move = None
      tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(cur_tel_obj, date)
   
   c = RequestContext(request, {
      'object':obj, 'extras':extras, 
      'finder_orientation':settings.FINDER_ORIENTATION, 
      'finder_size':settings.FINDER_SIZE,
      'message':message, 'error':error, 'epoch':epoch,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az, 'tel_status':tel_status, 'az_move':az_move
      })
   return HttpResponse(t.render(c))

def search_name(request, object_name):
   error = None
   objs = Object.objects.filter(name__contains=object_name)
   if len(objs) == 0:
      error = "No object matching your query was found"
      message = None
   else:
      message = "Found %d objects matching your pattern" % len(objs)

   t = loader.get_template('navigator/object_search.html')
   c = Context({
      'objects':objs, 'message':message, 'error':error,
      })
   return HttpResponse(t.render(c))

def palette(low, high, reverse=None):
   dval = high-low
   pal = []
   vals = range(256)
   for val in vals:
      intens = int(255./dval*(val-low))
      if intens > 255:  intens = 255
      if intens < 0:  intens = 0
      if reverse:  intens = 255-intens
      pal.extend((intens,)*3)
   return pal


def finder(request, objectid):
   obj = Object.objects.get(id=objectid)
   flip = request.GET.get('flip',None)
   rotate = request.GET.get('rotate',None)
   size = request.GET.get('size',None)
   low = int(request.GET.get('low',0))
   high = int(request.GET.get('high',255))
   reverse = request.GET.get('reverse',None)
   if obj.objtype == 'SS':
      if 'object_list_form' in request.session:
         epoch = str(request.session['object_list_form']['epoch'])
         tz_offset = float(request.session['object_list_form']['tz_offset'])
         if tz_offset is None:
            tz_offset = 0
         if not epoch:
            date = ephem.now()
         else:
            date = ephem.Date(epoch) - tz_offset*ephem.hour
      else:
         date = ephem.now()
      content = get_planets.get_image(obj.name, date, size)
      if content:
         response = HttpResponse(content, content_type="image/png")
         response['Content-Disposition'] = 'inline; filename=%s' % \
               (obj.name+".png")
         return response
      else:
         response = HttpResponse(obj.finder.read(), content_type="image/png")
         response['Content-Disposition'] = 'inline; filename=%s' % \
               (obj.name+".png")
         return response

   elif obj.objtype == "PARK":
      response = HttpResponse(obj.finder.read(), content_type="image/png")
      response['Content-Disposition'] = 'inline; filename=%s' % \
               (obj.name+".png")
      return response


   obj.finder.open()
   # If needed do some transformations
   outstr = StringIO.StringIO()
   img = Image.open(obj.finder)
   if size and int(size) < settings.FINDER_BASE_SIZE:
      size = int(size)
      scale = 1.0*settings.FINDER_BASE_SIZE/img.size[0]    # arc-min per pixel
      new_size = int(size/scale)  # New size in pixels
      img = img.crop((int(img.size[0]-new_size)/2,
                     int(img.size[1]-new_size)/2,
                     int(img.size[0]+new_size)/2,
                     int(img.size[1]+new_size)/2))
   if flip and (flip == 'leftright' or flip == "both"):
      img = img.transpose(Image.FLIP_LEFT_RIGHT)
   if flip and (flip == "topbottom" or flip == "both"):
      img = img.transpose(Image.FLIP_TOP_BOTTOM)
   if rotate and rotate in rotations:
      img = img.transpose(rotations[rotate])
   if (low != 0 or high !=255 or reverse) and (high > low):
      pal = palette(low, high, reverse)
      p = img.convert('P')
      p.putpalette(pal)
      img = p.convert('L')

   mid = img.size[0]/2
   if reverse:
      fill=0
   else:
      fill=255

   img.save(outstr,'PNG')
   content = outstr.getvalue()
   outstr.close()
   obj.finder.close()
   response = HttpResponse(content, content_type="image/png")
   response['Content-Disposition'] = 'inline; filename=%s' % obj.finder.name
   return response

