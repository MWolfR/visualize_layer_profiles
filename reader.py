import yaml
import numpy
import requests
from io import BytesIO
from zipfile import ZipFile


class LayerProfiles(object):
    def __init__(self, layer_labels, profile_map):
        self._labels = layer_labels
        self._profiles = profile_map

    def mix(self, mix_recipe):
        out = numpy.zeros(len(self._labels))
        for p in mix_recipe:
            v = p['fraction']
            out += (v * self._profiles[p['name']])
        return out

    def profile_for_projection(self, proj_spec):
        return proj_spec['density'] * self.mix(proj_spec['target_layer_profiles'])

def read_url(url, fn):
    buffer = BytesIO()
    with requests.get(url) as r:
        for some_bytes in r.iter_content():
            buffer.write(some_bytes)
    z = ZipFile(buffer, "r")
    raw = yaml.load(z.read(fn), Loader=yaml.FullLoader)
    layer_profiles = extract_layer_profiles(raw['layer_profiles'])
    return extract_projections(raw['projections'], layer_profiles), layer_profiles._labels 

def read(fn):
    with open(fn, 'r') as fid:
        raw = yaml.load(fid, Loader=yaml.FullLoader)
    layer_profiles = extract_layer_profiles(raw['layer_profiles'])
    return extract_projections(raw['projections'], layer_profiles), layer_profiles._labels 


def extract_projections(projections, layer_profiles):
    output = {}

    for proj in projections:
        curr_src = proj['source']

        if proj['targets'] is not None:
            for tgt_proj in proj['targets']:
                prof = layer_profiles.profile_for_projection(tgt_proj)
                tgt_region = tgt_proj['population'].replace("_ALL_LAYERS", "")
                tgt_hemi = tgt_proj['hemisphere']
                output.setdefault(tgt_region, []).append((curr_src, tgt_hemi, prof))

    return output


def extract_layer_profiles(layer_profiles):

    def lst2lbl(lst):
        return ','.join(lst)

    def read_profile(spec):
        layer_labels = [lst2lbl(d['layers']) for d in spec]
        vals = numpy.array([d['value'] for d in spec])
        return layer_labels, vals

    profile_names = [p['name'] for p in layer_profiles]
    layer_labels, vals = zip(*[read_profile(p['relative_densities']) for p in layer_profiles])

    for lbl in layer_labels: # Only for consistent layer labels at the moment
        assert lbl == layer_labels[0]

    return LayerProfiles(layer_labels[0], dict(zip(profile_names, vals)))




