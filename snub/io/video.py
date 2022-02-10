import numpy as np
import imageio
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


def transform_azure_ir_stream(inpath, outpath=None, num_frames=None):
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
    with imageio.get_writer(outpath, fps=fps) as writer:
        for i in tqdm.trange(num_frames):
            img = reader.get_data(i)
            img = azure_ir_transform(img)
            writer.append_data(img)

        
