#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
(
  cd "$SCRIPT_DIR/vcr_cassettes"
  ls -Q ./*.yaml | grep -v test_info_cli.yaml | xargs rm
  cd data
  rm ./* 
)
