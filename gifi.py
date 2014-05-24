import os
import re
from multiprocessing import Pool
from collections import defaultdict
import tempfile
import logging
import zipfile
import logging
import subprocess
import time
import wrap7z


PATH_CONVERT = r'C:\Program Files\ImageMagick-6.8.4-Q16\convert.exe'


def work(files, out_file, delay):
    args = [PATH_CONVERT] + files + ['-deconstruct', '-delay', delay, out_file]
    outputs = subprocess.check_call(args)
    # remove all files
    for fname in files:
        os.remove(fname)


class Tube(object):
    def __init__(self, order_dict=None):
        self.order_dict = order_dict.copy() if order_dict else {}
        self._cnt = sum((0 if d else 1) for d in self.order_dict.values())

    def feed(self, order, fname):
        """return True if job done"""
        assert not self.order_dict[order]
        assert fname
        d = self.order_dict
        d[order] = fname
        self._cnt -= 1
        if self._cnt <= 0:
            return list(d[k] for k in sorted(d.keys()))
        return False

        
def scraper(input, pattern, extension='.png'):
    """split a file name into 3-things:
    a unique tag name, a order name, and file extension (for file naming)
    """
    m = re.match(pattern, input)
    if not m:
        return None
    d = m.groupdict()
    tag = d['tag']
    order = d['order']
    ext = d.get('ext', None) or extension
    return tag, order, ext

    
def write_file(fullname, data):
    path, fname = os.path.split(fullname)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(fullname, 'wb') as f:
        f.write(data)

    
def logic_general(zf, scrap, out_dir, processes=3, delay='1x24'):
    # 1: analyse files to get pics->gif mapping
    files = list(wrap7z.getfiles(zf))
    tubeds = {}
    for fname, fsize in files:
        ptn = scrap(fname)
        if not ptn:
            continue
        tag, order, ext = ptn
        if not tag in tubeds:
            tubeds[tag] = set()
        assert not order in tubeds[tag], 'oops, %s already in tag %s' % (order, tag)
        tubeds[tag].add(order)
    tubes = dict((k, Tube(dict((o, None) for o in s)))for k, s in tubeds.iteritems())
    # 2: start extracting files, notify each file complete
    pool = Pool(processes=processes)
    
    for fname, data in wrap7z.readzipped(zf, files):
        logging.debug('extracted %s', fname)
        ptn = scrap(fname)
        if not ptn:  # write to out dir directly
            write_file(os.path.join(out_dir, fname), data)
            continue
        tag, order, ext = ptn
        tf = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tfname = tf.name
        with tf:
            tf.write(data)
        result = tubes[tag].feed(order, tfname)
        if not result:
            continue

        if len(result) == 1:  # moved as-is
            outfname = tag + ext
            os.rename(tfname, os.path.join(out_dir, outfname))
        else:
            outfname = tag + '.mng'
            pool.apply_async(work, [result, os.path.join(out_dir, outfname), delay])
            #work(result, os.path.join(out_dir, outfname), delay)
        logging.info('tag %s fulfilled', tag)
        del tubes[tag]
    pool.close()
    pool.join()

    
def gifimain(src_archive, # source zip file
             dst_dir, # dst dir for result files
             ):
    """
    
    """
    

if __name__ == '__main__':
    tempfile.tempdir = r'F:\tmp\temp'
    logging.basicConfig(level=logging.DEBUG)
    scrap = lambda s: scraper(s, pattern=r'^.*(?P<tag>\w{5})(?P<order>\d{3})\.bmp$', extension='.bmp')
    src = r'F:\tmp\ev.7z'
    out = r'F:\tmp\out'
    logic_general(src, scrap, out, processes=3, delay='1x24')