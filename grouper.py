import numpy
import plotly.graph_objects as go

def all_together(a_str):
    return "ALL"

def by_region(a_str):
    return a_str.split('_')[0]

def by_proj_class(a_str):
    return a_str.split('_')[1]

def no_grouping(a_str):
    return a_str


class RegionProfile(object):

    def __init__(self, raw_profile, layer_labels, colors=None):
        self._raw = raw_profile
        self._raw_sources, self._raw_densities = zip(*self._raw)
        self._raw_sources = numpy.array(self._raw_sources)
        self._raw_densities = numpy.vstack(self._raw_densities)
        self._layer_labels = layer_labels
        self._cols = colors
        self._types_of_groups = dict([("Region", by_region),
                                      ("Projection class", by_proj_class),
                                      ("No groups", no_grouping)])
        self._set_up_groups()

    def _set_up_groups(self, order=["Projection class", "Region", "No groups"]):
        base_lbls, base_grp, base_idx = self._group(all_together)
        self._base_str = numpy.vstack([self._raw_densities[idx].sum(axis=0) for
                     idx in base_grp])
        self._labels = [base_lbls]
        self._str_mats = [self._base_str.reshape((1,) + self._base_str.shape)]

        L = self._raw_densities.shape[1]
        grp_funcs = [self._types_of_groups[_grp] for _grp in order]
        for fun in grp_funcs:
            new_lbls, new_grp, new_idx = self._group(fun)
            mat = numpy.zeros((len(base_grp), len(new_grp), L))
            for i, idx1 in enumerate(base_grp):
                for j, idx2 in enumerate(new_grp):
                    idxx = numpy.intersect1d(idx1, idx2)
                    mat[i, j] = self._raw_densities[idxx].sum(axis=0)
            self._labels.append(new_lbls)
            self._str_mats.append(mat)
            base_lbls, base_grp, base_idx = new_lbls, new_grp, new_idx

    def _group(self, grp_fun):
        grp_labels = numpy.array(list(map(grp_fun, self._raw_sources)))
        u_labels = numpy.unique(grp_labels).tolist()
        grouping = [numpy.nonzero(grp_labels == u)[0]
                    for u in u_labels]
        reverse_grouping = [u_labels.index(l) for l in grp_labels]
        return u_labels, grouping, reverse_grouping

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

    def get_plotly_links(self, offsets, cols, layer, threshold=0.0):
        link_dict = dict([("source", []), ("target", []), ("value", []), ("color", [])])
        for mat_index, mat in enumerate(self._str_mats[1:]):
            o1 = offsets[mat_index]
            o2 = offsets[mat_index + 1]
            for i in range(mat.shape[0]):
                for j in range(mat.shape[1]):
                    if mat[i, j, layer] > threshold:
                        link_dict['source'].append(o1 + i)
                        link_dict['target'].append(o2 + j)
                        link_dict['value'].append(mat[i, j, layer])
                        link_dict['color'].append(cols[o1 + i].replace("1.0", "0.6"))
        return link_dict

    def make_sankey(self, layer, y_domain=[0, 1], threshold=0.0):
        all_labels, offset, lbl_colors = self.get_plotly_labels()
        label_dict = dict([("pad", 15), ("thickness", 20), ("line", dict([("color", "black"), ("width", 0.5)])),
                           ("label", all_labels), ("color", lbl_colors)])
        link_dict = self.get_plotly_links(offset, lbl_colors, layer, threshold=threshold)
        return go.Sankey(
                         node=label_dict,
                         link=link_dict,
                         domain=go.sankey.Domain(y=y_domain)
        )
       
    def plot_layer(self, layer):
        S = self.make_sankey(layer)
        ttl_dict = dict([("text", "Long-range innervation"), ("font_size", 12)])
        fig = go.FigureWidget(data=[S], layout=go.Layout(title=ttl_dict))
        # fig.show()
        return fig



