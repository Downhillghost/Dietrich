meta:
  id: samsung_spi
seq:
  - id: header_packet_size
    type: u4le
  - id: header_packet
    type: header_packet
    size: header_packet_size
  - id: image_packet_size
    type: u4le
  - id: image_packet
    type: image_packet
    size: image_packet_size
types:
  header_packet:
    seq:
      - id: tag
        type: u2be
      - id: reserved
        type: u2be
      - id: record_size
        type: u2be
      - id: record_reserved
        type: u2be
      - id: format_family
        type: u4be
      - id: width
        type: u2le
      - id: height
        type: u2le
      - id: texture_width_units
        type: u2be
      - id: fixed_00e0
        type: u2be
    instances:
      texture_width:
        value: texture_width_units * 256
  image_packet:
    seq:
      - id: tag
        type: u2be
      - id: reserved
        type: u2be
      - id: size_hint
        type: u4le
      - id: payload
        size-eos: true
instances:
  image_packet_size_matches_file_size:
    value: image_packet_size == _io.size - 8 - header_packet_size
