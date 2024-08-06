'''A module to make WEB querries to the NED and SIMBAD databases
and extract useful info'''

from astropy.utils.data import get_readable_fileobj
from astropy.table import Table
import requests
from io import BytesIO
from PIL import Image

NED_NAME_QUERY = "http://ned.ipac.caltech.edu/cgi-bin/objsearch?objname=%s&extend=no&hconst=73&omegam=0.27&omegav=0.73&corr_z=1&out_csys=Equatorial&out_equinox=J2000.0&obj_sort=RA+or+Longitude&of=%s&zv_breaker=30000.1&list_limit=5&img_stamp=NO"

NED_COORD_QUERY = "http://ned.ipac.caltech.edu/cgi-bin/objsearch?in_csys=Equatorial&in_equinox=J2000.0&lon=%.5fd&lat=%.5fd&radius=1.0&hconst=73&omegam=0.27&omegav=0.73&corr_z=1&z_constraint=Unconstrained&z_value1=&z_value2=&z_unit=z&ot_include=ANY&nmp_op=ANY&out_csys=Equatorial&out_equinox=J2000.0&obj_sort=Distance+to+search+center&of=%s&zv_breaker=30001.0&list_limit=5&img_stamp=YES&search_type=Near+Position+Search"

SIMBAD_URL = 'http://simbad.u-strasbg.fr/simbad/sim-script?script='
SIMBAD_QUERY = '''output console=off script=off
votable v1 {
   MAIN_ID
   RA(d;ICRS;2000.0;2000.0)
   DEC(d;ICRS;2000.0;2000.0)
   OTYPE(S)
   DIM_MAJAXIS
   FLUX(V)
}
votable open v1
%s
votable close
'''

poss_url = "http://archive.stsci.edu/cgi-bin/dss_search?v=poss2ukstu_red&r=%f&d=%f&e=J2000&h=60.0&w=60.0&f=gif"

def get_image(ra, dec):
   u = requests.get(poss_url % (ra,dec))
   f = BytesIO(u.content)
   u.close()
   im = Image.open(f)
   #f.close()
   x,y = im.size
   im2 = im.resize((x//2,y//2))
   f2 = BytesIO()
   im2.save(f2, format='PNG')
   f.close()
   retstring = f2.getvalue()
   f2.close()
   return retstring

def getObjectByName(name, service='ned'):
   if service not in ['simbad','ned']:
      raise ValueError("service must be one of 'ned' or 'simbad'")

   data = {}
   if service == 'ned':
      try:
         with get_readable_fileobj(NED_NAME_QUERY % \
                                   (urllib.quote(name),'xml_main')) as f:
            table = Table.read(f, format='votable')
      except:
         return None
      data['RA'] = float(table['main_col3'])
      data['DEC'] = float(table['main_col4'])
      data['objtype'] = str(table['main_col5'][0])
      data['descr'] = "Results of NED query"
      data['name'] = name
      data['Mv'] = str(table['main_col9'][0])
      data['rating'] = 0
 
      with get_readable_fileobj(NED_NAME_QUERY % \
            (urllib.quote(name),'xml_basic')) as f:
         table = Table.read(f, format='votable')
      if table['basic_col10'][0]:
         data['size'] = "%.1f arc-min" % (float(table['basic_col10'][0]))
      else:
         data['size'] = "..."
   elif service == 'simbad':
      try:
         with get_readable_fileobj(\
               SIMBAD_URL+urllib.quote(SIMBAD_QUERY % name)) as f:
            table = Table.read(f, format='votable')
      except:
         return None
      data['RA'] = table['RA_d_ICRS_2000_0_2000_0'][0]
      data['DEC'] = table['DEC_d_ICRS_2000_0_2000_0'][0]
      data['objtype'] = table['OTYPE_S'][0] or "--"
      data['objtype'] = table['OTYPE_S'][0] or "--"
      data['Mv'] = str((table['FLUX_V'][0] or "--"))
      data['descr'] = "Results from SIMBAD query"
      data['name'] = name
      data['rating'] = 0
      if table['GALDIM_MAJAXIS'][0]:
         data['size'] = "%.1f arc-min" % table['GALDIM_MAJAXIS'][0]
      else:
         data['size'] = '--'
   data['distance'] = -1.
   data['dark'] = False
   data['comments'] = 'None'
   return data

def getObjectByCoord(ra, dec, service='ned'):

   if service not in ['simbad','ned']:
      raise ValueError("service must be one of 'ned' or 'simbad'")

   data = {}
   if service == 'ned':
      try:
         with get_readable_fileobj(NED_COORD_QUERY % (ra,dec,'xml_main')) as f:
            table = Table.read(f, format='votable')
      except:
         return None
      data['RA'] = float(table['main_col3'][0])
      data['DEC'] = float(table['main_col4'][0])
      data['objtype'] = table['main_col5'][0]
      data['descr'] = "Results of NED query"
      data['name'] = table['main_col2'][0]
      data['Mv'] = table['main_col9'][0]
      data['rating'] = 0
 
      with get_readable_fileobj(NED_NAME_QUERY % \
                                (urllib.quote(data['name']),'xml_basic')) as f:
         table = Table.read(f, format='votable')
      try:
         data['size'] = "%.1f arc-min" % (float(table['basic_col10']))
      except:
         data['size'] = "..."
   elif service == 'simbad':
      coord = 'query coo %f %f radius=1m' % (ra,dec)
      try:
         with get_readable_fileobj(\
               SIMBAD_URL+urllib.quote(SIMBAD_QUERY % coord)) as f:
            table = Table.read(f, format='votable')
      except:
         return None
      data['RA'] = table['RA_d_ICRS_2000_0_2000_0'][0]
      data['DEC'] = table['DEC_d_ICRS_2000_0_2000_0'][0]
      data['objtype'] = table['OTYPE_S'][0] or "--"
      data['objtype'] = table['OTYPE_S'][0] or "--"
      data['Mv'] = str((table['FLUX_V'][0] or "--"))
      data['descr'] = "Results from SIMBAD query"
      data['name'] = table['MAIN_ID'][0]
      data['rating'] = 0
      if table['GALDIM_MAJAXIS'][0]:
         data['size'] = "%.1f arc-min" % table['GALDIM_MAJAXIS'][0]
      else:
         data['size'] = '--'
   data['distance'] = -1.
   data['dark'] = False
   data['comments'] = 'None'
   return data



