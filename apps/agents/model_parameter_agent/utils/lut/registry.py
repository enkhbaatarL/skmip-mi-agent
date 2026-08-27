from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
import yaml

from apps.agents.model_parameter_agent.utils.lut.models import domain_error
from apps.common.utils.yaml_utils import normalize_yaml_text


AdapterName = Literal[
    "tabular",
    "futures_price",
    "gdp_growth",
    "hurricane_intensity",
    "liq_prod",
    "liq_util",
    "pipeline",
    "pmi_reference",
    "population",
    "supply_disruption",
    "temperature_degree_days",
]
LayoutName = Literal["row", "year_columns"]

PACKAGE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_LUT_ROOT = PACKAGE_DIR / "resources" / "lut"


class _LutFileSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    required_columns: tuple[str, ...] = ()
    axis_columns: dict[str, str] = Field(default_factory=dict)
    value_column: str | None = None
    year_value_column: str | None = None

    @model_validator(mode="after")
    def validate_columns(self) -> _LutFileSpecModel:  # noqa: C901
        if not self.path.strip() or self.path != self.path.strip():
            msg = "LUT path must not be empty or padded with whitespace"
            raise ValueError(msg)
        if any(not str(axis_name).strip() for axis_name in self.axis_columns):
            msg = "canonical axis names in axis_columns must not be empty"
            raise ValueError(msg)
        declared = [
            *self.required_columns,
            *self.axis_columns.values(),
            *([self.value_column] if self.value_column else []),
            *([self.year_value_column] if self.year_value_column else []),
        ]
        if any(not str(column).strip() for column in declared):
            msg = "LUT column names must not be empty"
            raise ValueError(msg)
        if len(self.required_columns) != len(set(self.required_columns)):
            msg = "required_columns must not contain duplicates"
            raise ValueError(msg)
        if len(self.axis_columns) != len(set(self.axis_columns.values())):
            msg = "axis_columns must map to distinct CSV headers"
            raise ValueError(msg)
        mapped_value_headers = [
            *self.axis_columns.values(),
            *([self.value_column] if self.value_column else []),
        ]
        if len(mapped_value_headers) != len(set(mapped_value_headers)):
            msg = "axis_columns and value_column must map to distinct CSV headers"
            raise ValueError(msg)
        templates = [
            column
            for column in (*self.required_columns, self.year_value_column)
            if column is not None and ("{" in column or "}" in column)
        ]
        for template in templates:
            if template.count("{year}") != 1:
                msg = f"LUT column template may contain only one {{year}} placeholder: {template}"
                raise ValueError(msg)
            try:
                formatted = template.format(year=2026)
            except (KeyError, ValueError) as exc:
                msg = f"invalid LUT column template: {template}"
                raise ValueError(msg) from exc
            if "{" in formatted or "}" in formatted:
                msg = f"invalid LUT column template: {template}"
                raise ValueError(msg)
        return self


class _ParameterLutSpecModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True
    adapter: AdapterName
    layout: LayoutName | None = None
    files: dict[str, _LutFileSpecModel]
    key_axes: tuple[str, ...]
    metadata_axes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_shape(self) -> _ParameterLutSpecModel:  # noqa: C901
        if not self.files:
            msg = "files must contain at least one named LUT source"
            raise ValueError(msg)
        if not self.key_axes:
            msg = "key_axes must contain at least one canonical axis"
            raise ValueError(msg)
        if any(not axis.strip() for axis in (*self.key_axes, *self.metadata_axes)):
            msg = "canonical axis names must not be empty"
            raise ValueError(msg)
        if len(self.key_axes) != len(set(self.key_axes)):
            msg = "key_axes must not contain duplicates"
            raise ValueError(msg)
        if len(self.metadata_axes) != len(set(self.metadata_axes)):
            msg = "metadata_axes must not contain duplicates"
            raise ValueError(msg)
        overlap = sorted(set(self.key_axes) & set(self.metadata_axes))
        if overlap:
            raise ValueError(
                "key_axes and metadata_axes must not overlap: " + ", ".join(overlap),
            )

        if self.adapter == "tabular":
            if self.layout is None:
                msg = "tabular adapter requires layout"
                raise ValueError(msg)
            if set(self.files) != {"values"}:
                msg = "tabular adapter requires exactly one files.values source"
                raise ValueError(msg)
            values = self.files["values"]
            if "Year" not in self.key_axes:
                msg = "tabular LUT key_axes must include Year for horizon filtering"
                raise ValueError(msg)
            if self.layout == "year_columns" and "Year" in values.axis_columns:
                msg = "year_columns layout derives Year and must not map a Year CSV axis"
                raise ValueError(msg)
            expected_axis_columns = set(self.key_axes) - ({"Year"} if self.layout == "year_columns" else set())
            missing_axes = sorted(expected_axis_columns - set(values.axis_columns))
            unknown_axes = sorted(set(values.axis_columns) - set(self.key_axes) - set(self.metadata_axes))
            if missing_axes:
                raise ValueError(
                    "tabular axis_columns are missing canonical axes: " + ", ".join(missing_axes),
                )
            if unknown_axes:
                raise ValueError(
                    "tabular axis_columns contain undeclared axes: " + ", ".join(unknown_axes),
                )
            if self.layout == "row":
                if values.value_column is None or values.year_value_column is not None:
                    msg = "row layout requires value_column only"
                    raise ValueError(msg)
            elif values.year_value_column is None or "{year}" not in values.year_value_column:
                msg = "year_columns layout requires year_value_column with {year}"
                raise ValueError(msg)
            elif values.value_column is not None:
                msg = "year_columns layout must not declare value_column"
                raise ValueError(msg)
        elif self.layout is not None:
            msg = "custom adapters must not declare layout"
            raise ValueError(msg)

        required_roles = {
            "futures_price": {"values"},
            "gdp_growth": {"values"},
            "hurricane_intensity": {"intensity", "plants"},
            "liq_prod": {"values"},
            "temperature_degree_days": {"hdd", "cdd"},
            "liq_util": {"values"},
            "pipeline": {"values"},
            "pmi_reference": {"references", "values"},
            "population": {"values"},
            "supply_disruption": {"production", "seasonality"},
        }
        expected_roles = required_roles.get(self.adapter)
        if expected_roles is not None and set(self.files) != expected_roles:
            msg = f"{self.adapter} adapter requires file roles: {', '.join(sorted(expected_roles))}"
            raise ValueError(
                msg,
            )
        if self.adapter != "tabular":
            for file_spec in self.files.values():
                if file_spec.axis_columns or file_spec.value_column or file_spec.year_value_column:
                    msg = "custom adapters use required_columns, not tabular column fields"
                    raise ValueError(msg)
                if not file_spec.required_columns:
                    msg = "custom adapter files require required_columns"
                    raise ValueError(msg)
        return self


@dataclass(frozen=True, slots=True)
class LutFileSpec:
    role: str
    relative_path: str
    resolved_path: Path
    required_columns: tuple[str, ...]
    axis_columns: Mapping[str, str]
    value_column: str | None
    year_value_column: str | None


@dataclass(frozen=True, slots=True)
class ParameterLutSpec:
    parameter_name: str
    enabled: bool
    adapter: AdapterName
    layout: LayoutName | None
    files: Mapping[str, LutFileSpec]
    key_axes: tuple[str, ...]
    metadata_axes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParameterSpecRegistry:
    config_path: Path
    lut_root: Path
    specs: Mapping[str, ParameterLutSpec]
    references: Mapping[str, LutFileSpec]
    canonical_yaml: bytes
    schema_hash: str

    def get(self, parameter_name: str) -> ParameterLutSpec | None:
        return self.specs.get(str(parameter_name or "").strip())

    def is_registered(self, parameter_name: str) -> bool:
        return self.get(parameter_name) is not None

    @property
    def enabled_specs(self) -> Mapping[str, ParameterLutSpec]:
        return MappingProxyType(
            {parameter_name: spec for parameter_name, spec in self.specs.items() if spec.enabled},
        )

    @property
    def referenced_paths(self) -> tuple[Path, ...]:
        return tuple(
            sorted(
                {
                    file_spec.resolved_path
                    for parameter_spec in self.specs.values()
                    for file_spec in parameter_spec.files.values()
                }
                | {file_spec.resolved_path for file_spec in self.references.values()},
                key=str,
            ),
        )


def _safe_relative_path(raw_path: str, *, lut_root: Path) -> tuple[str, Path]:
    text = str(raw_path or "").strip()
    if not text or "\\" in text:
        msg = f"LUT path must be a non-empty POSIX relative path: {raw_path!r}"
        raise domain_error(msg)
    pure_path = PurePosixPath(text)
    if pure_path.is_absolute() or ".." in pure_path.parts or "." in pure_path.parts:
        msg = f"LUT path escapes the resource directory: {text}"
        raise domain_error(msg)
    root = lut_root.resolve()
    resolved = (root / Path(*pure_path.parts)).resolve()
    if not resolved.is_relative_to(root):
        msg = f"LUT path escapes the resource directory: {text}"
        raise domain_error(msg)
    return pure_path.as_posix(), resolved


def load_parameter_spec_registry(  # noqa: C901
    config_path: Path,
    *,
    lut_root: Path,
    yaml_bytes: bytes | None = None,
) -> ParameterSpecRegistry:
    try:
        raw_bytes = config_path.read_bytes() if yaml_bytes is None else yaml_bytes
    except OSError as exc:
        msg = f"failed to read LUT parameter config {config_path}: {exc}"
        raise domain_error(msg) from exc
    try:
        raw_document = yaml.safe_load(normalize_yaml_text(raw_bytes.decode("utf-8")))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        msg = f"invalid LUT parameter YAML {config_path}: {exc}"
        raise domain_error(msg) from exc
    if not isinstance(raw_document, dict) or not raw_document:
        msg = "LUT parameter YAML must be a non-empty parameter mapping"
        raise domain_error(msg)

    if "model_parameter_resources" in raw_document:
        raw_document = raw_document.get("model_parameter_resources")
        if not isinstance(raw_document, dict) or not raw_document:
            msg = "config model_parameter_resources must be a non-empty mapping"
            raise domain_error(msg)

    raw_reference_document: dict[str, object] = {}
    if {"basecase", "lut"}.issubset(raw_document):
        raw_lut_document = raw_document.get("lut")
        if not isinstance(raw_lut_document, dict) or not raw_lut_document:
            msg = "model parameter resource manifest lut must be a non-empty parameter mapping"
            raise domain_error(msg)
        raw_references = raw_document.get("references", {})
        if not isinstance(raw_references, dict):
            msg = "model parameter resource manifest references must be a mapping"
            raise domain_error(msg)
        raw_reference_document = raw_references
    else:
        # 기존 LUT-only YAML 호출과 테스트를 계속 지원한다.
        raw_lut_document = raw_document

    parsed_models: dict[str, _ParameterLutSpecModel] = {}
    for raw_parameter_name, raw_spec in raw_lut_document.items():
        parameter_name = str(raw_parameter_name or "").strip()
        if not parameter_name or parameter_name != raw_parameter_name:
            msg = f"invalid canonical LUT parameter name: {raw_parameter_name!r}"
            raise domain_error(msg)
        if not isinstance(raw_spec, dict):
            msg = f"invalid LUT spec for {parameter_name}: mapping is required"
            raise domain_error(msg)
        semantic_spec = dict(raw_spec)
        raw_files = semantic_spec.get("files")
        if isinstance(raw_files, dict):
            semantic_spec["files"] = {
                role: (
                    {key: value for key, value in file_spec.items() if key != "object_storage_path"}
                    if isinstance(file_spec, dict)
                    else file_spec
                )
                for role, file_spec in raw_files.items()
            }
        try:
            parsed_models[parameter_name] = _ParameterLutSpecModel.model_validate(semantic_spec)
        except ValidationError as exc:
            msg = f"invalid LUT spec for {parameter_name}: {exc}"
            raise domain_error(msg) from exc

    specs: dict[str, ParameterLutSpec] = {}
    for parameter_name, parsed in parsed_models.items():
        files: dict[str, LutFileSpec] = {}
        for role, file_model in parsed.files.items():
            relative_path, resolved_path = _safe_relative_path(
                file_model.path,
                lut_root=lut_root,
            )
            files[role] = LutFileSpec(
                role=role,
                relative_path=relative_path,
                resolved_path=resolved_path,
                required_columns=file_model.required_columns,
                axis_columns=MappingProxyType(dict(file_model.axis_columns)),
                value_column=file_model.value_column,
                year_value_column=file_model.year_value_column,
            )
        specs[parameter_name] = ParameterLutSpec(
            parameter_name=parameter_name,
            enabled=parsed.enabled,
            adapter=parsed.adapter,
            layout=parsed.layout,
            files=MappingProxyType(files),
            key_axes=parsed.key_axes,
            metadata_axes=parsed.metadata_axes,
        )

    parsed_references: dict[str, _LutFileSpecModel] = {}
    references: dict[str, LutFileSpec] = {}
    for raw_reference_name, raw_file_spec in raw_reference_document.items():
        reference_name = str(raw_reference_name or "").strip()
        if not reference_name or reference_name != raw_reference_name:
            msg = f"invalid model parameter reference name: {raw_reference_name!r}"
            raise domain_error(msg)
        if not isinstance(raw_file_spec, dict):
            msg = f"invalid model parameter reference for {reference_name}: mapping is required"
            raise domain_error(msg)
        semantic_file_spec = {key: value for key, value in raw_file_spec.items() if key != "object_storage_path"}
        try:
            parsed_reference = _LutFileSpecModel.model_validate(semantic_file_spec)
        except ValidationError as exc:
            msg = f"invalid model parameter reference for {reference_name}: {exc}"
            raise domain_error(msg) from exc
        if parsed_reference.axis_columns or parsed_reference.value_column or parsed_reference.year_value_column:
            msg = f"model parameter reference {reference_name} supports required_columns only"
            raise domain_error(msg)
        if not parsed_reference.required_columns:
            msg = f"model parameter reference {reference_name} requires required_columns"
            raise domain_error(msg)
        relative_path, resolved_path = _safe_relative_path(
            parsed_reference.path,
            lut_root=lut_root,
        )
        parsed_references[reference_name] = parsed_reference
        references[reference_name] = LutFileSpec(
            role=reference_name,
            relative_path=relative_path,
            resolved_path=resolved_path,
            required_columns=parsed_reference.required_columns,
            axis_columns=MappingProxyType({}),
            value_column=None,
            year_value_column=None,
        )

    canonical_payload = {
        "lut": {
            parameter_name: parsed_models[parameter_name].model_dump(mode="json")
            for parameter_name in sorted(parsed_models)
        },
        "references": {
            reference_name: parsed_references[reference_name].model_dump(mode="json")
            for reference_name in sorted(parsed_references)
        },
    }
    canonical_yaml = json.dumps(
        canonical_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return ParameterSpecRegistry(
        config_path=config_path.resolve(),
        lut_root=lut_root.resolve(),
        specs=MappingProxyType(specs),
        references=MappingProxyType(references),
        canonical_yaml=canonical_yaml,
        schema_hash=hashlib.sha256(canonical_yaml).hexdigest(),
    )
