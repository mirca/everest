#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
:py:mod:`run.py` - User-facing routines
---------------------------------------

Routines to run :py:mod:`everest` in batch mode on a PBS cluster.

'''

from __future__ import division, print_function, absolute_import, unicode_literals
from . import __version__ as EVEREST_VERSION
from .config import EVEREST_DAT, EVEREST_SRC
from .plot import Plot
from .data import GetK2Stars, GetK2Campaign, GetK2Data, GetK2Planets, GetK2InjectionTestStars
from .compute import Compute
from .utils import ExceptionHook, ExceptionHookPDB, FunctionWrapper
from .pool import Pool
from . import fits
import os
import sys
import traceback
DEF_KWARGS_FILE = os.path.join(EVEREST_DAT, 'kwargs.py')
from k2plr.config import KPLR_ROOT
import subprocess
import numpy as np
import imp
import time

def DownloadCampaign(campaign, queue = 'build', email = None, walltime = 8):
  '''
  Submits a cluster job to the build queue to download all TPFs for a given
  campaign.
  
  :param int campaign: The `K2` campaign to run
  :param str queue: The name of the queue to submit to. Default `build`
  :param str email: The email to send job status notifications to. Default `None`
  :param int walltime: The number of hours to request. Default `8`
  
  '''
  
  # Figure out the subcampaign
  if type(campaign) is int:
    subcampaign = -1
  elif type(campaign) is float:
    x, y = divmod(campaign, 1)
    campaign = int(x)
    subcampaign = round(y * 10)
          
  # Submit the cluster job      
  pbsfile = os.path.join(EVEREST_SRC, 'pbs', 'download.pbs')
  str_w = 'walltime=%d:00:00' % walltime
  str_v = 'EVEREST_DAT=%s,CAMPAIGN=%d,SUBCAMPAIGN=%d' % (EVEREST_DAT, campaign, subcampaign)
  if subcampaign == -1:
    str_name = 'DOWNLOAD_C%02d' % campaign
  else:
    str_name = 'DOWNLOAD_C%02d.%d' % (campaign, subcampaign)
  str_out = os.path.join(EVEREST_DAT, str_name + '.log')
  qsub_args = ['qsub', pbsfile, 
               '-q', queue,
               '-v', str_v, 
               '-o', str_out,
               '-j', 'oe', 
               '-N', str_name,
               '-l', str_w]
  if email is not None: qsub_args.append(['-M', email, '-m', 'ae'])
  # Now we submit the job
  print("Submitting the job...")
  subprocess.call(qsub_args)

def DownloadInjections(queue = 'build', email = None, walltime = 8):
  '''
  Submits a cluster job to the build queue to download all TPFs for a given
  campaign.
  
  :param int campaign: The `K2` campaign to run
  :param str queue: The name of the queue to submit to. Default `build`
  :param str email: The email to send job status notifications to. Default `None`
  :param int walltime: The number of hours to request. Default `8`
  
  '''
          
  # Submit the cluster job      
  pbsfile = os.path.join(EVEREST_SRC, 'pbs', 'downloadinj.pbs')
  str_w = 'walltime=%d:00:00' % walltime
  str_v = 'EVEREST_DAT=%s' % (EVEREST_DAT)
  str_out = os.path.join(EVEREST_DAT, 'DOWNLOAD_INJ.log')
  qsub_args = ['qsub', pbsfile, 
               '-q', queue,
               '-v', str_v, 
               '-o', str_out,
               '-j', 'oe', 
               '-N', 'DOWNLOAD_INJ',
               '-l', str_w]
  if email is not None: qsub_args.append(['-M', email, '-m', 'ae'])
            
  # Now we submit the job
  print("Submitting the job...")
  subprocess.call(qsub_args)

def _Run(EPIC, **kwargs):
  '''
  Wrapper around ``Compute()`` and ``Plot()``.
  
  '''
  
  try:
    data = Compute(EPIC, **kwargs)
    if data is not None:
      Plot(data)
      return True
    else:
      return False
  except:
    print('ERROR detrending EPIC %d:' % EPIC)
    etype, value, tb = sys.exc_info()
    for line in traceback.format_exception_only(etype, value):
      print(line.replace('\n', ''))
    for line in traceback.format_tb(tb):
      print(line.replace('\n', ''))
    return False
    
def RunSingle(EPIC, debug = False, kwargs_file = None):
  '''
  Compute and plot data for a given target.
  
  :param int EPIC: The 9-digit `K2` EPIC number
  :param bool debug: Debug mode? Default `False`. If `True`, enters `pdb` post-mortem when an error is raised
  :param str kwargs_file: The file containing the keyword arguments to pass to :py:func:`everest.compute.Compute`. \
                          Default `~/.everest/kwargs.py`

  
  '''
  
  # Get the kwargs
  if kwargs_file is None:
    kwargs_file = DEF_KWARGS_FILE
  kwargs = imp.load_source("kwargs", kwargs_file).kwargs
  
  # Set up our custom exception handlers
  if debug:
    sys.excepthook = ExceptionHookPDB
  else:
    sys.excepthook = ExceptionHook
  
  # Run
  _Run(EPIC, **kwargs)

def RunInjections(depth = 0.01, mask = False, queue = None,
                  nodes = 5, ppn = 12, walltime = 100, 
                  email = None, 
                  kwargs_file = None):
  '''
  Submits a cluster job to compute and plot data for a sample
  of targets chosen for transit injection tests.
  
  :param float depth: The fractional transit depth to inject. Default `0.01`
  :param bool mask: Mask injected transits? Default `False`.
  :param str queue: The queue to submit to. Default `None` (default queue)
  :param str kwargs_file: The file containing the keyword arguments to pass to :py:func:`everest.compute.Compute`. \
                          Default `~/.everest/kwargs.py`
  :param str email: The email to send job status notifications to. Default `None`
  :param int walltime: The number of hours to request. Default `100`
  :param int nodes: The number of nodes to request. Default `5`
  :param int ppn: The number of processors per node to request. Default `12`
  
  '''
  
  # Submit the cluster job   
  if kwargs_file is None:
    kwargs_file = DEF_KWARGS_FILE
  name = 'inject_%.4f%s' % (depth, ('m' if mask else 'u'))   
  pbsfile = os.path.join(EVEREST_SRC, 'pbs', 'runinjections.pbs')
  str_n = 'nodes=%d:ppn=%d,feature=%dcore' % (nodes, ppn, ppn)
  str_w = 'walltime=%d:00:00' % walltime
  str_v = 'EVEREST_DAT=%s,NODES=%d,MASK=%d,DEPTH=%0.4f,KWARGS_FILE=%s' % (EVEREST_DAT, 
          nodes, int(mask), depth, os.path.abspath(kwargs_file))
  str_out = os.path.join(EVEREST_DAT, '%s.log' % name)
  qsub_args = ['qsub', pbsfile, 
               '-v', str_v, 
               '-o', str_out,
               '-j', 'oe', 
               '-N', name, 
               '-l', str_n,
               '-l', str_w]
  if email is not None: 
    qsub_args.append(['-M', email, '-m', 'ae'])
  if queue is not None:
    qsub_args += ['-q', queue]
  # Now we submit the job
  print("Submitting the job...")
  subprocess.call(qsub_args)

def RunCandidates(nodes = 5, ppn = 12, walltime = 100, queue = None,
                  email = None, 
                  kwargs_file = None):
  '''
  Submits a cluster job to compute and plot data for all targets hosting
  confirmed planets or planet candidates.
  
  :param str queue: The queue to submit to. Default `None` (default queue)
  :param str kwargs_file: The file containing the keyword arguments to pass to :py:func:`everest.compute.Compute`. \
                          Default `~/.everest/kwargs.py`
  :param str email: The email to send job status notifications to. Default `None`
  :param int walltime: The number of hours to request. Default `100`
  :param int nodes: The number of nodes to request. Default `5`
  :param int ppn: The number of processors per node to request. Default `12`
  
  '''
          
  # Submit the cluster job  
  if kwargs_file is None:
    kwargs_file = DEF_KWARGS_FILE    
  pbsfile = os.path.join(EVEREST_SRC, 'pbs', 'runcandidates.pbs')
  str_n = 'nodes=%d:ppn=%d,feature=%dcore' % (nodes, ppn, ppn)
  str_w = 'walltime=%d:00:00' % walltime
  str_v = 'EVEREST_DAT=%s,NODES=%d,KWARGS_FILE=%s' % (EVEREST_DAT, 
          nodes, os.path.abspath(kwargs_file))
  str_out = os.path.join(EVEREST_DAT, 'candidates.log')
  qsub_args = ['qsub', pbsfile, 
               '-v', str_v, 
               '-o', str_out,
               '-j', 'oe', 
               '-N', 'candidates', 
               '-l', str_n,
               '-l', str_w]
  if email is not None: 
    qsub_args.append(['-M', email, '-m', 'ae'])
  if queue is not None:
    qsub_args += ['-q', queue]          
  # Now we submit the job
  print("Submitting the job...")
  subprocess.call(qsub_args)

def RunCampaign(campaign, nodes = 5, ppn = 12, walltime = 100, 
                email = None, queue = None,
                kwargs_file = None):
  '''
  Submits a cluster job to compute and plot data for all targets in a given campaign.
  
  :param campaign: The K2 campaign number. If this is an :py:class:`int`, returns \
                   all targets in that campaign. If a :py:class:`float` in the form \
                   `X.Y`, runs the `Y^th` decile of campaign `X`.
  :param str queue: The queue to submit to. Default `None` (default queue)
  :param str kwargs_file: The file containing the keyword arguments to pass to :py:func:`everest.compute.Compute`. \
                          Default `~/.everest/kwargs.py`
  :param str email: The email to send job status notifications to. Default `None`
  :param int walltime: The number of hours to request. Default `100`
  :param int nodes: The number of nodes to request. Default `5`
  :param int ppn: The number of processors per node to request. Default `12`
  
  '''
  
  # Figure out the subcampaign
  if type(campaign) is int:
    subcampaign = -1
  elif type(campaign) is float:
    x, y = divmod(campaign, 1)
    campaign = int(x)
    subcampaign = round(y * 10)
          
  # Submit the cluster job 
  if kwargs_file is None:
    kwargs_file = DEF_KWARGS_FILE     
  pbsfile = os.path.join(EVEREST_SRC, 'pbs', 'runcampaign.pbs')
  str_n = 'nodes=%d:ppn=%d,feature=%dcore' % (nodes, ppn, ppn)
  str_w = 'walltime=%d:00:00' % walltime
  str_v = 'EVEREST_DAT=%s,NODES=%d,KWARGS_FILE=%s,CAMPAIGN=%d,SUBCAMPAIGN=%d' % (EVEREST_DAT, 
          nodes, os.path.abspath(kwargs_file), campaign, subcampaign)
  if subcampaign == -1:
    str_name = 'C%02d' % campaign
  else:
    str_name = 'C%02d.%d' % (campaign, subcampaign)
  str_out = os.path.join(EVEREST_DAT, str_name + '.log')
  qsub_args = ['qsub', pbsfile, 
               '-v', str_v, 
               '-o', str_out,
               '-j', 'oe', 
               '-N', str_name,
               '-l', str_n,
               '-l', str_w]
  if email is not None: 
    qsub_args.append(['-M', email, '-m', 'ae'])
  if queue is not None:
    qsub_args += ['-q', queue]          
  # Now we submit the job
  print("Submitting the job...")
  subprocess.call(qsub_args)

def RunFITS(campaign, queue = 'build', email = None, walltime = 8):
  '''
  Submits a cluster job to make EVEREST FITS files for a given
  campaign.
  
  :param campaign: The K2 campaign number. If this is an :py:class:`int`, returns \
                   all targets in that campaign. If a :py:class:`float` in the form \
                   `X.Y`, runs the `Y^th` decile of campaign `X`.
  :param str queue: The queue to submit to. Default `build`
  :param str email: The email to send job status notifications to. Default `None`
  :param int walltime: The number of hours to request. Default `8`
  
  '''
  
  # Figure out the subcampaign
  if type(campaign) is int:
    subcampaign = -1
  elif type(campaign) is float:
    x, y = divmod(campaign, 1)
    campaign = int(x)
    subcampaign = round(y * 10)
          
  # Submit the cluster job      
  pbsfile = os.path.join(EVEREST_SRC, 'pbs', 'fits.pbs')
  str_w = 'walltime=%d:00:00' % walltime
  str_v = 'EVEREST_DAT=%s,CAMPAIGN=%d,SUBCAMPAIGN=%d' % (EVEREST_DAT, campaign, subcampaign)
  if subcampaign == -1:
    str_name = 'C%02d' % campaign
  else:
    str_name = 'C%02d.%d' % (campaign, subcampaign)
  str_out = os.path.join(EVEREST_DAT, str_name + '.log')
  qsub_args = ['qsub', pbsfile, 
               '-v', str_v, 
               '-o', str_out,
               '-j', 'oe', 
               '-N', str_name,
               '-l', str_w]
  if queue is not None:
    qsub_args += ['-q', queue]
  if email is not None: qsub_args.append(['-M', email, '-m', 'ae'])
  # Now we submit the job
  print("Submitting the job...")
  subprocess.call(qsub_args)

# ---- PBS routines ---- #

def _RunCandidates(kwargs_file):
  '''
  The actual function that runs all candidates; this must
  be called from ``pbs/runcandidates.pbs``.
  
  '''
  
  # Set up our custom exception handler
  sys.excepthook = ExceptionHook
  
  # Initialize our multiprocessing pool
  with Pool() as pool:

    # Get the kwargs
    kwargs = imp.load_source("kwargs", kwargs_file).kwargs
  
    # Override ``mask_candidates``
    kwargs['mask_candidates'] = True
  
    # Get all the stars
    stars = [int(p.epic_name[5:]) for p in GetK2Planets()]
    new = [int(f[:9]) for f in os.listdir(os.path.join(EVEREST_DAT, 'new')) if f.endswith('.npz')]
    stars = list(set(stars + new))
  
    # Compute and plot
    C = FunctionWrapper(_Run, **kwargs)
    pool.map(C, stars)

def _RunInjections(kwargs_file, depth, mask):
  '''
  The actual function that runs injection tests; this must
  be called from ``pbs/runinjections.pbs``.
  
  '''
  
  # Set up our custom exception handler
  sys.excepthook = ExceptionHook
  
  # Initialize our multiprocessing pool
  with Pool() as pool:

    # Get the kwargs
    kwargs = imp.load_source("kwargs", kwargs_file).kwargs
    
    # Get all the stars
    stars = [int(s) for s in GetK2InjectionTestStars()]
    
    # Override ``inject`` and ``run_name``
    kwargs['inject'] = dict(t0 = 0., 
                            per = 3 + 7 * np.random.random(),   # Random periods between 3 and 10 days
                            depth = depth, 
                            dur = 0.1,
                            mask = mask)
    kwargs['run_name'] = 'inject_%.4f%s' % (depth, ('m' if mask else 'u'))

    # Compute and plot
    C = FunctionWrapper(_Run, **kwargs)
    pool.map(C, stars)

def _RunCampaign(campaign, subcampaign, kwargs_file):
  '''
  The actual function that runs a given campaign; this must
  be called from ``pbs/runcampaign.pbs``.
  
  '''
  
  # Set up our custom exception handler
  sys.excepthook = ExceptionHook
  
  # Initialize our multiprocessing pool
  with Pool() as pool:

    # Get the kwargs
    kwargs = imp.load_source("kwargs", kwargs_file).kwargs
        
    # Are we doing a subcampaign?
    if subcampaign != -1:
      campaign = campaign + 0.1 * subcampaign
    
    # Get all the stars
    stars = GetK2Campaign(campaign)
  
    # Compute and plot
    C = FunctionWrapper(_Run, **kwargs)
    pool.map(C, stars)

def _DownloadCampaign(campaign, subcampaign):
  '''
  Download all stars from a given campaign. This is
  called from ``pbs/download.pbs``
  
  '''

  # Are we doing a subcampaign?
  if subcampaign != -1:
    campaign = campaign + 0.1 * subcampaign

  # Get all star IDs for this campaign
  stars = GetK2Campaign(campaign)
  nstars = len(stars)
  
  # Download the TPF data for each one
  for i, EPIC in enumerate(stars):
    print("Downloading data for EPIC %d (%d/%d)..." % (EPIC, i + 1, nstars))
    if not os.path.exists(os.path.join(KPLR_ROOT, 'data', 'everest', 
                          str(EPIC), str(EPIC) + '.npz')):
      try:
        GetK2Data(EPIC, calculate_contamination = False)
      except KeyboardInterrupt:
        sys.exit()
      except:
        # Some targets could be corrupted
        print("ERROR downloading EPIC %d." % EPIC)
        continue  

def _DownloadInjections():
  '''
  Download all stars for the injection tests. This is
  called from ``downloadinj.pbs``
  
  '''
  
  # Get all star IDs
  stars = [int(s) for s in GetK2InjectionTestStars()]
  nstars = len(stars)
  
  # Download the TPF data for each one
  for i, EPIC in enumerate(stars):
    print("Downloading data for EPIC %d (%d/%d)..." % (EPIC, i + 1, nstars))
    if not os.path.exists(os.path.join(KPLR_ROOT, 'data', 'everest', 
                          str(EPIC), str(EPIC) + '.npz')):
      try:
        GetK2Data(EPIC)
      except:
        # Some targets could be corrupted
        continue  

def _MakeFITS(campaign, subcampaign):
  '''
  Generates EVEREST FITS files for all stars in a given campaign. This is
  called from ``pbs/fits.pbs``
  
  '''
  
  # Are we doing a subcampaign?
  if subcampaign != -1:
    campaign = campaign + 0.1 * subcampaign
  
  # Get all star IDs for this campaign
  stars = GetK2Campaign(campaign)
  nstars = len(stars)
  
  for i, EPIC in enumerate(stars):
    print("Processing EPIC %d (%d/%d)..." % (EPIC, i + 1, nstars))
    fits.MakeFITS(EPIC, campaign = campaign)

def _MoveFigures(campaign, ext = 'jpg'):
  '''
  
  '''
  
  # Get all star IDs for this campaign
  stars = GetK2Campaign(campaign)
  nstars = len(stars)
  
  for i, EPIC in enumerate(stars):
    print("Processing EPIC %d (%d/%d)..." % (EPIC, i + 1, nstars))
    inpath = os.path.join(EVEREST_DAT, 'output', 'C%02d' % campaign, EPIC, 'default')
    outpath = os.path.join(EVEREST_DAT, 'fits', 'c%02d' % campaign, 
                          ('%09d' % EPIC)[:4] + '00000')
    if not os.path.exists(outpath):
      os.makedirs(outpath)
    prefix = 'hlsp_everest_k2_llc_%d-c%02d_kepler_v%s' % (EPIC, campaign, EVEREST_VERSION)
    
    for inimg, outimg in zip(['aper', 'contamination', 'outliers', 'acor', 'scatter', 'detrended'],
                             ['aper', 'contam', 'outliers', 'acor', 'crossval', 'detrended']):
      
      import pdb; pdb.set_trace()
      
      os.rename(os.path.join(inpath, '%s.%s' % (inimg, ext)), 
                os.path.join(outpath, '%s_%s.%s' % (prefix, outimg, ext)))