use std::{env, path::PathBuf};

fn main() {
    // Use a vendored protoc so contributors don't need it installed.
    let protoc_path = protoc_bin_vendored::protoc_bin_path().expect("vendored protoc not available");
    env::set_var("PROTOC", protoc_path);

    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR"));
    let proto_root = manifest_dir
        .join("../../../../proto")
        .canonicalize()
        .expect("proto/ directory not found");

    let protos = [
        proto_root.join("eigen_internal/v1/kernel_gateway.proto"),
        proto_root.join("eigen_internal/v1/types.proto"),
    ];

    tonic_build::configure()
        .build_server(true)
        .build_client(false)
        .compile(
            &protos
                .iter()
                .map(|p| p.to_string_lossy().to_string())
                .collect::<Vec<_>>(),
            &[proto_root.to_string_lossy().to_string()],
        )
        .expect("failed to compile protos");
}
