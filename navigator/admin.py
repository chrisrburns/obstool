from django.contrib import admin

from .models import Object

class ObjectAdmin(admin.ModelAdmin):

   list_display = ('name','RA','DEC','objtype')
   search_fields = ['name']


admin.site.register(Object, ObjectAdmin)
