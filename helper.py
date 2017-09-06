import sys
import linecache
import math

def get_distance_in_meters(lat1, lat2, lon1, lon2):
    """
    Расстояние между 2 точками Земли в метрах.
    """
    radius = 6371000
    fi1 = math.radians(lat1)
    fi2 = math.radians(lat2)
    delta_fi = math.radians(lat1 - lat2)
    delta_si = math.radians(lon1 - lon2)
    a = math.sin(delta_fi / 2) ** 2 + math.cos(fi1) * math.cos(fi2) * (math.sin(delta_si / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c
    return round(d)

def insert_4_spaces(card):
    res = ''
    index = 0
    for c in card:
        res += c
        index += 1
        if index in [4, 8, 12]:
            res += ' '

    return res

def insert_5_spaces_onai(onai):
    res = ''
    index = 0
    for c in onai:
        res += c
        index += 1
        if index in [4, 6, 11, 15]:
            res += ' '
    return res

def isAllDigits(card):
    for c in card:
        try:
            a = int(c)
        except:
            return False

    return True

def PrintException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION IN ({}, LINE {} "{}"): {}'.format(filename, lineno, line.strip(), exc_obj)
