// `len` is attacker-controlled (e.g. a length prefix from the wire).
// from_raw_parts with a length larger than the allocation = OOB read (UB).
fn read_slice(buf: &[u8], len: usize) -> Vec<u8> {
    let s = unsafe { std::slice::from_raw_parts(buf.as_ptr(), len) };
    s.to_vec()
}
