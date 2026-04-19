meta:
  id: samsung_note_text_object
  endian: le
seq:
  - id: object_base_size
    type: u4
    valid:
      min: 4
  - id: object_base_body
    size: object_base_size - 4
  - id: shape_base_size
    type: u4
    valid:
      min: 4
  - id: shape_base_body
    size: shape_base_size - 4
  - id: shape_text_record_size
    type: u4
    valid:
      min: 17
  - id: shape_text_record
    type: shape_text_record
    size: shape_text_record_size - 4
  - id: trailing_bytes
    size-eos: true
instances:
  shape_text_record_offset:
    value: object_base_size + shape_base_size
  text_common_size_offset:
    value: shape_text_record_offset + shape_text_record.own_data_offset
  text_common_size:
    pos: text_common_size_offset
    type: u4
    if: has_text_common
  text_common_bytes:
    pos: text_common_size_offset + 4
    size: text_common_size
    if: has_text_common and text_common_size <= _io.size - text_common_size_offset - 4
  has_text_common:
    value: shape_text_record.record_type == 7 and (shape_text_record.property_mask & 1) != 0 and text_common_size_offset + 4 <= _io.size
types:
  shape_text_record:
    seq:
      - id: record_type
        type: u2
      - id: own_data_offset
        type: u4
      - id: unknown_06
        size: 3
      - id: property_mask
        type: u4
      - id: remaining
        size-eos: true
