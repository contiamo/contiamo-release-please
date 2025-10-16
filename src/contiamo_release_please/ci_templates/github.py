"""GitHub Actions workflow templates for Contiamo Release Please."""

GITHUB_WORKFLOW_TEMPLATE = """name: Release Please

on:
  push:
    branches:
      - main

jobs:
  contiamo-release-please:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Required: Fetch all history for commit analysis

      - uses: contiamo/contiamo-release-please@main
        id: release
        with:
          token: ${{ secrets.CONTIAMO_CI_TOKEN }}
"""
