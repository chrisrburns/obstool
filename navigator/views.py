from django.shortcuts import render
import sys,os,subprocess
from django.template import Context, loader, RequestContext
from django.shortcuts import render_to_response
from navigator.models import Object
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
   tz_offset = forms.FloatField(required=False, initial=0)
   new_window = forms.BooleanField(required=False, initial=False)


def index(request):
   only_visible = None
   airmass_high = 2.0
   epoch = None
   rating_low = None
   new_window = False
   tz_offset = 0
   if request.method == "POST" or 'object_list_form' in request.session:
      if request.method == "POST":
         if request.POST['action'] == 'Update':
            form = FilterForm(request.POST)
            # save this form info into the session cache
            request.session['object_list_form'] = request.POST.copy()
         else:
            form = FilterForm()
            if 'object_list_form' in request.session:
               del request.session['object_list_form']
      else:
         form = FilterForm(request.session['object_list_form'])
      if form.is_valid():
         only_visible = form.cleaned_data.get('only_visible',None)
         airmass_high = form.cleaned_data.get('airmass_high',2.0)
         rating_low = form.cleaned_data.get('rating_low',None)
         epoch = form.cleaned_data.get('epoch',None)
         tz_offset =form.cleaned_data.get('tz_offset', 0)
         new_window = form.cleaned_data.get('new_window',False)
   else:
      form = FilterForm()

   if tz_offset is None:
      tz_offset = 0
   if epoch:  
      date = ephem.Date(epoch) - tz_offset*ephem.hour
   else:
      date = ephem.now()

   obj_list = sorted(Object.objects.all(), key=lambda a: float(a.PrecRAh()))
   for obj in obj_list:  
      if type(obj_list) is not type([]):
         obj_list = list(obj_list)
      new_list = []
      for obj in obj_list:
         if only_visible is not None and only_visible and not obj.visible(date):
            continue
         if airmass_high is not None and \
            not 0 < float(obj.airmass(date)) <= airmass_high:
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

   t = loader.get_template('navigator/object_list.sortable.html')
   c = RequestContext(request, {
      'object_list': obj_list, 'form':form, 'date':sdate,
      'method':request.method, 'new_window':new_window, 'tz_offset':stz_offset,
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
      epoch = str(request.session['object_list_form']['epoch'])
      tz_offset = float(request.session['object_list_form']['tz_offset'])
      if tz_offset is None:
         tz_offset = 0
      if not epoch:
         date = ephem.now()
      else:
         date = ephem.Date(epoch) - tz_offset*ephem.hour
   else:
      epoch = None

   if tz_offset is None:
      tz_offset = 0
   if epoch:  
      date = ephem.Date(epoch) - tz_offset 
   else:
      date = ephem.now()

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
   c = Context({
      'object':obj, 'extras':extras, 
      'finder_orientation':settings.FINDER_ORIENTATION, 
      'finder_size':settings.FINDER_SIZE,
      'message':message, 'error':error, 'epoch':epoch
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

class AMFilterForm(forms.Form):
   airmass_high = forms.FloatField(min_value=1.0, required=False,
         label='Airmass <',
         widget=forms.TextInput(attrs={'size':'5'}))
   epoch = forms.DateTimeField(required=False)
   rating_low = forms.IntegerField(required=False,
         label='Rating >=', 
         widget=forms.TextInput(attrs={'size':'5'}))
   new_window = forms.BooleanField(required=False, initial=False)

#def am_plot(request):
#   date = None            # date for which to do the airmass plot
#   airmass_high = 2.0     # only consider data with airmass < this
#   rating_low = None       # filter on priority
#   new_window = False     # Does clicking on object open a new window?
#
#   if request.method == "POST" or 'am_plot_form' in request.session:
#      if request.method == "POST":
#         if request.POST['action'] == 'Update':
#            form = AMFilterForm(request.POST)
#            request.session['am_plot_form'] = request.POST.copy()
#         else:
#            form = AMFilterForm()
#            if 'am_plot_form' in request.session:
#               del request.session['am_plot_form']
#      else:
#         form = AMFilterForm(request.session['am_plot_form'])
#      if form.is_valid():
#         date = form.cleaned_data.get('epoch',None)
#         airmass_high = form.cleaned_data.get('airmass_high',2.0)
#         if airmass_high is None:  airmass_high = 2.0
#         rating_low = form.cleaned_data.get('rating_low',None)
#         new_window = form.cleaned_data.get('new_window', False)
#   else:
#      form = AMFilterForm()
#
#   objs = Object.objects.all()
#   keep = []
#   if rating_low is not None:
#      for o in objs:
#         if rating_low is not None and o.rating < rating_low:  continue
#         keep.append(o)
#   else:
#      keep = objs
#
#   if date is None:  
#      date = ephem.now()
#   else:
#      date = ephem.Date(date)
#   embed_image = plot_ams_phases.plot_ams_map(keep, date=date,
#         max_am = airmass_high, new_window=new_window)
#   t = loader.get_template('navigator/am_plot.html')
#   c = RequestContext(request, {
#      'embed_image':embed_image, 'form':form, 'date':date, 'new_window':new_window,
#      })
#   return HttpResponse(t.render(c))
#
#
#def am_ha_plot(request):
#   only_visbile = None
#   airmass_high = 2.0
#   epoch = None
#   rating_low = None
#   new_window = False
#   if request.method == "POST" or 'object_list_form' in request.session:
#      if request.method == "POST":
#         if request.POST['action'] == 'Update':
#            form = FilterForm(request.POST)
#            # save this form info into the session cache
#            request.session['object_list_form'] = request.POST.copy()
#         else:
#            form = FilterForm()
#            if 'object_list_form' in request.session:
#               del request.session['object_list_form']
#      else:
#         form = FilterForm(request.session['object_list_form'])
#      if form.is_valid():
#         only_visible = form.cleaned_data.get('only_visible',None)
#         airmass_high = form.cleaned_data.get('airmass_high',2.0)
#         epoch = form.cleaned_data.get('epoch',None)
#         rating_low = form.cleaned_data.get('rating_low',None)
#         new_window = form.cleaned_data.get('new_window', False)
#   else:
#      form = FilterForm()
#
#   if epoch:
#      date = ephem.Date(epoch)
#   else:
#      date = ephem.now()
#
#   obj_list = Object.objects.all().order_by('name')
#
#   if only_visible is not None or airmass_high is not None or \
#      rating_low is not None:
#      # Apply the filters
#      if type(obj_list) is not type([]):
#         obj_list = list(obj_list)
#      new_list = []
#      for obj in obj_list:
#         obj.epoch = date
#         if only_visible is not None and not obj.visible(date):
#            continue
#         if airmass_high is not None and not 0 < float(obj.airmass()) <= airmass_high:
#            continue
#         if rating_low is not None and obj.rating < rating_low:
#            continue
#         new_list.append(obj)
#      obj_list = new_list
#
#   embed_image = plot_ams_HA.plot_ams_map(obj_list, date=date, 
#         new_window=new_window, airmass_high=airmass_high)
#   t = loader.get_template('navigator/am_ha_plot.html')
#   c = RequestContext(request, {
#      'embed_image':embed_image, 'form':form, 'date':date, 'new_window':new_window,
#      })
#   return HttpResponse(t.render(c))
