# -*- coding: utf-8 -*-
'''
Function 4 PASTA-ice

Sieves classification results and converts to shapefile

Input: 03_Classify output .tif as arguments

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import glob
import tqdm
import sys
import os
import time
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio import features
from shapely.geometry import shape
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
    
        ### Step 2: sieve raster

        print('Sieve raster')

        labels_all_s = features.sieve(labels_all,sieve_size)
    
    
        ### Step 3: keep interconnected objects of the same mainclass, but small portions of subclasses by comparing sieved images of subclasses with sieved images of mainclasses
    
        labels_piw = np.copy(labels_all)
        labels_piw_all_s = np.copy(labels_all_s)

        for k,v in all2piw.items():
            labels_piw[labels_piw == k] = v
            labels_piw_all_s[labels_piw_all_s == k] = v
    
        labels_piw_s = features.sieve(labels_piw,sieve_size)
        labels_all_s[np.logical_and(labels_piw!=labels_piw_all_s,labels_piw==labels_piw_s)]=labels_all[np.logical_and(labels_piw!=labels_piw_all_s,labels_piw==labels_piw_s)]

        ### Step 4: write output
        
        print('done, writing file')
        with rasterio.open(ffile.rsplit('.',1)[0]+'_sieved_'+str(sieve_size)+'.tif','w', **meta) as dst:
            dst.write(labels_all_s, 1)
            for b in range(2,4):
                dst.write(src1.read(b),b)
            
        ### Step 5: Vectorize raster
    
        print('vectorize raster')
        results = (
                    {'properties': {'raster_val': v}, 'geometry': s}
                    for i, (s, v) 
                    in tqdm.tqdm(enumerate(
                        features.shapes(labels_all_s, mask=src1.read(3)>123, transform=src1.transform))))
        geoms = list(results)
        gpd  = gp.GeoDataFrame.from_features(geoms)
        gpd.crs=src1.crs.data['init']
        print('done, writing file')
        gpd.to_file(ffile.rsplit('.',1)[0]+'_sieved_'+str(sieve_size)+'.shp')

print('done')

            