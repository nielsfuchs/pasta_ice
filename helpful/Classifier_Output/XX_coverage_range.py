# -*- coding: utf-8 -*-
'''
Function to calculate coverage and confidence ranges. Output data in latex table format. Yeiiij.

Niels Fuchs (2023) https://github.com/nielsfuchs
'''
import geopandas as gp
import numpy as np


gdf = gp.read_file('classified*_sieved_100_main.shp') # output of 05_Sub_and_mainclasses_P3.py
gdf_unsieved = gp.read_file('classified_ponds.shp') # output of XX_04_tif2shape_P3.py

cum_pond=0
cum_snow=0
cum_ow=0

for ind, row in gdf.iterrows():
    for n in [2,3,5,7,9]:
        cum_pond += row[str(n)+'_others']/100. * row[str(n)+'_area']
    for n in [0,4,6,8,11]:
        cum_snow += row[str(n)+'_others']/100. * row[str(n)+'_area']
    for n in [1]:
        cum_ow += row[str(n)+'_others']/100. * row[str(n)+'_area']

pond_cov=np.sum(gdf.loc[np.isin(gdf.main,[0,3])].geometry.area)/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3])].geometry.area)*100
ice_cov=np.sum(gdf.loc[np.isin(gdf.main,[0,1,3])].geometry.area)/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3,2])].geometry.area)*100
ow_cov=np.sum(gdf.loc[np.isin(gdf.main,[2])].geometry.area)/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3,2])].geometry.area)*100

pond_unsieved_factor = np.sum(gdf_unsieved.geometry.area)/np.sum(gdf.loc[np.isin(gdf.main,[0,3])].geometry.area)

print(data_dict[key][5]+' & {:.1f}\% & [{:.1f}\%,{:.1f}\%] & {:.1f} & [{:.1f}\%,{:.1f}\%] & {:.1f} & [{:.1f}\%,{:.1f}\%]'.format(
        pond_cov,
        pond_cov-cum_pond/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3])].geometry.area)*100,
        pond_cov+(cum_snow+cum_ow)/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3])].geometry.area)*100+np.max([(pond_unsieved_factor-1)*pond_cov,0]),
        ice_cov,
        ice_cov-(cum_snow+cum_pond)/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3,2])].geometry.area)*100,
        ice_cov+(cum_ow)/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3,2])].geometry.area)*100,
        ow_cov,
        ow_cov-cum_ow/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3,2])].geometry.area)*100,
        ow_cov+(cum_snow+cum_pond)/np.sum(gdf.loc[np.isin(gdf.main,[0,1,3])].geometry.area)*100
))



