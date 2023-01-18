#!/scratch/users/nifuchs/bin/anaconda2/ipython
# -*- coding: utf-8 -*-
import numpy as np
import cv2
import glob
from PIL import Image
import tqdm
from scipy.interpolate import interp1d
import sys
import os
import datetime as dt


class roi_stats:
    def __init__(self,rgb,surf_bool):
        self.rgb = rgb
        #self.hist_dict = hist_dict
        self.surf_bool=surf_bool
    
        
    def mean(self):
                                        
        return np.mean(self.rgb,axis=1)
    
    def ratios(self):
        
        R = np.copy(np.float64(self.rgb[:,:,0]))
        G = np.copy(np.float64(self.rgb[:,:,1]))
        B = np.copy(np.float64(self.rgb[:,:,2]))

        return np.float32(np.moveaxis(np.array([\
            R,\
                G,\
                    B,\
                        (G-R)/(G+R),\
                            (B-R)/(B+R),\
                                (B-G)/(B+G),\
                                    (B+G-2.*R),\
                                        (G-R)/(2.*B-G-R)\
                                            ]),0,-1))
    
        
    def textural(self,a,size):
        
        arr = np.copy(a)
        
        if size%2 != 1:
            raise NameError('choose odd window size!')
        
        if arr.ndim > 2:
            raise NameError('ndim must be exactly == 2!')
        
        field = np.zeros((arr.shape[0],arr.shape[1],size**2))*np.nan

        for y in range(size):
            dy = y-np.floor(size/2.)
            for x in range(size):
                dx = x-np.floor(size/2.)
                field[int(np.floor(size/2.)):int(arr.shape[0]-np.floor(size/2.)),int(np.floor(size/2.)):int(arr.shape[1]-np.floor(size/2.)),y*size+x] = \
                    arr[int(np.floor(size/2.)+dy):int(arr.shape[0]-np.floor(size/2.)+dy),int(np.floor(size/2.)+dx):int(arr.shape[1]-np.floor(size/2.)+dx)]
                    
        return field
        
    def calc_stats(self,window_size_vec,features_vec):
        
        rat = self.ratios()
        
        textures = np.zeros((rat.shape[0],rat.shape[1],len(features_vec),len(window_size_vec)))
        
        for feature in features_vec:
        
            for l,ws in enumerate(window_size_vec):
            
                textures[:,:,feature,l] = np.nanstd(self.textural(np.float16(rat[:,:,feature]),ws),axis=2)

        return textures
