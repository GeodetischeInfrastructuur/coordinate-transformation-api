# generated by datamodel-codegen:
#   filename:  cityjson.schema.json
#   timestamp: 2023-08-16T12:40:50+00:00

from __future__ import annotations

import math
import re
from datetime import date
from enum import Enum
from typing import Annotated, Any, Callable, Dict, List, Optional, Union, cast

from pydantic import AnyUrl, BaseModel, EmailStr, Field, StringConstraints
from pyproj import CRS

CityJSONBoundary = Union[
    List[List[List[int]]],
    List[List[List[List[int]]]],
    List[List[List[List[List[int]]]]],
    List[int],
    List[List[int]],
]


class Type(Enum):
    CityJSON = "CityJSON"


class Extensions(BaseModel):
    url: str
    version: Annotated[str, StringConstraints(pattern=r"^(\d+\.)(\d+)$")]


class Transform(BaseModel):
    class Config:
        extra = "forbid"

    scale: List[float] = Field(..., max_length=3, min_length=3)
    translate: List[float] = Field(..., max_length=3, min_length=3)


class ContactType(Enum):
    individual = "individual"
    organization = "organization"


class Role(Enum):
    resourceProvider = "resourceProvider"
    custodian = "custodian"
    owner = "owner"
    user = "user"
    distributor = "distributor"
    originator = "originator"
    pointOfContact = "pointOfContact"
    principalInvestigator = "principalInvestigator"
    processor = "processor"
    publisher = "publisher"
    author = "author"
    sponsor = "sponsor"
    co_author = "co-author"
    collaborator = "collaborator"
    editor = "editor"
    mediator = "mediator"
    rightsHolder = "rightsHolder"
    contributor = "contributor"
    funder = "funder"
    stakeholder = "stakeholder"


class ContactDetails(BaseModel):
    class Config:
        extra = "forbid"

    contactName: str
    phone: Optional[str] = None
    address: Optional[str] = None
    emailAddress: EmailStr
    contactType: Optional[ContactType] = None
    role: Optional[Role] = Field(None, description="from ISO 19115 codelist")
    organization: Optional[str] = None
    website: Optional[AnyUrl] = None


class Type1(Enum):
    Bridge = "Bridge"


class Type2(Enum):
    MultiPoint = "MultiPoint"


class TypeEnum(Enum):
    RoofSurface = "RoofSurface"


class TypeEnum1(Enum):
    GroundSurface = "GroundSurface"


class TypeEnum2(Enum):
    WallSurface = "WallSurface"


class TypeEnum3(Enum):
    ClosureSurface = "ClosureSurface"


class TypeEnum4(Enum):
    OuterCeilingSurface = "OuterCeilingSurface"


class TypeEnum5(Enum):
    OuterFloorSurface = "OuterFloorSurface"


class TypeEnum6(Enum):
    Window = "Window"


class TypeEnum7(Enum):
    Door = "Door"


class TypeEnum8(Enum):
    InteriorWallSurface = "InteriorWallSurface"


class TypeEnum9(Enum):
    CeilingSurface = "CeilingSurface"


class TypeEnum10(Enum):
    FloorSurface = "FloorSurface"


class TypeEnum11(Enum):
    WaterSurface = "WaterSurface"


class TypeEnum12(Enum):
    WaterGroundSurface = "WaterGroundSurface"


class TypeEnum13(Enum):
    WaterClosureSurface = "WaterClosureSurface"


class TypeEnum14(Enum):
    TrafficArea = "TrafficArea"


class TypeEnum15(Enum):
    AuxiliaryTrafficArea = "AuxiliaryTrafficArea"


class TypeEnum16(Enum):
    TransportationHole = "TransportationHole"


class TypeEnum17(Enum):
    TransportationMarking = "TransportationMarking"


class Semantics(BaseModel):
    type: Annotated[
        str | None,
        Optional[
            Union[
                TypeEnum,
                TypeEnum1,
                TypeEnum2,
                TypeEnum3,
                TypeEnum4,
                TypeEnum5,
                TypeEnum6,
                TypeEnum7,
                TypeEnum8,
                TypeEnum9,
                TypeEnum10,
                TypeEnum11,
                TypeEnum12,
                TypeEnum13,
                TypeEnum14,
                TypeEnum15,
                TypeEnum16,
                TypeEnum17,
                StringConstraints(pattern=r"(\+)\w+"),
            ]
        ],
    ] = None
    Direction: Optional[float] = None
    Slope: Optional[float] = None


class Type3(Enum):
    MultiSurface = "MultiSurface"


class Semantics1(BaseModel):
    surfaces: List[Semantics]
    values: List[Optional[int]]


class Texture1(BaseModel):
    values: Optional[List[List[List[Optional[int]]]]] = None


class MultiSurface(BaseModel):
    class Config:
        extra = "forbid"

    type: Type3
    lod: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$|^(\d)$")]
    boundaries: List[List[List[int]]]
    semantics: Optional[Semantics1] = None
    material: Optional[Dict] = None
    texture: Optional[Dict[str, Texture1]] = None


class Type4(Enum):
    CompositeSurface = "CompositeSurface"


class CompositeSurface(BaseModel):
    class Config:
        extra = "forbid"

    type: Type4
    lod: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$|^(\d)$")]
    boundaries: List[List[List[int]]]
    semantics: Optional[Semantics1] = None
    material: Optional[Dict] = None
    texture: Optional[Dict[str, Texture1]] = None


class Type5(Enum):
    Solid = "Solid"


class Semantics3(BaseModel):
    surfaces: List[Semantics]
    values: List[List[Optional[int]]]


class Texture3(BaseModel):
    values: Optional[List[List[List[List[Optional[int]]]]]] = None


class Solid(BaseModel):
    class Config:
        extra = "forbid"

    type: Type5
    lod: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$|^(\d)$")]
    boundaries: List[List[List[List[int]]]]
    semantics: Optional[Semantics3] = None
    material: Optional[Dict] = None
    texture: Optional[Dict[str, Texture3]] = None


class Type6(Enum):
    CompositeSolid = "CompositeSolid"


class Semantics4(BaseModel):
    surfaces: List[Semantics]
    values: List[List[List[Optional[int]]]]


class Texture4(BaseModel):
    values: Optional[List[List[List[List[List[Optional[int]]]]]]] = None


class CompositeSolid(BaseModel):
    class Config:
        extra = "forbid"

    type: Type6
    lod: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$|^(\d)$")]
    boundaries: List[List[List[List[List[int]]]]]
    semantics: Optional[Semantics4] = None
    material: Optional[Dict] = None
    texture: Optional[Dict[str, Texture4]] = None


class FieldAbstractCityObject(BaseModel):
    attributes: Optional[Dict[str, Any]] = None
    parents: Optional[List[str]] = Field(None, description="the IDs of the parents")
    children: Optional[List[str]] = Field(None, description="the IDs of children")
    geographicalExtent: Optional[List[float]] = Field(None, max_length=6, min_length=6)


class Type7(Enum):
    BridgeConstructiveElement = "BridgeConstructiveElement"


class Type8(Enum):
    MultiLineString = "MultiLineString"


class Semantics5(BaseModel):
    surfaces: List[Semantics]
    values: List[Optional[int]]


class MultiLineString(BaseModel):
    class Config:
        extra = "forbid"

    type: Type8
    lod: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$|^(\d)$")]
    boundaries: List[List[int]]
    semantics: Optional[Semantics5] = None


class Type9(Enum):
    MultiSolid = "MultiSolid"


class Semantics6(BaseModel):
    surfaces: List[Semantics]
    values: List[List[List[Optional[int]]]]


class MultiSolid(BaseModel):
    class Config:
        extra = "forbid"

    type: Type9
    lod: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$|^(\d)$")]
    boundaries: List[List[List[List[List[int]]]]]
    semantics: Optional[Semantics6] = None
    material: Optional[Dict] = None
    texture: Optional[Dict[str, Texture4]] = None


class Type10(Enum):
    GeometryInstance = "GeometryInstance"


class GeometryInstance(BaseModel):
    class Config:
        extra = "forbid"

    type: Type10
    template: int
    boundaries: List[int] = Field(..., max_length=1, min_length=1)
    transformationMatrix: List[float] = Field(..., max_length=16, min_length=16)


class Type11(Enum):
    BridgeFurniture = "BridgeFurniture"


class Type12(Enum):
    BridgeInstallation = "BridgeInstallation"


class Type13(Enum):
    BridgePart = "BridgePart"


class Type14(Enum):
    BridgeRoom = "BridgeRoom"


class BridgeRoom(FieldAbstractCityObject):
    type: Type14
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class Type15(Enum):
    Building = "Building"


class Type16(Enum):
    BuildingConstructiveElement = "BuildingConstructiveElement"


class Type17(Enum):
    BuildingFurniture = "BuildingFurniture"


class Type18(Enum):
    BuildingInstallation = "BuildingInstallation"


class Type19(Enum):
    BuildingPart = "BuildingPart"


class Type20(Enum):
    BuildingRoom = "BuildingRoom"


class BuildingRoom(FieldAbstractCityObject):
    type: Type20
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class Type21(Enum):
    BuildingStorey = "BuildingStorey"


class BuildingStorey(FieldAbstractCityObject):
    type: Type21
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class Type22(Enum):
    BuildingUnit = "BuildingUnit"


class Type23(Enum):
    CityFurniture = "CityFurniture"


class Type24(Enum):
    CityObjectGroup = "CityObjectGroup"


class ExtensionObject(BaseModel):
    type: Annotated[str, StringConstraints(pattern=r"(\+)([A-Z])\w+")]


class Type25(Enum):
    LandUse = "LandUse"


class LandUse(FieldAbstractCityObject):
    type: Type25
    geometry: Optional[List[Union[MultiSurface, CompositeSurface]]] = None


class Type26(Enum):
    OtherConstruction = "OtherConstruction"


class Type27(Enum):
    PlantCover = "PlantCover"


class PlantCover(FieldAbstractCityObject):
    type: Type27
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid, MultiSolid]]
    ] = None


class Type28(Enum):
    Railway = "Railway"


class FieldAbstractTransportationComplex(FieldAbstractCityObject):
    geometry: Optional[
        List[Union[MultiLineString, MultiSurface, CompositeSurface]]
    ] = None


class Type29(Enum):
    Road = "Road"


class Road(FieldAbstractTransportationComplex):
    type: Type29


class Type30(Enum):
    SolitaryVegetationObject = "SolitaryVegetationObject"


class Type31(Enum):
    TINRelief = "TINRelief"


class TINRelief(FieldAbstractCityObject):
    type: Type31
    geometry: Optional[List[CompositeSurface]] = None


class Type32(Enum):
    TransportSquare = "TransportSquare"


class TransportSquare(FieldAbstractTransportationComplex):
    type: Type32


class Type33(Enum):
    Tunnel = "Tunnel"


class Tunnel(FieldAbstractCityObject):
    type: Type33
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class Type34(Enum):
    TunnelConstructiveElement = "TunnelConstructiveElement"


class Type35(Enum):
    TunnelFurniture = "TunnelFurniture"


class Type36(Enum):
    TunnelHollowSpace = "TunnelHollowSpace"


class TunnelHollowSpace(FieldAbstractCityObject):
    type: Type36
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class Type37(Enum):
    TunnelInstallation = "TunnelInstallation"


class Type38(Enum):
    TunnelPart = "TunnelPart"


class TunnelPart(FieldAbstractCityObject):
    type: Type38
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class Type39(Enum):
    WaterBody = "WaterBody"


class WaterBody(FieldAbstractCityObject):
    type: Type39
    geometry: Optional[
        List[
            Union[
                MultiLineString, MultiSurface, CompositeSurface, Solid, CompositeSolid
            ]
        ]
    ] = None


class Type40(Enum):
    Waterway = "Waterway"


class Waterway(FieldAbstractTransportationComplex):
    type: Type40


class Material(BaseModel):
    class Config:
        extra = "forbid"

    name: str
    ambientIntensity: Optional[float] = None
    diffuseColor: Optional[List[float]] = Field(None, max_length=3, min_length=3)
    emissiveColor: Optional[List[float]] = Field(None, max_length=3, min_length=3)
    specularColor: Optional[List[float]] = Field(None, max_length=3, min_length=3)
    shininess: Optional[float] = None
    transparency: Optional[float] = None
    isSmooth: Optional[bool] = None


class Type41(Enum):
    PNG = "PNG"
    JPG = "JPG"


class WrapMode(Enum):
    none = "none"
    wrap = "wrap"
    mirror = "mirror"
    clamp = "clamp"
    border = "border"


class TextureType(Enum):
    unknown = "unknown"
    specific = "specific"
    typical = "typical"


class Texture(BaseModel):
    class Config:
        extra = "forbid"

    type: Optional[Type41] = None
    image: Optional[str] = None
    wrapMode: Optional[WrapMode] = None
    textureType: Optional[TextureType] = None
    borderColor: Optional[List[float]] = Field(None, max_length=4, min_length=3)


class Appearance(BaseModel):
    class Config:
        extra = "forbid"

    default_theme_texture: Optional[str] = Field(None, alias="default-theme-texture")
    default_theme_material: Optional[str] = Field(None, alias="default-theme-material")
    materials: Optional[List[Material]] = None
    textures: Optional[List[Texture]] = None
    vertices_texture: Optional[List[List[float]]] = Field(
        None, alias="vertices-texture"
    )


class Metadata(BaseModel):
    class Config:
        extra = "forbid"

    identifier: Optional[str] = None
    pointOfContact: Optional[ContactDetails] = None
    referenceDate: Optional[date] = None
    title: Optional[str] = None
    geographicalExtent: Optional[List[float]] = Field(None, max_length=6, min_length=6)
    referenceSystem: Optional[
        Annotated[
            str | None,
            StringConstraints(
                pattern=r"^(http|https)://www.opengis.net/def/crs/.+/.+/.+"
            ),
        ]
    ] = None


class SemanticsModel(BaseModel):
    surfaces: List[Semantics]
    values: List[Optional[int]]


class MultiPoint(BaseModel):
    class Config:
        extra = "forbid"

    type: Type2
    lod: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$|^(\d)$")]
    boundaries: List[int]
    semantics: Optional[SemanticsModel] = None


class BridgeConstructiveElement(FieldAbstractCityObject):
    type: Type7
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class BridgeFurniture(FieldAbstractCityObject):
    type: Type11
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class BridgeInstallation(FieldAbstractCityObject):
    type: Type12
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class Addres(BaseModel):
    location: Optional[MultiPoint] = None


class BridgePart(FieldAbstractCityObject):
    type: Type13
    address: Optional[List[Addres]] = None
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class FieldAbstractBuilding(FieldAbstractCityObject):
    address: Optional[List[Addres]] = None
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class BuildingConstructiveElement(FieldAbstractCityObject):
    type: Type16
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class BuildingFurniture(FieldAbstractCityObject):
    type: Type17
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class BuildingInstallation(FieldAbstractCityObject):
    type: Type18
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class BuildingPart(FieldAbstractBuilding):
    type: Type19


class BuildingUnit(FieldAbstractCityObject):
    type: Type22
    address: Optional[List[Addres]] = None
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class CityFurniture(FieldAbstractCityObject):
    type: Type23
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class CityObjectGroup(FieldAbstractCityObject):
    type: Type24
    children_roles: Optional[List[Optional[str]]] = Field(
        None, description="the role of each of the CityObjects members of that group"
    )
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
            ]
        ]
    ] = None


class OtherConstruction(FieldAbstractCityObject):
    type: Type26
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class Railway(FieldAbstractTransportationComplex):
    type: Type28


class SolitaryVegetationObject(FieldAbstractCityObject):
    type: Type30
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class TunnelConstructiveElement(FieldAbstractCityObject):
    type: Type34
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class TunnelFurniture(FieldAbstractCityObject):
    type: Type35
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class TunnelInstallation(FieldAbstractCityObject):
    type: Type37
    geometry: Optional[
        List[
            Union[
                MultiPoint,
                MultiLineString,
                MultiSurface,
                CompositeSurface,
                Solid,
                CompositeSolid,
                MultiSolid,
                GeometryInstance,
            ]
        ]
    ] = None


class GeometryTemplates(BaseModel):
    class Config:
        extra = "forbid"

    templates: List[
        Union[
            MultiPoint,
            MultiLineString,
            Solid,
            MultiSolid,
            CompositeSolid,
            MultiSurface,
            CompositeSurface,
        ]
    ]
    vertices_templates: List[List[float]] = Field(..., alias="vertices-templates")


class Bridge(FieldAbstractCityObject):
    type: Type1
    address: Optional[List[Addres]] = None
    geometry: Optional[
        List[Union[MultiSurface, CompositeSurface, Solid, CompositeSolid]]
    ] = None


class Building(FieldAbstractBuilding):
    type: Type15


CityObject = Union[
    Bridge,
    BridgeConstructiveElement,
    BridgeFurniture,
    BridgeInstallation,
    BridgePart,
    BridgeRoom,
    Building,
    BuildingConstructiveElement,
    BuildingFurniture,
    BuildingInstallation,
    BuildingPart,
    BuildingRoom,
    BuildingStorey,
    BuildingUnit,
    CityFurniture,
    CityObjectGroup,
    ExtensionObject,
    LandUse,
    OtherConstruction,
    PlantCover,
    Railway,
    Road,
    SolitaryVegetationObject,
    TINRelief,
    TransportSquare,
    Tunnel,
    TunnelConstructiveElement,
    TunnelFurniture,
    TunnelHollowSpace,
    TunnelInstallation,
    TunnelPart,
    WaterBody,
    Waterway,
]

CityObjectWithGeometry = Union[
    Bridge,
    BridgeConstructiveElement,
    BridgeFurniture,
    BridgeInstallation,
    BridgePart,
    BridgeRoom,
    Building,
    BuildingConstructiveElement,
    BuildingFurniture,
    BuildingInstallation,
    BuildingPart,
    BuildingRoom,
    BuildingStorey,
    BuildingUnit,
    CityFurniture,
    CityObjectGroup,
    LandUse,
    OtherConstruction,
    PlantCover,
    Railway,
    Road,
    SolitaryVegetationObject,
    TINRelief,
    TransportSquare,
    Tunnel,
    TunnelConstructiveElement,
    TunnelFurniture,
    TunnelHollowSpace,
    TunnelInstallation,
    TunnelPart,
    WaterBody,
    Waterway,
]


class CityjsonV113(BaseModel):
    """CityJSON 1.1.3 Pydantic class, generated with:

    ```
    wget --no-parent  --recursive https://3d.bk.tudelft.nl/schemas/cityjson/1.1.3/
    pip install datamodel-code-generator
    datamodel-codegen  --input  3d.bk.tudelft.nl/schemas/cityjson/1.1.3/metadata.schema.json  --input-file-type jsonschema --output cityjson.py
    ```

    Class methods taken and adapted from: https://github.com/cityjson/cjio
    """

    type: Type
    version: Annotated[str, StringConstraints(pattern=r"^(\d\.)(\d)$")]

    metadata: Optional[Metadata] = None
    extensions: Optional[Dict[str, Extensions]] = None
    CityObjects: Dict[str, CityObject]
    vertices: list[list[float | int]]
    transform: Transform
    appearance: Optional[Appearance] = None
    geometry_templates: Optional[GeometryTemplates] = Field(
        None, alias="geometry-templates"
    )

    def set_epsg(self: CityjsonV113, crs_auth_identifier: str):
        pattern_string = "^(OGC|EPSG):.*$"
        pattern = re.compile(pattern_string)
        if not pattern.match(crs_auth_identifier):
            raise ValueError(
                f"crs_auth_identifier does not matchr regex pattern: `{pattern_string}`"
            )
        crs_auth, crs_identifier = crs_auth_identifier.split(":")
        crs_ref_system_string = (
            f"https://www.opengis.net/def/crs/{crs_auth}/0/{crs_identifier}"
        )
        if self.metadata:
            self.metadata.referenceSystem = crs_ref_system_string

    def decompress(self: CityjsonV113):
        if self.transform is not None:
            scale = self.transform.scale
            translate = self.transform.translate
            # transform vertices to unquantized values: https://www.cityjson.org/specs/1.1.3/#transform-object
            self.vertices = [
                [
                    (vi[0] * scale[0]) + translate[0],
                    (vi[1] * scale[1]) + translate[1],
                    (vi[2] * scale[2]) + translate[2],
                ]
                for vi in self.vertices
            ]

    def update_bbox(self: CityjsonV113):
        """
        Update the bbox (["metadata"]["geographicalExtent"]) of the CityJSON. Assumes vertices are not quantized.

        """
        if len(self.vertices) == 0:
            return [0, 0, 0, 0, 0, 0]
        x, y, z = zip(*self.vertices)
        bbox = [min(x), min(y), min(z), max(x), max(y), max(z)]
        if self.metadata:
            self.metadata.geographicalExtent = bbox

    def remove_duplicate_vertices(self: CityjsonV113):
        def update_geom_indices(a: CityJSONBoundary, newids: list[int]):
            for i, each in enumerate(a):
                if isinstance(each, list):
                    update_geom_indices(each, newids)
                else:
                    a_list = cast(list[int], a)
                    each_int = cast(int, each)
                    a_list[i] = newids[each_int]

        totalinput = len(self.vertices)
        h: Dict[str, int] = {}
        newids: list[int] = [-1] * len(self.vertices)
        newvertices: list[str] = []
        for i, v in enumerate(self.vertices):
            s = "{x} {y} {z}".format(x=v[0], y=v[1], z=v[2])
            if s not in h:
                newid = len(h)
                newids[i] = newid
                h[s] = newid
                newvertices.append(s)
            else:
                newids[i] = h[s]
        for theid in self.CityObjects:
            c_object = self._get_cityobject_without_extension(self.CityObjects[theid])
            if c_object is not None and c_object.geometry is not None:
                for g in c_object.geometry:
                    update_geom_indices(g.boundaries, newids)
        newv2: list[Union[list[float], list[int]]] = []
        for v2 in newvertices:
            a: list[int] | list[float]
            if hasattr(self, "transform") and self.transform is not None:
                a = list(map(lambda x: int(x), v2.split()))
            else:
                a = list(map(lambda x: float(x), v2.split()))
            newv2.append(a)
        self.vertices = newv2  # type: ignore
        return totalinput - len(self.vertices)

    def _get_cityobject_without_extension(
        self,
        c_object: CityObject,
    ) -> CityObjectWithGeometry | None:
        if isinstance(c_object, ExtensionObject):
            return None
            # only process objects with geometries
        return cast(
            CityObjectWithGeometry,
            c_object,
        )

    def remove_orphan_vertices(self: CityjsonV113):
        def visit_geom(
            a: CityJSONBoundary,
            old_new_index_map: dict[int, int],
            new_vertex_indices: list[int],
        ):
            for _, each in enumerate(a):
                if isinstance(each, list):
                    visit_geom(each, old_new_index_map, new_vertex_indices)
                elif isinstance(each, int):
                    if each not in old_new_index_map:
                        old_new_index_map[each] = len(new_vertex_indices)
                        new_vertex_indices.append(each)

        def update_face(
            boundary: CityJSONBoundary,
            old_new_index_map: dict[int, int],
        ):
            for i, each in enumerate(boundary):
                if isinstance(each, list):
                    update_face(each, old_new_index_map)
                else:
                    boundary_int = cast(list[int], boundary)
                    each_int = cast(int, each)
                    boundary_int[i] = old_new_index_map[each_int]

        totalinput: int = len(self.vertices)
        old_new_index_map: dict[int, int] = {}
        new_vertex_indices: list[int] = []

        for obj_id in self.CityObjects:
            if isinstance(self.CityObjects[obj_id], ExtensionObject):
                continue
            # only process objects with geometries
            c_object = cast(
                CityObjectWithGeometry,
                self.CityObjects[obj_id],
            )
            if c_object.geometry is not None:
                for g in c_object.geometry:
                    visit_geom(g.boundaries, old_new_index_map, new_vertex_indices)

        # -- update the faces ids
        for obj_id in self.CityObjects:
            if isinstance(self.CityObjects[obj_id], ExtensionObject):
                continue
            # only process objects with geometries
            c_object = cast(
                CityObjectWithGeometry,
                self.CityObjects[obj_id],
            )
            if c_object.geometry is not None:
                for g in c_object.geometry:
                    update_face(g.boundaries, old_new_index_map)

        # -- replace the vertices, innit?
        newv2: list[list[float | int]] = []
        for v in new_vertex_indices:
            newv2.append(self.vertices[v])
        self.vertices = newv2
        return totalinput - len(self.vertices)

    def compress(self: CityjsonV113, important_digits=3, translate=None) -> None:
        """Compress the city model by scaling and translating it.

        The scaling factor is defined by 'important_digits'. The translation properties
        are either determined as the minimum coordinates of the city model if
        'translate=None', or can be
        set by providing the ``[x, y, z]`` translation properties to 'translate'.
        """
        # assuming vertices need to be compressed - maybe add check if vertices are ints

        # -- find the minx/miny/minz or set from translate
        vertices: list[list[float | int]] = self.vertices

        if translate:
            bbox = translate
        else:
            bbox = [9e9, 9e9, 9e9]
            v: list[float]
            for v in vertices:
                for i in range(3):
                    if v[i] < bbox[i]:
                        bbox[i] = v[i]
        # -- convert vertices in self.j to int
        n = [0, 0, 0]
        p = "%." + str(important_digits) + "f"
        for v in vertices:
            for i in range(3):
                n[i] = v[i] - bbox[i]
            for i in range(3):
                v[i] = int((p % n[i]).replace(".", ""))
        # -- put transform
        ss: str = "0."
        ss += "0" * (important_digits - 1)
        ss += "1"
        ss_float = float(ss)
        self.transform.scale = [ss_float, ss_float, ss_float]
        self.transform.translate = [bbox[0], bbox[1], bbox[2]]
        # -- clean the file
        self.remove_duplicate_vertices()
        self.remove_orphan_vertices()

    def update_bbox_each_cityobjects(self: CityjsonV113, addifmissing=False):
        def recusionvisit(a: CityJSONBoundary, vs: list[int]):
            for each in a:
                if isinstance(each, list):
                    recusionvisit(each, vs)
                else:
                    vs.append(each)

        for co in self.CityObjects:
            if addifmissing == True or hasattr(
                self.CityObjects[co], "geographicalExtent"
            ):
                vs: list[int] = []
                bbox = [9e9, 9e9, 9e9, -9e9, -9e9, -9e9]
                c_object = self._get_cityobject_without_extension(self.CityObjects[co])
                if c_object is not None and c_object.geometry is not None:
                    geometries = c_object.geometry

                    if not isinstance(geometries, list):
                        geometries = [geometries]
                    for g in geometries:
                        if g is not None:
                            if hasattr(g, "boundaries") and g.boundaries is not None:
                                recusionvisit(g.boundaries, vs)
                        else:
                            continue  # TODO: improve code to calculate bbox for all cityobjects, including parent objects with only child objects
                        for each in vs:
                            v = self.vertices[each]
                            for i in range(3):
                                if v[i] < bbox[i]:
                                    bbox[i] = v[i]
                            for i in range(3):
                                if v[i] > bbox[i + 3]:
                                    bbox[i + 3] = v[i]
                        if hasattr(self, "transform") and self.transform is not None:
                            for i in range(3):
                                bbox[i] = (
                                    bbox[i] * self.transform.scale[i]
                                ) + self.transform.translate[i]
                            for i in range(3):
                                bbox[i + 3] = (
                                    bbox[i + 3] * self.transform.scale[i]
                                ) + self.transform.translate[i]
                        self.CityObjects[co].geographicalExtent = bbox

    def get_x_unit_crs(self, crs_str: str) -> str:
        target_crs_crs = CRS.from_authority(*crs_str.split(":"))
        axe = next(
            (
                x
                for x in target_crs_crs.axis_info
                if x.abbrev.lower() in ["x", "e", "lon"]
            ),
            None,
        )
        if axe is None:
            raise ValueError(
                f"unable to retrieve unit x axis (x, e, lon) CRS {crs_str}"
            )
        unit_name = axe.unit_name
        if unit_name not in ["degree", "metre"]:
            raise ValueError(
                f"Unexpected unit in x axis (x, e, lon) CRS {crs_str} - expected values: degree, meter, actual value: {unit_name}"
            )
        return unit_name

    def crs_transform(
        self: CityjsonV113,
        callback: Callable[
            [Union[tuple[float, float], tuple[float, float, float]]],
            Union[tuple[float, float], tuple[float, float, float]],
        ],
        source_crs: str,
        target_crs: str,
    ):
        imp_digits = math.ceil(abs(math.log(self.transform.scale[0], 10)))
        self.decompress()
        self.vertices = [
            list(callback(vertex))
            for vertex in cast(list[tuple[float, float, float]], self.vertices)
        ]
        self.vertices = [
            list(vertex) for vertex in self.vertices
        ]  # convert result to list since, callback function to transform coordinates returns tuples
        self.set_epsg(target_crs)
        self.update_bbox()

        src_unit = self.get_x_unit_crs(source_crs)
        target_unit = self.get_x_unit_crs(target_crs)

        # 0.00001 degree ~= 1 meter
        if src_unit == "metre" and target_unit == "degree":
            imp_digits += 5
        elif src_unit == "degree" and target_unit == "metre":
            imp_digits -= 5
        else:  # src_unit == target_unit
            pass  # imp_digits unchanged

        self.compress(imp_digits)
        self.update_bbox_each_cityobjects(False)
