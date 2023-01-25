import numpy as np
import imageio
import scipy
import tqdm
import os


def azure_ir_transform(input_image):
    """
    Apply the following transformation to better visualize high-dynamic-range 
    infrared video (used in :py:func:`snub.io.video.transform_azure_ir_stream`)
    This method is useful for viewing the infrared stream output by
    an `Azure Kinect (K4A) depth sensor <https://github.com/microsoft/Azure-Kinect-Sensor-SDK>`_. ::

        transformed_image = log(input_image)*322 - 350
    


    Parameters
    ----------
    input_image: ndarray
        Input image as a numpy array (can be any shape)
        
    Returns
    -------
    transformed_image: ndarray 
    """
    transformed_image = np.log(np.float32(input_image)+100)*70-350
    transformed_image = np.uint8(np.clip(transformed_image,0,255))
    return transformed_image


def transform_azure_ir_stream(inpath, outpath=None, num_frames=None, quality=7):
    """
    Convert a 16bit monochrome video to an 8bit mp4 video that 
    can be viewed within SNUB. Each frame is transformed using 
    :py:func:`snub.io.video.azure_ir_transform` and the output 
    video is compressed using ffmpeg. This method is useful for 
    viewing the infrared stream output by an 
    `Azure Kinect (K4A) depth sensor <https://github.com/microsoft/Azure-Kinect-Sensor-SDK>`_.
    
    Parameters
    ----------
    inpath : str 
        Path to the input video
        
    outpath: str, default=None
        Path where the output video will be written (must end in '.mp4'). 
        If ``outpath=None``, then the output video will have the same location 
        as ``inpath`` with the file extension switched to ``.mp4``.
        
    num_frames: int, default=None
        Number of frames to convert. By default the full video is converted.

    quality: int, default=7
        Quality of output video (passed to imageio writer).
    """
    if not os.path.exists(inpath): 
        raise AssertionError('The video {} does not exist'.format(inpath))
    if outpath is None: 
        outpath = os.path.splitext(inpath)[0]+'.mp4'
        if outpath==inpath:
            raise AssertionError('Cannot overwrite the input video. Make sure the input video does not end in .mp4 or specify an alternative `outpath`')
    elif not os.path.splitext(outpath)[1]=='.mp4':
        raise AssertionError('`outpath` must end with .mp4')
        
    reader = imageio.get_reader(inpath, pixelformat='gray16', dtype='uint16')
    num_frames_in_video = reader.count_frames()
    fps = reader.get_meta_data()['fps']
    
    if num_frames is None: num_frames = num_frames_in_video
    elif num_frames > num_frames_in_video:
        raise AssertionError('`num_frames={} but there are only {} frames in the input video'.format(num_frames, num_frames_in_video))

    print('Saving transformed video to '+outpath)
    with imageio.get_writer(outpath, fps=fps, quality=quality, pixelformat='yuv420p') as writer:
        for i in tqdm.trange(num_frames):
            img = reader.get_data(i)
            img = azure_ir_transform(img)
            writer.append_data(img)


def detrend_video(
    videopath_in, videopath_out, window_length=150, window_step=10, 
    pctl=20, clipping_bounds=(-20,45), quality=6):
    """
    Detrend a video by subtracting a pixel-wise running percentile.  
    
    Parameters
    ----------
    videopath_in : str 
        Path to the input video

    videopath_out : str
        Path to write the detrended video
        
    window_length: int, default=75
        Window over which to calculate the running percentile. 
        
    window_step: int, default=5
        Downsampling factor for computing running percentile. For frame `i`, the
        frames used to compute the percetile will be 
        `[i, i-window_step, i-2*window_step,...,i-window_length]`

    pctl: int, default=20
        Percentile used to calculate background

    clipping_bounds: tuple(float,float), default=(-20,45)
        Clipping bounds for normalizing detrended video. The interval defined
        by `clip` is rescaled to [0,255] in the final video. 

    quality: int, defaut=6
        Quality of output video (passed to imageio writer). 

    """    
    
    reader = imageio.get_reader(videopath_in)
    metadata = reader.get_meta_data()
    buffer = [np.zeros(metadata['size'][::-1]) for i in range(0,window_length,window_step)]

    writer = imageio.get_writer(
        videopath_out, fps=metadata['fps'], quality=quality, 
        macro_block_size=1, pixelformat=metadata['pix_fmt'])
    
    for im in tqdm.tqdm(reader, total=reader.count_frames()):
        x = im[:,:,0].astype(float)
        buffer.insert(0,x)
        buffer = buffer[:window_length]
        background = np.percentile(buffer[::window_step],pctl,axis=0)
        x = np.clip(x - background, *clipping_bounds)
        x = (x - clipping_bounds[0])/(clipping_bounds[1]-clipping_bounds[0])*255
        writer.append_data(np.repeat(x[:,:,None],3,axis=2).astype(np.uint8))
        
    writer.close() 



def fast_prct_filt(input_data, level=8, frames_window=3000):
    """
    Fast approximate percentage filtering
    Borrowed from CaImAn
    """
    from scipy.ndimage import zoom
    data = np.atleast_2d(input_data).copy()
    T = np.shape(data)[-1]
    downsampfact = frames_window

    elm_missing = int(np.ceil(T * 1.0 / downsampfact)
                      * downsampfact - T)
    padbefore = int(np.floor(elm_missing / 2.))
    padafter = int(np.ceil(elm_missing / 2.))
    tr_tmp = np.pad(data.T, ((padbefore, padafter), (0, 0)), mode='reflect')
    numFramesNew, num_traces = np.shape(tr_tmp)
    #% compute baseline quickly

    tr_BL = np.reshape(tr_tmp, (downsampfact, int(numFramesNew / downsampfact),
                                num_traces), order='F')

    tr_BL = np.percentile(tr_BL, level, axis=0)
    tr_BL = zoom(np.array(tr_BL, dtype=np.float32),
                               [downsampfact, 1], order=3, mode='nearest',
                               cval=0.0, prefilter=True)

    if padafter == 0:
        data -= tr_BL.T
    else:
        data -= tr_BL[padbefore:-padafter].T

    return data.squeeze()