'''This defines a database router that will redirect
models from the 'objects' app to its own database.
this gets around the problem of other stuff (like sessions)
getting put into the same database.  We want to keep our
data clean.'''

class MyAppRouter(object):

   def db_for_read(self, model, **hints):
      '''Point all 'objects' to the objects database.'''
      print model._meta.app_label
      if model._meta.app_label == 'navigator':
         return 'objects'
      return None

   def db_for_write(self, model, **hints):
      if model._meta.app_label == 'navigator':
         return 'objects'
      return None

   def allow_relation(self, obj1, obj2, **hints):
      if obj1._meta.app_label == 'navigator' or \
         obj2._meta.app_label == 'navigator':
         return True
      return None

   def allow_migrage(self, db, app_label, model_name=None, **hints):
      if app_label == 'navigator':
         return db == 'objects'
      return None
