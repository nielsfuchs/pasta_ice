# -*- coding: utf-8 -*-
'''
Function to convert .ppm only to lin_opt without opening GUI for brightness corrected data. Handy function.

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import glob
from PIL import Image
import tqdm
import sys
import os

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
        

for pic in tqdm.tqdm(sys.argv[1:]):
    
    folder=pic.rsplit('/',1)[0]
    
    linear_rad = np.float32(read_ppm_rgb(pic.rsplit('.',1)[0]+'.ppm','16bit'))
    
    linear_rad = (linear_rad+1.)/(256.)-1
            
    assure_path_exists(folder.rsplit('/',1)[0]+'/Lin_opt/')
                        
    Image.fromarray(np.uint8(linear_rad)).save(folder.rsplit('/',1)[0]+'/Lin_opt/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg', quality=100, subsampling=0)
    
    os.system('exiftool -quiet -TagsFromFile ' + pic.rsplit('.',1)[0] + str('.CR2') + ' "-all:all>all:all" ' + folder.rsplit('/',1)[0]+'/Lin_opt/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg')
    os.system('rm ' + folder.rsplit('/',1)[0]+'/Lin_opt/'+(pic.rsplit('/',1)[1]).rsplit('.',1)[0]+'.jpg' + '_original')
