# -*- coding: utf-8 -*-
import numpy as np
import glob
import tqdm
import sys
import os
import datetime as dt
import exifread

def read_imu_RT3000(imu_filename):
    
    ''' 
    Reads postprocessed OxTS RT3000 IMU/GPS .txt file and returns two arrays:
    - datetime with microsecond precision
    - data array with: 0:Lat (deg), 1:Lon (deg), 2: Altitude (m), 3: Heading (deg), 4: Pitch (deg), 5: Roll (deg)
    
    (OBS! export orthometric (EM96) height in RT Postprocess, not ellipsoid)
    '''
    #data array with: 0:Lat (deg), 1:Lon (deg), 2: Altitude (m), 3: Heading (deg), 4: Pitch (deg), 5: Roll (deg)
    
    date_conv = lambda y: dt.datetime.strptime(y,'%d.%m.%Y') # date converter function
    time_conv = lambda m: dt.datetime.strptime(m,'%H:%M:%S.%f')  # time converter function
    
    data_string = open(imu_filename,'r').read().replace(',','.')
    
    temp_long = np.genfromtxt(StringIO.StringIO(data_string),skip_header=1,delimiter=';',converters={0:date_conv,1:time_conv},usecols=(0,1,2,3,4,6,7,8)) #   skip header and last row, temp is numpy object array
    
    temp = temp_long[np.where(np.array([temp_long[i][1].microsecond for i in range(len(temp_long))]) == 0.)]
    
    date = np.array([temp[i][0]+dt.timedelta(hours=temp[i][1].hour,minutes=temp[i][1].minute,seconds=temp[i][1].second,microseconds=temp[i][1].microsecond) for i in range(len(temp))])
    
    return date, np.array([temp[i].tolist()[2:] for i in range(len(temp))],dtype=np.float)

def read_imu(imu_filename):
    
    ''' 
    Reads postprocessed Applanix IMU/GPS .txt file and returns two arrays:
    - datetime with microsecond precision
    - data array with: 0:Lat (deg), 1:Lon (deg), 2: Altitude (m), 3: Heading (deg), 4: Pitch (deg), 5: Roll (deg)
    
    (OBS! export orthometric (EM96) height in POSPAC, not ellipsoid)
    '''
    date = None
    with open(imu_filename,'r') as ffile:
        while date==None:
            line = ffile.readline()
            if line[3:18] == 'Date of Mission':
                date = dt.datetime.strptime(line[20:30],'%Y-%m-%d')
        
    temp_long = np.genfromtxt(imu_filename,skip_header=29,delimiter=(13,14,12,12,9,12,13,9,9,9,9,9,9,9,9,9,9,9,9,9)\
    ,usecols=(0,5,6,7,10,9,8)) #   skip header 28 lines + first measurement line (some problems appeared sometimes due to it), temp is numpy object array
    
    start_of_week = date-dt.timedelta(days=(date.isoweekday()%7))
    
    temp = temp_long[np.where(np.array([str(temp_long[i][0]).split('.')[1][0] for i in range(len(temp_long))]) == '0')] # dirty as hell
        
    time_array = np.array([start_of_week + dt.timedelta(seconds=np.floor(temp[i][0])) for i in range(len(temp))]) # doesn't make sense to continue with microsecond precision for CANON cams
        
    return time_array, np.array([temp[i].tolist()[1:] for i in range(len(temp))],dtype=np.float)
    
def get_ins_data(utc_time,ins_date,ins_data):
    if np.sum(ins_date==utc_time) == 0:
        lat = 0
        lon = 0
        alt = 0
        yawl = 0
        pitch = 0
        roll = 0
        x= 0
        y = 0
        z = 0
        flag=False
    else:
        lat = float(ins_data[ins_date==utc_time][0][0])
        lon = float(ins_data[ins_date==utc_time][0][1])
        alt = float(ins_data[ins_date==utc_time][0][2])
        yawl = float(ins_data[ins_date==utc_time][0][3])
        pitch = float(ins_data[ins_date==utc_time][0][4])
        roll = float(ins_data[ins_date==utc_time][0][5])
        x = float(0)   # free for floe coordinates
        y = float(0)   # free for floe coordinates
        z = float(ins_data[ins_date==utc_time][0][2])
        flag = True
    return lat, lon, alt, yawl, pitch, roll, x, y, z, flag
    
class EXIF():
    
    def __init__(self,filename):
        
        work_dict=self.read_EXIF(filename)

        self.cameratime = dt.datetime.strptime(work_dict['Image DateTime'].values,'%Y:%m:%d %H:%M:%S')
        try:
            self.subsectime = float(work_dict['EXIF SubSecTime'].values)/100.
        except:
            pass
        #self.length = work_dict['Image ImageLength'].values[0]
        #self.width = work_dict['Image ImageWidth'].values[0]
        #self.exposure = self.ExifRatio2float(work_dict['EXIF ExposureTime'].values[0])
        #self.aperture = float(work_dict['EXIF FNumber'].values[0].num)
        #self.iso = float(work_dict['EXIF ISOSpeedRatings'].values[0])
        #self.WB = work_dict['MakerNote WhiteBalance'].printable
        #self.orientation = work_dict['Image Orientation'].printable
        
        if 'GPS GPSAltitude' in list(work_dict.keys()):
            #self.altitude = self.ExifRatio2float(work_dict['GPS GPSAltitude'].values[0])
            #self.lat = self.ExifRatio2Geo(work_dict['GPS GPSLatitude'].values)
            #self.lon = self.ExifRatio2Geo(work_dict['GPS GPSLongitude'].values)
            #self.speed = ExifRatio2float(work_dict['GPS GPSSpeed'].values[0])
            self.gpstime = self.EXIF2datetime(work_dict['GPS GPSDate'],work_dict['GPS GPSTimeStamp'])
            self.garminflag = True
        else:
            self.garminflag = False
            
        
            
    def ExifRatio2Geo(self,ratio_list):
        
        ''' Converts EXIF iFdTag Instance geo coordinate ratio into decimal-degree geo coordinates '''

        degree = float(ratio_list[0].num)
        minutes = float(ratio_list[1].num)/float(ratio_list[1].den)

        return degree + minutes/60.
    
    def ExifRatio2float(self,ratio):
        
        ''' Converts EXIF iFdTag Ratio Instance into floating number '''
        
        return float(ratio.num) / float(ratio.den)
    
    def EXIF2datetime(self,date,time):
    
        ''' Converts EXIF Date and Time values to datetime format '''
        
        datestring = date.values
        timestring = str(time.values[0])+':'+str(time.values[1])+':'+str(np.int(self.ExifRatio2float(time.values[2])))

        return dt.datetime.strptime(datestring+' '+timestring,'%Y:%m:%d %H:%M:%S')

    
    def read_EXIF(self,filename):
    
        ''' Subroutine reads necessary metadata from EXIF and stores it into EXIF_dict '''
        
        with open(filename, 'br') as file:
            work_dict = exifread.process_file(file)
        return work_dict
