# -*- coding: utf-8 -*-
"""Thêm thư mục gốc vào sys.path để tất cả test import src.* được."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
