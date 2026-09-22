use std::{env, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let protoc_path = protoc_bin_vendored::protoc_bin_path()?;
    unsafe {
        env::set_var("PROTOC", protoc_path);
    }

    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR")?);
    let proto_root = manifest_dir.join("../../../../proto").canonicalize()?;
    let protos = [
        proto_root.join("eigen/api/v1/types.proto"),
        proto_root.join("eigen/api/v1/job_service.proto"),
    ];
    let proto_paths: Vec<_> = protos.iter().map(|p| p.to_string_lossy().to_string()).collect();
    let proto_root_str = proto_root.to_string_lossy().to_string();

    tonic_prost_build::configure()
        .build_client(true)
        .build_server(true)
        .compile_protos(&proto_paths, &[proto_root_str])?;

    Ok(())
}
