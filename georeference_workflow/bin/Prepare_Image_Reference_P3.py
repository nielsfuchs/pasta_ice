# -*- coding: utf-8 -*-
import numpy as np
import glob
import tqdm
import sys
import os
import datetime as dt
from Prepare_Image_Reference_functions_P3 import *
from geographiclib.geodesic import Geodesic
import logging
logging.basicConfig(level=logging.ERROR)    # useful to avoid numerous Exifread Warnings

#### Python script for MOSAiC HELI RGB data preparation for Metashape use

print('********************************************************************')
print('Python script for MOSAiC HELI RGB data preparation for Metashape use')
print('********************************************************************')
print('***Written by: Niels Fuchs 2019, Questions? -> niels.fuchs@awi.de***')
print('********************************************************************')
print('******Do not forget to adjust the configuration part in file: ******')
print('********************** Prepare_Image_Data.py ***********************')
print('********************************************************************')


### Configuration part

camera = 'canon' # 'canon' or 'gopro'

vel_ice=0.300 #m/s
azi=217

### Collect all raw data files

if camera == 'canon':
    filelist = sorted(glob.glob('*.CR2'))
elif camera == 'gopro':
    filelist = sorted(glob.glob('*.JPG'))
if filelist == '':
    raise ValueError('No image data found, run script in the image folder or check file extensions: CANON=.CR2, Gopro=.JPG')

### GPS/INS Data

if os.path.isfile('Applanix.txt'):
    imu_file = 'Applanix.txt'
    ins_date, ins_data = read_imu(imu_file)
elif os.path.isfile('RT3000.txt'):
    imu_file = 'RT3000.txt'
    ins_data, ins_data = read_imu_RT3000(imu_file)
else:
    raise ValueError('No INS/GPS file found, check if \"Applanix.txt\" or \"RT3000.txt\" exists in the raw image folder')

### Initialize variables

filelist_new_names=[]
skipped_images=[]
skipped_dates=[]
success_counter=0

### Conversion

if camera == 'canon':
    
    print('Collect filenames')

    for image_file in tqdm.tqdm(filelist):
    
        new_filename = image_file.rsplit('.',1)[0]+'.jpg'

        filelist_new_names.append(new_filename)
        
elif camera == 'gopro':
    
    print('Collect filenames')
    
    for image_file in tqdm.tqdm(filelist):
        
        filelist_new_names.append(image_file)
    
### Determine timestamp, get attitude & position data and write reference file

if os.path.isfile('Reference_data.txt'):
    print('File Reference_data.txt already exists!, you want to replace it? (y,n)')
    del_answer = input()
    if del_answer == 'y':
        os.remove('Reference_data.txt')
    else:
        raise ValueError('Cannot overwrite old reference data. Do some housekeeping in the folder and run the script again')
outfile = open('Reference_data.txt', 'w')

outfile.write('# filename; lat; lon; alt; yawl; pitch; roll; x; y; z'+'\n')

print('Write reference file: Reference_data.txt')

for image_file in tqdm.tqdm(sorted(filelist_new_names)):

    if camera=='canon':
        exifdata = EXIF(image_file.rsplit('.',1)[0]+'.CR2') # read EXIF data from original file, forgot to install exiftool on the processing laptop to copy exif data properly. Dcraw does some strang stuff
    elif camera=='gopro':
        exifdata = EXIF(image_file)
    
    
    '''
    not in use for MOSAiC Data
    
    if exifdata.garminflag:
        utc_time = exifdata.gpstime # if possible, always use GPS time
    else:
        if camera == 'canon':
            utc_time =  dt.datetime.strptime(image_file[:15],'%Y%m%d_%H%M%S')    # use time from filename
        elif camera == 'gopro':
            utc_time = exifdata.cameratime  # use camera time
    '''
    utc_time = exifdata.cameratime
    
    if camera == 'canon':
        try:
            if exifdata.subsectime>=0.5:
                utc_time = utc_time + dt.timedelta(seconds=1) # try to add sub sec time. Applanix ASCII data is usually given in 1 second resolution. To avoid comprehensive processing and due to anyways low synchronisation resolution, round subsectime to 0 or 1. 
        except:
            utc_time = utc_time + dt.timedelta(seconds=1) # add 1 second, due to general incorrect time management
    
    
    lat, lon, alt, yawl, pitch, roll, x, y, z, flag = get_ins_data(utc_time,ins_date,ins_data)  # flag: True, if position data was available
    
    if flag:
        
        # correct icedrift if necessary
        if vel_ice>0:
            if 'utc_start' not in locals():
                utc_start=utc_time
            geod = Geodesic.WGS84
            dir = geod.Direct(lat,lon,azi,-vel_ice*(utc_time-utc_start).seconds)
            y = dir['lat2']
            x = dir['lon2']
            
        outfile.write('%s; %.6f; %.6f; %.3f; %.3f; %.3f; %.3f; %.6f; %.6f; %.3f%s' % (image_file, lat, lon, alt, yawl, pitch, roll, x, y, z,  '\n'))
        success_counter+=1
    else:
        skipped_images.append(image_file)
        skipped_dates.append(utc_time)
outfile.close()

print('Images skipped due to missing IMU data: ')
print('#Filename                     #Image time')
if len(skipped_images) == 0:
    print('None')
else:
    for i in range(len(skipped_images)):
        print(skipped_images[i], dt.datetime.strftime(skipped_dates[i],'%Y-%m-%d %H:%M:%S'))
print('***************************************************************')
print('Done! Files processed: ' + str(len(filelist_new_names)) + ', successfully: ' + str(success_counter) + ', skipped: ' + str(len(skipped_images)) + ', lost: ' + str(len(filelist)-success_counter-len(skipped_images)))


