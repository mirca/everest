#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
k2sc_cdpp.py
------------

Computes the 6-hr CDPP for all the `K2SC` de-trended light curves.

'''

from __future__ import division, print_function, absolute_import, unicode_literals
import os, sys
import everest
from everest.config import EVEREST_SRC, EVEREST_DAT
from everest.utils import RMS
import k2plr as kplr
from k2plr.config import KPLR_ROOT
import random
import numpy as np
import shutil
import subprocess
import warnings
from urllib.error import HTTPError
from scipy.signal import savgol_filter

for campaign in range(3,8):
  
  print("\nRunning campaign %02d..." % campaign)
  
  # Create file if it doesn't exist
  if not os.path.exists(os.path.join('CDPP', 'k2sc_C%02d.tsv' % campaign)):
    open(os.path.join('CDPP', 'k2sc_C%02d.tsv' % campaign), 'a').close()
  
  # Get all EPIC stars
  stars = list(np.loadtxt(os.path.join(EVEREST_SRC, 'tables', 'C%02d.csv' % campaign), dtype = int))  
  nstars = len(stars)

  # Remove ones we've done
  with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    done = np.loadtxt(os.path.join('CDPP', 'k2sc_C%02d.tsv' % campaign), dtype = float)
  if len(done):
    done = [int(s) for s in done[:,0]]
  stars = list(set(stars) - set(done))
  n = len(done) + 1

  # Open the output file
  with open(os.path.join('CDPP', 'k2sc_C%02d.tsv' % campaign), 'a') as outfile:

    # Loop over all to get the CDPP
    for star in stars:

      # Progress
      sys.stdout.write('\rRunning target %d/%d...' % (n, nstars))
      sys.stdout.flush()
      n += 1
      
      # Get the cdpp
      try:
        s = kplr.K2SC(star)
      except (HTTPError, TypeError, ValueError):
        print("{:>09d} {:>15.3f} {:>15.3f}".format(star, 0, 0), file = outfile)
        continue
      flux = s.pdcflux[~np.isnan(s.pdcflux)]
      rms = RMS(flux / np.median(flux), remove_outliers = True)
      flux_sv2 = flux - savgol_filter(flux, 49, 2) + np.median(flux)
      rms_sv2 = RMS(flux_sv2 / np.nanmedian(flux_sv2), remove_outliers = True)
      print("{:>09d} {:>15.3f} {:>15.3f}".format(star, rms, rms_sv2), file = outfile)
      # Delete the lightcurve on disk
      os.remove(s._file)
      try:
        os.rmdir(os.path.dirname(s._file))
      except:
        # I'm getting an "OSError: [Errno 39] Directory not empty:" error
        # when trying to do this sometimes... But the directory *is* empty.
        # No idea why!
        pass