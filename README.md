# Coordinate Transformation API

RESTful Coordinate Transformation API offering NSGI defined and NSGI recommended transformations for the Netherlands.
Build on top of pyproj and FastAPI.

## Assumptions

- API metadata, documentation and source code is in English
- API provides easy accesible and correct coordinate transformations
- Conforms (as much is possible) to the [OGC API Common](https://ogcapi.ogc.org/common/) and the
  [NL API Design rules](https://gitdocumentatie.logius.nl/publicatie/api/adr/)

## pyproj

> :warning: pyproj makes use of it's own proj binaries and `PROJ_DIR`. These are set when pyproj is build.

Pyproj with default configuration is not capable in performing the right transformations, because our primary
transformations layer on the following transformation grids:

Recommended RDNAPTRANS(TM)2018 variant:

- [`https://cdn.proj.org/nl_nsgi_nlgeo2018.tif`](https://cdn.proj.org/nl_nsgi_nlgeo2018.tif)
- [`https://cdn.proj.org/nl_nsgi_rdcorr2018.tif`](https://cdn.proj.org/nl_nsgi_rdcorr2018.tif)

And the geoid for BESTRANS2020.

These transformation grids need to be downloaded from the [PROJ.org Datumgrid CDN](https://cdn.proj.org/) and put in the
correct directory. This can be done in a couple of ways.

1. Enable [`PROJ_NETWORK`](https://proj.org/en/9.1/usage/environmentvars.html#envvar-PROJ_NETWORK) environment variable
2. Edit [`proj.ini`](https://proj.org/en/9.1/resource_files.html#proj-ini) file by setting `network = on`

These will download the necessary files to a cache so they can be use for the correct transformation. But this requires
a network connection, preferable we don't want to rely on this network connection and provide these files with the
application. This can be done by:

1. [Mirror](https://pyproj4.github.io/pyproj/stable/transformation_grids.html) <https://dcn.proj.org> and write the
   these file to the data directory
2. Download the specific files to the root of the data directory

## Development

Project uses [uv](https://docs.astral.sh/uv/) for package management. To get started install `uv` and run:

Install dev dependencies with:

```sh
uv sync
```

Enable [pre-commit](https://pre-commit.com/) hooks with:

```sh
pre-commit install
```

### direnv config

Repository also contains a [`.envrc`](https://direnv.net/) config file, which automatically activates the `uv` managed
virtual environment. See the [direnv wiki](https://github.com/direnv/direnv/wiki/Python#uv) for how to set this up.

### Tests and Coverage

Run all tests or run all tests except the validation tests:

```sh
pytest tests # all tests
pytest tests -k 'not validation' tests # all tests except validation
pytest tests -k 'validation' tests # only validation tests
```

Check test coverage (install `coverage` with `pip install coverage`):

```sh
coverage run --source=src/coordinate_transformation_api -m pytest -v tests && coverage report -m
```

Validate OAS document:

```sh
# install spectral with: npm install -g @stoplight/spectral-cli - then validate openapi doc with:
echo 'extends: "spectral:oas"\n'> /tmp/ruleset.yaml
spectral lint http://127.0.0.1:8000/openapi.json --ruleset /tmp/ruleset.yaml 
rm /tmp/ruleset.yaml
```

### Install NSGI proj.db

Execute the following shell commands to install the NSGI `proj.time.dependent.transformations.db` as `proj.db` from the
[GeodetischeInfrastructuur/transformations](https://github.com/GeodetischeInfrastructuur/transformations/releases) repo:

```sh
NSGI_PROJ_DB_VERSION=$(sed -rn 's/ARG NSGI_PROJ_DB_VERSION="(.*)"/\1/p' < Dockerfile)
proj_data_dir=$(python3 -c 'import pyproj;print(pyproj.datadir.get_data_dir());')
# ( cmd ) -> subshell to execute commands in $proj_data_dir without changing workdir of current shell
(
   cd "$proj_data_dir"
   echo "NSGI PROJ DB VERSION: $NSGI_PROJ_DB_VERSION"
   curl -sL --show-error -w "%{url}\n" -o nl_nsgi_nlgeo2018.tif https://cdn.proj.org/nl_nsgi_nlgeo2018.tif && \
   curl -sL --show-error -w "%{url}\n" -o nl_nsgi_rdcorr2018.tif https://cdn.proj.org/nl_nsgi_rdcorr2018.tif && \
   curl -sL --show-error -w "%{url}\n" -o nl_nsgi_rdtrans2018.tif https://cdn.proj.org/nl_nsgi_rdtrans2018.tif && \
   release_url="https://api.github.com/repos/GeodetischeInfrastructuur/transformations/releases/tags/${NSGI_PROJ_DB_VERSION}" && \
   curl -sL --show-error -w "%{url}\n" -H "Accept: application/octet-stream" \
      $(curl -s "$release_url" | jq -r '.assets[] | select(.name=="bq_nsgi_bongeo2004.tif").url') -o bq_nsgi_bongeo2004.tif && \
   curl -sL --show-error -w "%{url}\n" -H "Accept: application/octet-stream" \
      $(curl -s "$release_url" | jq -r '.assets[] | select(.name=="nllat2018.gtx").url') -o nllat2018.gtx && \
   curl -sL --show-error -w "%{url}\n" -H "Accept: application/octet-stream" \
      $(curl -s "$release_url" | jq -r '.assets[] | select(.name=="proj.time.dependent.transformations.db").url') -o proj.db
)
```

> :warning: For 'default' usage, like QGIS, use the proj.db. The coordinate transformation API it self uses the
> proj.time.dependent.transformations.db for specific time dependent transformations.

## Docker

### Build container

```bash
docker build -t nsgi/coordinate-transformation-api .
```

### Run container

```bash
docker run --rm -d -p 8000:8000 --name ct-api nsgi/coordinate-transformation-api
```

## CityJSON

### Generate CityJSON models

```sh
wget --no-parent  --recursive https://3d.bk.tudelft.nl/schemas/cityjson/1.1.3/
pip install datamodel-code-generator
datamodel-codegen  --input  3d.bk.tudelft.nl/schemas/cityjson/1.1.3/metadata.schema.json  --input-file-type jsonschema --output cityjson.py
```

### Working with CityJSON (with cjio cli)

Download test/sample data from [www.cityjson.org/datasets/](https://www.cityjson.org/datasets/).

Creating a subset of CityJSON file (for - for example - testing purposes):

```sh
cjio DenHaag_01.city.json subset --random 10 save test_10.city.json
```

CRS transformation with `cjio`:

```sh
cjio test_1.city.json crs_reproject 4937 save test_1_4937.city.json
```

```mermaid
flowchart
    input([/transform endpoint]) ==> filetype{content-type<br>request body}
    filetype==> | GeoJSON | dc_param{density-check parameter}
    filetype==> | CityJSON | a4[add response header:<br>density-check-result: not-implemented]
    a4 --> tf
    dc_param ==> |"`default: *true*`"|ms_param{max_segment param}
    ms_param -.-> |max_segment_deviation param| bc[check if data within bbox]
    bc --> |success| dc
    bc --> |failure| output_error_bbox([HTTP 400 with bbox error])

    ms_param ==> |"`max_segment_length param (default: *200*)`"| dc[density check]
    dc_param -.-> |"`*false*`"| a5[add response header:<br>density-check-result: not-run]

    a5 --> tf[transform]

    dc --> |"not applicable: geometrytype is point" | a2[add response header:<br>density-check-result: not-applicable-geom-type]
    dc --> |"success"| a3[add response header:<br>density-check-result: success]
    dc --> |"failure"| a6[add response header:<br>density-check-result: failed]
    a6 --> output_error([HTTP 400 with density check report])
    a2 --> tf
    a3 --> tf
    tf --> output([http 200 response])
    class output_error error
    class output_error_bbox error
    classDef error stroke: red,stroke-width:2px
    style output stroke: green,stroke-width:2px
```
