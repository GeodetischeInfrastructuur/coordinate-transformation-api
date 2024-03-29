# OGC API - Features - Part 2: Coordinate Reference Systems by Reference

<https://docs.ogc.org/is/18-058/18-058.html>

## Requirements

| requirement                             | applicable         | description                                                                                                                 |
| --------------------------------------- | ------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| /req/crs/crs-uri                        | :x:                | {Authoritie}:{Code} is used in the request and a URN is used in the feature response. URI is used in the `/crss` responses. |
| /req/crs/fc-md-crs-list                 | :x:                | We don't have a `collection` object in this API                                                                             |
| /req/crs/fc-md-storageCrs               | :x:                | No spatial feature collection is stored on the server                                                                       |
| /req/crs/fc-md-storageCrs-valid-value   | :x:                | No storageCrs is advertised                                                                                                 |
| /req/crs/fc-md-crs-list-global          | :x:                | No spatial feature collection is advertised                                                                                 |
| /req/crs/fc-bbox-crs-definition         | :x:                | No request with a bbox or bbox-crs are supported                                                                            |
| /req/crs/fc-bbox-crs-valid-value        | :x:                | No bbox-crs is supported                                                                                                    |
| /req/crs/fc-bbox-crs-valid-defaultValue | :x:                | No bbox-crs is supported                                                                                                    |
| /req/crs/fc-bbox-crs-action             | :x:                | No bbox-crs is specified                                                                                                    |
| /req/crs/fc-crs-definition              | :x:                | No requests on a features or feature resource is available                                                                  |
| /req/crs/fc-crs-valid-value             | :x:                | No crs on a featues or feature resource is supported                                                                        |
| /req/crs/fc-crs-default-value           | :x:                | No crs on a featues or feature resource is supported                                                                        |
| /req/crs/fc-crs-action                  | :x:                | No crs is specified                                                                                                         |
| /req/crs/geojson                        | :grey_exclamation: | We are subjected to this rfc7946                                                                                            |
| /req/crs/ogc-crs-header                 | :heavy_check_mark: | We use the `Content-Crs` header in our response                                                                             |
| /req/crs/ogc-crs-header-value           | :x:                | The `Content-Crs` header returns a {AUTH}:{CODE} value for the CRS                                                          |

## Recommendations

| recommendation                 | applicable | description                                           |
| ------------------------------ | ---------- | ----------------------------------------------------- |
| /rec/crs/crs-format-model      | :x:        | see requirement `/req/crs/crs-uri`                    |
| /rec/crs/fc-md-coordinateEpoch | :x:        | No spatial feature collection is stored on the server |

## Permission

| recommendation         | applicable | description                                    |
| ---------------------- | ---------- | ---------------------------------------------- |
| /per/crs/fc-crs-action | :x:        | No features or feature resources are available |
