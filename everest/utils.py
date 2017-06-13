#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
:py:mod:`utils.py` - General utils
----------------------------------

General utility functions called from various parts of the code.

'''

from __future__ import division, print_function, absolute_import, unicode_literals
import numpy as np
import os, sys, traceback, pdb
import logging
from matplotlib.ticker import FuncFormatter
log = logging.getLogger(__name__)

#: Marks a pixel into which a row was collapsed. Note that ``AP_COLLAPSED_PIXEL & 1 = 1``
AP_COLLAPSED_PIXEL = 9
#: Marks a saturated pixel that was masked out.  Note that ``AP_SATURATED_PIXEL & 1 = 0``
AP_SATURATED_PIXEL = 8

class FunctionWrapper(object):
  '''
  A simple function wrapper class. Stores :py:obj:`args` and :py:obj:`kwargs` and
  allows an arbitrary function to be called with a single parameter :py:obj:`x`
  
  '''
  
  def __init__(self, f, *args, **kwargs):
    '''
    
    '''
    
    self.f = f
    self.args = args
    self.kwargs = kwargs
  
  def __call__(self, x):
    '''
    
    '''
    
    return self.f(x, *self.args, **self.kwargs)

class NoPILFilter(logging.Filter):
  '''
  The :py:obj:`PIL` image module has a nasty habit of sending all sorts of 
  unintelligible information to the logger. We filter that out here.
  
  '''
  
  def filter(self, record):
    return not record.name == 'PIL.PngImagePlugin'

def InitLog(file_name = None, log_level = logging.DEBUG, 
            screen_level = logging.CRITICAL, pdb = False):
  '''
  A little routine to initialize the logging functionality.
  
  :param str file_name: The name of the file to log to. Default :py:obj:`None` (set internally by :py:mod:`everest`)
  :param int log_level: The file logging level (0-50). Default 10 (debug)
  :param int screen_level: The screen logging level (0-50). Default 50 (critical)
  
  '''
  
  # Initialize the logging
  root = logging.getLogger()
  root.handlers = []
  root.setLevel(logging.DEBUG)

  # File handler
  if file_name is not None:
    if not os.path.exists(os.path.dirname(file_name)):
      os.makedirs(os.path.dirname(file_name))
    fh = logging.FileHandler(file_name)
    fh.setLevel(log_level)
    fh_formatter = logging.Formatter("%(asctime)s %(levelname)-5s [%(name)s.%(funcName)s()]: %(message)s", datefmt="%m/%d/%y %H:%M:%S")
    fh.setFormatter(fh_formatter)
    fh.addFilter(NoPILFilter())    
    root.addHandler(fh)

  # Screen handler
  sh = logging.StreamHandler(sys.stdout)
  if pdb:
    sh.setLevel(logging.DEBUG)
  else:
    sh.setLevel(screen_level)
  sh_formatter = logging.Formatter("%(levelname)-5s [%(name)s.%(funcName)s()]: %(message)s")
  sh.setFormatter(sh_formatter)
  sh.addFilter(NoPILFilter()) 
  root.addHandler(sh)
  
  # Set exception hook
  if pdb:
    sys.excepthook = ExceptionHookPDB
  else:
    sys.excepthook = ExceptionHook
      
def ExceptionHook(exctype, value, tb):
  '''
  A custom exception handler that logs errors to file.
  
  '''
  
  for line in traceback.format_exception_only(exctype, value):
    log.error(line.replace('\n', ''))
  for line in traceback.format_tb(tb):
    log.error(line.replace('\n', ''))
  sys.__excepthook__(exctype, value, tb)

def ExceptionHookPDB(exctype, value, tb):
  '''
  A custom exception handler, with :py:obj:`pdb` post-mortem for debugging.
  
  '''
  
  for line in traceback.format_exception_only(exctype, value):
    log.error(line.replace('\n', ''))
  for line in traceback.format_tb(tb):
    log.error(line.replace('\n', ''))
  sys.__excepthook__(exctype, value, tb)
  pdb.pm()

def _float(s):
  '''
  A silly but useful wrapper around :py:obj:`float()` that returns :py:obj:`NaN` on error
  
  :param s: The object to be converted to a float
  
  '''
  
  try:
    res = float(s)
  except:
    res = np.nan
  return res

def sort_like(l, col1, col2):
  '''
  Sorts the list :py:obj:`l` by comparing :py:obj:`col2` to :py:obj:`col1`. Specifically,
  finds the indices :py:obj:`i` such that ``col2[i] = col1`` and returns ``l[i]``. This is
  useful when comparing the CDPP values of catalogs generated by different pipelines. The
  target IDs are all the same, but won't necessarily be in the same order. This allows
  :py:obj:`everest` to sort the CDPP arrays so that the targets match.
  
  :param array_like l: The list or array to sort
  :param array_like col1: A list or array (same length as :py:obj:`l`)
  :param array_like col2: A second list or array containing the same elements as :py:obj:`col1` but in a different order
  
  '''
  
  s = np.zeros_like(col1) * np.nan
  for i, c in enumerate(col1):
    j = np.argmax(col2 == c)
    if j == 0:
      if col2[0] != c:
        continue
    s[i] = l[j]
  return s

class DataContainer(object):
  '''
  A generic data container. Nothing fancy here.
  
  '''
  
  def __init__(self):
    '''
    
    '''
    
    self.ID = None
    self.campaign = None
    self.cadn = None
    self.time = None
    self.fpix = None
    self.fpix_err = None
    self.nanmask = None
    self.badmask = None
    self.aperture = None
    self.aperture_name = None
    self.apertures = None
    self.quality = None
    self.Xpos = None
    self.Ypos = None
    self.mag = None
    self.pixel_images = None
    self.nearby = None
    self.hires = None
    self.saturated = None
    self.meta = None

class Formatter(object):
  '''
  Custom function formatters for displaying ticks on plots.
  
  '''
  
  #: Integer formatter for a flux axis
  Flux = FuncFormatter(lambda x, p : '%6d' % x)
  #: Integer formatter for a CDPP axis
  CDPP = FuncFormatter(lambda x, p : '%3d' % x)
  #: Floating point formatter for a CDPP axis (1 digit after decimal)
  CDPP1F = FuncFormatter(lambda x, p : '%.1f' % x)
  #: Floating point formatter for a CDPP axis (2 digits after decimal)
  CDPP2F = FuncFormatter(lambda x, p : '%.2f' % x)
  #: Integer formatter for chunk number
  Chunk = FuncFormatter(lambda x, p : '%2d' % x)
  
def prange(x):
  '''
  Progress bar range with `tqdm`
  '''
  
  try:
    root = logging.getLogger()
    if len(root.handlers):
      for h in root.handlers:
        if (type(h) is logging.StreamHandler) and (h.level != logging.CRITICAL):
          from tqdm import tqdm
          return tqdm(range(x))
      return range(x)
    else:
      from tqdm import tqdm
      return tqdm(range(x))
  except ImportError:
    return range(x)