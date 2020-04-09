import numpy
import plotly.graph_objects as go

def all_together(a_str, include_layer):
    return "ALL"

def by_region(a_str):
    return a_str.split('_')[0]

def by_proj_class(a_str):
    return a_str.split('_')[1]

def no_grouping(a_str):
    return a_str

def parse_label(lbl, hemi, densities, layer_labels):
    assert len(densities) == len(layer_labels)
    region, proj_class = lbl.split('_')
    out_specs = [{'Region': region, 'Projection class': proj_class,
                  'Hemisphere': hemi,
                  'Target layer': l_label} for l_label in layer_labels]
    return out_specs, densities

groupings = dict([("With layers",
                   dict([("All together", ("Tgt. layer {0}", ["Target layer"])),
                         ("By region", ("{0} to layer {1}", ["Region", "Target layer"])),
                         ("By projection class", ("Via {0} to layer {1}", ["Projection class", "Target layer"])),
                         ("By hemisphere", ("{0} to layer {1}", ["Hemisphere", "Target layer"])),
                         ("No grouping", ("{0} via {1} to layer {2}", ["Region", "Projection class", "Target layer"]))])),
                  ("Without layers",
                   dict([("All together", ("All", [])),
                         ("By region", ("{0}", ["Region"])),
                         ("By projection class", ("Via {0}", ["Projection class"])),
                         ("By hemisphere", ("{0}", ["Hemisphere"])),
                         ("No grouping", ("{0} via {1}", ["Region", "Projection class"]))]))
                 ])

def make_label(spec, lbl_str, lbl_keys):
    return lbl_str.format(*[spec[_k] for _k in lbl_keys])

def labeller_factory(layer_handling, grouping):
    lbl_str, lbl_keys = groupings[layer_handling][grouping]
    def out_func(spec):
        return make_label(spec, lbl_str, lbl_keys)
    return out_func


class RegionProfile(object):

    def __init__(self, raw_profile, layer_labels, colors=None):
        self._raw = raw_profile
        self._raw_sources, self._raw_densities = self._extract_data(raw_profile, layer_labels)
        self._layer_labels = layer_labels
        self._cols = colors
        self._types_of_layer_handling, self._types_of_groups, self._cache = \
                                       self._cache_groupings()
    
    def _extract_data(self, raw_profile, layer_labels):
        raw_sources, raw_densities = [], []
        for src, hemi, density in raw_profile:
            out_specs, out_densities = parse_label(src, hemi, density, layer_labels)
            raw_sources.extend(out_specs)
            raw_densities.extend(out_densities)
        assert len(raw_sources) == len(raw_densities)
        return raw_sources, numpy.array(raw_densities)
    
    def _group(self, layer_handling, grouping):
        grp_fun = labeller_factory(layer_handling, grouping)
        grp_labels = numpy.array(list(map(grp_fun, self._raw_sources)))
        u_labels = numpy.unique(grp_labels).tolist()
        grouping = [numpy.nonzero(grp_labels == u)[0]
                    for u in u_labels]
        reverse_grouping = [u_labels.index(l) for l in grp_labels]
        return u_labels, grouping, reverse_grouping
    
    def _cache_groupings(self):
        cache = {}
        types_of_groupings = []
        types_of_layer_handling = []
        for layer_handling in groupings.keys():
            types_of_layer_handling.append(layer_handling)
            for grp in groupings[layer_handling].keys():
                if grp not in types_of_groupings:
                    types_of_groupings.append(grp)
                cache.setdefault(layer_handling, {})[grp] = self._group(layer_handling, grp)
        return types_of_layer_handling, types_of_groupings, cache

    def set_up_groups(self, group_specs):
        base_spec, group_specs = group_specs[0], group_specs[1:]
        base_lbls, base_grp, base_idx = self._cache[base_spec[0]][base_spec[1]]
        self._base_str = numpy.vstack([self._raw_densities[idx].sum() for
                                       idx in base_grp])
        self._labels = [base_lbls]
        self._str_mats = [self._base_str.reshape((1,) + self._base_str.shape)]

        # L = self._raw_densities.shape[1]
        # grp_funcs = [self._types_of_groups[_grp] for _grp in order]
        for spec in group_specs:
            new_lbls, new_grp, new_idx = self._cache[spec[0]][spec[1]]
            mat = numpy.zeros((len(base_grp), len(new_grp)))
            for i, idx1 in enumerate(base_grp):
                for j, idx2 in enumerate(new_grp):
                    idxx = numpy.intersect1d(idx1, idx2)
                    mat[i, j] = self._raw_densities[idxx].sum()
            self._labels.append(new_lbls)
            self._str_mats.append(mat)
            base_lbls, base_grp, base_idx = new_lbls, new_grp, new_idx

    def get_plotly_labels(self):
        all_labels = []
        offsets = []
        for lbls in self._labels:
            offsets.append(len(all_labels))
            all_labels.extend(lbls)
        if self._cols is None:
            lbl_colors = "blue"
        else:
            lbl_colors = self._cols.color_labels(all_labels)
        return all_labels, offsets, lbl_colors

    def get_plotly_links(self, offsets, cols, threshold=0.0):
        link_dict = dict([("source", []), ("target", []), ("value", []), ("color", [])])
        for mat_index, mat in enumerate(self._str_mats[1:]):
            o1 = offsets[mat_index]
            o2 = offsets[mat_index + 1]
            for i in range(mat.shape[0]):
                for j in range(mat.shape[1]):
                    if mat[i, j] > threshold:
                        link_dict['source'].append(o1 + i)
                        link_dict['target'].append(o2 + j)
                        link_dict['value'].append(mat[i, j])
                        link_dict['color'].append(cols[o1 + i].replace("1.0", "0.6")) # Adjusting transparency
        return link_dict

    def make_sankey(self, y_domain=[0, 1], threshold=0.0):
        all_labels, offset, lbl_colors = self.get_plotly_labels()
        label_dict = dict([("pad", 15), ("thickness", 20), ("line", dict([("color", "black"), ("width", 0.5)])),
                           ("label", all_labels), ("color", lbl_colors)])
        link_dict = self.get_plotly_links(offset, lbl_colors, threshold=threshold)
        return go.Sankey(
                         node=label_dict,
                         link=link_dict,
                         domain=go.sankey.Domain(y=y_domain)
        )
       
    def plot(self):
        S = self.make_sankey()
        ttl_dict = dict([("text", "Long-range innervation"), ("font_size", 12)])
        fig = go.FigureWidget(data=[S], layout=go.Layout(title=ttl_dict))
        # fig.show()
        return fig



