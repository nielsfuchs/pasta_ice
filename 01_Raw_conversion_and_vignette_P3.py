# -*- coding: utf-8 -*-
'''
Function 1 PASTA-ice

Convert .CR2 with linear conversion function to .ppm and correct for vignetting

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

# read/ write functions
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

def write_ppm(data,file,size):

    with open(file,'w') as outfile:
        outfile.write('P6\n')
        outfile.write(str(data.shape[1])+' '+str(data.shape[0])+'\n')
        #outfile.write('3908 2600\n')
        maxval = int(np.nanmax(data))
        #maxval = 2**16-1
        outfile.write(str(int(maxval))+'\n')
        if size=='8bit':
            data=np.uint8(data)
            data.astype('>u1').tofile(outfile)
        elif size == '16bit':
            data=np.uint16(data)
            data.astype('>u2').tofile(outfile)

# load calibration
linear_opt_vign_file = 'Calibration_files/Vignette_correction_image_linear_opt_512138_FLT6921_14mm_FLT1889_200601.npy'

linear_opt_vign = np.load(linear_opt_vign_file)

# load all files passed as arguments
for pic in tqdm.tqdm(sys.argv[1:]):
       
    if not os.path.isfile(pic.rsplit('.',1)[0]+'.ppm'):
        # convert to ppm with dcraw
        os.system('dcraw -t 0 -o 0 -k 1025 -S 15280 -r 1 1 1 1 -W -g 1 1 -6 -j -C 0.99950424 0.999489075 -n 100 ' + pic)
        while not os.path.isfile(pic.rsplit('.',1)[0]+'.ppm'):
            time.sleep(1)
        linear_opt_image = np.float32(read_ppm_rgb(pic.rsplit('.',1)[0]+'.ppm','16bit'))
        # vignette correction
        if 'vign_corr' not in locals():
            vign_corr=cv2.resize(linear_opt_vign,dsize=(linear_opt_image.shape[1],linear_opt_image.shape[0]),interpolation=cv2.INTER_LINEAR)
        
        # write
        write_ppm(np.clip(linear_opt_image*vign_corr,0,(2**16)-1),pic.rsplit('.',1)[0]+'.ppm','16bit')

  
