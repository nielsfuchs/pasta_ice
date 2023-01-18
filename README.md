# PASTA-Ice

**Proportional Analysis of Surface Types in Arctic Sea Ice Images**

Niels Fuchs, 2021
(last update January 2023)

## Preface

Aerial image classification scheme developped during my time as PhD canditate at the Alfred-Wegener-Institute. 

The classification scheme is intended to classify AWI aerial image datasets of summery sea ice surface recorded with CANON cameras deployed in the POLAR aircrafts and the Polarstern helicopter D-HARK on campaigns in the Arctic during 2008 and 2020. The algorithm was especially designed for the characteristics of the AWI imaging system and differs from other methods by processing the image data pixel by pixel and subclass by subclass. It then semantically combines them into surface type objects belonging to the three main classes ice/snow, open water and ponds with proportions of subclasses. This provides a high degree of classification accuracy and control, as well as increasing the information content of the data providing for the area coverage of subclasses. Pixelwise classification simultaneously allows for a better temporal study of surface evolution. 

The classification scheme has been particullarly designed to study melt ponds and distinguish them clearly from other sea ice surface types and open water for this purpose.

Code is prepared to be used with Python3 installations.

## Workflow

### Auxiliary data

Some files were to big for Github. They need to be downloaded from: 

* Training data for PASTA-ice, and radiometric calibration files used in the algorithm including the vignette correction and confidence conversion matrix are available under DOI: https://doi.org/10.5281/zenodo.7513631.

* Radiometric calibrations are available under DOI: https://doi.org/10.5281/zenodo.7513653.

Sort all features and labels files to a folder `training_data`, and all vignette calibration files to `Calibration_Files`


### Image Data preparation

#### Image georeferencing

Run georeferencing using Agisoft Metashape as described in [Workflow_Manual_NFuchs.pdf](georeference_workflow/Documentation/Workflow_Manual_NFuchs.pdf)

#### Convert image data into brightness harmonized JPEG images

CANON images are by default recorded in RAW format (.CR2). This gives us the possibility to derive individual converted image files optimally tailored to the application purpose. These purposes are (including the optimal image properties):
* Orthorectification – contrast rich, bright images. Corrected vignette.
* Classification – standardized conversion without ambiguous automated correction algorithm. Corrected vignette and applied manually brightness correction. 
* Radiance – pure linear conversion of the data and vignette correction. 
Input images to the classification workflow are in 8-bit JPEG, with disabled compression and no subsampling. 
Vignette correction files were obtained from laboratory measurements at the outlet of an Ulbricht sphere in Leipzig in October 2019. Cross comparison has shown that the results are applicable for the different CANON cameras. 

The classification is based on the assumption that surfaces belonging to the same class/subclass always have a comparable appearance, independent of the incident light and camera settings. Therefore flight surveys need to be splitted up into shorter flight legs with mostly constant incident light conditions. These flight legs are then individually corrected in their image brightness. To do so, copy all raw images of a specific flight leg into a directory.
We first convert these into linearly converted and optimized .ppm files. They will be refered to as **lin_opt** files. In this step we adjust the dark current and saturation value, deactivating automatic rotation, gamma correction, white balance correction and colorspace conversion as well as reduce chromatic aberration and noise. Furthermore, a diskrete vignette correction is applied on the data. 
Execute the python script [01_Raw_conversion_and_vignette_P3.py](01_Raw_conversion_and_vignette_P3.py). The script requests all image filepaths as argument `{imagefilepath}/*.CR2`. 
Subsequently, brightness correction is applied to the **lin_opt** images to convert them to **lin_corr** files. At the same step, **lin_corr** and **lin_opt** images are converted to compression free JPEG to be used in Metashape. 
Run script [02_Brightness_correction_P3.py](02_Brightness_correction_P3.py) with passing the directory that contains all .ppm images as argument. Then, using polygons, mark one representative ROI of open water and one of smooth, non-directly reflective snow. If possible, in the centre of the picture. If there is none, switch to the next image. As soon as both ROIs are selected, the script starts to prepare brightness corrected images. Change the image file path in Metashape and recompile the orthomosaic. 

#### Orthomosaic

Replace the initial images used in Metashape with the lin_opt and lin_cor files to export GeoTIFFs of those or rectify the images on another way (e.g. direct georeferencing, must be GeoTIFF in the end to continue).
Export the orthomosaic from Metashape in a projected UTM grid as geotiff without compression. For the compilation of timeseries align the different scenes directly in Metashape using markers and the align chunks by points tool. To make this effective, DEM and orthomosaic must be recalculated.

### Classification

#### Pixelwise classification

The classification script [03_Classify_P3.py](03_Classify_P3.py) uses a random forest classifier trained with RV Polarstern expedition PS106 data to classify sea ice geotiffs into ten (+1) different classes. Because of the abundance of sediments on the MOSAiC floe, the scheme has been subsequently extended to include the snow/ice class "sediments" if requested. Since the classifier is stored in a python pickle which cannot be exchanged across different platforms, it needs an initialisation when it is used for first time on a computer. All necessary training data for the initialisation is stored in included datasets. 
Output of the classification scheme is a geotiff containing labeled pixels and a RGB image of surface classes.\
Use `03_Classify_P3.py {geotiff}.tiff` to classify the sea ice image into subclasses
* Water
    * open water
* Snow/Ice
    * bright snow/ice
    * bare ice (grey appearance)
    * bare ice (blue shimmer)
    * shadows on ice/snow
    * (sediments)
* Melt Pond
    * melt pond (bright/blue)
    * melt pond (dark/grey)
    * melt pond with organic content (brownish/green)
    * submerged ice (at the edge of ice floes)
    * shadows in ponds


or `03_Classify_P3.py sediments {geotiff}.tiff` to add **sediments** to the list of Snow/Ice subclasses.


#### Assembling into objects and sieving

High resolution aerial imaging means that the image resolution is in comparison much finer than the minimum size of surface objects. We therefore assume that objects that consist of less than 100 pixels cannot be resolved and can be excluded. Such groups of pixels mostly occur at blurry edges or are caused by noise anyway. 
In this processing step [04_Sieve_and_combine_P3.py](04_Sieve_and_combine_P3.py), pixels are combined into objects and too small ones are attached to the adjacent larger ones. Objects of less than 100 pixels are not sieved out however, if they form objects of more than 100 pixels together with surrounding objects of the same main class.\
Run script `04_Sieve_and_combine_P3.py {classified_geotiff}.tiff`.

#### Calculate area fractions of subclasses

In the last prepared processing step [05_Sub_and_mainclasses_P3.py](05_Sub_and_mainclasses_P3.py), main class objects are retrieved out of the subclasses and saved as shapefile containing a polygon table. For each polygon, the areal fractions of subclasses are calculated, classification uncertainty propagation is determined and pond structures are analysed if they rather belong to submerged ice depending on their position and neighbours. They are relabeled as submerged ice if they adjoining a larger area of open water. \
Run script `05_Sub_and_mainclasses_P3.py {classified_geotiff}.tiff`.

## Additional scripts

The folder `helpful` contains some handy scripts to post-process the classification, retrieve albedo and pond depth, and an example on how to add additional training data or further classes to PASTA-ice.




