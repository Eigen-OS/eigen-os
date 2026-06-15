"""Generated protocol buffer code for eigen.internal.v1.NeuroSymbolicService."""

from __future__ import annotations

from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()


_file_proto = _descriptor_pb2.FileDescriptorProto()
_file_proto.name = "eigen/internal/v1/neuro_symbolic_service.proto"
_file_proto.package = "eigen.internal.v1"
_file_proto.syntax = "proto3"


def _add_message(name: str):
    return _file_proto.message_type.add(name=name)


def _add_field(message, *, name: str, number: int, label: int, type_: int, type_name: str = ""):
    field = message.field.add()
    field.name = name
    field.number = number
    field.label = label
    field.type = type_
    if type_name:
        field.type_name = type_name
    return field


def _add_enum(name: str, values: list[tuple[str, int]]):
    enum = _file_proto.enum_type.add(name=name)
    for value_name, value_number in values:
        enum.value.add(name=value_name, number=value_number)
    return enum


_add_message("NeuroSymbolicContractEnvelope")
_add_field(
    _file_proto.message_type[0],
    name="contract_version",
    number=1,
    label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
    type_=_descriptor.FieldDescriptor.TYPE_STRING,
)

_add_message("NeuroSymbolicRequestContext")
for idx, field_name in enumerate(
    [
        "request_id",
        "tenant_id",
        "project_id",
        "feature_schema_version",
        "policy_snapshot_version",
        "trace_id",
        "traceparent",
    ],
    start=1,
):
    _add_field(
        _file_proto.message_type[1],
        name=field_name,
        number=idx,
        label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
        type_=_descriptor.FieldDescriptor.TYPE_STRING,
    )

_add_message("ScoreCompilationPlanRequest")
_add_field(
    _file_proto.message_type[2],
    name="envelope",
    number=1,
    label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
    type_=_descriptor.FieldDescriptor.TYPE_MESSAGE,
    type_name=".eigen.internal.v1.NeuroSymbolicContractEnvelope",
)
_add_field(
    _file_proto.message_type[2],
    name="context",
    number=2,
    label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
    type_=_descriptor.FieldDescriptor.TYPE_MESSAGE,
    type_name=".eigen.internal.v1.NeuroSymbolicRequestContext",
)
_add_field(
    _file_proto.message_type[2],
    name="feature_vector",
    number=3,
    label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
    type_=_descriptor.FieldDescriptor.TYPE_BYTES,
)
_add_field(
    _file_proto.message_type[2],
    name="feature_digest_sha256",
    number=4,
    label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
    type_=_descriptor.FieldDescriptor.TYPE_STRING,
)
_add_field(
    _file_proto.message_type[2],
    name="deterministic_seed",
    number=5,
    label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
    type_=_descriptor.FieldDescriptor.TYPE_UINT64,
)
_add_field(
    _file_proto.message_type[2],
    name="model_hint",
    number=6,
    label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
    type_=_descriptor.FieldDescriptor.TYPE_STRING,
)

_add_enum(
    "AdvisoryDecision",
    [
        ("ADVISORY_DECISION_UNSPECIFIED", 0),
        ("ADVISORY_DECISION_ACCEPT", 1),
        ("ADVISORY_DECISION_REVIEW", 2),
        ("ADVISORY_DECISION_REJECT", 3),
    ],
)

_add_message("ScoreCompilationPlanResponse")
for number, field_name, field_type in [
    (1, "contract_version", _descriptor.FieldDescriptor.TYPE_STRING),
    (2, "request_id", _descriptor.FieldDescriptor.TYPE_STRING),
    (3, "tenant_id", _descriptor.FieldDescriptor.TYPE_STRING),
    (4, "project_id", _descriptor.FieldDescriptor.TYPE_STRING),
    (5, "feature_schema_version", _descriptor.FieldDescriptor.TYPE_STRING),
    (6, "policy_snapshot_version", _descriptor.FieldDescriptor.TYPE_STRING),
    (7, "model_version", _descriptor.FieldDescriptor.TYPE_STRING),
    (8, "decision", _descriptor.FieldDescriptor.TYPE_ENUM),
    (9, "score", _descriptor.FieldDescriptor.TYPE_DOUBLE),
    (10, "confidence", _descriptor.FieldDescriptor.TYPE_DOUBLE),
    (11, "explanation_ref", _descriptor.FieldDescriptor.TYPE_STRING),
    (12, "replay_digest", _descriptor.FieldDescriptor.TYPE_STRING),
    (13, "deterministic_compatible", _descriptor.FieldDescriptor.TYPE_BOOL),
]:
    _add_field(
        _file_proto.message_type[3],
        name=field_name,
        number=number,
        label=_descriptor.FieldDescriptor.LABEL_OPTIONAL,
        type_=field_type,
        type_name=".eigen.internal.v1.AdvisoryDecision" if field_name == "decision" else "",
    )

service = _file_proto.service.add(name="NeuroSymbolicService")
method = service.method.add(name="ScoreCompilationPlan")
method.input_type = ".eigen.internal.v1.ScoreCompilationPlanRequest"
method.output_type = ".eigen.internal.v1.ScoreCompilationPlanResponse"

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(_file_proto.SerializeToString())

NeuroSymbolicContractEnvelope = _reflection.GeneratedProtocolMessageType(
    "NeuroSymbolicContractEnvelope",
    (_message.Message,),
    {"DESCRIPTOR": DESCRIPTOR.message_types_by_name["NeuroSymbolicContractEnvelope"], "__module__": __name__},
)
_sym_db.RegisterMessage(NeuroSymbolicContractEnvelope)

NeuroSymbolicRequestContext = _reflection.GeneratedProtocolMessageType(
    "NeuroSymbolicRequestContext",
    (_message.Message,),
    {"DESCRIPTOR": DESCRIPTOR.message_types_by_name["NeuroSymbolicRequestContext"], "__module__": __name__},
)
_sym_db.RegisterMessage(NeuroSymbolicRequestContext)

ScoreCompilationPlanRequest = _reflection.GeneratedProtocolMessageType(
    "ScoreCompilationPlanRequest",
    (_message.Message,),
    {"DESCRIPTOR": DESCRIPTOR.message_types_by_name["ScoreCompilationPlanRequest"], "__module__": __name__},
)
_sym_db.RegisterMessage(ScoreCompilationPlanRequest)

AdvisoryDecision = DESCRIPTOR.enum_types_by_name["AdvisoryDecision"]
ADVISORY_DECISION_UNSPECIFIED = 0
ADVISORY_DECISION_ACCEPT = 1
ADVISORY_DECISION_REVIEW = 2
ADVISORY_DECISION_REJECT = 3

ScoreCompilationPlanResponse = _reflection.GeneratedProtocolMessageType(
    "ScoreCompilationPlanResponse",
    (_message.Message,),
    {"DESCRIPTOR": DESCRIPTOR.message_types_by_name["ScoreCompilationPlanResponse"], "__module__": __name__},
)
_sym_db.RegisterMessage(ScoreCompilationPlanResponse)


__all__ = [
    "ADVISORY_DECISION_ACCEPT",
    "ADVISORY_DECISION_REJECT",
    "ADVISORY_DECISION_REVIEW",
    "ADVISORY_DECISION_UNSPECIFIED",
    "AdvisoryDecision",
    "DESCRIPTOR",
    "NeuroSymbolicContractEnvelope",
    "NeuroSymbolicRequestContext",
    "ScoreCompilationPlanRequest",
    "ScoreCompilationPlanResponse",
]
