# -*- coding: utf-8 -*-
'''
Exemplary function used to add new class (sediment snow) and further Bio Pond training data to PASTA-ice

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import sys
sys.path.insert(0,'../')
import numpy as np
import cv2
import glob
from PIL import Image
import tqdm
import os
import src.roi_stats
import time
from sklearn.ensemble import RandomForestClassifier as RFC
from joblib import dump, load

prev_feature_array=np.load('../../training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_features.npy')
prev_label_array=np.load('../../training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_labels.npy')

# example pictures

sed1_path='MOSAiC_Add_on_RFC/sedimentsnow.png'
sed2_path='MOSAiC_Add_on_RFC/sedimentsnow2.png'
biopond1_path='MOSAiC_Add_on_RFC/biopond.png'
biopond2_path='MOSAiC_Add_on_RFC/biopond1.png'


classdict={'snow':[0,'orange','Snow/ice'],'water':[1,'red','Open water'],'brimelt':[2,'green','bright Pond'],\
'bromelt':[3,'darkred','biology Pond'],'bgray':[4,'darkblue','bare, wet \nand thin ice - blue'],\
'shadowpond':[5,'cyan','Shadow Pond'],'ggray':[6,'gray','bare, wet \nand thin ice - gray'],\
'darkmelt':[7,'darkgreen','dark Pond'],'shadowsnow':[8,'magenta','Shadow snow'],\
'submerged':[9,'black','SubmergedIce'],'ridge area':[10,'purple','Ridge area'],'nan':[-1,'white','nan'],'sedisnow':[11,'peru','Sediment Snow']}


for ffile,label in [(sed1_path,'sedisnow'),(sed2_path,'sedisnow'),(biopond1_path,'bromelt'),(biopond2_path,'bromelt')]:
    
    data=np.float32(Image.open(ffile))
    data_mask=data[:,:,3]==255
    
    data=cv2.bilateralFilter(data[:,:,:3],5,9,7) 
    
    stats_opt_rad = roi_stats.roi_stats(data,None)
    features_data = stats_opt_rad.ratios()#[:,:,:-1]
    
    data1d=features_data[data_mask]
    
    prev_feature_array=np.vstack((prev_feature_array,data1d))
    prev_label_array=np.hstack((prev_label_array,np.ones(data1d.shape[0])*classdict[label][0]))
    

feature_mat = prev_feature_array[np.all(np.isfinite(prev_feature_array),axis=1),:]
label_vec = prev_label_array[np.all(np.isfinite(prev_feature_array),axis=1)]

np.save('../../training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_features_sediments.npy',feature_mat)
np.save('../../training_data/clf_50_rfc_linear_opt_corr_all_leg_all_training_labels_sediments.npy',label_vec)

clf = RFC(n_estimators=50,n_jobs=-1,oob_score=True,max_features='sqrt')
clf.fit(feature_mat,label_vec)
print('normal:',clf.oob_score_)
dump(clf,'clf_50_rfc_linear_opt_corr_all_leg_all_mac_sediments.joblib')

clf = RFC(n_estimators=50,n_jobs=-1,oob_score=True,max_features='sqrt')
clf.fit(feature_mat[:,:7],label_vec)
print('clean:',clf.oob_score_)
dump(clf,'clf_50_rfc_linear_opt_corr_all_leg_all_mac_clean_sediments.joblib')

    