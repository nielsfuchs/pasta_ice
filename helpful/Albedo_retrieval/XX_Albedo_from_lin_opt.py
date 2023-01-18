# -*- coding: utf-8 -*-
'''
Function to retrieve pixelwise broadband albedo estimate from lin_opt data

Input: lin_opt data and sieved 100 Shape file (output of 04_sieve_and_combine_P3.py)

Note: if data range utilization is low in lin_opt JPGs, consider to scale them

Applies Empirical Line calibration between open water and snow/white ice surfaces

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import glob
import tqdm
import sys
import os
import datetime as dt
import geopandas as gp
from rasterio import mask
import rasterio


filelist=[('*LinOpt_.tif', '*sieved_100.shp', 'sun', 200, 1./1000., 6.3, 6)] # [(filepath, sky condition (sun or cloud), ISO, Exposure, Aperture, Month)
# filepath, sky condition, ISO, Exposure, Aperture

ref_albedo={6:np.array([[0.835,0.835,0.835],[0.07,0.07,0.07]]),7:np.array([[0.75,0.75,0.75],[0.07,0.07,0.07]])} # reference values for spectral albedo in 6:June (snow), 7:July (white ice -> SSL)

popt_mat=np.load('../Calibration_Files/Calib_cooefizient_14mm_diff_settings.npy')
spec_params=np.load('spec2broad_params.npy',allow_pickle=True).tolist()


def f(x,k1,k2,k3):
    # x1 ISO, x2 Exp
    return 1./(k1*x[0]+k2*x[1]+k3*x[0]*x[1])#
    
def spec2broad(x,a,b,c):
    return a*x[0]+b*x[1]+c*x[2] 

def aperture_cor(Aperture):
    ref_aperture=8.0
    return (4.*Aperture/np.pi)/(4.*ref_aperture/np.pi)
    
def bit8to16(img):
    return ((img+1)*256.)-1.
    


for (lin_opt_file, sieved_100_shp, sky, ISO, Exposure, Aperture, month) in filelist:
    
    month=int(month)
    
    with rasterio.open(lin_opt_file,'r') as src1:
        meta = src1.meta.copy()
        lin_opt = (np.stack((src1.read(b) for b in (1,2,3,4)))) # read Red,Green,Blue,Alpha channel

    lin_opt=np.moveaxis(lin_opt,0,2) # swap axes back into regular format [vertical,horizontal,band]
    
    GSD = np.abs(src1.transform[4])
    
    bool_mask = lin_opt[:,:,3]>123.
    lin_opt=lin_opt[:,:,:3]

    # calculate radiance

    rad=np.zeros(lin_opt.shape,dtype=np.float32)

    for b in range(3):
        rad[:,:,b]=np.float32(bit8to16(lin_opt[:,:,b]))*f([ISO,Exposure],popt_mat[b,0],popt_mat[b,1],popt_mat[b,2])\
        *aperture_cor(Aperture)  # (ISO,exposure)

    meta.update(dtype='float32')

    with rasterio.open(lin_opt_file.rsplit('.',1)[0]+'_radiance.tif','w+',**meta) as dst:
        for b in range(3):
            dst.write(rad[:,:,b],b+1)
        dst.write(np.float32(bool_mask),4)

    radiance = rad
    
    # calculate snow ref        
        
    gp_class = gp.read_file(sieved_100_shp)
            
    with rasterio.open(lin_opt_file.rsplit('.',1)[0]+'_radiance.tif','r') as src1:
        meta = src1.meta.copy()
        nodata=src1.meta['nodata']
        masked, mask_transform = mask.mask(dataset=src1, shapes=gp_class.loc[gp_class['raster_val']==0,'geometry'] , crop=False, all_touched=False ,nodata=nodata)
        GSD = np.abs(src1.transform[4])
    snow_rad=masked[:3,:,:]
    snow_rad=np.moveaxis(snow_rad,0,2)
    sn_rad=np.zeros(snow_rad.shape,dtype=np.float32)
    snow_rad[masked[3,:,:]<1.]=np.nan
    
    snow_rad=np.float32(snow_rad)
    sn_rad[:,:,:]=np.nanmean(np.nanmean(snow_rad,axis=0),axis=0)
    meta.update(dtype='float32')
    
    with rasterio.open(lin_opt_file.rsplit('.',1)[0]+'_snow_ref.tif','w+',**meta) as dst:
        for b in range(3):
            dst.write(sn_rad[:,:,b],b+1)
        dst.write(np.float32(bool_mask),4)
    
    # open water reference
    
    gp_class = gp.read_file(lin_opt_file.rsplit('LinOpt',1)[0]+'LinCor_UTM31N_5dm_classified_sediments_sieved_100.shp')
            
    with rasterio.open(lin_opt_file.rsplit('.',1)[0]+'_radiance.tif','r') as src1:
        meta = src1.meta.copy()
        nodata=src1.meta['nodata']
        masked, mask_transform = mask.mask(dataset=src1, shapes=gp_class.loc[gp_class['raster_val']==1,'geometry'] , crop=False, all_touched=False ,nodata=nodata)
    ow_rad=masked[:3,:,:]
    ow_rad=np.moveaxis(ow_rad,0,2)
    ow=np.zeros(ow_rad.shape,dtype=np.float32)
    ow_rad[masked[3,:,:]<1.]=np.nan
    ow_rad=np.float32(ow_rad)
    ow[:,:,:]=np.nanmean(np.nanmean(ow_rad,axis=0),axis=0)
    
    meta.update(dtype='float32')

    with rasterio.open(lin_opt_file.rsplit('.',1)[0]+'_ow_ref.tif','w+',**meta) as dst:
        for b in range(3):
            dst.write(ow[:,:,b],b+1)
        dst.write(np.float32(bool_mask),4)
    ow_rad=ow
    
    # empirical line calibration
    
    irrad = (sn_rad-ow_rad)/(ref_albedo[month][0]-ref_albedo[month][1])
    at = (ref_albedo[month][0]*ow_rad-ref_albedo[month][1]*sn_rad)/(ref_albedo[month][0]-ref_albedo[month][1])
    
    spec_a_default = (radiance-at)/irrad
    
    broad_a_default = spec2broad(np.moveaxis(spec_a_default,2,0),*spec_params[sky])

    meta.update(count=5)
    with rasterio.open(lin_opt_file.rsplit('.',1)[0]+'_albedo.tif','w+',**meta) as dst:
        for b in range(3):
            dst.write(np.float32(spec_a_default[:,:,b]),b+1)
        dst.write(np.float32(broad_a_default),4)
        dst.write(np.float32(bool_mask),5)

    