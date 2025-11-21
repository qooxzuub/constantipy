#!/usr/bin/env bash

jq -r '
  to_entries
  | .[] 
  | {
      name: .key, 
      val: .value.value, 
      count: (.value.occurrences | length)
    }
  | [ .count, .name, .val ] 
  | @tsv
' | sort -n
