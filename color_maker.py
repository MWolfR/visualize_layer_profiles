from region_mapper import RegionMapper
import json


class ColorMaker(object):
    def __init__(self, cols, mapper):
        self.mapper = mapper
        self.cols = cols
       
    def __getitem__(self, a_str):
        if a_str in self.mapper.region_names:
            a_str = self.mapper.region2module(a_str)
        return self.cols.get(a_str, self.cols["_default"])
    
    def color_labels(self, lst_str):
        return [self[a_str] for a_str in lst_str]
    
    @classmethod
    def factory(cls):
        with open("default.json", "r") as fid:
            parcellation_recipe = json.load(fid)
            m = RegionMapper(parcellation_recipe["BrainParcellation"])
        return cls(parcellation_recipe["Colors"], m)
