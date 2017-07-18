from django.contrib import admin
from .models import Person, Photograph, Document, Marriage, Event, Location, Country
# Register your models here.

admin.site.register(Person)
admin.site.register(Photograph)
admin.site.register(Document)
admin.site.register(Marriage)
admin.site.register(Event)
admin.site.register(Location)
admin.site.register(Country)
