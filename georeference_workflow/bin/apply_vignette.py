import sys
from PIL import Image
import numpy as np
import tqdm

opt_mean=np.load('Vignette_correction_image_opt_512138_FLT6921_14mm_FLT1889_2000701_mosaics.npy')

for ffile in tqdm.tqdm(sys.argv[1:]):

    opt = np.float32(Image.open(ffile))

    for i in range(3):
        opt[:,:,i] = np.clip(opt[:,:,i] * opt_mean[:,:,i],0,255)
	
    Image.fromarray(np.uint8(opt)).save(ffile)
