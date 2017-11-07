from django.shortcuts import get_object_or_404, render
from .models import Person, Marriage
from django.core.cache import cache


def index(request):
    current = 'family'
    return render(request, 'family/index.html', locals())


def detail(request, person_id):
    current = 'family'
    person = get_object_or_404(Person, pk=person_id)
    template = 'family/detail.html'
    bare = request.GET.get('bare', '')
    if bare:
        template = 'family/detailbare.html'
    return render(request, template, locals())


def mDetail(request, marriage_id):
    marriage = get_object_or_404(Marriage, pk=marriage_id)
    template = 'family/mDetail.html'
    bare = request.GET.get('bare', '')
    if bare:
        template = 'family/mDetailbare.html'
    current = 'family'
    return render(request, template, locals())


def listjson(request):
    context = dict()
    nodes = cache.get('nodes')  # 2 strings, id and label
    edges = cache.get('edges')  # 2 strings, fromid and toid
    if nodes is None:
        nodes = list()
        edges = list()

        # Add all marriages as nodes and edges
        ethan = Person.objects.filter(pk=1)[0]
        for m in ethan.parents.ordered():
            s = 'Marriage'
            mColor = 'white'
            if m.divorced:
                s = 'Divorced'
                mColor = 'gray'
            nodes.append(('m' + str(m.id), s, 'ellipse', mColor, 0))
            for p in m.spouses.all():
                edges.append(('p' + str(p.id), 'm' + str(m.id)))
        for p in ethan.relatives():
            if p.gender == 'M':
                nColor = "#ccffff"
            else:
                nColor = "#ffb6c1"
            nodes.append(('p' + str(p.id), p.name().replace('"', "'"), 'box', nColor, 1))
            if p.parents:
                edges.append(('m' + str(p.parents.id), 'p' + str(p.id)))
        cache.set('nodes', nodes, None)
        cache.set('edges', edges, None)

    context["nodes"] = nodes
    context["edges"] = edges

    return render(request, 'family/list.json', context)
