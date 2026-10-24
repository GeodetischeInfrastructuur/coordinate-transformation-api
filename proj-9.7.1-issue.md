# proj 9.7.1

## NSGI:Saba2020_GEOCENTRIC-NSGI:Saba_DPnet_Height

### pyproj-3.7.2 + proj 9.7.1

```txt
h_transformer='proj=pipeline step inv proj=helmert x=1138.7432 y=-2064.4761 z=110.7016 rx=-214.615206 ry=479.360036 rz=-164.703951 s=-402.32073 convention=coordinate_frame exact step inv proj=cart ellps=intl step proj=tmerc lat_0=0 lon_0=-63 k=0.9996 x_0=29973.97 y_0=-1947925.94 ellps=intl'

v_transformer='proj=pipeline step inv proj=helmert x=1138.7432 y=-2064.4761 z=110.7016 rx=-214.615206 ry=479.360036 rz=-164.703951 s=-402.32073 convention=coordinate_frame exact step inv proj=cart ellps=intl step inv proj=vgridshift grids=null multiplier=1 step proj=tmerc lat_0=0 lon_0=-63 k=0.9996 x_0=29973.97 y_0=-1947925.94 ellps=intl'
```

### pyproj-3.7.2 + proj 9.5.1

```txt
h_transformer='proj=pipeline step inv proj=helmert x=1138.7432 y=-2064.4761 z=110.7016 rx=-214.615206 ry=479.360036 rz=-164.703951 s=-402.32073 convention=coordinate_frame exact step inv proj=cart ellps=intl step proj=tmerc lat_0=0 lon_0=-63 k=0.9996 x_0=29973.97 y_0=-1947925.94 ellps=intl'

v_transformer='proj=pipeline step inv proj=helmert x=1138.7432 y=-2064.4761 z=110.7016 rx=-214.615206 ry=479.360036 rz=-164.703951 s=-402.32073 convention=coordinate_frame exact step inv proj=cart ellps=intl step inv proj=vgridshift grids=null multiplier=1 step proj=tmerc lat_0=0 lon_0=-63 k=0.9996 x_0=29973.97 y_0=-1947925.94 ellps=intl'
```

## NSGI:Bonaire2004_GEOCENTRIC-NSGI:Bonaire_DPnet_KADpeil

### pyproj-3.7.2 + proj 9.7.1

```txt
h_transformer='proj=pipeline step inv proj=helmert x=-366.1939 y=-115.0688 z=-776.7039 rx=20.963080 ry=16.462749 rz=-14.276379 s=-12.80900 convention=coordinate_frame exact step inv proj=cart ellps=intl step proj=tmerc lat_0=12.180658675 lon_0=-68.251802281 k=1 x_0=23209.56 y_0=21423.99 ellps=intl'

v_transformer='proj=pipeline step inv proj=helmert x=-366.1939 y=-115.0688 z=-776.7039 rx=20.963080 ry=16.462749 rz=-14.276379 s=-12.80900 convention=coordinate_frame exact step inv proj=cart ellps=intl step inv proj=vgridshift grids=nl_nsgi_bongeo2004.tif multiplier=1 step proj=tmerc lat_0=12.180658675 lon_0=-68.251802281 k=1 x_0=23209.56 y_0=21423.99 ellps=intl'
```

### pyproj-3.7.2 + proj 9.5.1

```txt
h_transformer='proj=pipeline step inv proj=helmert x=-366.1939 y=-115.0688 z=-776.7039 rx=20.963080 ry=16.462749 rz=-14.276379 s=-12.80900 convention=coordinate_frame exact step inv proj=cart ellps=intl step proj=tmerc lat_0=12.180658675 lon_0=-68.251802281 k=1 x_0=23209.56 y_0=21423.99 ellps=intl'

v_transformer='proj=pipeline step inv proj=cart ellps=GRS80 step proj=vgridshift grids=bq_nsgi_bongeo2004.tif step proj=push v_3 step inv proj=vgridshift grids=bq_nsgi_bongeo2004.tif omit_inv step proj=cart ellps=GRS80 step inv proj=helmert x=-366.1939 y=-115.0688 z=-776.7039 rx=20.963080 ry=16.462749 rz=-14.276379 s=-12.80900 convention=coordinate_frame exact step inv proj=cart ellps=intl step proj=tmerc lat_0=12.180658675 lon_0=-68.251802281 k_0=1 x_0=23209.5600 y_0=21423.9900 ellps=intl step proj=pop v_3'
```