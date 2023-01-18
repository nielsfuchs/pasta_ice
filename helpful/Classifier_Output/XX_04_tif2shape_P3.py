# -*- coding: utf-8 -*-
'''
Function 04 of PASTA ice but without sieving. Necessary for geometrical analysis of all initially classified pond objects, independent of their size. 

Outputs only pond objects

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import glob
import tqdm
import sys
import os
import time
import rasterio
from rasterio import features
import geopandas as gp

### configuration part

sieve_size=100  # minimum size of object


### standard conversion dict subclass2mainclass
all2piw = {0:0,1:1,2:2,3:2,4:0,5:2,6:0,7:2,8:0,9:2,10:0,11:0}

### Loop over all input files:

for ffile in sys.argv[1:]:

    with rasterio.open(ffile,'r') as src1:

        ### Step 1: read data

        labels_all = src1.read(1)
        meta = src1.meta.copy()
    

        print('vectorize raster')
        results = (
                    {'properties': {'raster_val': v}, 'geometry': s}
                    for i, (s, v) 
                    in tqdm.tqdm(enumerate(
                        features.shapes(labels_all, mask=src1.read(3)>123, transform=src1.transform))))
        geoms = list(results)
        gpd  = gp.GeoDataFrame.from_features(geoms)
        gpd.crs=src1.crs.data['init']
        
        gpd['main']=[all2piw[sc] for sc in gpd.raster_val]
        
        gpd = gpd[gpd['main']==2] # or gpd[np.logical_and(gpd['main']==2, gpd['raster_val']!=9)] if submerged ice should be excluded
        
        gpd.main=0 # added 2ß22-08-27 to make ponds main class 0
        
        gpd.reset_index(inplace=True)
        
        df_main_compact=gpd.dissolve(by='main',aggfunc='sum')

        # reset index

        df_main_compact.reset_index(level=0, inplace=True) 

        # split multipolygons into single ones

        df_main=df_main_compact.explode()

        # remove all unnecessary columns

        df_main=df_main[['main','geometry']]

        # reset index after multipolygon split

        df_main=df_main.reset_index()

        # remove old index column

        df_main=df_main[['main','geometry']]

        # store polygon areas into single column

        df_main['area']=df_main.geometry.area
        
        print('done, writing file')
        df_main.to_file(ffile.rsplit('.',1)[0]+'_ponds.shp')

print('done')

            