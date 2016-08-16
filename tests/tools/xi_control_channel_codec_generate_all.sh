# c
../../../xi_client_c/src/import/protobuf-c/compiler/protoc-c-macos --c_out=../../../xi_client_c/src/tests/tools/xi_libxively_driver xi_control_channel_protocol.proto

# py
protoc --python_out=../tools xi_control_channel_protocol.proto