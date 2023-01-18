for g in *.CR2
do  
    echo "Converting $g"
    if [[ $g == *","* ]]; then
        f=${g%,*}_${g##*,}
        mv $g $f
    else
        f=$g
    fi
    dcraw -T -t 0 -W -b 1.0 -r 2.036133 1.000000 1.471680 1.0000000 -C 0.99950424 0.999489075 -n 40 $f
done
echo "Apply vignette"
/scratch/users/nifuchs/bin/anaconda3/bin/ipython apply_vignette.py *.tiff
echo "Resize file and copy EXIF"
for f in *.tiff
do
    convert -quality 100 $f "$(basename "$f" .tiff).jpg"
    rm $f
    /scratch/users/nifuchs/bin/exiftool/Image-ExifTool-12.12/exiftool -TagsfromFile "$(basename "$f" .tiff).CR2" "$(basename "$f" .tiff).jpg"
    rm "$(basename "$f" .tiff).jpg_original"
    mv "$(basename "$f" .tiff).jpg" ../JPG
done






### dcraw commands

# -v        Print verbose messages
# -c        Write image data to standard output
# -e        Extract embedded thumbnail image
# -i        Identify files without decoding them
# -i -v     Identify files and show metadata
# -z        Change file dates to camera timestamp
# -w        Use camera white balance, if possible
# -a        Average the whole image for white balance
# -A <x y w h> Average a grey box for white balance
# -r <r g b g> Set custom white balance
# +M/-M     Use/don't use an embedded color matrix
# -C <r b>  Correct chromatic aberration
# -P <file> Fix the dead pixels listed in this file
# -K <file> Subtract dark frame (16-bit raw PGM)
# -k <num>  Set the darkness level
# -S <num>  Set the saturation level
# -n <num>  Set threshold for wavelet denoising
# -H [0-9]  Highlight mode (0=clip, 1=unclip, 2=blend, 3+=rebuild)
# -t [0-7]  Flip image (0=none, 3=180, 5=90CCW, 6=90CW)
# -o [0-5]  Output colorspace (raw,sRGB,Adobe,Wide,ProPhoto,XYZ)
# -o <file> Apply output ICC profile from file
# -p <file> Apply camera ICC profile from file or "embed"
# -d        Document mode (no color, no interpolation)
# -D        Document mode without scaling (totally raw)
# -j        Don't stretch or rotate raw pixels
# -W        Don't automatically brighten the image
# -b <num>  Adjust brightness (default = 1.0)
# -g <p ts> Set custom gamma curve (default = 2.222 4.5)
# -q [0-3]  Set the interpolation quality
# -h        Half-size color image (twice as fast as "-q 0")
# -f        Interpolate RGGB as four colors
# -m <num>  Apply a 3x3 median filter to R-G and B-G
# -s [0..N-1] Select one raw image or "all" from each file
# -6        Write 16-bit instead of 8-bit
# -4        Linear 16-bit, same as "-6 -W -g 1 1"
# -T        Write TIFF instead of PPM
