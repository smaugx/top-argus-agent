# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: xrpc.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='xrpc.proto',
  package='top',
  syntax='proto3',
  serialized_options=_b('\n\033io.grpc.examples.helloworldB\017HelloWorldProtoP\001\242\002\003HLW'),
  serialized_pb=_b('\n\nxrpc.proto\x12\x03top\",\n\x0cxrpc_request\x12\x0e\n\x06\x61\x63tion\x18\x01 \x01(\t\x12\x0c\n\x04\x62ody\x18\x02 \x01(\t\"*\n\nxrpc_reply\x12\x0e\n\x06result\x18\x01 \x01(\t\x12\x0c\n\x04\x62ody\x18\x02 \x01(\t2t\n\x0cxrpc_service\x12,\n\x04\x63\x61ll\x12\x11.top.xrpc_request\x1a\x0f.top.xrpc_reply\"\x00\x12\x36\n\x0ctable_stream\x12\x11.top.xrpc_request\x1a\x0f.top.xrpc_reply\"\x00\x30\x01\x42\x36\n\x1bio.grpc.examples.helloworldB\x0fHelloWorldProtoP\x01\xa2\x02\x03HLWb\x06proto3')
)




_XRPC_REQUEST = _descriptor.Descriptor(
  name='xrpc_request',
  full_name='top.xrpc_request',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='action', full_name='top.xrpc_request.action', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='body', full_name='top.xrpc_request.body', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=19,
  serialized_end=63,
)


_XRPC_REPLY = _descriptor.Descriptor(
  name='xrpc_reply',
  full_name='top.xrpc_reply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='result', full_name='top.xrpc_reply.result', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='body', full_name='top.xrpc_reply.body', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=65,
  serialized_end=107,
)

DESCRIPTOR.message_types_by_name['xrpc_request'] = _XRPC_REQUEST
DESCRIPTOR.message_types_by_name['xrpc_reply'] = _XRPC_REPLY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

xrpc_request = _reflection.GeneratedProtocolMessageType('xrpc_request', (_message.Message,), dict(
  DESCRIPTOR = _XRPC_REQUEST,
  __module__ = 'xrpc_pb2'
  # @@protoc_insertion_point(class_scope:top.xrpc_request)
  ))
_sym_db.RegisterMessage(xrpc_request)

xrpc_reply = _reflection.GeneratedProtocolMessageType('xrpc_reply', (_message.Message,), dict(
  DESCRIPTOR = _XRPC_REPLY,
  __module__ = 'xrpc_pb2'
  # @@protoc_insertion_point(class_scope:top.xrpc_reply)
  ))
_sym_db.RegisterMessage(xrpc_reply)


DESCRIPTOR._options = None

_XRPC_SERVICE = _descriptor.ServiceDescriptor(
  name='xrpc_service',
  full_name='top.xrpc_service',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=109,
  serialized_end=225,
  methods=[
  _descriptor.MethodDescriptor(
    name='call',
    full_name='top.xrpc_service.call',
    index=0,
    containing_service=None,
    input_type=_XRPC_REQUEST,
    output_type=_XRPC_REPLY,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='table_stream',
    full_name='top.xrpc_service.table_stream',
    index=1,
    containing_service=None,
    input_type=_XRPC_REQUEST,
    output_type=_XRPC_REPLY,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_XRPC_SERVICE)

DESCRIPTOR.services_by_name['xrpc_service'] = _XRPC_SERVICE

# @@protoc_insertion_point(module_scope)
