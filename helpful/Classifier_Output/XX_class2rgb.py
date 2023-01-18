# -*- coding: utf-8 -*-
'''
Handy function to generate colorful surface class full-color tiff from classification output tif or shapefile

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import glob
from PIL import Image
import tqdm
import sys
import os
import time
#import h5py
import PIL.ImageColor as IC
import rasterio
from rasterio import features
from matplotlib.colors import to_rgb
import geopandas as gp




classdict={'snow':[0,'orange','Snow/ice'],'water':[1,'red','Open water'],'brimelt':[2,'green','bright Pond'],'bromelt':[3,'darkred','biology Pond'],'bgray':[4,'darkblue','bare, wet \nand thin ice - blue'],'shadowpond':[5,'cyan','Shadow Pond'],'ggray':[6,'gray','bare, wet \nand thin ice - gray'],'darkmelt':[7,'darkgreen','dark Pond'],'shadowsnow':[8,'magenta','Shadow snow'],'submerged':[9,'black','SubmergedIce'],'ridge area':[10,'purple','Ridge area'],'nan':[-1,'white','nan'],'sedisnow':[11,'peru','Sediment Snow']}   #snow,open water,brightpond,broken pond,shadow pond,ice,darkpond,shadow snow, submerged ice scheme
maindict={'snow':[1,'orange','Snow/ice'],'water':[2,'red','Open water'],'melt':[0,'green','bright Pond'],'submerged':[3,'cyan','SubmergedIce']}

for ffile in sys.argv[1:]:
    
    if ffile.rsplit('.',1)[1]=='tif':
        with rasterio.open(ffile,'r') as src:
            labels=src.read(1)
            meta = src.meta.copy()
            meta.update(count = 4)

            with rasterio.open(ffile.rsplit('.',1)[0]+'_RGB.tif', 'w', **meta) as dst:
                rgb=np.ones((labels.shape[0],labels.shape[1],3),dtype=np.uint8)*255
                for clab in tqdm.tqdm(classdict.keys()): 
                    n_class=classdict[clab][0] 
                    c=classdict[clab][1] 
                    rgb[np.where(labels==n_class)[0],np.where(labels==n_class)[1],:]=np.array(to_rgb(c))*255
                
                for id, layer in enumerate([rgb[:,:,0],rgb[:,:,1],rgb[:,:,2],src.read(4)], start=1):
                    dst.write_band(id,layer)
    
    
    elif ffile.rsplit('.',1)[1]=='shp':
        
        gpd=gp.read_file(ffile)
        
        print('Insert reference raster:')
        reference_rst = input()
        with rasterio.open(reference_rst,'r') as ref:
            meta=ref.meta.copy()
        meta.update(count=4)
        meta1=meta.copy()
        meta1.update(count=1)

        with rasterio.open(ffile.rsplit('.',1)[0]+'_RGB.tif','w+',**meta) as rst:
            
            with rasterio.open(ffile.rsplit('.',1)[0]+'_pond_bool.tif','w+',**meta1) as rst1:
                nan=255
                out_arr = np.ones((rst.read(1).shape[0],rst.read(1).shape[1]),dtype=np.uint8)*nan
            
                shapes = ((geom,values) for geom,values in zip(gpd.geometry,gpd.main))
        
                labels = features.rasterize(shapes=shapes, fill=nan, out=out_arr, transform=rst.transform)
                print(labels)
                if np.all(np.logical_or(labels<4,labels==nan)):
                    lab_dict=maindict
                else:
                    lab_dict=classdict
                
                
                rgb=np.ones((labels.shape[0],labels.shape[1],4),dtype=np.uint8)*255
                pond_bool=np.zeros((labels.shape[0],labels.shape[1]),dtype=np.uint8)
                pond_bool[np.isin(labels,[0,3])] = 255
                rst1.write_band(1,pond_bool)
            
                for clab in tqdm.tqdm(lab_dict.keys()): 
                    n_class=lab_dict[clab][0] 
                    c=lab_dict[clab][1] 
                    rgb[np.where(labels==n_class)[0],np.where(labels==n_class)[1],:3]=np.array(to_rgb(c))*255

                for id, layer in enumerate([rgb[:,:,0],rgb[:,:,1],rgb[:,:,2],rgb[:,:,3]], start=1):
                    rst.write_band(id,layer)
    
        