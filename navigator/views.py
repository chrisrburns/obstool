from django.template import Context, loader, RequestContext
from django.db import models
from navigator.models import Object,genMWO
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django import forms
from obstool import settings
import datetime
#import plot_ams_phases,plot_ams_HA
import plot_skyview_proj as plot_skyview
import plot_objs
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
   ha_high = forms.FloatField(min_value=0.0, required=False,
         label='|HA| <', initial=settings.HA_SOFT_LIMIT,
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
   new_window = False
   tz_offset = 0
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
      tz_offset =form.cleaned_data.get('tz_offset', 0)
      new_window = form.cleaned_data.get('new_window',False)

   if tz_offset is None:
      tz_offset = 0
   if epoch:  
      date = ephem.Date(epoch) - tz_offset*ephem.hour
   else:
      date = ephem.now()

   # Now deal with telescope position
   tel_RA,tel_DEC,tel_ha,tel_alt,tel_az = telescope_position(cur_tel_obj, date)
   # Also see if window is to be displayed:
   module_display = request.session.get('module_display', {});
   print "module_display=",module_display

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
   else:
      sdate = ephem.Date(ephem.now()+tz_offset*ephem.hour)
      sdate = sdate.datetime().strftime('%m/%d/%y %H:%M:%S')
   if tz_offset != 0:
      stz_offset = "%.1f" % (tz_offset)
   else:
      stz_offset = ""

   embed_image = plot_skyview.plot_sky_map(obj_list, date=date, 
         tel_az=tel_az, tel_alt=tel_alt)
   t = loader.get_template('navigator/object_list.sortable.html')
   c = RequestContext(request, {
      'object_list': obj_list, 'form':form, 'date':sdate,
      'method':request.method, 'new_window':new_window, 'tz_offset':stz_offset,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az,'sid_time':sid_time,'embed_image':embed_image,
      'module_display':module_display,
      })
   return HttpResponse(t.render(c))

def mapview(request):
   only_visible = None
   ha_high = settings.HA_SOFT_LIMIT
   epoch = None
   rating_low = None
   new_window = False
   tz_offset = 0
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
      tz_offset =form.cleaned_data.get('tz_offset', 0)
      new_window = form.cleaned_data.get('new_window',False)

   if tz_offset is None:
      tz_offset = 0
   if epoch:  
      date = ephem.Date(epoch) - tz_offset*ephem.hour
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
   else:
      sdate = ephem.Date(ephem.now()+tz_offset*ephem.hour)
      sdate = sdate.datetime().strftime('%m/%d/%y %H:%M:%S')
   if tz_offset != 0:
      stz_offset = "%.1f" % (tz_offset)
   else:
      stz_offset = ""

   embed_image = plot_skyview.plot_sky_map(obj_list, date=date, 
         tel_az=tel_az, tel_alt=tel_alt, imsize=7)
   t = loader.get_template('navigator/object_map.html')
   c = RequestContext(request, {
      'form':form, 'date':sdate,
      'method':request.method, 'new_window':new_window, 'tz_offset':stz_offset,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az,'sid_time':sid_time,'embed_image':embed_image,
      'module_display':module_display,
      })
   return HttpResponse(t.render(c))

def detail(request, object_id):
   obj = Object.objects.get(id=object_id)
   message = None
   error = None
   extras = "?"
   epoch = None
   tz_offset = 0
   if 'object_list_form' in request.session:
      tz_offset = float(request.session['object_list_form']['tz_offset'])
      if tz_offset is None:
         tz_offset = 0

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
         elif request.POST['action'] == "Update":
            comments = request.POST['comments']
            rating = int(request.POST['rating'])
            obj.comments = comments
            obj.rating = rating
            obj.save()

      elif 'eyepiece' in request.POST:
         request.session['cur_eye'] = request.POST['eyepiece']

   cur_tel_obj = request.session.get('cur_tel_obj', 'Park')
   prev_tel_obj = request.session.get('prev_tel_obj', 'Park')
   tel_status = request.session.get('tel_status', 'IDLE')

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
   t = loader.get_template('navigator/object_detail.html')

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
   embed_plot = plot_objs.plot_alt_map([obj], date=date, toff=tz_offset) 
   c = RequestContext(request, {
      'object':obj, 'extras':extras, 
      'finder_orientation':settings.FINDER_ORIENTATION, 
      'finder_size':FOV,
      'eyepieces':settings.fovs,'cur_eyepiece':eyepiece,
      'message':message, 'error':error, 'epoch':epoch,
      'tel_RA':tel_RA,'tel_DEC':tel_DEC,'tel_ha':tel_ha,'tel_alt':tel_alt,
      'tel_az':tel_az, 'tel_status':tel_status, 'az_move':az_move,
      'ra_move':ra_move, 'dec_move':dec_move, 'embed_plot':embed_plot,
      })
   return HttpResponse(t.render(c))

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

@csrf_protect
def update_session(request):
   #message = request.GET.get('message', 'nothing')
   if 'var' not in request.POST:
      print 'var not found'
      return HttpResponse('ok')
   var = request.POST['var']
   print 'var = ',var
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
            date = ephem.Date(ephem.Date(epoch) - tz_offset*ephem.hour)
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
      print size
      size = int(size)
      print size
      scale = 1.0*settings.FINDER_BASE_SIZE/img.size[0]    # arc-min per pixel
      print scale
      new_size = int(size/scale)  # New size in pixels
      print new_size
      print img.size[0], img.size[1]
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

