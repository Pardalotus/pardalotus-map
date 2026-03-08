from io import StringIO
from rdflib import Graph, URIRef, graph
from os.path import join
import shutil
import markdown
import json

g = Graph()
g.parse('./file.ttl')

BUILD_DIR = "docs"

base_uri = 'https://map.pardalotus.tech/'

label_uri = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
see_also_uri = URIRef("http://www.w3.org/2000/01/rdf-schema#seeAlso")
type_uri = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
comment_uri = URIRef("http://www.w3.org/2000/01/rdf-schema#comment")
homepage_uri = URIRef("https://map.pardalotus.tech/Homepage")
background_reading_uri = URIRef("https://map.pardalotus.tech/BackgroundReading")

source_code_uri = URIRef("https://map.pardalotus.tech/SourceCode")


ignore_list = {
    URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
    URIRef('http://www.w3.org/2000/01/rdf-schema#seeAlso'),
    URIRef('http://www.w3.org/2000/01/rdf-schema#related'),
}

ignore_instances = {
    URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate')
}


# These have special cases for display so filter them out of the 'other' listing.
ignore = {
    label_uri, comment_uri, type_uri, see_also_uri
}

graph_ignore = {
    label_uri, comment_uri, see_also_uri, homepage_uri, source_code_uri, background_reading_uri
}


# only subjects
# give a label if you want to include it
all_items = g.subjects(unique=True)
all_items = sorted(all_items, key=lambda x: str(x))

md = StringIO()

def get_path(g, subject):
    stripped = subject.removeprefix(base_uri)
    if stripped.startswith("http"):
        return stripped
    else:
        return f"#{stripped}"

def get_label(g, subject):
    label = g.value(predicate=label_uri, subject=subject)
    return label or get_path(g, subject).removeprefix("#")

for subject in all_items:
    skip = False

    if subject in ignore_list:
        skip = True

    for instance_type in ignore_instances:
        if list(g.triples((subject,None, instance_type))):
            skip = True

    if skip:
        continue

    display_label = get_label(g, subject)
    path = get_path(g, subject).removeprefix("#")
    comment = g.value(predicate=comment_uri, subject=subject)
    see_also = list(g.objects(predicate=see_also_uri, subject=subject))
    instances = list(g.subjects(predicate=type_uri, object=subject))
    types = list(g.objects(predicate=type_uri, subject=subject))

    others = [(s,v,o) for (s,v,o) in g.triples((subject, None, None)) if v not in ignore]

    others_references = [(s,v,o) for (s,v,o) in g.triples((None, None, subject)) if v not in ignore]

    md.write(f"<a name='{path}'></a>\n")
    if display_label:
        md.write(f"## {display_label} \n")

    if comment:
        md.write(f"> {comment} \n\n")

    if types:
        for typ in types:
            label = get_label(g, typ)
            path = get_path(g, typ)

            md.write(f"- Type of [{label}]({path}). \n")

    for x in see_also:
        md.write(f"- See: <{x}> \n")

    if others:

        for (s, v, o) in others:
            v_label = get_label(g, v)
            o_label = get_label(g, o)
            o_path = get_path(g, o)

            md.write(f"- {v_label} [{o_label}]({o_path}) \n")
        md.write("\n")

    md.write("\n")

    if instances:
        md.write("### Instances \n")
        for instance in instances:
            label = get_label(g, instance)
            path = get_path(g, instance)
            md.write(f"- [{label}]({path}) \n")

        md.write("\n")

    if others_references:
        md.write("### References \n")

        for (s, v, o) in others_references:
            v_label = get_label(g, v)
            s_label = get_label(g, s)
            s_path = get_path(g, s)

            md.write(f"- [{s_label}]({s_path}) {v_label} ～\n")
        md.write("\n")

    md.write("\n")

with open(join(BUILD_DIR, 'file.md'), 'w') as of:
    md.seek(0)
    shutil.copyfileobj(md, of)

md.seek(0)

html = markdown.markdown(md.getvalue())

data = []
for (s, v, o) in g:
    if v not in graph_ignore:
        s_label = str(s).removeprefix(base_uri)
        o_label = str(o).removeprefix(base_uri)
        data.append({'source': s_label, 'target': o_label, 'type': v})

with open(join(BUILD_DIR, 'index.html'), 'w') as of:
    with open("preamble.html", 'r') as pf:
        template = pf.read()

        # extra quotes in source so the JS parses pre-template.
        templated = template.replace('"<!-- data -->"', json.dumps(data)).replace('<!-- content -->', html)

    of.write(templated)


g.bind("f", URIRef("http://www.w3.org/2000/01/rdf-schema#"));
g.bind("s", URIRef("https://schema.org/"));
g.bind("o", URIRef("https://www.w3.org/TR/owl-ref/#"));
g.bind("k", URIRef("http://www.w3.org/2004/02/skos/core#"));


g.serialize(destination=join(BUILD_DIR, 'map.ttl'), format="longturtle", base=base_uri)
