"""Адаптер XYZ из PointCloud2 с учетом шагов памяти, без зависимости от импортов ROS."""
import numpy as np

class PointCloudError(ValueError):pass

def xyz_from_pointcloud2(message):
    width,height,step,row=map(int,(message.width,message.height,message.point_step,message.row_step))
    if min(width,height,step,row)<0:raise PointCloudError('Negative PointCloud2 dimensions')
    if step<=0 or row<width*step:raise PointCloudError('Invalid point_step or row_step')
    fields={}
    for field in message.fields:
        if field.name in ('x','y','z'):
            if field.name in fields:raise PointCloudError(f'Duplicate XYZ field: {field.name}')
            if field.datatype!=7 or field.count!=1:raise PointCloudError(f'{field.name} requires scalar FLOAT32 (datatype=7), got {field.datatype}/{field.count}')
            if field.offset<0 or field.offset+4>step:raise PointCloudError(f'{field.name} field extends outside point_step')
            fields[field.name]=int(field.offset)
    if set(fields)!=set('xyz'):raise PointCloudError('PointCloud2 must contain x, y, z fields')
    offsets=list(fields.values())
    if any(abs(a-b)<4 for i,a in enumerate(offsets) for b in offsets[i+1:]):raise PointCloudError('Overlapping XYZ fields')
    try:data=memoryview(message.data)
    except TypeError as error:raise PointCloudError('PointCloud2 data is not a byte buffer') from error
    if data.nbytes!=row*height:raise PointCloudError('Data length does not equal row_step * height')
    if width*height==0:return np.empty((0,3),dtype=np.float32)
    dtype=np.dtype({'names':list('xyz'),'formats':[('>' if message.is_bigendian else '<')+'f4']*3,'offsets':[fields[n] for n in 'xyz'],'itemsize':step})
    cloud=np.ndarray((height,width),dtype=dtype,buffer=data,strides=(row,step))
    # Фильтрация нулей, NaN и дальности остается в неизменном ядре с арифметикой float32
    # и исходными индексами организованного облака в построчном порядке.
    return np.stack([cloud[n].reshape(-1) for n in 'xyz'],axis=1).astype(np.float32,copy=False)
