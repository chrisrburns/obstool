from django.db import models
from django.db.models import F
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from navigator.models import Object,genMWO
from django.http import HttpResponse,HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django import forms
from django.shortcuts import render
from obstool import settings
import datetime
from zoneinfo import ZoneInfo
zone = ZoneInfo(settings.TIME_ZONE)
#import plot_ams_phases,plot_ams_HA
from . import plot_skyview_bokeh as plot_skyview
from . import plot_objs_bokeh as plot_objs
from io import BytesIO
#import Image, ImageDraw
from PIL import Image,ImageDraw
from numpy import argsort,mean
try:
   import ephem3 as ephem
except:
   import ephem
from math import pi
from . import get_planets
from . import utils
from . import query

def type_included(typ, show_types):
   if 'All' in show_types:
      return True
   if typ[0:2] == 'G-':
      if u'Galaxies' in show_types:
         return True
   if typ in ['E/RN','EN','EN-OC','E/DN','RN','SNR'] and \
         u'Nebulae' in show_types:
         return True
   if typ == 'GC' and u'GC' in show_types:
      return True
   if typ == 'SS' and u'Planets' in show_types:
      return True
   if typ == 'PN' and u'PNe' in show_types:
      return True
   if typ == 'OC' and u'OCs' in show_types:
      return True
   if typ == 'QSO' and u'QSOs' in show_types:
      return True
   if typ in ['Double','Triple'] and u"Stars" in show_types:
      return True
   return False

rotations = {'90':Image.ROTATE_90,
             '180':Image.ROTATE_180,
             '270':Image.ROTATE_270,
             '-90':Image.ROTATE_270}

TYPE_CHOICES = (
      ('All','All'),
      ('Galaxies','Galaxies'),
      ('Planets','Planets'),
      ('Stars','Stars'),
      ('PNe','PNe'),
      ('Nebulae','Nebulae'),
      ('GCs','GCs'),
      ('OCs','OCs'),
      ('QSOs','QSOs'))

# Keep this around for posterity. We're now going to keep the timzeone
# logic as timezone-aware datetime objects. 
#def tzoffset(date, utc=True):
#   '''Given a date (ephem Date), figure out if it's US PST or PDT and return
#   correct offset. If utc is True, date is UTC, otherwise local time'''
#   return 0
#   dt = date.datetime()
#   if dt.month in [1,2,12]:
#      # Definitely PST
#      return -8
#   if dt.month in [4,5,6,7,8,9,10]:
#      # Definitely PDT
#      return -7
#
#   year = dt.year
#   # More work
#   if dt.month == 3:
#      # PDT stars 2nd Sunday
#      first_day = datetime.datetime(year, 3, 1, 1, 0, 0).isoweekday()
#      sec_sun = 7 + (8-first_day)
#      # PDT stars 10:00 UT or 2:00 PST, which is ambiguous
#      if utc:
#         pdt_start = datetime.datetime(year, 3, sec_sun, 10, 0, 0)
#      else:
#         pdt_start = datetime.datetime(year, 3, sec_sun, 2, 0, 0)
#      if dt < pdt_start:
#         return -8
#      return -7
#
#   # November
#   first_day = datetime.datetime(year, 11, 1, 1, 0, 0),isoweekday()
#   first_sun = 8 - first_day
#   # PST starts 09:00 UT or 2:00 am PDT, which is ambiguous
#   if utc:
#      pst_start = datetime.datetime(year, 11, first_sun, 9, 0, 0)
#   else:
#      pst_start = datetime.datetime(year, 11, first_sun, 2, 0, 0)
#   if dt < pst_star:
#      return -7
#   return -8
#

class FilterForm(forms.Form):
   ha_high = forms.FloatField(min_value=0.0, required=False,
         label='|HA| <', initial=settings.HA_SOFT_LIMIT,
         widget=forms.TextInput(attrs={'size':'5'}))
   rating_low = forms.IntegerField(required=False,
         label='rating >', initial=0,
         widget=forms.TextInput(attrs={'size':'5'}))
   show_types = forms.MultipleChoiceField(required=False,
                      choices=TYPE_CHOICES,
                      initial=['All'],
                      widget=forms.CheckboxSelectMultiple)
   only_visible = forms.BooleanField(required=False, label='Only Visible')
   # Settings
   epoch = forms.DateTimeField(required=False, 
         widget=forms.TextInput(attrs={'size':20,'autocomplete':'off'}),
         input_formats=['%Y-%m-%d %H:%M','%Y-%m-%d %H:%M:%S'])
                
   #new_window = forms.BooleanField(required=False, initial=False)
   auto_reload = forms.BooleanField(required=False, initial=True)

class AddObjectForm(forms.Form):
   object_name = forms.CharField(
         required=False, label='Object Name')
   object_coordinates = forms.CharField(
         required=False, label='Object Coordinates (J2000)')
   resolve_choice = forms.ChoiceField(
         choices=(('simbad','Simbad'),('ned','NED')), 
         label='Select search facility', required=True)

   def clean(self):
      cleaned_data = super(AddObjectForm, self).clean()
      name = cleaned_data.get('object_name').strip()
      coords = cleaned_data.get('object_coordinates').strip()
      if (name and coords) or not (name or coords):
         raise forms.ValidationError("Specify only object name or coordinates")
      return cleaned_data


def get_current_time(request):
   '''Get the current time. This could be 'now' or stored in the session.
   Return as an ephem date object, so in UTC. Any session-saved date is
   taken to be a timezone-aware datetime object.'''
   epoch = None
   if 'object_list_form' in request.session:
      epoch = request.session['object_list_form']['epoch']
      if not epoch:
         date = ephem.now()
      else:
         # Assumed to be in localtime
         date = ephem.Date(epoch)
         #date = ephem.Date(date - tzoffset(date)*ephem.hour)
   else:
      date = ephem.now()
   date = date

   return date

def telescope_position(obj_name,date):
   '''Given an object name and date, return the precessed RA, DEC, hour-angle,
   altitude, and azimuth as strings.
   '''
   obj = Object.objects.get(name=obj_name)
   obj.epoch = date
   return (obj.PrecRAh(),
           obj.PrecDecd(),
           ephem.hours(obj.hour_angle()*15.0*pi/180.),
           "%.2f" % (obj.altitude()),
           "%.2f" % (obj.azimuth()))

def index(request):
   only_visible = None
   ha_high = settings.HA_SOFT_LIMIT
   epoch = None
   rating_low = None
   new_window = True
   auto_reload = True
   #Default:  nothing posted and no session info
   cur_tel_obj = request.session.get('cur_tel_obj', 'Park')
   prev_tel_obj = request.session.get('prev_tel_obj', 'Park')
   selected_tab = request.session.get('selected_tab', 'table')
   selected_object = request.session.get('selected_object', '143')
   show_types = ['All']
   form = FilterForm()

   deltat = 0

   if request.method == "POST":
      if request.POST.get('action','') == "Reset":
         form = FilterForm()
         if 'object_list_form' in request.session:
            del request.session['object_list_form']
      elif request.POST.get('action','') == "Park":
         request.session['cur_tel_obj'] = 'Park'
         cur_tel_obj = 'Park'
         selected_object = '143'
      else:
         # Any other button
         form = FilterForm(request.POST)
         if form.is_valid():
            request.session['object_list_form'] = form.cleaned_data.copy()


      if request.POST.get('action','') == '-1h':
         # decrease time by 1h
         deltat = -1*ephem.hour
      elif request.POST.get('action','') == '-30m':
         # decrease time by 30m
         deltat = -0.5*ephem.hour
      elif request.POST.get('action','') == '+30m':
         # increase time by 30m
         deltat = 0.5*ephem.hour
      elif request.POST.get('action','') == '+1h':
         # increase time by 1h
         deltat = 1*ephem.hour
   elif 'object_list_form' in request.session:
      form = FilterForm(request.session['object_list_form'])

   if form.is_valid():
      only_visible = form.cleaned_data.get('only_visible',None)
      ha_high = form.cleaned_data.get('ha_high',settings.HA_SOFT_LIMIT)
      show_types = form.cleaned_data.get('show_types', ['All'])
      rating_low = form.cleaned_data.get('rating_low',None)
      epoch = form.cleaned_data.get('epoch',None)
      if epoch is not None: 
         if isinstance(epoch, str):
            epoch = epoch.encode('ascii','ignore')
      auto_reload = form.cleaned_data.get('auto_reload',False)

   if epoch:
      # assumed to be in local time as a timezone-aware datetime object
      date = ephem.Date(ephem.Date(epoch))
      #date = ephem.Date(date - tzoffset(date)*ephem.hour)
      #form.fields['epoch'].initial = str(date).replace('/','-')
   else:
      date = ephem.now()

   if deltat != 0:
      date = ephem.Date(date + deltat)
      #ldate = ephem.Date(date + tzoffset(date)*ephem.hour)
      #dt = ldate.datetime()
      dt = ephem.to_timezone(date, zone)

      if 'object_list_form' in request.session:
         # Update the form so that the local time "sticks"
         # Need to do this because we need integer seconds (no microseconds)
         request.session['object_list_form']['epoch'] = \
               datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute,
                     dt.second)
         form = FilterForm(request.session['object_list_form'])

   # Now deal with telescope position
   tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(cur_tel_obj, date)
   # Also see if window is to be displayed:
   module_display = request.session.get('module_display', {});

   obs = genMWO(date)
   sid_time = str(obs.sidereal_time())
   # Let's be a little smarter here. If we are imposing telescope limits
   # or an hour-angle limit, that will cut down on objects
   sql = 'SELECT *, CASE WHEN RA-%s < -180 THEN RA-%s+360 WHEN RA-%s > 180 THEN RA-%s - 360 ELSE RA-%s END as HA from navigator_object'
   RAoffset = obs.sidereal_time()*180/pi    # Now in degrees
   l = [RAoffset]*5
   if (only_visible is not None and only_visible):
      sql += " WHERE ( abs(HA) < %s AND DEC > %s)"
      l += [settings.HA_LIMIT*15, settings.DEC_LIMIT]
   elif ha_high is not None:
      sql += " WHERE (abs(HA) < %s and DEC > %s)"
      l += [ha_high*15, settings.DEC_LIMIT]
   else:
      sql += " WHERE (abs(HA) < 90 and DEC > %s)"
      l += [settings.DEC_LIMIT]

   if rating_low is not None:
      sql += " AND rating >= %s"
      l.append(rating_low)
   sql += " OR objtype = 'SS'"
   obj_list = Object.objects.raw(sql, l)

   if show_types is not None:
      obj_list = [obj for obj in obj_list if \
            type_included(obj.objtype,show_types)]
   newlist = []
   for obj in obj_list:  
      obj.epoch = date
      if obj.objtype == 'SS':
         if only_visible is not None and only_visible and not obj.visible():
            continue
         elif ha_high is not None and abs(obj.hour_angle()) > ha_high:
            continue
      newlist.append(obj)
   obj_list = newlist

   #sdate = ephem.Date(date+tzoffset(date)*ephem.hour)
   #sdate = sdate.datetime().strftime('%m/%d/%y %H:%M:%S')
   ldate = ephem.to_timezone(date, zone)
   sdate = ldate.strftime('%m/%d/%y %H:%M:%S')
   stz_offset = "%.1f" % (ldate.utcoffset().total_seconds()/3600)

   script,div = plot_skyview.plot_sky_map(obj_list, date=date, 
         tel_az=tel_az, tel_alt=tel_alt, new_window=True)
   c = {
      'object_list': obj_list, 'form':form, 'date':sdate,
      'method':request.method, 'new_window':True, 'tz_offset':stz_offset,
      'auto_reload':auto_reload, 'selected_object':selected_object,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az,'sid_time':sid_time,'script':script,'div':div,
      'module_display':module_display,
      'selected_tab':selected_tab,
      }
   return render(request, 'navigator/object_list.sortable.html', c)

def mapview(request):
   only_visible = None
   ha_high = settings.HA_SOFT_LIMIT
   epoch = None
   rating_low = None
   new_window = True
   #Default:  nothing posted and no session info
   cur_tel_obj = request.session.get('cur_tel_obj', 'Park')
   prev_tel_obj = request.session.get('prev_tel_obj', 'Park')
   show_types = None
   form = FilterForm()

   if request.method == "POST":
      if request.POST.get('action','') == 'Update':
         form = FilterForm(request.POST)
         # save this form info into the session cache
         request.session['object_list_form'] = request.POST.copy()
      elif request.POST.get('action','') == 'Park':
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
      ha_high = form.cleaned_data.get('ha_high',settings.HA_SOFT_LIMIT)
      show_types = form.cleaned_data.get('show_types', None)
      rating_low = form.cleaned_data.get('rating_low',None)
      epoch = form.cleaned_data.get('epoch',None)

   if epoch:  
      date = ephem.Date(epoch)
      #date = ephem.Date(date - tzoffset(date)*ephem.hour)
   else:
      date = ephem.now()

   # Now deal with telescope position
   tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(cur_tel_obj, date)
   # Also see if window is to be displayed:
   module_display = request.session.get('module_display', {});

   obs = genMWO(date)
   sid_time = str(obs.sidereal_time())
   obj_list = Object.objects.all()
   for obj in obj_list:
      obj.epoch = date
      obj.tel_az = float(tel_az)
   obj_list = sorted(obj_list, key=lambda a: float(a.PrecRAh()))

   new_list = []
   for obj in obj_list:  
      #obj.epoch = date
      if only_visible is not None and only_visible and not obj.visible():
         continue
      if ha_high is not None and \
         abs(obj.hour_angle()) > ha_high:
         continue
      if rating_low is not None and obj.rating < rating_low:
         continue
      if show_types is not None and obj.type not in show_types:
         continue
      new_list.append(obj)
   obj_list = new_list

   if epoch:
      sdate = epoch.strftime('%m/%d/%y %H:%M:%S')
      #stz_offset = "%.1f" % (tzoffset(ephem.Date(epoch), utc=False))
      stz_offset = "%.1f" % (epoch.utcoffset().total_seconds()/3600)
   else:
      #sdate = ephem.Date(ephem.now()+tzoffset(ephem.now())*ephem.hour)
      sdate = ephem.to_timezone(ephem.now(),zone)
      stz_offset = "%.1f" % (sdate.utcoffset().total_seconds()/3600)
      sdate = sdate.strftime('%m/%d/%y %H:%M:%S')

   script,div = plot_skyview.plot_sky_map(obj_list, date=date, 
         tel_az=tel_az, tel_alt=tel_alt)
   c = {
      'form':form, 'date':sdate,
      'method':request.method, 'new_window':True, 'tz_offset':stz_offset,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az,'sid_time':sid_time,'script':script, 'div':div,
      'module_display':module_display,
      }
   return render(request, 'navigator/object_map.html', c)

def detail(request, object_id, view=None):
   obj = Object.objects.get(id=object_id)
   message = None
   error = None
   extras = "?"
   epoch = None
   if view == 'basic':
      request.session['selected_object'] = object_id

   date = get_current_time(request)
   obj.epoch = date
   

   if request.method == 'POST':
      if 'action' in request.POST:
         if request.POST['action'] == 'GOTO':
            request.session['prev_tel_obj'] = request.session.get('cur_tel_obj',
                                                                  'Park')
            request.session['cur_tel_obj'] = obj.name
            request.session['tel_status'] = 'SLEW'
         elif request.POST['action'] == "Sync":
            request.session['prev_tel_obj'] = request.session.get('cur_tel_obj',
                                                                  'Park')
            request.session['tel_status'] = 'IDLE'
         elif request.POST['action'] == "Cancel":
            request.session['cur_tel_obj'] = request.session.get('prev_tel_obj',
                                                                 'Park')
            request.session['tel_status'] = 'IDLE'
            request.session['delete_object'] = 'None'
         elif request.POST['action'] == "Update":
            comments = request.POST['comments']
            rating = int(request.POST.get('rating',0))
            obj.comments = comments
            obj.rating = rating
            obj.save()
         elif request.POST['action'] == "Delete":
            request.session['delete_object'] = 'confirm'
         elif request.POST['action'] == "Confirm":
            request.session['delete_object'] = 'None'
            obj.delete()
            return HttpResponseRedirect('/navigator/')

      elif 'eyepiece' in request.POST:
         request.session['cur_eye'] = request.POST['eyepiece']

   cur_tel_obj = request.session.get('cur_tel_obj', 'Park')
   prev_tel_obj = request.session.get('prev_tel_obj', 'Park')
   tel_status = request.session.get('tel_status', 'IDLE')
   delete_object = request.session.get('delete_object', 'None')

   eyepiece = request.session.get('cur_eye', None)
   if eyepiece is not None:
      FOV = settings.fovs[eyepiece]
   else:
      FOV = settings.FINDER_SIZE

   if FOV != settings.FINDER_BASE_SIZE:
      extras += "size=%d&" % (FOV)
   if settings.FINDER_REVERSE:
      extras += "reverse=1&"
   if settings.FINDER_LOW:
      extras += "low=%d&" % (settings.FINDER_LOW)
   if settings.FINDER_HIGH:
      extras += "high=%d&" % (settings.FINDER_HIGH)
   extras = extras[:-1]     # cleanup trailing & or ?

   # Now deal with telescope position
   if tel_status == "SLEW":
      tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(prev_tel_obj, date)
      new_RA,new_DEC,new_ha,new_alt,new_az = telescope_position(cur_tel_obj, date)
      # Now we move the dome
      delta_az = float(new_az) - float(tel_az)
      if delta_az < -180:
         delta_az += 360
      elif delta_az > 180:
         delta_az -= 360
      if delta_az > 0:
         az_move = "Dome Right %.2f" % (delta_az)
      else:
         az_move = "Dome Left %.2f" % (-delta_az)

      # Now we move in RA
      delta_ra = (ephem.hours(new_RA) - ephem.hours(tel_RA))/pi*12.
      if delta_ra < 0:
         ra_move = "Slew West %.2f h" % (abs(delta_ra))
      else:
         ra_move = "Slew East %.2f h" % (abs(delta_ra))

      # Now we move in DEC
      delta_dec = (ephem.degrees(new_DEC) - ephem.degrees(tel_DEC))/pi*180
      if delta_dec < -180:  delta_dec += 180
      if delta_dec > 180: delta_dec -= 180
      if delta_dec < 0:
         dec_move = "Slew South %.2f" % (abs(delta_dec))
      else:
         dec_move = "Slew North %.2f" % (abs(delta_dec))


   else:
      az_move = None
      ra_move = None
      dec_move = None
      tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(cur_tel_obj, date)
   toff = ephem.to_timezone(date, zone).utcoffset().total_seconds()/3600
   script,div = plot_objs.plot_alt_map([obj], date=date, toff=toff) 
   c = {
      'object':obj, 'extras':extras, 
      'finder_orientation':settings.FINDER_ORIENTATION, 
      'finder_size':FOV,
      'eyepieces':settings.fovs,'cur_eyepiece':eyepiece,
      'message':message, 'error':error, 'epoch':epoch,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az, 'tel_status':tel_status, 'az_move':az_move,
      'ra_move':ra_move, 'dec_move':dec_move, 'script':script, 'div':div,
      'delete_object':delete_object,
      }
   if view is None:
      return render(request, 'navigator/object_detail.html', c)
   else:
      return render(request, 'navigator/object_basic.html', c)

def search_name(request, object_name):
   error = None
   #objs = Object.objects.filter(name__contains=object_name)
   objs = Object.objects.filter(models.Q(name__icontains=object_name) |\
                                models.Q(descr__icontains=object_name) |
                                models.Q(objtype__icontains=object_name))
   if len(objs) == 0:
      error = "No object matching your query was found"
      message = None
   else:
      message = "Found %d objects matching your pattern" % len(objs)

   new_window = True
   #if 'object_list_form' in request.session:
   #   new_window = request.session['object_list_form'].get('new_window', False)
   c = {
      'objects':objs, 'message':message, 'error':error, 'new_window':new_window,
      }
   return render(request, 'navigator/object_search.html', c)

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

@csrf_protect
def update_session(request):
   #message = request.GET.get('message', 'nothing')
   if 'var' not in request.POST:
      return HttpResponse('ok')
   var = request.POST['var']
   if 'key' in request.POST and 'val' in request.POST:
      if var not in request.session:
         request.session[var] = {}
      key = request.POST['key']
      value = request.POST['val']
      request.session[var][key] = value
   elif 'val' in request.POST:
      value = request.POST['val']
      request.session[var] = value
   request.session.modified = True
   return HttpResponse('ok')

@csrf_protect
def update_rating(request):
   if 'obj' not in request.POST or 'rating' not in request.POST:
      return HttpResponse('ok')
   objectid = int(request.POST['obj'])
   obj = Object.objects.get(id=objectid)
   rating = int(request.POST['rating'])
   obj.rating = rating
   obj.save()
   return HttpResponse('ok')

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
         epoch = request.session['object_list_form']['epoch']
         if not epoch or epoch == 'None':
            date = ephem.now()
         else:
            date = ephem.Date(ephem.Date(epoch))
            #date = ephem.Date(date - tzoffset(date)*ephem.hour)
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
   outstr = BytesIO()
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

def add_object(request):

   error = None
   message = None
   if request.method == 'POST':
      form = AddObjectForm(request.POST)
      if form.is_valid():
         object_name = form.cleaned_data['object_name'].strip()
         object_coordinates = form.cleaned_data['object_coordinates'].strip()
         resolve_choice = form.cleaned_data['resolve_choice'].strip()
         
         if object_name:
            data = query.getObjectByName(object_name, 
                  service=resolve_choice)
         else:
            # Need to convert into proper RA/DEC
            # if we have two elements, space-separated, treat as RA/DEC in deg.
            ra,dec = utils.string2RADEC(object_coordinates)
            if ra is None:
               error = "Unrecognized coordinate format"
               data = None
            else:
               data = query.getObjectByCoord(ra,dec, service=resolve_choice)
      if data is None:
         if error is None:  error = "No object found"
      else:
         try:
            o = Object.objects.get(name=object_name)
            for key in data:
               setattr(o, key, data[key])
            message = "Updated exising object"
         except ObjectDoesNotExist:
            message = "Adding object %s" % data['name']
            o = Object(**data)
         # Get the finder
         img = query.get_image(o.RA, o.DEC)
         o.finder.save('finder_'+o.savename()+'.gif', ContentFile(img))
         o.save()
         return HttpResponseRedirect('/navigator/%d/' % o.pk)
   else:
      form = AddObjectForm()

   c = {
      'form':form, 'message':message, 'error':error, 'action':'add'}
   return render(request, 'navigator/add_object.html', c)
