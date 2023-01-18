# -*- coding: utf-8 -*-
'''
Function to retrieve pond bathymetry from classified orthomosaic and GeoTiff DEM.

Was developed for MOSAiC floe, thus clips data to a floe shape. Can be removed.

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import glob
import tqdm
import sys
import os
import datetime as dt
import time
import rasterio
from shapely.geometry import shape, Polygon, LineString, LinearRing
import geopandas as gp
from rasterio import mask
import rasterstats


# input files

gpfile='*_sieved_100_main.shp'
demfile_ow='*.tif'

floe_file='*_Floe_contour.shp'

workdir=''

print('1. load data')

main_df = gp.read_file(gpfile)

floe_shape = gp.read_file(floe_file)

print('2. extract ponds')

pond_df = main_df[main_df['main']==0].clip((floe_shape.to_crs(main_df.crs)).convex_hull)
pond_df.reset_index(inplace=True)
pond_df.to_file(workdir+gpfile.rsplit('/',1)[1].rsplit('.',1)[0]+'_floe_ponds.shp')

ring_df=pond_df.copy()
ring_df.loc[ring_df['geometry'].exterior!=None, 'geometry'] = [LinearRing(geo.coords) for geo in ring_df.geometry.exterior if geo]

droplist=[]
for i,g in ring_df.iterrows():
    if not isinstance(g.geometry, LineString):
        droplist.append(i)
ring_df=ring_df.drop(droplist)
pond_df=pond_df.drop(droplist)

ring_df.reset_index(inplace=True)
pond_df.reset_index(inplace=True)

ring_df.to_file(workdir+gpfile.rsplit('/',1)[1].rsplit('.',1)[0]+'_floe_pond_rings.geojson', driver='GeoJSON')

print('3. retrieve pond water level')

stats_ring=np.array(rasterstats.zonal_stats(workdir+gpfile.rsplit('/',1)[1].rsplit('.',1)[0]+'_floe_pond_rings.geojson',demfile_ow,stats="mean"))

pond_df['waterlevel']=np.nan

for i,dummy in ring_df.iterrows():
    pond_df.loc[i,'waterlevel']=stats_ring[i]['mean']

pond_df.to_file(workdir+gpfile.rsplit('/',1)[1].rsplit('.',1)[0]+'_floe_ponds.shp')

print('4. read raster data')

with rasterio.open(demfile_ow,'r') as src:
    transform_src = src.transform
    meta=src.meta.copy()
    dem = src.read(1)
    nodata=src.nodata

pond_depth = np.float32(np.zeros(dem.shape))
pond_depth[:,:] = np.nan

print('5. burn raster')

out = np.zeros(dem.shape)
out[:,:] = np.nan

shapes = ((geom,values) for geom,values in tqdm.tqdm(zip(pond_df.geometry,pond_df.waterlevel)))
waterlevel = features.rasterize(shapes=shapes, fill=nodata, out=out, transform=transform_src)

print('6. calculate pond depth')

pond_depth[np.isfinite(waterlevel)]=(dem[np.isfinite(waterlevel)]-waterlevel[np.isfinite(waterlevel)])*1.335

pond_depth[~np.isfinite(dem)]=np.nan

print('7. output')

with rasterio.open(workdir+demfile_ow.rsplit('/',1)[1].rsplit('.',1)[0]+'_pondbathymetry.tif','w+',**meta) as dst:
    dst.write_band(1,pond_depth)


