# -*- coding: utf-8 -*-
'''
Function 5 PASTA-ice

Combines subclasses to mainclasses

Input: 03_classify output .tif as arguments

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import numpy as np
import glob
import tqdm
import sys
import os
import rasterio
from rasterio import features
from shapely.geometry import shape
import geopandas as gp
import time
from rasterio import mask

#### Analysis tool for predicted sea ice surface type maps. Outcome is a geodataframe containing sea ice surface objects separated into four main classes:
# 0: ponds, 1: snow/ice, 2: open water, 3: submerged ice. Each object furthermore contains the fraction of subclasses from which the object was originally
# made of and their respective averaged prediction probabilities. 

classdict={'snow':[0,'orange','Snow/ice'],'water':[1,'red','Open water'],'brimelt':[2,'green','bright Pond'],'bromelt':[3,'darkred','biology Pond'],'bgray':[4,'darkblue','bare, wet \nand thin ice - blue'],'shadowpond':[5,'cyan','Shadow Pond'],'ggray':[6,'gray','bare, wet \nand thin ice - gray'],'darkmelt':[7,'darkgreen','dark Pond'],'shadowsnow':[8,'magenta','Shadow snow'],'submerged':[9,'black','SubmergedIce'],'ridge area':[10,'purple','Ridge area'],'nan':[-1,'white','nan'],'sedisnow':[11,'peru','Sediment Snow']}   #snow,open water,brightpond,broken pond,shadow pond,ice,darkpond,shadow snow, submerged ice scheme

all2piw = {0:0,1:1,2:2,3:2,4:0,5:2,6:0,7:2,8:0,9:2,10:0,11:0}

conf_mat_without_sed=np.load('Calibration_Files/Probability_confidence_matrix_201028.npy')    # probability-confidence conversion matrix
conf_shape=conf_mat_without_sed.shape
conf_mat = np.zeros((conf_shape[0]+2,conf_shape[1],conf_shape[2],conf_shape[3]))

print(conf_mat.shape)
conf_mat[:-2,:,:,:]=conf_mat_without_sed
conf_mat[11,:,:,:]=conf_mat[0,:,:,:]    #   sediments equal snow, artifical value due to missing reference for sediments


### Loop over all given input files:

for ffile in sys.argv[1:]:
    
    ### Step 1: open data

    gpd = gp.read_file(ffile.rsplit('.',1)[0]+'_sieved_100.shp') # open shapefile with surface type map polygons
    
    src1 = rasterio.open(ffile.rsplit('.',1)[0]+'_sieved_100.tif','r')  # open surface type map raster data
    
    ### Step 3: read raster data
    
    df_raster = src1.read(1)    # surface type map
    df_prob = np.float32(src1.read(2))/255.*100.  # Prediction probability
    df_mask = src1.read(3)>123  # mask, True for valid data, false outside the domain
    meta = src1.meta.copy() # raster meta data
    df_transform = src1.transform   # affine transformation matrix

    ### Step 4: prepare geodataframe

    gpd.crs=src1.crs.data['init']   # set CRS; since raster and polygon data is produced in the same script "sieve.py", CRS can be copied without doubts
    
    df=gpd.copy()   # duplicate original dataframe to working variable df    
    
    df.reset_index(level=0, inplace=True)   # reset geodataframe index
    df=df[df['raster_val']!=255]    # remove nans
    
    df['area'] = df.area    # save polygon area into column to avoid recalculation

    df['main'] = None   # allocate column for main class labels
    
    # assign main classes to polygons dependent on their subclass predicition stored in 'raster_val'
    df.loc[np.isin(df['raster_val'],[2,3,5,7,9]),'main']=0  # ponds (ponds+submerged)
    df.loc[np.isin(df['raster_val'],[0,4,6,8,11]),'main']=1    # ice
    df.loc[np.isin(df['raster_val'],[1]),'main']=2  # water


    ### Step 5: Geometry analysis

    print('start geometry analysis')
    
    
    # this part needs the most time. therefore the intermediate result is stored to a file "process". If "process" was already compiled, this part is skipped
    
    if not os.path.isfile(ffile.rsplit('.',1)[0]+'_sieved_100_main_process.shp'):
        
        # compute main class polygons, aggfunc can be arbitrary, since all variables are computed again later semantically correcct

        df_main_compact=df.dissolve(by='main',aggfunc='sum')

        # reset index
        
        df_main_compact.reset_index(level=0, inplace=True) 
        
        # split multipolygons into single ones
    
        df_main=df_main_compact.explode()
        
        # remove all unnecessary columns
        
        df_main=df_main[['main','geometry']]
        
        # reset index after multipolygon split
        
        df_main=df_main.reset_index()
        
        # remove old index column
        
        df_main=df_main[['main','geometry']]
        
        # store polygon areas into single column
        
        df_main['area']=df_main.geometry.area

        # reclassify main polygons: subermerged ice, ponds
    
        print('search for submerged ice','number of polygons:','water',str(len(df_main[df_main['main']==2])),'ice',str(len(df_main[df_main['main']==1])),'pond',str(len(df_main[df_main['main']==0])))
        
        # loop over all open water areas. The small amount compared to ponds is speeding up the algorithm dramatically. Means, submerged areas are pond areas, which touch open water areas and which are smaller than the open water area. 
        
        pond_sindex = df_main[df_main['main']==0].sindex
        
        
        for index, field in tqdm.tqdm(df_main[df_main['main']==2].iterrows()):
            
            item_bounds = list(field.geometry.bounds)
            
            pond_candidate_idx = list(pond_sindex.intersection(item_bounds))
            pond_candidates = df_main[np.isin(df_main['main'], [0,3])].loc[pond_candidate_idx]
            ind_sindex=df_main.where(~pond_candidates.geometry.disjoint(field.geometry)).dropna().index
            
            ind=df_main.where(~df_main[df_main['main']==0].geometry.disjoint(field.geometry)).dropna().index    # opposite of joint is used, to avoid problems with touching and overlaying polygons which are not clearly defined

            df_main.loc[ind[df_main.loc[ind,'area']<field['area']],'main']=3   # define as submerged, only ponds smaller than adajacent open water area

        # Initialize columns for object area subclass information

        for n_class in [0,1,2,3,4,5,6,7,8,9,11]:
            
            df_main[str(n_class)+'_area'] = 0. # area
            
            df_main[str(n_class)+'_over'] = 0.  # averaged overestimation of truepositive pixels in percent
            df_main[str(n_class)+'_others'] = 0.  # averaged overestimation of truepositive pixels that most probably belong to another maijn class in percent
            
            df_main[str(n_class)+'_bool'] = 0 # True, if subclass included in object area
        
        df_main.to_file(ffile.rsplit('.',1)[0]+'_sieved_100_main_process.shp')
    
    else:
        df_main=gp.read_file(ffile.rsplit('.',1)[0]+'_sieved_100_main_process.shp')
        
        
    ### Step 6: Burn raster from polygons, crucial for an increased computing efficiency of the areal fraction calculations
    # calculating areas is much faster with boolean arrays than looping through an arbitrary number of polygons
    
    print('Burn polygons to raster')
    
    # choose datatype depending on number of objects
    
    if len(df_main.index)>=2**16-1:
        dt='uint32'
        nan=2**32-1
    else:
        dt='uint16'
        nan=2**16-1
    
    # update raster metadata
    
    meta.update(dtype=dt)
    meta.update(count=1)
    
    # burn raster data
    
    with rasterio.open(ffile.rsplit('.',1)[0]+'_sieved_100_main.tif','w+',**meta) as rst:
        out_arr = rst.read(1)
        
        shapes = ((geom,values) for geom,values in zip(df_main.geometry,df_main.index))
        
        burned = features.rasterize(shapes=shapes, fill=nan, out=out_arr, transform=rst.transform)
        
        
        
        out_arr[~df_mask]=-1
        rst.write_band(1,out_arr)
    

    
    ### Step 7: Calculate areal fractions of subclasses in main class polygons
    
    print('Calculate area fractions of: '+str(len(df_main))+' elements')
    
    # retrieve pixel area in square meters
    
    pix_area=np.abs(df_transform[0])*np.abs(df_transform[4])
    
    # loop over all objects
    
    for index, field in tqdm.tqdm(df_main.iterrows()):
        
        # "index" is the number of the object which is equally stored in the burned raster, "field" contains all columns
    
        # store main class of object into extra variable
        
        main = field.main
        
        # set subclass lists:
        
        # ponds and submerged
        if main==0 or main==3:   
            class_list=[2,3,5,7,9]
        # snow/ice
        elif main==1:
            class_list=[0,4,6,8,11]
        # open water
        elif main==2:
            class_list=[1]
        
        # go through subclasses:
        
        for n_class in class_list:
            
            idx=np.logical_and(burned==index,df_raster==n_class) # boolean array, True for all pixels of the corresponding subclass in the object
            
            # only continue if subclass is present in the object
            
            if np.any(idx):
                df_main.loc[index,str(n_class)+'_area']=np.sum(idx)*pix_area

                idx_ind=np.where(idx.flatten())[0]
                idx_conf_mat=np.min([np.int8(df_prob.flatten()[idx_ind]/5.),np.ones(np.sum(idx),dtype=np.int8)*19],axis=0)
                df_main.loc[index,str(n_class)+'_over']=np.mean(1.-conf_mat[n_class,0,idx_conf_mat,0])*100.
                df_main.loc[index,str(n_class)+'_others']=np.mean((1.-conf_mat[n_class,0,idx_conf_mat,0])*conf_mat[n_class,0,idx_conf_mat,1])*100.
                df_main.loc[index,str(n_class)+'_bool'] = 1       
    
    ### Final step: save geodataframe

    df_main.to_file(ffile.rsplit('.',1)[0]+'_sieved_100_main.shp')

