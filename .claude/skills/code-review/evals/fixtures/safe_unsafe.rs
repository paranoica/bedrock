// bounds-check the requested length against the real allocation; stay in safe Rust
fn read_slice(buf: &[u8], len: usize) -> Vec<u8> {
    let end = len.min(buf.len());
    buf[..end].to_vec()
}
