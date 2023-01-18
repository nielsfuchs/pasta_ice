# -*- coding: utf-8 -*-
'''
Function 2 PASTA-ice

Converts .ppm to lin_opt and lin_cor data. Perfect linear conversion and brightness corrected with empirical line method

If not done yet, opens GUI to select reference surfaces (open water) and (white snow)

Input: Directory containing all .CR2 files as argument

Note: The output must be converted to GeoTiff for further processing, either by rectification or full orthomosaic compilation

Niels Fuchs (2023) https://github.com/nielsfuchs
'''

import numpy as np
import glob
from PIL import Image
import tqdm
import sys
import os
import datetime as dt
from skimage.transform import resize
import PIL.ImageEnhance as ImEnh
import src.window
import time


## if image brightness in the reference area selection window is not sufficient, change here: 

enhance_factor = 1.0

# reference reflectance used for "empirical line" brightness correction

ref_water = 0.1
ref_snow = 0.9

# helpful functions

def read_ppm_rgb(file,size):
    infile = open(file,'rb')
    
    type = infile.readline().decode('UTF-8').rstrip()
    dim = infile.readline().decode('UTF-8').rstrip().split(' ')
    width = int(dim[0])
    height = int(dim[1])
    maxval = int(infile.readline().decode('UTF-8').rstrip().split('.')[0])
    if size=='16bit':
        image = np.fromfile(infile, dtype='>u2').reshape((height, width,3))
    elif size=='8bit':
        image = np.fromfile(infile, dtype='>u1').reshape((height, width,3))
    return image

def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)

# dictionnary with all classes, ridge area was included in training and test data but is not used in the classification

classdict={'snow':[0,'orange','Snow/ice'],'water':[1,'red','Open water'],'brimelt':[2,'green','bright Pond'],'bromelt':[3,'darkred','biology Pond'],'bgray':[4,'darkblue',u'bare, wet \nand thin ice - blue'],'shadowpond':[5,'cyan','Shadow Pond'],'ggray':[6,'gray',u'bare, wet \nand thin ice - gray'],'darkmelt':[7,'darkgreen','dark Pond'],'shadowsnow':[8,'magenta','Shadow snow'],'submerged':[9,'black','SubmergedIce'],u'ridge area':[10,'purple','Ridge area']}   #ridge area is not used

# some parameters

folder=sys.argv[1]

filelist=sorted(glob.glob(folder+'/*.CR2'))

snow_water_dict = np.zeros((2,3)) #[snow/water],color band,[linear_corr,opt_rad]
segment_dict={}
n_class_flag = np.zeros(2)

# if no image brightness references were selected yet, open gui

if not os.path.isfile(folder+'/Snow_water_mean_trainingdata.npy'):

    for l,pic in tqdm.tqdm(enumerate(filelist[int(len(filelist)/2)::5])):

        os.system('dcraw -t 0 -o 0 -T -k 1025 -S 15280 -r 2.036133 1.000000 1.471680 1.000000 -W -g 2.222 0 -j -C 0.99950424 0.999489075 -n 100 ' + pic)
        while not os.path.isfile(pic.rsplit('.',1)[0]+'.tiff'):
            time.sleep(1)
        im=Image.open(pic.rsplit('.',1)[0]+'.tiff')
        
        thumb = np.array(ImEnh.Brightness(im).enhance(enhance_factor))

        segment_dict={}
        gui=window.TrainingWindow(thumb,classdict,'dummy',segment_dict)
        segment_dict=gui.segment_dict
        os.system('rm ' + pic.rsplit('.',1)[0]+'.tiff')
        
        for n_class in [0,1]:
            if len(segment_dict[n_class])>0 and n_class_flag[n_class] == 0:
                
                linear_rad = np.float32(read_ppm_rgb(pic.rsplit('.',1)[0]+'.ppm','16bit'))
                print(thumb.shape, linear_rad.shape, segment_dict[n_class])
                for b in range(3):
                    snow_water_dict[n_class,b]=np.nanmean(linear_rad[:,:,b][segment_dict[n_class]])
                    n_class_flag[n_class] = 1
        if np.sum(n_class_flag) == 2:
            np.save(folder+'/Snow_water_mean_trainingdata.npy',snow_water_dict)
            break
else:
    snow_water_dict=np.load(folder+'/Snow_water_mean_trainingdata.npy')

# convert ppm to lin_opt (linear optimized, e.g. for albedo) and lin_cor (brightness corrected, for classification) data 

for pic in tqdm.tqdm(filelist):
            
    linear_rad = np.float32(read_ppm_rgb(pic.rsplit('.',1)[0]+'.ppm','16bit'))
    linear_rad_corr=linear_rad.copy()
    
    for b in range(3):

        drange = float(snow_water_dict[0,b]-snow_water_dict[1,b])/float(ref_snow-ref_water)
        linear_rad_corr[:,:,b] = ((linear_rad[:,:,b]-(snow_water_dict[1,b]-ref_water*drange))/drange)*(2**16-1)
            
    # convert to 8bit
    linear_rad_corr = (linear_rad_corr+1.)/(256.)-1
    
    #linear_rad = (linear_rad-Min)/(Max-Min)*255
    linear_rad = (linear_rad+1.)/(256.)-1
            
    # avoid infinite features:
            
    for b in range(3):
                
        linear_rad_corr[:,:,b] = np.clip(linear_rad_corr[:,:,b],3-b,255-b)  # avoid all 0 or all 255 
            
    assure_path_exists(folder.rsplit('/',1)[0]+'/Lin_corr/')
    assure_path_exists(folder.rsplit('/',1)[0]+'/Lin_opt/')
                        
    Image.fromarray(np.uint8(linear_rad_corr)).save(folder.rsplit('/',1)[0]+'/Lin_corr/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg', quality=100, subsampling=0)
    Image.fromarray(np.uint8(linear_rad)).save(folder.rsplit('/',1)[0]+'/Lin_opt/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg', quality=100, subsampling=0)

    os.system('exiftool -quiet -TagsFromFile ' + pic + ' "-all:all>all:all" ' + folder.rsplit('/',1)[0]+'/Lin_corr/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg')
    os.system('rm ' + folder.rsplit('/',1)[0]+'/Lin_corr/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg' + '_original')

    os.system('exiftool -quiet -TagsFromFile ' + pic + ' "-all:all>all:all" ' + folder.rsplit('/',1)[0]+'/Lin_opt/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg')
    os.system('rm ' + folder.rsplit('/',1)[0]+'/Lin_opt/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg' + '_original')
