# -*- coding: utf-8 -*-
'''
Function 3 PASTA-ice

Classifies lin_cor orthophotos/orthomosaics into sea ice surface classes

Input: lin_cor Geotiffs as arguments

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import cv2
import glob
import tqdm
import sys
import os
import datetime as dt
import time
import src.roi_stats
from sklearn.ensemble import RandomForestClassifier as RFC
from joblib import dump, load
from skimage.measure import label
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from matplotlib.colors import to_rgb


#### Standard dict for all processing steps
classdict={'snow':[0,'orange','Snow/ice'],'water':[1,'red','Open water'],'brimelt':[2,'green','bright Pond'],'bromelt':[3,'darkred','biology Pond'],'bgray':[4,'darkblue','bare, wet \nand thin ice - blue'],'shadowpond':[5,'cyan','Shadow Pond'],'ggray':[6,'gray','bare, wet \nand thin ice - gray'],'darkmelt':[7,'darkgreen','dark Pond'],'shadowsnow':[8,'magenta','Shadow snow'],'submerged':[9,'black','SubmergedIce'],'ridge area':[10,'purple','Ridge area'],'nan':[-1,'white','nan'],'sedisnow':[11,'peru','Sediment Snow']}   #snow,open water,brightpond,broken pond,shadow pond,ice,darkpond,shadow snow, submerged ice scheme

##### Step 1: load Random forest training data

### Possibility 1: classifier data is available
try:
    if sys.argv[1]=='sediments':
        clf_linear_cor_all=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_sediments.joblib')
        clf_linear_cor_all_clean=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_clean_sediments.joblib')
    else:
        clf_linear_cor_all=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all.joblib')
        clf_linear_cor_all_clean=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_clean.joblib')

### Possibility 2: classifier data is not available
except:
    
    print('No appropriate training was found, two potential reasons are: 1. no data available, 2. available training data was saved on another system and cannot be read')
    
    print('Start to compile new training data, this process takes a while')
    
    
    ### Load raw training data
    
    if sys.argv[1]=='sediments':
        feature_array=np.load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_features_sediments.npy')
        label_array=np.load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_labels_sediments.npy')
    else:
        feature_array=np.load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_features.npy')
        label_array=np.load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_labels.npy')   
        
    ### clean data
    
    feature_mat = feature_array[np.all(np.isfinite(feature_array),axis=1),:]
    label_vec = label_array[np.all(np.isfinite(feature_array),axis=1)]
    
    
    ### compile RFC including all features
    clf = RFC(n_estimators=50,n_jobs=-1,oob_score=True,max_features='sqrt')
    clf.fit(feature_mat,label_vec)
    #print('normal:',clf.oob_score_)
    
    if sys.argv[1]=='sediments':
        dump(clf,'training_data/clf_50_rfc_linear_opt_corr_all_leg_all_sediments.joblib')
    else:
        dump(clf,'training_data/clf_50_rfc_linear_opt_corr_all_leg_all.joblib')
    del(clf)

    ### compile RFC without feature 8 which often causes infinite values
    clf = RFC(n_estimators=50,n_jobs=-1,oob_score=True,max_features='sqrt')
    clf.fit(feature_mat[:,:7],label_vec)
    #print('clean:',clf.oob_score_)
    if sys.argv[1]=='sediments':
        dump(clf,'training_data/clf_50_rfc_linear_opt_corr_all_leg_all_clean_sediments.joblib')
    else:
        dump(clf,'training_data/clf_50_rfc_linear_opt_corr_all_leg_all_clean.joblib')
    del(clf)
    
    ### load classifiers again
    if sys.argv[1]=='sediments':
        clf_linear_cor_all=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_sediments.joblib')
        clf_linear_cor_all_clean=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_clean_sediments.joblib')
    else:
        clf_linear_cor_all=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all.joblib')
        clf_linear_cor_all_clean=load('training_data/clf_50_rfc_linear_opt_corr_all_leg_all_clean.joblib')
    print('Welcome back, classifiers are ready')
    
    
#### Loop over all files to be processed
if sys.argv[1]=='sediments':
    filelist=sys.argv[2:]
else:
    filelist=sys.argv[1:]

for ffile in filelist:
    
    ### Step 2: Load raster data

    print('load raster data')
    
    with rasterio.open(ffile, 'r') as src1:
        
        src_crs=src1.crs # read coordinate system
        
        ### quickndirty check if coordinate system is in UTM
        if int(src1.crs.data['init'].split(':')[1])<10000 and int(src1.crs.data['init'].split(':')[1]) != 3413:
            print('file: '+ffile+' is not saved in projected CRS, use other data')
            sys.exit()
            
        rgb_raw = (np.stack((src1.read(b) for b in (1,2,3,4)))) # read Red,Green,Blue,Alpha channel

    rgb_raw=np.swapaxes(rgb_raw,0,2) # swap axes back into regular format [vertical,horizontal,band]
    rgb_raw=np.swapaxes(rgb_raw,0,1)

    mask=rgb_raw[:,:,3]<123 # mask from alpha channel
    
    rgb=np.float32(rgb_raw[:,:,:3]) # change dtype to floating point

    ### Step 3: filter data
    print()
    print('start filtering')
    start=time.time()
    opt_rad = cv2.bilateralFilter(rgb,5,9,7) # reduce noise
    print('done in:'+str(time.time()-start)+' seconds')
    

    ### Step 4: calculate band ratios/features
    print()
    print('calculate features')
    start=time.time()
    stats_opt_rad = roi_stats.roi_stats(opt_rad,None)
    features_opt_rad_all = stats_opt_rad.ratios()#[:,:,:-1]

    features_opt_rad_all[np.isfinite(features_opt_rad_all)==False] = 99999
    features_opt_rad_all[np.where(mask)[0],np.where(mask)[1],:]= 99999
    print('done in:'+str(time.time()-start)+' seconds')
    
    
    ### Step 5: predict class labels for every single pixel
    print()
    print('Start prediction')
    start=time.time()

    predict_labels_opt_rad_all=np.int8(np.ones(mask.shape))*-1

    predict_labels_opt_rad_all[mask==0] = clf_linear_cor_all.predict(features_opt_rad_all[np.where(mask==0)[0],np.where(mask==0)[1],:])

    predict_labels_opt_rad_all[np.any(features_opt_rad_all.reshape(opt_rad.shape[0]*opt_rad.shape[1],features_opt_rad_all.shape[2])==99999,axis=1).reshape(opt_rad.shape[0],opt_rad.shape[1])]=-1

    bool_mat = predict_labels_opt_rad_all==-1
    bool_mat[mask]=False


    if np.sum(bool_mat)>0:
        predict_labels_opt_rad_all[bool_mat]=clf_linear_cor_all_clean.predict(features_opt_rad_all[np.where(bool_mat)[0],np.where(bool_mat)[1],:-1])
        
    print('done in:'+str(time.time()-start)+' seconds')
    
    ### Step 6: Get prediction probability
    print()
    print('Process prediction probability')
    start=time.time()

    probability_opt_rad_all=np.float32(np.zeros(mask.shape))
       
    probability_opt_rad_all[mask==0] = np.max(clf_linear_cor_all.predict_proba(features_opt_rad_all[np.where(mask==0)[0],np.where(mask==0)[1],:]),axis=1)
    
    if np.sum(bool_mat)>0:
        probability_opt_rad_all[bool_mat] = np.max(clf_linear_cor_all_clean.predict_proba(features_opt_rad_all[np.where(bool_mat)[0],np.where(bool_mat)[1],:-1]),axis=1)

    # make sure only valid input pixels are used

    predict_labels_opt_rad_all[mask]=-1
    print('done in:'+str(time.time()-start)+' seconds')
    
    
    ### Step 7: Save data
    
    print('write data')
    
    dst_crs = src_crs
    with rasterio.open(ffile,'r') as src:

        meta = src.meta.copy()
        meta.update(count = 3)

        if sys.argv[1]=='sediments':
            f_out=ffile.rsplit('.',1)[0]+'_classified_sediments.tif'
        else:
            f_out=ffile.rsplit('.',1)[0]+'_classified.tif'
        
        
        ### Classification raster 
        
        with rasterio.open(f_out, 'w', **meta) as dst:
    
            for id, layer in enumerate([np.uint8(predict_labels_opt_rad_all), np.uint8(probability_opt_rad_all*255), np.uint8(~mask*255)], start=1):
                
                dst.write_band(id,layer)

        if sys.argv[1]=='sediments':
            f_out=ffile.rsplit('.',1)[0]+'_RGB_sediments.tif'
        else:
            f_out=ffile.rsplit('.',1)[0]+'_RGB.tif'
        
        ### RGB raster in class label colors
        meta.update(count = 4)
        with rasterio.open(f_out, 'w', **meta) as dst:
            rgb=np.zeros((predict_labels_opt_rad_all.shape[0],predict_labels_opt_rad_all.shape[1],3),dtype=np.uint8)
            for clab in tqdm.tqdm(classdict.keys()): 
                n_class=classdict[clab][0] 
                c=classdict[clab][1] 
                rgb[np.where(predict_labels_opt_rad_all==n_class)[0],np.where(predict_labels_opt_rad_all==n_class)[1],:]=np.array(to_rgb(c))*255
            
            
            for id, layer in enumerate([rgb[:,:,0],rgb[:,:,1],rgb[:,:,2],src.read(4)], start=1):
                dst.write_band(id,layer)

