use std::io::Result;

fn main() -> Result<()> {
    // Compile the proto files for the memvid gRPC service
    // Support both local development (proto in parent) and container builds (proto in manifest_dir)
    let manifest_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    let out_dir = std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap());

    // Try local development layout first (proto in parent directory)
    let proto_dir_parent = manifest_dir.parent().and_then(|p| {
        let candidate = p.join("proto");
        if candidate.exists() {
            Some(candidate)
        } else {
            None
        }
    });

    // Fall back to container layout (proto in manifest directory)
    let proto_dir_local = {
        let candidate = manifest_dir.join("proto");
        if candidate.exists() {
            Some(candidate)
        } else {
            None
        }
    };

    let proto_dir = proto_dir_parent.or(proto_dir_local).unwrap_or_else(|| {
        panic!(
            "proto directory not found. Checked:\n  {}\n  {}",
            manifest_dir
                .parent()
                .map(|p| p.join("proto").display().to_string())
                .unwrap_or_default(),
            manifest_dir.join("proto").display()
        )
    });

    let proto_file = proto_dir.join("memvid/v1/memvid.proto");

    if !proto_file.exists() {
        panic!("Proto file not found at: {}", proto_file.display());
    }

    tonic_build::configure()
        .build_server(true)
        .build_client(true)
        .out_dir(&out_dir)
        .compile_protos(
            &[proto_file.to_str().unwrap()],
            &[proto_dir.to_str().unwrap()],
        )?;

    // Re-run if proto files change
    println!("cargo:rerun-if-changed={}", proto_file.display());
    println!("cargo:rerun-if-changed={}", proto_dir.display());

    Ok(())
}
