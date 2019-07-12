########################################
#  Sage Sefton
#  Options for calculating IoU and the
#  relevant tables.  To calculate matches
#  over another IoU, 
#  Dynamic programming would possibly
#  be fastest here.
#  I converted to classes because it seems
#  to be much easier to deal with.
#  2019 07 09
########################################


#scipy
import scipy.sparse 
#custom
import modules.utils as utils


ERROR_MARGIN = 10 ** -10


class rect:
  def __init__( self ):
    self.llp = [0,0]
    self.urp = [0,0]
    self.ty  = None

  #def __len__(self):
  #  return len()

  def _debug_str( self ):
    str_  = 'Lower  Left: ' + str(self.llp[0]) + ', ' + str(self.llp[1]) + '\t'
    str_ += 'Upper Right: ' + str(self.urp[0]) + ', ' + str(self.urp[1])
    str_ += 'Ty: ' + self.ty
    return str_

  def _area( self ):
      dx = self.urp[0] - self.llp[0]
      dy = self.urp[1] - self.llp[1]
      return abs(dx * dy)

  

  def _in_rect( self, point, other ):
    """ Internal Function
      _overlap( point:list(2)
        rect_:list(4)
        ):bool
    """
    def _between( test, x1, x2 ):
      #WARNING: assumes x1<x2
      return ((x1 <= test) and (test <= x2)) #or \
       #(test > x1 and test < x2)

    return _between( point[0], other.llp[0], other.urp[0] ) and \
           _between( point[1], other.llp[1], other.urp[1] )

  def _get_corners_inside( self, other ):
    ret  = [ self._in_rect(  self.llp,                  other ), #bottom left
             self._in_rect( [self.llp[0], self.urp[1]], other ), #top left
             self._in_rect(  self.urp,                  other ), #top right
             self._in_rect( [self.urp[0], self.llp[1]], other )] #bottom right
    num = 0
    for i in ret:
      if i:
        num += 1
    return ret, num

  def _calc_iou( self, other ):
    """ Internal Function
      _calc_iou( rect_a:list(4*float)
             rect_b:list(4*float)
      ) :float
      Calculate the IOU (if any) and return it (or None)
    """
    box_i = rect()

    #Determine which corners are within rect_b, if any
    k, s = self._get_corners_inside(other)
    if s == 1:#point
      if   k == [1, 0, 0, 0]: #point - LL
        box_i.llp =  self.llp
        box_i.urp = other.urp
      elif k == [0, 1, 0, 0]: #point - UL
        box_i.llp = [ self.llp[0], other.llp[1]]
        box_i.urp = [other.urp[0],  self.urp[1]]
      elif k == [0, 0, 1, 0]: #point - UR
        box_i.llp = other.llp
        box_i.urp =  self.urp
      elif k == [0, 0, 0, 1]: #point - LR
        box_i.llp = [other.llp[0],  self.llp[1]]
        box_i.urp = [ self.urp[0], other.urp[1]]
      else:
        print("Mathematically impossible.")
        print("DEBUG: ", self._debug_str(), '\n', other._debug_str(), '\n', k, s)
        sys.exit(1)
    elif s == 2: #side
      if   k == [1, 1, 0, 0]: #side - LEFT
        box_i.llp = self.llp
        box_i.urp = [ other.urp[0],  self.urp[1] ]
      elif k == [0, 1, 1, 0]: #side - TOP
        box_i.llp = [  self.llp[0], other.llp[1] ] 
        box_i.urp = self.urp
      elif k == [0, 0, 1, 1]: #side - RIGHT
        box_i.llp = [ other.llp[0],  self.llp[1] ]
        box_i.urp = self.urp
      elif k == [1, 0, 0, 1]: #side - BOTTOM
        box_i.llp = self.llp
        box_i.urp = [  self.urp[0], other.urp[1] ]
      else:
        print("Mathematically impossible.")
        print("DEBUG: ", self._debug_str(), '\n', other._debug_str(), '\n', k, s)
        sys.exit(1)
    elif s == 4: #inside
      box_i = self
    elif s == 0: #outside
      k2, s2 = self._get_corners_inside(other)
      if s2 == 2: #bump (side of b in a)
        if   k2 == [0, 0, 1, 1]: #along left side
          box_i.llp = [  self.llp[0], other.llp[1] ]
          box_i.urp = other.urp
        elif k2 == [1, 0, 0, 1]: #along top side
          box_i.llp = other.llp
          box_i.urp = [ other.urp[0],  self.urp[1] ]
        elif k2 == [1, 1, 0, 0]: #along right side
          box_i.llp = other.llp
          box_i.urp = [  self.urp[0], other.urp[1] ] 
        elif k2 == [0, 1, 1, 0]: #along bottom side
          box_i.llp = [ other.llp[0],  self.llp[1] ]
          box_i.urp = other.urp
      elif s2 == 4: #encompass
        box_i = other
      else:
        return None
    else:
      print("Mathematically impossible.")
      print("DEBUG: ", self._debug_str(), '\n', other._debug_str(), '\n', k, s)
      sys.exit(1) #failure
    #calculate areas
    area_a =  self._area()
    area_b = other._area()
    area_i = box_i._area()
    area_u = area_a + area_b - area_i
    return float(area_i / area_u)


class IoU_table:
  def __init__( self, ntrue=None, ncomp=None):
    
    #files
    self.comp_file = ncomp
    self.true_file = ntrue

    #annotation data
    self.comp_rects = [] #[(rect(), conf)]
    self.true_rects = [] #[rect()]
    self.table = []

  def _get_rects( self ):
    with open(self.true_file) as t:
      for i in t:
        i = i.split(',')
        tmp = rect()
        tmp.llp = [ float(i[3]), float(i[4]) ]
        tmp.urp = [ float(i[5]), float(i[6]) ]
        tmp.ty  =   str(i[9])
        self.true_rects += [ tmp ]
    with open(self.comp_file) as c:
      for i in c:
        i = i.split(',')
        tmp = rect()
        tmp.llp = [ float(i[3]), float(i[4]) ] 
        tmp.urp = [ float(i[5]), float(i[6]) ]
        tmp.ty  =   str(i[9])
        c_conf  =   float(i[10])
        self.comp_rects += [ (tmp, c_conf) ]

  def _make_table( self ):
    self._get_rects()
    print(self.true_rects)
    self.table = scipy.sparse.lil_matrix( (len(self.true_rects), len(self.comp_rects)) )
    print(len(self.true_rects), ':', len(self.comp_rects))
    for t_idx in range(len(self.true_rects)):
      for c_idx in range(len(self.comp_rects)):
        iou = self.true_rects[t_idx-1]._calc_iou( self.comp_rects[c_idx-1][0] )
        if iou and iou > ERROR_MARGIN:
          self.table[ t_idx-1, c_idx-1 ] = iou
    return None

  def set_comp( self, ncomp ):
    self.comp_file = ncomp
  def set_true( self, ntrue ):
    self.true_file = ntrue

  def run( self ):
    self._make_table()
    print(self.table)
    return self.table

