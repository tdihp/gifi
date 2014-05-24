import subprocess
import sys
import re
import locale
import logging

KW_PATTERN = re.compile(r'^(?P<key>\w+) = (?P<val>.*)$')
SYSENCODING = locale.getpreferredencoding()
PATH_7Z = r'C:\Program Files\7-Zip\7z.exe'

def kwgen(lines):
    kw = {}
    for line in lines:
        if line == '':
            yield kw
            kw = {}
            continue
        m = KW_PATTERN.match(line)
        if not m:
            continue
        d = m.groupdict()
        kw[d['key']] = d['val']
    yield kw

    
def getfiles(zf):
    """yields file name and file size"""
    # print repr(zf)
    # outputs = subprocess.Popen([PATH_7Z, 'l', '-slt', zf.encode(SYSENCODING)],
    outputs = subprocess.Popen([PATH_7Z, 'l', '-slt', zf.encode(sys.getfilesystemencoding())],
                               stdout=subprocess.PIPE,)
    files = []
    flist = outputs.stdout.read()
    flist = flist.decode(SYSENCODING)
    for kw in kwgen(flist.splitlines()):
        try:
            path = kw['Path']
            attributes = kw['Attributes']
            size = kw['Size']
        except KeyError as e:
            logging.debug('skipping kw %s for %s', kw, e)
            continue
        size = int(size)
        if attributes != '....A':
            
            if size == 0:
                logging.debug('skipping %s for not archive (%s)', path, attributes)
                continue
            else:
                logging.info('adding %s but no archive (%s)', path, attributes)

        logging.info('adding %s, %s', path, size)
        files.append((path, int(size)))
    return files
    
    
def readzipped(zf, files):
    """ yields (path, data) """
    outputs = subprocess.Popen([PATH_7Z, 'x', '-so', zf.encode(sys.getfilesystemencoding())],
                               stdout=subprocess.PIPE)
    for path, size in files:
        data = outputs.stdout.read(size)
        assert len(data) == size
        yield path, data
    assert outputs.stdout.read() == ''