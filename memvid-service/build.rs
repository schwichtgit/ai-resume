use std::io::Result;

fn main() -> Result<()> {
    // Compile the proto files for the memvid gRPC service
    // Output goes to OUT_DIR (target/debug/build/...) by default
    tonic_build::configure()
        .build_server(true)
        .build_client(true) // Need client for healthcheck binary
        .compile_protos(
            &["proto/memvid/v1/memvid.proto"],
            &["proto"],
        )?;

    // Re-run if proto files change
    println!("cargo:rerun-if-changed=proto/memvid/v1/memvid.proto");

    Ok(())
}
