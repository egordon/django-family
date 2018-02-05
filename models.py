from django.db import models
from django.contrib.auth.models import User
from .fields import UncertainDateField
from opencage.geocoder import OpenCageGeocode
import os
from django.conf import settings
from datetime import date
from tinymce.models import HTMLField
from django.core.cache import cache
# Based off of:
# https://github.com/dwdyer/familytree/blob/master/people/models.py


class Person(models.Model):
    birth = models.ForeignKey('Event', null=True, blank=True, related_name='+')
    death = models.ForeignKey('Event', null=True, blank=True, related_name='+')
    burial = models.ForeignKey('Event', null=True, blank=True, related_name='+')
    gender = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female'), ('O', 'Other')), blank=False, default=None)
    bio = HTMLField(blank=True)
    parents = models.ForeignKey('Marriage', blank=True, null=True, related_name='children_of', on_delete=models.SET_NULL)
    mugshot = models.ForeignKey('Photograph', blank=True, null=True, related_name='photo_of', on_delete=models.SET_NULL)

    # A person can be linked to a user account. This allows a user to see
    # information relevant to their own relationships.
    user = models.OneToOneField(User, blank=True, null=True)

    # And now all the name craziness
    firstName = models.CharField(blank=True, max_length=20, verbose_name='First/Given Name')
    middleNames = models.CharField(blank=True, max_length=50, verbose_name='Middle Names(s)')
    nickName = models.CharField(blank=True, max_length=20, verbose_name='Nickname')
    lastName = models.CharField(max_length=30, verbose_name='Last/Family Name')
    birthName = models.CharField(blank=True, max_length=30, verbose_name='Maiden/Birth Name')
    birthFirstName = models.CharField(blank=True, max_length=30, verbose_name='Birth First Name', help_text='(if different)')

    def __str__(self):
        if self.birth:
            return self.name() + " (" + str(self.birth.date.year) + ')'
        return self.name() + " (Unknown)"

    def name(self, useMiddle=True, useMaiden=False):
        '''Returns the full name of this person.'''
        name = ' '.join([self.firstName, self.middleNames]) if useMiddle and self.middleNames else self.firstName
        if self.nickName:
            name = name + ' "{0}"'.format(self.nickName)
        if self.birthName != '':
            return name + ' ' + (self.birthName if useMaiden else self.lastName)
        else:
            return name + ' ' + self.lastName

    def given_names(self):
        return " ".join([self.firstName, self.middleNames]) if self.middleNames else self.firstName

    def birth_lastname(self):
        return self.birthName if self.birthName else self.lastName

    def birth_firstname(self):
        return self.birthFirstName if self.birthFirstName else self.firstName

    def birth_name(self):
        return '{0} {1}'.format(self.birth_firstname().upper(), self.birth_lastname().upper())

    def date_of_birth(self):
        return self.birth.date if self.birth else None

    def birth_location(self):
        return self.birth.location if self.birth else None

    def date_of_death(self):
        return self.death.date if self.death else None

    def age(self):
        '''Calculate the person's age in years.'''
        if not self.date_of_birth():
            return None
        end = self.date_of_death() if self.date_of_death() else date.today()
        years = end.year - self.date_of_birth().year
        if end.month and self.date_of_birth().month:
            if end.month < self.date_of_birth().month or (end.month == self.date_of_birth().month and end.day and self.date_of_birth().day and end.day < self.date_of_birth().day):
                years -= 1
        return years

    class Meta:
        ordering = ['lastName', 'firstName', 'middleNames', '-birth__date']

    def relatives(self, visited=None):
        if visited is None:
            visited = set()
        visited.add(self)
        # First parent
        if self.parents:
            p = self.parents.spouses.all()[0]
            if p not in visited:
                for n in p.relatives(visited):
                    yield n

        # Then Self
        yield self

        # Then Spouse and Children
        for m in self.marriages.all():
            for s in m.spouses.all():
                if s not in visited:
                    for n in s.relatives(visited):
                        yield n
            for child in m.children_of.all():
                if child not in visited:
                    for n in child.relatives(visited):
                        yield n

        # Then other parent
        if self.parents and len(self.parents.spouses.all()) > 1:
            p = self.parents.spouses.all()[1]
            if p not in visited:
                for n in p.relatives(visited):
                    yield n


class Country(models.Model):
    name = models.CharField(max_length=50)
    country_code = models.CharField(max_length=3)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'countries'


class Location(models.Model):
    '''A location is not meant to be a pinpoint address but a general place such
    as a town or village.'''
    name = models.CharField(blank=True, max_length=30, help_text='Place Name')
    city = models.CharField(blank=True, max_length=30, help_text='City / Town / Village')
    county_state_province = models.CharField(blank=True, max_length=30, verbose_name='county/state/province', help_text='County / State / Province')
    country = models.ForeignKey(Country, help_text='Country')
    # If left blank, these fields will be set by geocoding when the model is
    # saved.
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not (self.latitude and self.longitude):
            try:
                geocoder = OpenCageGeocode(settings.OPENCAGE_API_KEY)
                query = '{0}, {1}, {2}, {3}'.format(self.name, self.city, self.county_state_province, self.country.name)
                result = geocoder.geocode(query)
                geometry = result[0].get('geometry')
                self.latitude = geometry.get('lat')
                self.longitude = geometry.get('lng')
            except Exception as e:
                # If something goes wrong, there's not much we can do, just leave
                # the coordinates blank.
                print(e)
        super(Location, self).save(*args, **kwargs)

    def __str__(self):
        lStrings = list()
        if self.name:
            lStrings.append(self.name)
        if self.city:
            lStrings.append(self.city)
        if self.county_state_province:
            lStrings.append(self.county_state_province)
        if self.country:
            lStrings.append(self.country.country_code)
        return ", ".join(lStrings)

    def __hash__(self):
        return hash(self.name) + hash(self.latitude) + hash(self.longitude)

    class Meta:
        ordering = ['country', 'county_state_province', 'city', 'name']
        unique_together = [('country', 'county_state_province', 'city', 'name')]


class Photograph(models.Model):
    '''The photograph record combines an image with an optional caption and date
    and links it to one or more people.'''
    image = models.ImageField(upload_to='photos', blank=False, null=False)
    people = models.ManyToManyField(Person, related_name='photos')
    caption = models.TextField(blank=True)
    date = UncertainDateField(blank=True, null=True)
    location = models.ForeignKey(Location, blank=True, null=True, related_name='photos')

    def __str__(self):
        return self.image.url

    class Meta:
        ordering = ['date']


class Document(models.Model):
    file = models.FileField(upload_to='documents', blank=False, null=False)
    title = models.CharField(max_length=100)
    people = models.ManyToManyField(Person, related_name='documents')

    def file_extension(self):
        _, extension = os.path.splitext(self.file.name)
        return extension[1:]

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']


class Event(models.Model):
    '''Arbitrary event connected to a person.'''
    BIRTH = 0
    MARRIAGE = 1
    DEATH = 2
    BURIAL = 3
    eventType = [(BIRTH, 'Birth'), (DEATH, 'Death'), (BURIAL, 'Burial')]

    person = models.ForeignKey(Person, related_name='events')
    eventType = models.PositiveSmallIntegerField(choices=eventType)
    date = UncertainDateField()
    location = models.ForeignKey(Location, blank=True, null=True, related_name='events')
    reference = models.URLField(blank=True, null=True)

    def verb(self):
        if self.eventType == Event.BIRTH:
            return 'born'
        elif self.eventType == Event.DEATH:
            return 'died'
        elif self.eventType == Event.BURIAL:
            return 'buried'
        else:
            return None

    def __str__(self):
        return self.person.name() + ' ' + self.verb() + ' ' + self.date.__str__()

    def save(self, *args, **kwargs):
        super(Event, self).save(*args, **kwargs)
        # If this event is a birth or death event, the corresponding person
        # record must point back to it for the database to be consistent, so
        # update that here.
        if self.eventType == Event.BIRTH:
            self.person.birth = self
            self.person.save()
        elif self.eventType == Event.DEATH:
            self.person.death = self
            self.person.save()

    class Meta:
        ordering = ['date']


class Marriage(models.Model):
    '''The marriage record links spouses.'''
    eventType = Event.MARRIAGE
    date = UncertainDateField(blank=True, null=True)
    location = models.ForeignKey(Location, blank=True, null=True, related_name='weddings')
    reference = models.URLField(blank=True, null=True)

    divorced = UncertainDateField(blank=True, null=True)
    isMarriage = models.BooleanField(default=True)
    spouses = models.ManyToManyField(Person, related_name='marriages')
    album = models.ManyToManyField(Photograph, blank=True)

    def save(self, *args, **kwargs):
        cache.delete('nodes')
        cache.delete('edges')
        super(Marriage, self).save(*args, **kwargs)

    def __str__(self):
        nameList = list()
        for spouse in self.spouses.all():
            nameList.append(spouse.name())
        return " & ".join(nameList)

    def verb(self):
        return 'married'

    class Meta:
        ordering = ['-date']

    def ordered(self, visited=None):
        if visited is None:
            visited = set()
        visited.add(self)

        # First spouse parents
        s = self.spouses.all()[0]
        if s.parents and s.parents not in visited:
            for n in s.parents.ordered(visited):
                yield n

        # Then other marriages
        for m in s.marriages.all():
            if m not in visited:
                for n in m.ordered(visited):
                    yield n

        # Then Self
        yield self

        # Then Children's Marriages
        for child in self.children_of.all():
            for m in child.marriages.all():
                if m not in visited:
                    for n in m.ordered(visited):
                        yield n

        # Then other spouse's parents
        if len(self.spouses.all()) > 1:
            s = self.spouses.all()[1]
            if s.parents and s.parents not in visited:
                for n in s.parents.ordered(visited):
                    yield n

            # And marriages
            for m in s.marriages.all():
                if m not in visited:
                    for n in m.ordered(visited):
                        yield n
