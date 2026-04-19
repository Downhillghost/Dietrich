meta:
  id: samsung_page_id_info
  endian: le
seq:
  - id: file_hash
    size: 32
  - id: num_entries
    type: u2
  - id: entries
    type: entry
    repeat: expr
    repeat-expr: num_entries
types:
  utf16_string_u16:
    seq:
      - id: len
        type: u2
      - id: value
        type: str
        size: len * 2
        encoding: UTF-16LE
        if: len != 65535
  entry:
    seq:
      - id: page_id
        type: utf16_string_u16
      - id: page_hash
        size: 32
