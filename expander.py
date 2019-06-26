#!/usr/bin/python

#expander.py

import os
import re
import sys
import shutil
import argparse
import subprocess
import shlex      #shell tokenizer
import time       #for sleep
import pathlib
import matplotlib.pyplot as plt
#Custom imports
import utils
import exec_score


def get_imgs( directory ):
  img_names = []

  if not directory.suffix:
    for l in os.listdir( directory ):
      l = l.strip().split('.')
      if len( l[0] ) > 0 and l[0][0] == '#':
        continue
      if len( l[0] ) == 0:
        continue
      img_names.append(l[0])
  elif directory.suffix == '.txt':
    with open( directory ) as d:
      for l in d:
        l = l.strip().split('.')
        if len(l[0]) == 0 or l[0][0] == '#':
          continue
        img_names.append(l[0])

  return img_names

def create_subtrack_files( img_names, args ):
  for i in img_names:
    with open( args.truth ) as t:
      #create sub-truth files
      with open( 'truth_' + i + ".csv", 'w' ) as o:
        count = 0
        for l in t:
          #find lines associated with the image
          l = l.strip().split(',')
          name = (l[1].split('.'))[0]
          if name == i:
            l[0] = count
            l[2] = 0
            o.write( utils.ltos_csv(l) + "\n" )#'x'.join(y) adds list y to the end of string x
            count += 1

    with open( args.computed ) as c:
    #create sub-computed files
      with open( 'computed_' + i + ".csv", 'w' ) as o:
        count = 0
        for l in c:
          #find lines associated with the image
          l = l.strip().split(',')
          name = (l[1].split('.'))[0]
          if name == i:
            l[0] = count
            l[2] = 0
            o.write( utils.ltos_csv(l) + "\n" )#'x'.join(y) adds list y to the end of string x
            count += 1

  return None

def move_subtrack_files( img_names, args ):
  
  cwd = os.getcwd()
  for i in img_names:
    #truth
    tname = "truth_"+i+".csv"
    src = cwd + '/' + tname
    dst = cwd + '/' + i + '/' + tname
    os.rename( src, dst )
    #computed
    cname = "computed_"+i+".csv"
    src = cwd + '/' + cname
    dst = cwd + '/' + i + '/' + cname
    os.rename( src, dst )

  return None

def make_dir_tree( img_names, newdir ):
  if os.path.exists( newdir ):
    #if not shutil.rmtree.avoids_symlink_attacks:
    #  print( 'You are vulnerable to symlink attacks, please upgrade python or remove the output directory manualy.' )
    #  sys.exit( 0 )
    shutil.rmtree( newdir )

  os.mkdir( newdir )
  os.chdir( newdir )
  for i in img_names:
    os.mkdir( i )
  os.mkdir( 'all ' )
  os.mkdir( 'results' )
  os.chdir( '..' )

  return None

def copy_vitals( args ):
  shutil.copyfile(   args.script, args.output /        args.script.name)
  shutil.copyfile(    args.truth, args.output /         args.truth.name)
  shutil.copyfile( args.computed, args.output /      args.computed.name)
  shutil.copyfile(    args.truth, args.output / 'all' /    'truth_all.csv')
  shutil.copyfile( args.computed, args.output / 'all' / 'computed_all.csv')
  return None

def print_human_results( score, roc, destination, wipe=False ):
  #Define a variable for the amount of data printed?
  #Make sure to append, or wipe clean
  #Takes full directory-like objects
  if wipe and os.path.exists( destination ):
    os.remove( destination )

  #Parentheticals are group(1) of re.search(l)
  rex_PD    = re.compile(      'Detection-Pd: (.*)' )
  rex_FA    = re.compile(      'Detection-FA: (.*)' )
  rex_PFA   = re.compile(     'Detection-PFA: (.*)' )
  rex_TrDet = re.compile(   'n-gt-detections: (.*)' )
  rex_CoDet = re.compile( 'n-comp-detections: (.*)' )

  with open( score ) as s:
    for l in s:
      if rex_TrDet.search(l):
        n_detTrue = int(rex_TrDet.search(l).group(1))
      if rex_CoDet.search(l):
        n_detComp = rex_CoDet.search(l).group(1)

      if rex_PD.search(l):
        p_TP = float(rex_PD.search(l).group(1))
      if rex_PFA.search(l):
        p_FP = float(rex_PFA.search(l).group(1))
      #if rex_PTN.search(l):
      #if rex_PFN.search(l):
      
      if rex_FA.search(l):
        n_FA = int(l[16:])

  with open( roc ) as r:
    l = r.read(256).split(';')
    n_TP = l[4][5:]
    n_FP = l[5][5:]
    n_TN = l[6][5:]
    n_FN = l[7][5:]

  with open( destination, 'a' ) as d:
    d.write( '\n' + '-'*40 + '\n' )
    d.write('Data for ' + score.parts[-2] + ':\n' )
    d.write( f'{"  # Computed Detections ":=<30}> {n_detComp:<10}' + '\n')
    d.write( f'{"  # True Detections ":=<30}> {n_detTrue:<10}' + '\n')
    d.write('\n')
    d.write( f'{"  # True  Positives (TP) ":=<30}> {n_TP:<10}' + '\n')
    d.write( f'{"  # False Positives (FP) ":=<30}> {n_FP:<10}' + '\n')
    d.write( f'{"  # True  Negatives (TN) ":=<30}> {n_TN:<10}' + '\n')
    d.write( f'{"  # False Negatives (FN) ":=<30}> {n_FN:<10}' + '\n')
    #d.write( f'{"  # False Positives ":=<30}> {n_FA:<10}' + '\n' )
    d.write('\n')
    d.write( f'{"  P {True Positive} ":=<30}> {p_TP:<10.5f}' + '\n' )
    d.write( f'{"  P {False Positive} ":=<30}> {p_FP:<10.5f}' + '\n' )
      #print("none")
  return None

def make_confidence_name_table( computed ):
  table = []
  #confidence to #, or to coordinates?
  with open( computed ) as c:
    for l in c:
      l = l.strip().split(',')
      if len(l[0]) > 0 and l[0][0] == '#':
        continue
      if len(l[0]) == 0:
        continue
      entry = [(float(l[10]), l[0])]
      table += entry
  
  return table

def make_result_csv( score, roc, destination, dictionary=None, wipe=False ):
  if wipe and os.path.exists( destination ):
    os.remove( destination )

  table = []
  #Image, Name, Confidence, T, F, ACCTP, ACCFP, ACCTN, ACCFN, Precision, Recall

  with open(roc) as r:
    previous = [None] * 11
    for l in r:
      l = l.strip().split(';')
      conf = float(l[0][16:])

      #TODO: convert to enumerated?  dictionary-like?
      entry = [None] * 11
      entry[ 0] = score.parts[-2]
      #entry += [conf]
      entry[ 2] = conf
      entry[ 3] = 0
      entry[ 4] = 0
      entry[ 5] = int(l[4][5:])
      entry[ 6] = int(l[5][5:])
      entry[ 7] = int(l[6][5:])
      entry[ 8] = int(l[7][5:])


      if not previous[0]:
      #Check if TP, FP, etc.
        d_truth = 0
        d_false = 0
      else:
        d_truth = previous[ 5] - entry[ 5]
        d_false = previous[ 6] - entry[ 6]
      while d_truth > 0 or d_false > 0: #or tndiff > 0 or fndiff > 0:
        tmp = entry.copy()
        if d_truth > 0:  #true
          tmp [ 3]  = 1
          tmp [ 5] += d_truth
          tmp [ 8] -= d_truth #decriment FN counter=
          d_truth  -= 1
        elif d_false > 0: #false
          tmp [ 4]  = 1
          tmp [ 6] += d_false
          tmp [ 7] -= d_false #decriment TN counter
          #tmp [7] -= 1
          d_false  -= 1
        table += [tmp]
      previous = entry.copy()

    table = table[::-1]
    #Match the conf levels to the annotation name. Picks largest that is < conf
    #It would be fastest to sort the dictionary list then do a 1:1 match.  No double loop needed
    if dictionary:
        for e in table:
          idx = 0
          best = (0,0)
          for i in range(len(dictionary)):
            if dictionary[i][0] < e[2]:
              if dictionary[i][0] > best[0]:
                best = dictionary[i]
                idx = i
          e[1] = best[1]
          e[2] = best[0]
          del dictionary[idx]
  #  for i in table:
  #    print(i)
  #  print(' Table Len: ' + str(len(table)))
  #  print(' Unused Dict (' + str(len(dictionary)) + '): ')
  #  for i in dictionary:
  #    print(i)
  #  print("\n\n\n")
  return table

def update_tfpn( data, negatives ): #update true and false pos and neg, idk what else to call this function.
  TP = 0
  FP = 0
  TN = negatives[0]
  FN = negatives[1]
  for i in data:
    if i[3]:
      TP += 1
      FN -= 1
    elif i[4]:
      FP += 1  
      TN -= 1
    i[ 5] = TP  #ACC TP
    i[ 6] = FP  #ACC FP
    i[ 7] = TN   #TN
    i[ 8] = FN   #FN
    i[ 9] = TP / (TP+FP)#Precision
    i[10] = TP / (TP+FN)#Recall
  return data

def combine_result_csv( data, negatives ):
  tupledata = []
  for i in data:
    tupledata += [( i[2], i )]
  tupledata.sort()
  tupledata = tupledata[::-1]
  
  newdat = []
  for i in tupledata:
    newdat += [i[1]]

  newdat = update_tfpn( newdat, negatives )

  return newdat

def print_csv( data, dest ):
  print('Writing to: ' + str(dest))
  with open(dest, 'w') as d:
    for i in data:
      writ = ''
      for j in i:
        writ += str(j)
        writ += ','
      writ = writ[:-1] + '\n'
      d.write(writ)
  return None

def plot_pvr( data, dest=None ):
  """ 
      plot_pvr( data: , dest:pathlib.PurePath )
  """
  xs = []
  ys = []
  n = []

  for i in data:
    xs += [i[ 9]]
    ys += [i[10]]
    n += [(i[9],i[10])]
  plt.plot(xs,ys)
  #plt.plot(n,'rx')
  plt.xlabel('Precision')
  plt.ylabel('Recall')
  plt.axis([1.0,0.9,0.0,1.0])
  if dest:
    plt.savefig(dest)
  else:
    plt.show()
  return None

def get_results( img_names, args ):
  print(args.res_file)
  roc_path = args.output / 'all' / 'output_roc.txt'
  out_path = args.output / 'all' / 'output_score_tracks.txt'
  com_path = args.output / 'all' / 'computed_all.csv'
  hum_path = args.output / 'results' / args.res_file
  csv_path = args.output / 'results' / args.res_csv

  #Do 'all' first
  print_human_results( out_path, roc_path, hum_path, True )
      #1: get human-readable data and print to args.res_file=

  data = []
  for i in img_names:
    roc_path = args.output / i / 'output_roc.txt'
    out_path = args.output / i / 'output_score_tracks.txt'
    com_path = args.output / i / ('computed_' + i + '.csv')
    print_human_results( out_path, roc_path, hum_path )
    dictionary = make_confidence_name_table( com_path )
    data += make_result_csv( out_path, roc_path, csv_path, dictionary )

  roc_path = args.output / 'all' / 'output_roc.txt'
  out_path = args.output / 'all' / 'output_score_tracks.txt'
  com_path = args.output / 'all' / ('computed_all.csv')
  print_human_results( out_path, roc_path, hum_path )
  dictionary = make_confidence_name_table( com_path )
  tmp = make_result_csv( out_path, roc_path, csv_path, dictionary )

  total_TN = tmp[0][7]
  total_FN = tmp[0][8]
  #Alter negatives based on the first entry:
  if tmp[3]:
    total_FN += 1
  elif tmp[4]:
    total_TN += 1

  data = combine_result_csv( data, (total_TN, total_FN) )
  header = ['Image Name','Annotation Name','Confidence Score','True','False','# True Positives','# False Positives','# True Negatives','# False Negatives','Precision','Recall']
  types = ['str','str','float','bool','bool','int','int','int','int','float','float']
  pretty_data = [header] + [types] + data
  #for i in data:
  #  print(i)

  #TODO: rename the file for csv
  print_csv( pretty_data, args.results / 'precr.csv' )
  plot_pvr( data, args.results / 'PvR_graph.svg' )

  return None

if __name__ == "__main__":
  parser = argparse.ArgumentParser( description = 'Creates scoring directories by the image' )

  print('\n')

  # Inputs
  parser.add_argument( '-truth', default=None,
             help='Input filename for groundtruth file.' )
  parser.add_argument( '-computed', default=None,
             help='Input filename for computed tracks file.' )
  parser.add_argument( '-images', default=None, #edit to accept file, or just computed
             help='Input directory for images.')
  parser.add_argument( '-script', default=None,
             help='The name of the scoring script.  Will not copy otherwise.')

  # Outputs
  parser.add_argument( '-output', default='exp',
             help='Output directory for expanded folders.')
  parser.add_argument( '-results', default='results',
             help='Results folder name, stored within output dir.')
  parser.add_argument( '-res_file', default='results.txt',
             help='Specify a human-readable results txt file.')
  parser.add_argument( '-res_csv', default='stats.csv',
             help='Specify the csv file with calculated statistics.')
  parser.add_argument( '-csv_by_file', default=None,
             help='If true, CSV files will be created per image, not combined to one file.')

  # Configs?
  #overlap
  #pixel overlap ratio stuff?
  #etc...

  args = parser.parse_args()

  if not args.truth:
    print( 'Error: truths file must be specified' )
    sys.exit( 0 )
  if not args.computed: #note the user could not do this, and instead create annotations manually
    print( 'Error: computed file must be specified' )
    print( '       manual addition of computed tracks not yet supported' )
    sys.exit( 0 )
  if not args.images:
    print( 'Error: images directory must be specified' )
    sys.exit( 0 )

  #if not args.script:
  #  print( 'Error: a running script must be specified' )
  #  sys.exit( 0 )
  if args.script and not os.path.exists(args.script): #can I raise an exception here?
    print( 'Error: specified script scoring file does not exist' )
    sys.exit( 0 )

  if os.path.exists(args.output):
    print( 'Warning: directory already exists and will be overwritten' )

  cwd = os.getcwd()

  args.truth    = utils.make_PurePath(    args.truth )
  args.computed = utils.make_PurePath( args.computed )
  args.images   = utils.make_PurePath(   args.images ) 
  args.output   = utils.make_PurePath(   args.output )
  args.script   = utils.make_PurePath(   args.script )
  args.results  = args.output / args.results
  #args.res_file = utils.make_PurePath( args.res_file )
  #args.res_csv  = utils.make_PurePath(  args.res_csv )

  #get the names of the images
  img_names = get_imgs( args.images )

  #create directory tree
  ###make_dir_tree( img_names, args.output )

  #copy over vital files
  ###copy_vitals( args )

  #create a new truth file for each image
  ###os.chdir(args.output)
  ###create_subtrack_files( img_names, args )
  ###move_subtrack_files(   img_names, args )

  #make the scripts
  ###exec_score.run_scripts(  img_names, args )
  ###os.chdir( '..' )

  get_results( img_names, args )

  print( 'Done\n' )
  #create a new computed file for each image
  #don't forget the "all" directory
